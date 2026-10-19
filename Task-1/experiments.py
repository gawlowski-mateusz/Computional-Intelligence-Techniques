"""Comparative study of the GA parameters (crossover / mutation probability, population size).

Every configuration is run RUNS times (seeds 0..RUNS-1) on the same dataset.
Results are written to results/ (CSV, Markdown tables, PNG figures).

Usage: python experiments.py
"""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ga import DietProblem, GAConfig, describe, exact_optimum, run_ga

RUNS = 10
POP_SIZE = 20
GENERATIONS = 300
TOURNAMENT = 3
P_CROSSOVER = [0.0, 0.3, 0.6, 0.8, 1.0]
P_MUTATION = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2]
POP_SIZES = [10, 20, 50, 100]
BASE_PC, BASE_PM = 0.8, 0.05

OUT = Path(__file__).parent / "results"

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


def to_objective(fitness):
    """Inverse of F = 1 / (1 + objective): penalised cost in PLN (lower is better)."""
    return 1.0 / np.asarray(fitness) - 1.0


def run_config(problem, optimum_cost, pop_size, pc, pm):
    rows, curves_best, curves_mean = [], [], []
    for seed in range(RUNS):
        cfg = GAConfig(pop_size=pop_size, generations=GENERATIONS, p_crossover=pc,
                       p_mutation=pm, tournament_size=TOURNAMENT, seed=seed)
        res = run_ga(problem, cfg)
        x = res.best_chromosome
        obj = float(problem.objective(x))
        rows.append({
            "pop_size": pop_size, "p_crossover": pc, "p_mutation": pm, "seed": seed,
            "objective": round(obj, 4), "cost": round(float(problem.cost(x)), 2),
            "violation": round(float(problem.violation(x)), 5),
            "feasible": bool(problem.is_feasible(x)),
            "optimal": bool(problem.is_feasible(x) and abs(problem.cost(x) - optimum_cost) < 1e-6),
            "best_generation": res.best_generation,
            "chromosome": " ".join(map(str, x)),
        })
        curves_best.append(to_objective(res.history_best_so_far))
        curves_mean.append(to_objective(res.history_mean))
    return rows, np.mean(curves_best, axis=0), np.mean(curves_mean, axis=0)


def summarize(rows, optimum_cost):
    obj = np.array([r["objective"] for r in rows])
    feas = np.array([r["feasible"] for r in rows])
    feas_cost = np.array([r["cost"] for r in rows if r["feasible"]])
    return {
        "pop_size": rows[0]["pop_size"], "p_crossover": rows[0]["p_crossover"],
        "p_mutation": rows[0]["p_mutation"],
        "obj_mean": obj.mean(), "obj_std": obj.std(ddof=1), "obj_min": obj.min(), "obj_max": obj.max(),
        "gap_mean_pct": 100 * (obj.mean() - optimum_cost) / optimum_cost,
        "feasible_rate": feas.mean(),
        "feasible_cost_mean": feas_cost.mean() if len(feas_cost) else float("nan"),
        "optimal_hits": int(sum(r["optimal"] for r in rows)),
        "best_gen_mean": np.mean([r["best_generation"] for r in rows]),
    }


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def markdown_table(summaries):
    head = ("| N | p_c | p_m | śr. f. celu [zł] | odch. std | min | max | luka do opt. | "
            "dopuszczalne | trafienia opt. | śr. pokolenie best |")
    lines = [head, "|" + "---|" * 11]
    for s in summaries:
        lines.append(
            f"| {s['pop_size']} | {s['p_crossover']} | {s['p_mutation']} | {s['obj_mean']:.2f} | "
            f"{s['obj_std']:.2f} | {s['obj_min']:.2f} | {s['obj_max']:.2f} | {s['gap_mean_pct']:.1f}% | "
            f"{s['feasible_rate'] * 100:.0f}% | {s['optimal_hits']}/{RUNS} | {s['best_gen_mean']:.0f} |")
    return "\n".join(lines)


def plot_heatmap(summaries, optimum_cost, path):
    grid = np.array([[next(s["obj_mean"] for s in summaries
                           if s["p_crossover"] == pc and s["p_mutation"] == pm)
                      for pm in P_MUTATION] for pc in P_CROSSOVER])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    im = ax.imshow(grid, cmap=cmap, aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(P_MUTATION)), [str(p) for p in P_MUTATION])
    ax.set_yticks(range(len(P_CROSSOVER)), [str(p) for p in P_CROSSOVER])
    ax.set_xlabel("prawdopodobieństwo mutacji p_m")
    ax.set_ylabel("prawdopodobieństwo krzyżowania p_c")
    ax.set_title(f"Średnia wartość funkcji celu najlepszego osobnika [zł]\n"
                 f"N = {POP_SIZE}, {RUNS} uruchomień, optimum = {optimum_cost:.2f} zł",
                 loc="left", fontsize=10)
    threshold = grid.min() + 0.55 * (grid.max() - grid.min())
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=9,
                    color="white" if grid[i, j] > threshold else TEXT)
    cbar = fig.colorbar(im, ax=ax, shrink=0.9)
    cbar.outline.set_visible(False)
    cbar.set_label("zł (mniej = lepiej)", color=TEXT_2)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_curves(curves, labels, title, optimum_cost, path, logx=False):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    gens = np.arange(GENERATIONS + 1)
    for curve, label, color in zip(curves, labels, SERIES):
        ax.plot(gens, curve, color=color, linewidth=2, label=label)
    ax.axhline(optimum_cost, color=TEXT_2, linewidth=1, linestyle="--")
    ax.text(GENERATIONS, optimum_cost, f"optimum {optimum_cost:.2f} zł", color=TEXT_2,
            ha="right", va="bottom", fontsize=9)
    ax.set_ylim(optimum_cost - 1, min(40, max(c[5] for c in curves) * 1.05))
    ax.set_xlim(0, GENERATIONS)
    ax.set_xlabel("pokolenie")
    ax.set_ylabel("najlepsza dotychczas f. celu [zł]")
    ax.set_title(title, loc="left")
    ax.legend(ncols=3, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_population_mean(curves_mean, curves_best, labels, optimum_cost, path):
    fig, axes = plt.subplots(1, len(labels), figsize=(9, 3.6), sharey=True)
    gens = np.arange(GENERATIONS + 1)
    for ax, mean, best, label in zip(axes, curves_mean, curves_best, labels):
        ax.plot(gens, mean, color=SERIES[1], linewidth=2, label="średnia populacji")
        ax.plot(gens, best, color=SERIES[0], linewidth=2, label="najlepszy dotychczas")
        ax.axhline(optimum_cost, color=TEXT_2, linewidth=1, linestyle="--")
        ax.set_title(label, loc="left")
        ax.set_xlabel("pokolenie")
        ax.set_xlim(0, GENERATIONS)
        ax.set_ylim(0, 80)
    axes[0].set_ylabel("f. celu [zł] (średnia z uruchomień)")
    axes[0].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    problem = DietProblem()
    optimum = exact_optimum(problem)
    optimum_cost = float(problem.cost(optimum))
    print(f"Optimum referencyjne (ILP): {optimum_cost:.2f} zł\n")

    # --- Experiment 1: p_c x p_m grid -----------------------------------------------------
    all_rows, summaries, curves_best, curves_mean = [], [], {}, {}
    for pc in P_CROSSOVER:
        for pm in P_MUTATION:
            rows, cb, cm = run_config(problem, optimum_cost, POP_SIZE, pc, pm)
            all_rows += rows
            summaries.append(summarize(rows, optimum_cost))
            curves_best[pc, pm], curves_mean[pc, pm] = cb, cm
            s = summaries[-1]
            print(f"pc={pc:<4} pm={pm:<6} obj={s['obj_mean']:6.2f} ± {s['obj_std']:5.2f}  "
                  f"feasible={s['feasible_rate']:.0%}  optimum hits={s['optimal_hits']}/{RUNS}")

    # --- Experiment 2: population size (base p_c, p_m) ------------------------------------
    pop_rows, pop_summaries, pop_curves = [], [], []
    for n in POP_SIZES:
        rows, cb, _ = run_config(problem, optimum_cost, n, BASE_PC, BASE_PM)
        pop_rows += rows
        pop_summaries.append(summarize(rows, optimum_cost))
        pop_curves.append(cb)

    write_csv(OUT / "runs.csv", all_rows + pop_rows)
    write_csv(OUT / "summary.csv", summaries + pop_summaries)

    ranked = sorted(summaries, key=lambda s: s["obj_mean"])
    best_run = min(all_rows + pop_rows, key=lambda r: r["objective"])
    best_x = np.array(list(map(int, best_run["chromosome"].split())))
    report = [
        f"# Wyniki eksperymentów\n",
        f"Optimum referencyjne (ILP): **{optimum_cost:.2f} zł**. "
        f"N = {POP_SIZE}, {GENERATIONS} pokoleń, turniej k = {TOURNAMENT}, {RUNS} uruchomień na konfigurację.\n",
        "## Eksperyment 1: siatka p_c x p_m\n", markdown_table(summaries), "",
        "## Ranking (5 najlepszych / 5 najgorszych konfiguracji)\n",
        markdown_table(ranked[:5] + ranked[-5:]), "",
        f"## Eksperyment 2: rozmiar populacji (p_c = {BASE_PC}, p_m = {BASE_PM})\n",
        markdown_table(pop_summaries), "",
        "## Najlepsze znalezione rozwiązanie\n",
        f"Konfiguracja: N = {best_run['pop_size']}, p_c = {best_run['p_crossover']}, "
        f"p_m = {best_run['p_mutation']}, "
        f"seed = {best_run['seed']}\n", "```", describe(problem, best_x), "```", "",
        "## Rozwiązanie optymalne (ILP)\n", "```", describe(problem, optimum), "```",
    ]
    (OUT / "summary.md").write_text("\n".join(report), encoding="utf-8")

    plot_heatmap(summaries, optimum_cost, OUT / "heatmap_pc_pm.png")
    plot_curves([curves_best[BASE_PC, pm] for pm in P_MUTATION],
                [f"p_m = {pm}" for pm in P_MUTATION],
                f"Zbieżność dla różnych p_m (p_c = {BASE_PC}, średnia z {RUNS} uruchomień)",
                optimum_cost, OUT / "convergence_pm.png")
    plot_curves([curves_best[pc, BASE_PM] for pc in P_CROSSOVER],
                [f"p_c = {pc}" for pc in P_CROSSOVER],
                f"Zbieżność dla różnych p_c (p_m = {BASE_PM}, średnia z {RUNS} uruchomień)",
                optimum_cost, OUT / "convergence_pc.png")
    plot_curves(pop_curves, [f"N = {n}" for n in POP_SIZES],
                f"Zbieżność dla różnych rozmiarów populacji (p_c = {BASE_PC}, p_m = {BASE_PM})",
                optimum_cost, OUT / "convergence_pop.png")
    pms = [0.005, BASE_PM, 0.2]
    plot_population_mean([curves_mean[BASE_PC, pm] for pm in pms],
                         [curves_best[BASE_PC, pm] for pm in pms],
                         [f"p_m = {pm}" for pm in pms], optimum_cost, OUT / "population_mean.png")
    print(f"\nWyniki zapisane w {OUT}")


if __name__ == "__main__":
    main()
