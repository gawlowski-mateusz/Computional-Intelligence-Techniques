"""Comparative study of selection, crossover and mutation methods (Task 2).

Stage 1 (screening): full factorial grid of methods and their parameters, every configuration
         run RUNS times (seeds 0..RUNS-1).
Stage 2 (validation): the best configurations from stage 1, the best configuration of every
         method and the Task 1 baseline are re-run VALIDATION_RUNS times on new seeds
         (1000, 1001, ...), so the final choice is not biased by the lucky seeds of stage 1.
Stage 3 (budget): the winning configuration with a different population size and the same
         number of fitness evaluations.

Results are written to results/ (CSV, Markdown tables, PNG figures).

Usage: python experiments.py
"""

import csv
import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import mannwhitneyu

from ga import DietProblem, GAConfig, describe, exact_optimum, run_ga

POP_SIZE = 20
GENERATIONS = 300
RUNS = 30
VALIDATION_RUNS = 100
VALIDATION_SEED0 = 1000
TOP_VALIDATED = 10

# Stage 1 grid: (selection, its parameters) x elite size x (crossover, p_c) x (mutation, p_m)
SELECTIONS = [("tournament", {"tournament_size": k}) for k in (2, 3, 5)] + \
             [("roulette", {})] + \
             [("ranking", {"ranking_pressure": s}) for s in (1.5, 2.0)]
ELITE_SIZES = [0, 1, 2, 5]
CROSSOVERS = ["one_point", "two_point", "uniform"]
P_CROSSOVER = [0.6, 0.8, 1.0]
MUTATION_RATES = {
    "reset": [0.02, 0.05, 0.1, 0.2],      # per gene
    "creep": [0.02, 0.05, 0.1, 0.2],      # per gene
    "inversion": [0.2, 0.5, 0.8, 1.0],    # per chromosome
}
BASELINE = dict(selection="tournament", tournament_size=3, elite_size=0, crossover="one_point",
                p_crossover=0.8, mutation="reset", p_mutation=0.05)  # Task 1 configuration
BUDGET = [(10, 600), (20, 300), (50, 120), (100, 60)]  # (N, generations), ~6000 evaluations each

SELECTION_PL = {"tournament": "turniej", "roulette": "ruletka", "ranking": "ranking"}
CROSSOVER_PL = {"one_point": "jednopunktowe", "two_point": "dwupunktowe", "uniform": "równomierne"}
MUTATION_PL = {"reset": "reset", "creep": "±1 (creep)", "inversion": "inwersja"}

OUT = Path(__file__).parent / "results"
PROBLEM = DietProblem()

# Reference palette (categorical slots in fixed order, sequential blue ramp)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
TEXT, TEXT_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT_2, "xtick.color": TEXT_2, "ytick.color": TEXT_2,
    "text.color": TEXT, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold", "legend.frameon": False,
})


# --- Configurations ---------------------------------------------------------------------------

def selection_label(c):
    if c["selection"] == "tournament":
        return f"turniej k={c['tournament_size']}"
    if c["selection"] == "ranking":
        return f"ranking s={c['ranking_pressure']}"
    return "ruletka"


def label(c):
    return (f"{selection_label(c)} | elita {c['elite_size']} | "
            f"{CROSSOVER_PL[c['crossover']]} p_c={c['p_crossover']} | "
            f"{MUTATION_PL[c['mutation']]} p_m={c['p_mutation']}")


def grid_configs():
    configs = []
    for (sel, sel_params), elite, cx, pc in itertools.product(SELECTIONS, ELITE_SIZES, CROSSOVERS,
                                                              P_CROSSOVER):
        for mut, rates in MUTATION_RATES.items():
            for pm in rates:
                c = dict(selection=sel, tournament_size=3, ranking_pressure=1.5, elite_size=elite,
                         crossover=cx, p_crossover=pc, mutation=mut, p_mutation=pm)
                c.update(sel_params)
                configs.append(c)
    return configs


def config_key(c):
    return tuple(sorted(c.items()))


# --- Running ----------------------------------------------------------------------------------

def to_objective(fitness):
    """Inverse of F = 1 / (1 + objective): penalised cost in PLN (lower is better)."""
    return 1.0 / np.asarray(fitness) - 1.0


def run_config(job):
    """Worker: run one configuration for the given seeds, return per-run results and mean curves."""
    c, seeds, optimum_cost, pop_size, generations = job
    runs, best, mean, unique = [], [], [], []
    for seed in seeds:
        res = run_ga(PROBLEM, GAConfig(pop_size=pop_size, generations=generations, seed=seed, **c))
        x = res.best_chromosome
        feasible = bool(PROBLEM.is_feasible(x))
        runs.append({
            "seed": seed, "objective": round(float(PROBLEM.objective(x)), 4),
            "cost": round(float(PROBLEM.cost(x)), 2), "feasible": feasible,
            "optimal": feasible and abs(PROBLEM.cost(x) - optimum_cost) < 1e-6,
            "best_generation": res.best_generation, "chromosome": " ".join(map(str, x)),
        })
        best.append(to_objective(res.history_best_so_far))
        mean.append(to_objective(res.history_mean))
        unique.append(res.history_unique)
    return runs, np.mean(best, axis=0), np.median(mean, axis=0), np.mean(unique, axis=0)


def run_many(configs, seeds, optimum_cost, pop_size=POP_SIZE, generations=GENERATIONS):
    jobs = [(c, seeds, optimum_cost, pop_size, generations) for c in configs]
    with ProcessPoolExecutor() as ex:
        return list(ex.map(run_config, jobs, chunksize=4))


def summarize(c, runs, optimum_cost):
    obj = np.array([r["objective"] for r in runs])
    s = dict(c)
    s.update({
        "label": label(c), "runs": len(runs),
        "obj_mean": obj.mean(), "obj_std": obj.std(ddof=1), "obj_median": np.median(obj),
        "obj_min": obj.min(), "obj_max": obj.max(),
        "gap_mean_pct": 100 * (obj.mean() - optimum_cost) / optimum_cost,
        "feasible_rate": np.mean([r["feasible"] for r in runs]),
        "optimal_rate": np.mean([r["optimal"] for r in runs]),
        "best_gen_mean": np.mean([r["best_generation"] for r in runs]),
    })
    return s


# --- Output helpers ---------------------------------------------------------------------------

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def markdown_table(summaries, first_col="konfiguracja", first=lambda s: s["label"]):
    lines = [f"| {first_col} | śr. f [zł] | odch. std | mediana | min | max | luka do opt. | "
             "dopuszczalne | trafienia opt. | śr. pokolenie best |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        lines.append(
            f"| {first(s)} | {s['obj_mean']:.2f} | {s['obj_std']:.2f} | {s['obj_median']:.2f} | "
            f"{s['obj_min']:.2f} | {s['obj_max']:.2f} | {s['gap_mean_pct']:.1f}% | "
            f"{s['feasible_rate'] * 100:.0f}% | {s['optimal_rate'] * 100:.0f}% | "
            f"{s['best_gen_mean']:.0f} |")
    return "\n".join(lines)


def factor_table(summaries, factor_name, key, levels, level_name):
    """Grid average and best configuration for every level of one factor."""
    lines = [f"| {factor_name} | średnia danej metody [zł] | najlepsza konfiguracja: śr. f [zł] | "
             "trafienia opt. | najlepsza konfiguracja |", "|---|---|---|---|---|"]
    for level in levels:
        group = [s for s in summaries if key(s) == level]
        best = min(group, key=lambda s: s["obj_mean"])
        lines.append(f"| {level_name(level)} | {np.mean([s['obj_mean'] for s in group]):.2f} | "
                     f"{best['obj_mean']:.2f} | {best['optimal_rate'] * 100:.0f}% | {best['label']} |")
    return "\n".join(lines)


def heatmap(ax, grid, row_labels, col_labels, title, vmin, vmax):
    """Annotated heatmap; panels compared side by side share vmin / vmax (one colour scale)."""
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
    im = ax.imshow(grid, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    ax.grid(False)
    ax.set_xticks(range(len(col_labels)), col_labels)
    ax.set_yticks(range(len(row_labels)), row_labels)
    ax.set_title(title, loc="left", fontsize=10)
    threshold = vmin + 0.55 * (vmax - vmin)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=9,
                    color="white" if grid[i, j] > threshold else TEXT)
    return im


def heatmap_pair(avg, best, rows, cols, xlabel, title, name, figsize):
    """Grid average (left) and best configuration (right) on one shared colour scale."""
    vmin, vmax = min(avg.min(), best.min()), max(avg.max(), best.max())
    fig, axes = plt.subplots(1, 2, figsize=figsize, layout="constrained")
    heatmap(axes[0], avg, rows, cols, "średnia danej metody [zł]", vmin, vmax)
    im = heatmap(axes[1], best, rows, cols, "najlepsza konfiguracja: śr. f [zł]", vmin, vmax)
    axes[1].tick_params(labelleft=False)  # same rows as the left panel
    for ax in axes:
        ax.set_xlabel(xlabel)
    cbar = fig.colorbar(im, ax=axes, shrink=0.9)
    cbar.outline.set_visible(False)
    cbar.set_label("zł (mniej = lepiej)", color=TEXT_2)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold")
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


def optimum_line(ax, optimum_cost, x):
    ax.axhline(optimum_cost, color=TEXT_2, linewidth=1, linestyle="--")
    ax.text(x, optimum_cost, f"optimum {optimum_cost:.2f} zł", color=TEXT_2, ha="right",
            va="bottom", fontsize=8)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


# --- Figures ----------------------------------------------------------------------------------

def plot_main_effects(summaries, optimum_cost):
    factors = [
        ("selekcja", selection_label, [selection_label(dict(selection=s, **p)) for s, p in SELECTIONS]),
        ("elitaryzm", lambda s: f"e={s['elite_size']}", [f"e={e}" for e in ELITE_SIZES]),
        ("krzyżowanie", lambda s: CROSSOVER_PL[s["crossover"]], list(CROSSOVER_PL.values())),
        ("mutacja", lambda s: MUTATION_PL[s["mutation"]], list(MUTATION_PL.values())),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.8), sharey=True,
                             gridspec_kw={"width_ratios": [6, 4, 3, 3]})
    for ax, (name, key, levels) in zip(axes, factors):
        avg = [np.mean([s["obj_mean"] for s in summaries if key(s) == lv]) for lv in levels]
        best = [min(s["obj_mean"] for s in summaries if key(s) == lv) for lv in levels]
        x = np.arange(len(levels))
        ax.scatter(x, avg, color=SERIES[0], marker="s", s=40, zorder=3, label="średnia danej metody")
        ax.scatter(x, best, color=SERIES[1], s=40, zorder=3, label="najlepsza konfiguracja")
        optimum_line(ax, optimum_cost, len(levels) - 0.6)
        ax.set_xticks(x, levels, rotation=30, ha="right")
        ax.set_xlim(-0.6, len(levels) - 0.4)
        ax.set_title(name, loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("śr. f. celu najlepszego osobnika [zł]")
    axes[0].set_ylim(optimum_cost - 0.3, 11.6)
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle(f"Efekty główne (etap 1: {len(summaries)} konfiguracji × {RUNS} uruchomień)",
                 x=0.01, ha="left", fontweight="bold")
    save(fig, "main_effects.png")


def plot_selection_elitism(summaries):
    sel_levels = [selection_label(dict(selection=s, **p)) for s, p in SELECTIONS]
    best = np.array([[min(s["obj_mean"] for s in summaries
                          if selection_label(s) == sl and s["elite_size"] == e)
                      for e in ELITE_SIZES] for sl in sel_levels])
    avg = np.array([[np.mean([s["obj_mean"] for s in summaries
                              if selection_label(s) == sl and s["elite_size"] == e])
                     for e in ELITE_SIZES] for sl in sel_levels])
    heatmap_pair(avg, best, sel_levels, [f"e = {e}" for e in ELITE_SIZES],
                 "liczba osobników elitarnych", "Selekcja × elitaryzm", "selection_elitism.png",
                 (11, 3.8))


def plot_mutation_rates(summaries, optimum_cost):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, (mut, rates) in zip(axes, MUTATION_RATES.items()):
        for e, color in zip(ELITE_SIZES, SERIES):
            ys = [np.mean([s["obj_mean"] for s in summaries if s["mutation"] == mut
                           and s["p_mutation"] == pm and s["elite_size"] == e]) for pm in rates]
            ax.plot(range(len(rates)), ys, marker="o", color=color, linewidth=2, label=f"elita e = {e}")
        ax.set_xticks(range(len(rates)), [str(r) for r in rates])
        ax.set_xlabel("p_m na chromosom" if mut == "inversion" else "p_m na gen")
        ax.set_title(f"mutacja: {MUTATION_PL[mut]}", loc="left")
    axes[0].set_ylabel("śr. f [zł] (średnia po selekcji i krzyżowaniu)")
    axes[0].legend(fontsize=8)
    save(fig, "mutation_rates.png")


def plot_crossover(summaries):
    best = np.array([[min(s["obj_mean"] for s in summaries
                          if s["crossover"] == cx and s["p_crossover"] == pc and s["elite_size"] > 0)
                      for pc in P_CROSSOVER] for cx in CROSSOVERS])
    avg = np.array([[np.mean([s["obj_mean"] for s in summaries
                              if s["crossover"] == cx and s["p_crossover"] == pc and s["elite_size"] > 0])
                     for pc in P_CROSSOVER] for cx in CROSSOVERS])
    heatmap_pair(avg, best, [CROSSOVER_PL[c] for c in CROSSOVERS], [f"p_c = {p}" for p in P_CROSSOVER],
                 "prawdopodobieństwo krzyżowania", "Krzyżowanie × p_c (konfiguracje z elitaryzmem)",
                 "crossover.png", (10, 3))


def plot_validation_box(validated, results):
    order = sorted(range(len(validated)), key=lambda i: validated[i]["obj_mean"])
    data = [[r["objective"] for r in results[i][0]] for i in order]
    names = [f"#{rank + 1}  {validated[i]['label']}" for rank, i in enumerate(order)]
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(order) + 1.4))
    box = ax.boxplot(data[::-1], vert=False, widths=0.6, patch_artist=True,
                     medianprops={"color": SERIES[1], "linewidth": 2},
                     flierprops={"marker": "o", "markersize": 3, "markerfacecolor": TEXT_2,
                                 "markeredgecolor": "none"})
    for patch in box["boxes"]:
        patch.set(facecolor="#cde2fb", edgecolor=SERIES[0])
    ax.scatter([np.mean(d) for d in data[::-1]], range(1, len(data) + 1), color=TEXT, s=14, zorder=3,
               label="średnia")
    ax.set_yticks(range(1, len(names) + 1), names[::-1], fontsize=8)
    ax.set_xlabel("f. celu najlepszego osobnika [zł]")
    ax.set_title(f"Walidacja: {VALIDATION_RUNS} uruchomień na nowych ziarnach", loc="left")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, "validation_boxplot.png")


def plot_final_curves(curves, labels, optimum_cost):
    best_curves, mean_curves, unique_curves = zip(*curves)
    gens = np.arange(GENERATIONS + 1)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for b, m, u, lab, color in zip(best_curves, mean_curves, unique_curves, labels, SERIES):
        axes[0].plot(gens, b, color=color, linewidth=2, label=lab)
        axes[1].plot(gens, m, color=color, linewidth=2)
        axes[2].plot(gens, u, color=color, linewidth=2)
    for ax in axes[:2]:
        optimum_line(ax, optimum_cost, GENERATIONS)
    axes[0].set_ylim(optimum_cost - 0.5, 20)
    axes[1].set_ylim(0, 80)
    axes[2].set_ylim(0, 1.05)
    axes[0].set_title("najlepszy dotychczas [zł] (średnia)", loc="left")
    axes[1].set_title("średnia populacji [zł] (mediana)", loc="left")
    axes[2].set_title("odsetek unikalnych osobników", loc="left")
    for ax in axes:
        ax.set_xlim(0, GENERATIONS)
        ax.set_xlabel("pokolenie")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncols=2, fontsize=8)
    fig.suptitle(f"Przebieg algorytmu ({VALIDATION_RUNS} uruchomień walidacyjnych)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0.06 * ((len(labels) + 1) // 2), 1, 1))
    fig.savefig(OUT / "final_convergence.png", dpi=150)
    plt.close(fig)


def plot_budget(budget_summaries, curves, optimum_cost):
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for (n, g), curve, color in zip(BUDGET, curves, SERIES):
        evals = n * (np.arange(g + 1) + 1)
        ax.plot(evals, curve, color=color, linewidth=2, label=f"N = {n}, {g} pokoleń")
    optimum_line(ax, optimum_cost, max(n * (g + 1) for n, g in BUDGET))
    ax.set_ylim(optimum_cost - 0.5, 20)
    ax.set_xlabel("liczba ocen funkcji przystosowania")
    ax.set_ylabel("najlepszy dotychczas [zł] (średnia)")
    ax.set_title("Rozmiar populacji przy stałym budżecie obliczeń", loc="left")
    ax.legend()
    save(fig, "budget.png")


# --- Main -------------------------------------------------------------------------------------

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    optimum = exact_optimum(PROBLEM)
    optimum_cost = float(PROBLEM.cost(optimum))
    print(f"Optimum referencyjne (ILP): {optimum_cost:.2f} zł")

    # --- Stage 1: screening ------------------------------------------------------------------
    configs = grid_configs()
    print(f"Etap 1: {len(configs)} konfiguracji × {RUNS} uruchomień ...")
    results = run_many(configs, list(range(RUNS)), optimum_cost)
    screening = [summarize(c, r[0], optimum_cost) for c, r in zip(configs, results)]
    write_csv(OUT / "screening.csv", screening)
    ranked = sorted(screening, key=lambda s: (s["obj_mean"], -s["optimal_rate"]))
    print(markdown_table(ranked[:5]))

    # --- Stage 2: validation -----------------------------------------------------------------
    def best_where(pred):
        return min((s for s in screening if pred(s)), key=lambda s: s["obj_mean"])

    candidates = ranked[:TOP_VALIDATED]
    candidates += [best_where(lambda s, sel=sel: s["selection"] == sel and (s["elite_size"] > 0) == el)
                   for sel in SELECTION_PL for el in (False, True)]
    candidates += [best_where(lambda s, cx=cx: s["crossover"] == cx) for cx in CROSSOVERS]
    candidates += [best_where(lambda s, m=m: s["mutation"] == m) for m in MUTATION_RATES]
    baseline = dict(BASELINE, ranking_pressure=1.5)
    validated_cfgs, seen = [], set()
    for c in [baseline] + [{k: s[k] for k in baseline} for s in candidates]:
        if config_key(c) not in seen:
            seen.add(config_key(c))
            validated_cfgs.append(c)
    print(f"\nEtap 2: walidacja {len(validated_cfgs)} konfiguracji × {VALIDATION_RUNS} uruchomień ...")
    val_seeds = list(range(VALIDATION_SEED0, VALIDATION_SEED0 + VALIDATION_RUNS))
    val_results = run_many(validated_cfgs, val_seeds, optimum_cost)
    validated = [summarize(c, r[0], optimum_cost) for c, r in zip(validated_cfgs, val_results)]
    for s in validated:
        s["screening_obj_mean"] = next(x["obj_mean"] for x in screening
                                       if config_key({k: x[k] for k in baseline}) == config_key(
                                           {k: s[k] for k in baseline}))
    win_i = min(range(len(validated)),
                key=lambda i: (validated[i]["obj_mean"], -validated[i]["optimal_rate"]))
    winner = validated[win_i]
    win_obj = [r["objective"] for r in val_results[win_i][0]]
    for s, r in zip(validated, val_results):
        other = [x["objective"] for x in r[0]]
        s["p_value_vs_winner"] = (float("nan") if s is winner else
                                  mannwhitneyu(win_obj, other, alternative="less").pvalue)
    validated_sorted = sorted(validated, key=lambda s: s["obj_mean"])
    write_csv(OUT / "validation.csv", validated_sorted)
    write_csv(OUT / "validation_runs.csv",
              [dict(label=s["label"], **run) for s, r in zip(validated, val_results) for run in r[0]])
    print(markdown_table(validated_sorted))

    # --- Stage 3: population size at a fixed budget -------------------------------------------
    win_cfg = {k: winner[k] for k in baseline}
    budget_summaries, budget_curves = [], []
    for n, g in BUDGET:
        r = run_many([win_cfg], val_seeds, optimum_cost, pop_size=n, generations=g)[0]
        s = summarize(win_cfg, r[0], optimum_cost)
        s["label"] = f"N = {n}, {g} pokoleń"
        budget_summaries.append(s)
        budget_curves.append(r[1])

    # --- Report ------------------------------------------------------------------------------
    sel_levels = [selection_label(dict(selection=s, **p)) for s, p in SELECTIONS]
    by_label = {s["label"]: (s, r) for s, r in zip(validated, val_results)}
    baseline_s = by_label[label(baseline)][0]
    best_run = min(by_label[winner["label"]][1][0], key=lambda r: r["objective"])
    best_x = np.array(list(map(int, best_run["chromosome"].split())))
    sel_rows = []
    for sel in SELECTION_PL:
        for el in (False, True):
            s = min((v for v in validated if v["selection"] == sel and (v["elite_size"] > 0) == el),
                    key=lambda v: v["obj_mean"])
            sel_rows.append(s)

    report = [
        "# Wyniki eksperymentów (zadanie 2)\n",
        f"Optimum referencyjne (ILP): **{optimum_cost:.2f} zł**. Wszystkie konfiguracje: "
        f"N = {POP_SIZE}, {GENERATIONS} pokoleń.\n",
        f"## Etap 1: przegląd siatki ({len(screening)} konfiguracji × {RUNS} uruchomień)\n",
        "### Selekcja\n",
        factor_table(screening, "selekcja", selection_label, sel_levels, str), "",
        "### Elitaryzm\n",
        factor_table(screening, "elita", lambda s: s["elite_size"], ELITE_SIZES, lambda e: f"e = {e}"), "",
        "### Krzyżowanie\n",
        factor_table(screening, "krzyżowanie", lambda s: s["crossover"], CROSSOVERS, CROSSOVER_PL.get), "",
        "### Prawdopodobieństwo krzyżowania\n",
        factor_table(screening, "p_c", lambda s: s["p_crossover"], P_CROSSOVER, str), "",
        "### Mutacja\n",
        factor_table(screening, "mutacja", lambda s: s["mutation"], list(MUTATION_RATES), MUTATION_PL.get), "",
        "### Mutacja × prawdopodobieństwo\n",
        factor_table(screening, "mutacja, p_m", lambda s: (s["mutation"], s["p_mutation"]),
                     [(m, p) for m, rates in MUTATION_RATES.items() for p in rates],
                     lambda mp: f"{MUTATION_PL[mp[0]]}, {mp[1]}"), "",
        "### Ranking: 20 najlepszych konfiguracji\n", markdown_table(ranked[:20]), "",
        "### 5 najgorszych konfiguracji\n", markdown_table(ranked[-5:]), "",
        f"## Etap 2: walidacja ({VALIDATION_RUNS} uruchomień, ziarna {val_seeds[0]}–{val_seeds[-1]})\n",
        "Kandydaci: 10 najlepszych konfiguracji z etapu 1, najlepsza konfiguracja każdej metody "
        "selekcji (bez i z elitaryzmem), krzyżowania i mutacji oraz konfiguracja z zadania 1. "
        "Kolumna *p* to wynik jednostronnego testu Manna–Whitneya „zwycięzca daje mniejsze f”.\n",
        "| # | konfiguracja | śr. f [zł] (etap 1) | śr. f [zł] | odch. std | mediana | min | max | "
        "dopuszczalne | trafienia opt. | p |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(validated_sorted, 1):
        p = "—" if s is winner else f"{s['p_value_vs_winner']:.3g}"
        report.append(f"| {i} | {s['label']} | {s['screening_obj_mean']:.2f} | {s['obj_mean']:.2f} | "
                      f"{s['obj_std']:.2f} | {s['obj_median']:.2f} | {s['obj_min']:.2f} | "
                      f"{s['obj_max']:.2f} | {s['feasible_rate'] * 100:.0f}% | "
                      f"{s['optimal_rate'] * 100:.0f}% | {p} |")
    report += [
        "", "### Najlepsza konfiguracja każdej metody selekcji (walidacja)\n",
        markdown_table(sel_rows), "",
        f"## Etap 3: rozmiar populacji przy stałym budżecie (zwycięska konfiguracja, "
        f"{VALIDATION_RUNS} uruchomień)\n",
        markdown_table(budget_summaries, "N, pokolenia"), "",
        "## Zwycięska konfiguracja\n",
        f"**{winner['label']}**\n",
        f"- średnia f: {winner['obj_mean']:.2f} zł (zadanie 1: {baseline_s['obj_mean']:.2f} zł)",
        f"- trafienia optimum: {winner['optimal_rate'] * 100:.0f}% "
        f"(zadanie 1: {baseline_s['optimal_rate'] * 100:.0f}%)\n",
        f"Najlepsze rozwiązanie (ziarno {best_run['seed']}):\n", "```", describe(PROBLEM, best_x), "```", "",
        "## Rozwiązanie optymalne (ILP)\n", "```", describe(PROBLEM, optimum), "```",
    ]
    (OUT / "summary.md").write_text("\n".join(report), encoding="utf-8")

    plot_main_effects(screening, optimum_cost)
    plot_selection_elitism(screening)
    plot_mutation_rates(screening, optimum_cost)
    plot_crossover(screening)
    plot_validation_box(validated, val_results)
    final = [baseline_s] + [s for s in sel_rows if s["elite_size"] > 0]
    final = list({s["label"]: s for s in [winner] + final}.values())[:6]
    plot_final_curves([by_label[s["label"]][1][1:] for s in final],
                      [("zadanie 1: " if s is baseline_s else "") + s["label"] for s in final],
                      optimum_cost)
    plot_budget(budget_summaries, budget_curves, optimum_cost)
    print(f"\nZwycięzca: {winner['label']}  (śr. f = {winner['obj_mean']:.2f} zł)")
    print(f"Wyniki zapisane w {OUT}")


if __name__ == "__main__":
    main()
