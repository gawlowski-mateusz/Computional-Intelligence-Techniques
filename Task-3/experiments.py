"""Task 3: PSO for the diet problem - parameter tuning and comparison with the genetic algorithm.

Stage 1 (screening): full factorial grid of PSO parameters, every configuration run RUNS times
         (seeds 0..RUNS-1) with a budget of ~6000 evaluations of the objective function.
Stage 2 (validation): the best PSO configurations, the best configuration of every parameter
         level, the standard PSO setting and the GA configurations from Tasks 1 and 2 are re-run
         VALIDATION_RUNS times on new seeds (1000, 1001, ...).
Stage 3 (budget): the best PSO and GA configurations for budgets of 1500 ... 24000 evaluations.
Stage 4 (analysis): behaviour of the populations (diversity, new solutions, step length) and the
         distribution of the final results, used to explain the differences between the methods.

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
from pso import PSOConfig, run_pso

EVALUATIONS = 6020          # GA from Tasks 1-2: population 20 x (300 generations + initial one)
RUNS = 30
VALIDATION_RUNS = 100
VALIDATION_SEED0 = 1000
TOP_VALIDATED = 10

# Stage 1 grid
SWARM_SIZES = [10, 20, 40]
INERTIA = [(0.4, None), (0.6, None), (0.729, None), (0.9, None), (1.0, None), (1.1, None),
           (0.9, 0.4)]                                   # (w_start, w_end); None = constant w
COEFFICIENTS = [(1.0, 1.0), (1.49445, 1.49445), (2.0, 2.0), (0.5, 2.5), (2.5, 0.5), (3.0, 0.0)]
TOPOLOGIES = ["global", "ring"]
V_MAX = [0.1, 0.25, 0.5, 1.0]

# Standard PSO setting (Clerc's constriction coefficients, global topology, no velocity clamping)
STANDARD_PSO = dict(swarm_size=20, w_start=0.729, w_end=None, c1=1.49445, c2=1.49445,
                    topology="global", v_max=1.0)
GA_TASK1 = dict(selection="tournament", tournament_size=3, ranking_pressure=1.5, elite_size=0,
                crossover="one_point", p_crossover=0.8, mutation="reset", p_mutation=0.05)
GA_TASK2 = dict(selection="tournament", tournament_size=3, ranking_pressure=1.5, elite_size=1,
                crossover="one_point", p_crossover=1.0, mutation="inversion", p_mutation=0.8)
GA_POP = 20
BUDGETS = [1500, 3000, 6000, 12000, 24000]

TOPOLOGY_PL = {"global": "globalna", "ring": "pierścień"}

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


# --- Formatting and configurations ------------------------------------------------------------

def num(x, digits=2):
    """Number with a Polish decimal comma."""
    return f"{x:.{digits}f}".replace(".", ",")


def short(x):
    return f"{x:.4g}".replace(".", ",")


def pval(p):
    return f"{p:.3g}".replace(".", ",")


def inertia_label(w_start, w_end):
    return short(w_start) if w_end is None else f"{short(w_start)}→{short(w_end)}"


def coeff_label(c1, c2):
    return f"({short(c1)}; {short(c2)})"


def iterations_for(swarm_size, evaluations=EVALUATIONS):
    """Number of iterations giving ~evaluations evaluations (swarm_size per iteration)."""
    return max(1, round(evaluations / swarm_size) - 1)


def label(c):
    if c["method"] == "ga":
        return c["name"]
    return (f"S={c['swarm_size']} · w={inertia_label(c['w_start'], c['w_end'])} · "
            f"c={coeff_label(c['c1'], c['c2'])} · {TOPOLOGY_PL[c['topology']]} · "
            f"v_max={short(c['v_max'])}")


def grid_configs():
    return [dict(method="pso", swarm_size=s, w_start=w0, w_end=w1, c1=c1, c2=c2, topology=top, v_max=vm)
            for s, (w0, w1), (c1, c2), top, vm in itertools.product(SWARM_SIZES, INERTIA, COEFFICIENTS,
                                                                   TOPOLOGIES, V_MAX)]


def ga_config(name, params):
    return dict(method="ga", name=name, **params)


PSO_KEYS = ["swarm_size", "w_start", "w_end", "c1", "c2", "topology", "v_max"]


def config_key(c):
    return label(c)


def stability(c):
    """Theoretical behaviour of a PSO particle (order-2 stability region of Poli, 2009).

    The particle converges (in mean and variance) if |w| < 1 and
    c1 + c2 < 24 (1 - w^2) / (7 - 5 w). For a decreasing w the final value is used.
    """
    w = c["w_start"] if c["w_end"] is None else c["w_end"]
    if abs(w) >= 1:
        return False
    return c["c1"] + c["c2"] < 24 * (1 - w * w) / (7 - 5 * w)


# --- Running ----------------------------------------------------------------------------------

def to_objective(fitness):
    """Inverse of F = 1 / (1 + objective): penalised cost in PLN (lower is better)."""
    return 1.0 / np.asarray(fitness) - 1.0


def run_one(problem, c, seed, evaluations=EVALUATIONS):
    """Run one configuration (PSO or GA) with the given budget; returns (solution, curve, size)."""
    if c["method"] == "pso":
        cfg = PSOConfig(seed=seed, iterations=iterations_for(c["swarm_size"], evaluations),
                        **{k: c[k] for k in PSO_KEYS})
        res = run_pso(problem, cfg)
        return res.best_solution, res.best_iteration, res.history_best_so_far, c["swarm_size"]
    gens = iterations_for(GA_POP, evaluations)
    cfg = GAConfig(pop_size=GA_POP, generations=gens, seed=seed,
                   **{k: v for k, v in c.items() if k not in ("method", "name")})
    res = run_ga(problem, cfg)
    return res.best_chromosome, res.best_generation, res.history_best_so_far, GA_POP


def run_config(job):
    """Worker: run one configuration for the given seeds, return per-run results and mean curve."""
    c, seeds, optimum_cost, evaluations = job
    runs, curves = [], []
    for seed in seeds:
        x, best_it, curve, size = run_one(PROBLEM, c, seed, evaluations)
        feasible = bool(PROBLEM.is_feasible(x))
        runs.append({
            "seed": seed, "objective": round(float(PROBLEM.objective(x)), 4),
            "cost": round(float(PROBLEM.cost(x)), 2), "feasible": feasible,
            "optimal": feasible and abs(PROBLEM.cost(x) - optimum_cost) < 1e-6,
            "best_evaluation": size * (best_it + 1), "solution": " ".join(map(str, x)),
        })
        curves.append(to_objective(curve))
    return runs, np.mean(curves, axis=0)


def random_search(seed, evaluations=EVALUATIONS):
    """Baseline without any search strategy: the best of `evaluations` random menus."""
    rng = np.random.default_rng(seed)
    return float(PROBLEM.objective(PROBLEM.random_population(evaluations, rng)).min())


def run_many(configs, seeds, optimum_cost, evaluations=EVALUATIONS):
    jobs = [(c, seeds, optimum_cost, evaluations) for c in configs]
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
        "best_eval_mean": np.mean([r["best_evaluation"] for r in runs]),
    })
    return s


class TracingProblem(DietProblem):
    """DietProblem recording statistics of every evaluated population or swarm (stage 4).

    Both run_ga (through fitness) and run_pso call objective() once per generation / iteration
    with the whole population, so the same measurements are taken for both methods:
    - diversity: mean Hamming distance between two solutions of the population,
    - new: fraction of evaluated solutions that did not appear in the previous population,
    - step: Hamming distance from a new solution to the nearest solution of the previous
      population (how far the method moves from what it already knows).
    """

    def start(self):
        self.prev, self.diversity, self.new, self.step = None, [], [], []

    def objective(self, pop):
        if pop.ndim == 2:
            n = len(pop)
            self.diversity.append((pop[:, None, :] != pop[None, :, :]).sum() / (n * (n - 1)))
            if self.prev is not None:
                dist = (pop[:, None, :] != self.prev[None, :, :]).sum(-1).min(axis=1)
                self.new.append(np.mean(dist > 0))
                self.step.append(dist[dist > 0].mean() if np.any(dist > 0) else 0.0)
            self.prev = pop.copy()
        return super().objective(pop)


def trace_config(job):
    """Worker for stage 4: mean dynamics curves of one configuration over the given seeds."""
    c, seeds = job
    problem = TracingProblem()
    div, new, step, best = [], [], [], []
    for seed in seeds:
        problem.start()
        _, _, curve, size = run_one(problem, c, seed)
        div.append(problem.diversity)
        new.append(problem.new)
        step.append(problem.step)
        best.append(to_objective(curve))
    return size, *(np.mean(a, axis=0) for a in (best, div, new, step))


# --- Output helpers ---------------------------------------------------------------------------

def write_csv(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def markdown_table(summaries, first_col="konfiguracja", first=lambda s: s["label"]):
    lines = [f"| {first_col} | śr. f [zł] | odch. std | mediana | min | max | luka do opt. | "
             "dopuszczalne | trafienia opt. | śr. ocena best |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        lines.append(
            f"| {first(s)} | {num(s['obj_mean'])} | {num(s['obj_std'])} | {num(s['obj_median'])} | "
            f"{num(s['obj_min'])} | {num(s['obj_max'])} | {num(s['gap_mean_pct'], 1)}% | "
            f"{s['feasible_rate'] * 100:.0f}% | {s['optimal_rate'] * 100:.0f}% | "
            f"{s['best_eval_mean']:.0f} |")
    return "\n".join(lines)


def factor_table(summaries, factor_name, key, levels, level_name):
    """Mean of all configurations with the given level and the best of them."""
    lines = [f"| {factor_name} | średnia danej wartości [zł] | najlepsza konfiguracja: śr. f [zł] | "
             "trafienia opt. | najlepsza konfiguracja |", "|---|---|---|---|---|"]
    for level in levels:
        group = [s for s in summaries if key(s) == level]
        best = min(group, key=lambda s: s["obj_mean"])
        lines.append(f"| {level_name(level)} | {num(np.mean([s['obj_mean'] for s in group]))} | "
                     f"{num(best['obj_mean'])} | {best['optimal_rate'] * 100:.0f}% | {best['label']} |")
    return "\n".join(lines)


def heatmap(ax, grid, row_labels, col_labels, title, vmin, vmax, marked=None):
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
            ax.text(j, i, num(grid[i, j]), ha="center", va="center", fontsize=9,
                    color="white" if grid[i, j] > threshold else TEXT)
            if marked is not None and marked[i, j]:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, hatch="///",
                                           edgecolor=SERIES[1], linewidth=0))
    return im


def heatmap_pair(avg, best, rows, cols, xlabel, title, name, figsize, marked=None, note=None,
                 color_max=None):
    """Mean of the configurations (left) and the best configuration (right), one colour scale.

    color_max caps the colour scale, so a few extreme cells do not wash out the rest (the numbers
    in the cells are always exact).
    """
    vmin, vmax = min(avg.min(), best.min()), max(avg.max(), best.max())
    if color_max is not None:
        vmax = min(vmax, color_max)
    fig, axes = plt.subplots(1, 2, figsize=figsize, layout="constrained")
    heatmap(axes[0], avg, rows, cols, "średnia danej wartości [zł]", vmin, vmax, marked)
    im = heatmap(axes[1], best, rows, cols, "najlepsza konfiguracja: śr. f [zł]", vmin, vmax, marked)
    axes[1].tick_params(labelleft=False)  # same rows as the left panel
    for ax in axes:
        ax.set_xlabel(xlabel)
    cbar = fig.colorbar(im, ax=axes, shrink=0.9)
    cbar.outline.set_visible(False)
    cbar.set_label("zł (mniej = lepiej)", color=TEXT_2)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold")
    if note:
        fig.text(0.01, -0.02, note, fontsize=8.5, color=TEXT_2, ha="left", va="top")
    fig.savefig(OUT / name, dpi=150, bbox_inches="tight")
    plt.close(fig)


def optimum_line(ax, optimum_cost, x):
    ax.axhline(optimum_cost, color=TEXT_2, linewidth=1, linestyle="--")
    ax.text(x, optimum_cost, f"optimum {num(optimum_cost)} zł", color=TEXT_2, ha="right",
            va="bottom", fontsize=8)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


# --- Figures ----------------------------------------------------------------------------------

FACTORS = [
    ("rozmiar roju S", lambda s: s["swarm_size"], SWARM_SIZES, lambda v: f"S={v}"),
    ("bezwładność w", lambda s: (s["w_start"], s["w_end"]), INERTIA, lambda v: inertia_label(*v)),
    ("współczynniki (c1; c2)", lambda s: (s["c1"], s["c2"]), COEFFICIENTS, lambda v: coeff_label(*v)),
    ("topologia", lambda s: s["topology"], TOPOLOGIES, TOPOLOGY_PL.get),
    ("v_max (część zakresu)", lambda s: s["v_max"], V_MAX, short),
]


def plot_main_effects(summaries, optimum_cost, ga_best):
    fig, axes = plt.subplots(1, 5, figsize=(14, 4), sharey=True,
                             gridspec_kw={"width_ratios": [3, 7, 6, 2, 4]})
    for ax, (name, key, levels, level_name) in zip(axes, FACTORS):
        avg = [np.mean([s["obj_mean"] for s in summaries if key(s) == lv]) for lv in levels]
        best = [min(s["obj_mean"] for s in summaries if key(s) == lv) for lv in levels]
        x = np.arange(len(levels))
        ax.scatter(x, avg, color=SERIES[0], marker="s", s=40, zorder=3, label="średnia danej wartości")
        ax.scatter(x, best, color=SERIES[1], s=40, zorder=3, label="najlepsza konfiguracja")
        ax.axhline(ga_best, color=SERIES[2], linewidth=1.5, linestyle=":")
        optimum_line(ax, optimum_cost, len(levels) - 0.6)
        ax.set_xticks(x, [level_name(lv) for lv in levels], rotation=30, ha="right")
        ax.set_xlim(-0.6, len(levels) - 0.4)
        ax.set_title(name, loc="left")
        ax.grid(axis="x", visible=False)
    axes[0].plot([], [], color=SERIES[2], linestyle=":", label="najlepszy AG (zad. 2), etap 1")
    axes[0].set_ylabel("śr. f. celu najlepszego rozwiązania [zł]")
    axes[0].set_ylim(optimum_cost - 0.3, None)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncols=3, fontsize=8)
    fig.suptitle(f"PSO – wpływ parametrów (etap 1: {len(summaries)} konfiguracji × {RUNS} uruchomień)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT / "main_effects.png", dpi=150)
    plt.close(fig)


def plot_inertia_coefficients(summaries):
    rows = [inertia_label(*w) for w in INERTIA]
    cols = [coeff_label(*c) for c in COEFFICIENTS]
    group = lambda w, c: [s for s in summaries if (s["w_start"], s["w_end"]) == w and (s["c1"], s["c2"]) == c]
    avg = np.array([[np.mean([s["obj_mean"] for s in group(w, c)]) for c in COEFFICIENTS] for w in INERTIA])
    best = np.array([[min(s["obj_mean"] for s in group(w, c)) for c in COEFFICIENTS] for w in INERTIA])
    marked = np.array([[stability(dict(w_start=w0, w_end=w1, c1=c1, c2=c2)) for c1, c2 in COEFFICIENTS]
                       for w0, w1 in INERTIA])
    heatmap_pair(avg, best, [f"w = {r}" for r in rows], cols, "współczynniki (c1; c2)",
                 "Bezwładność × współczynniki przyspieszenia", "inertia_coefficients.png", (13, 4.6),
                 marked, "Kreskowanie: rój teoretycznie zbieżny (cząstki zatrzymują się); "
                         "pozostałe pola: rój niezbieżny, ruch ograniczony tylko przez v_max i granice. "
                         "Skala kolorów ucięta na 15 zł.", color_max=15)


def plot_swarm_topology_vmax(summaries):
    rows = [(s, t) for s in SWARM_SIZES for t in TOPOLOGIES]
    group = lambda r, vm: [s for s in summaries if (s["swarm_size"], s["topology"]) == r and s["v_max"] == vm]
    avg = np.array([[np.mean([s["obj_mean"] for s in group(r, vm)]) for vm in V_MAX] for r in rows])
    best = np.array([[min(s["obj_mean"] for s in group(r, vm)) for vm in V_MAX] for r in rows])
    heatmap_pair(avg, best, [f"S={s}, {TOPOLOGY_PL[t]}" for s, t in rows],
                 [f"v_max = {short(v)}" for v in V_MAX], "ograniczenie prędkości (część zakresu zmiennej)",
                 "Rozmiar roju × topologia × v_max", "swarm_topology_vmax.png", (11, 4))


def plot_validation_box(validated, results):
    order = sorted(range(len(validated)), key=lambda i: validated[i]["obj_mean"])
    data = [[r["objective"] for r in results[i][0]] for i in order]
    names = [f"#{rank + 1}  {validated[i]['label']}" for rank, i in enumerate(order)]
    is_ga = [validated[i]["method"] == "ga" for i in order]
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(order) + 1.4))
    box = ax.boxplot(data[::-1], vert=False, widths=0.6, patch_artist=True,
                     medianprops={"color": TEXT, "linewidth": 2},
                     flierprops={"marker": "o", "markersize": 3, "markerfacecolor": TEXT_2,
                                 "markeredgecolor": "none"})
    for patch, ga in zip(box["boxes"], is_ga[::-1]):
        patch.set(facecolor="#fbd9c9" if ga else "#cde2fb", edgecolor=SERIES[1] if ga else SERIES[0])
    ax.scatter([np.mean(d) for d in data[::-1]], range(1, len(data) + 1), color=TEXT, s=14, zorder=3,
               label="średnia")
    ax.set_yticks(range(1, len(names) + 1), names[::-1], fontsize=8)
    for tick, ga in zip(ax.get_yticklabels(), is_ga[::-1]):
        tick.set_color(SERIES[1] if ga else TEXT)
    ax.set_xlabel("f. celu najlepszego rozwiązania [zł]")
    ax.set_title(f"Walidacja: {VALIDATION_RUNS} uruchomień na nowych ziarnach", loc="left")
    handles = [matplotlib.patches.Patch(facecolor="#cde2fb", edgecolor=SERIES[0], label="PSO"),
               matplotlib.patches.Patch(facecolor="#fbd9c9", edgecolor=SERIES[1], label="AG"),
               *ax.get_legend_handles_labels()[0]]
    ax.legend(handles=handles, loc="upper right")
    ax.grid(axis="y", visible=False)
    save(fig, "validation_boxplot.png")


def plot_budget(rows, names, optimum_cost):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for name, color in zip(names, SERIES):
        rs = [r for r in rows if r["method_name"] == name]
        axes[0].plot(BUDGETS, [r["obj_mean"] for r in rs], marker="o", color=color, linewidth=2, label=name)
        axes[1].plot(BUDGETS, [100 * r["optimal_rate"] for r in rs], marker="o", color=color, linewidth=2)
    optimum_line(axes[0], optimum_cost, BUDGETS[-1])
    axes[0].set_ylabel("śr. f. celu najlepszego rozwiązania [zł]")
    axes[1].set_ylabel("trafienia optimum [%]")
    axes[1].set_ylim(0, 100)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks(BUDGETS, [str(b) for b in BUDGETS])
        ax.minorticks_off()
        ax.set_xlabel("budżet: liczba ocen funkcji celu")
    axes[0].set_title("średni wynik", loc="left")
    axes[1].set_title("odsetek uruchomień, które znalazły optimum", loc="left")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncols=2, fontsize=8)
    fig.suptitle(f"PSO i AG przy różnym budżecie ({VALIDATION_RUNS} uruchomień)", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(OUT / "budget.png", dpi=150)
    plt.close(fig)


def plot_dynamics(traces, names, optimum_cost):
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5))
    axes = axes.ravel()
    for (size, best, div, new, step), name, color in zip(traces, names, SERIES):
        evals = size * (np.arange(len(best)) + 1)
        axes[0].plot(evals, best, color=color, linewidth=2, label=name)
        axes[1].plot(evals, div, color=color, linewidth=2)
        axes[2].plot(evals[1:], 100 * new, color=color, linewidth=1.5)
        axes[3].plot(evals[1:], step, color=color, linewidth=1.5)
    optimum_line(axes[0], optimum_cost, EVALUATIONS)
    axes[0].set_ylim(optimum_cost - 0.5, 16)
    axes[0].set_title("najlepsze dotychczas [zł] (średnia)", loc="left")
    axes[1].set_title("różnorodność: śr. odległość Hamminga w populacji", loc="left")
    axes[2].set_title("nowe rozwiązania: % ocen, których nie było w poprz. populacji", loc="left")
    axes[3].set_title("długość kroku: odległość od najbliższego poprz. rozwiązania", loc="left")
    axes[1].set_ylabel("liczba różnych produktów")
    axes[2].set_ylabel("%")
    axes[3].set_ylabel("liczba zmienionych produktów")
    axes[2].set_ylim(0, 102)
    for ax in axes:
        ax.set_xlim(0, EVALUATIONS)
        ax.set_xlabel("liczba ocen funkcji celu")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncols=2, fontsize=8)
    fig.suptitle(f"Dynamika PSO i AG ({VALIDATION_RUNS} uruchomień walidacyjnych)", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(OUT / "dynamics.png", dpi=150)
    plt.close(fig)


FINAL_BINS = [(0, 7.7001, "7,70 (optimum)"), (7.7001, 8.1001, "7,71–8,10"), (8.1001, 8.5001, "8,11–8,50"),
              (8.5001, 9.0001, "8,51–9,00"), (9.0001, 10.0001, "9,01–10,00"), (10.0001, np.inf, "> 10,00")]


def final_distribution(runs):
    obj = np.array([r["objective"] for r in runs])
    return [100 * np.mean((obj >= lo) & (obj < hi)) for lo, hi, _ in FINAL_BINS]


def plot_final_distribution(dists, names):
    fig, ax = plt.subplots(figsize=(10, 3.8))
    width = 0.8 / len(names)
    x = np.arange(len(FINAL_BINS))
    for k, (d, name, color) in enumerate(zip(dists, names, SERIES)):
        bars = ax.bar(x + (k - (len(names) - 1) / 2) * width, d, width, color=color, label=name)
        ax.bar_label(bars, [f"{v:.0f}" if v else "" for v in d], fontsize=7.5, color=TEXT_2, padding=1)
    ax.set_xticks(x, [b[2] for b in FINAL_BINS])
    ax.set_xlabel("wynik końcowy [zł]")
    ax.set_ylabel("% uruchomień")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=8)
    ax.set_title(f"Rozkład wyników końcowych ({VALIDATION_RUNS} uruchomień walidacyjnych)", loc="left")
    save(fig, "final_distribution.png")


# --- Main -------------------------------------------------------------------------------------

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    optimum = exact_optimum(PROBLEM)
    optimum_cost = float(PROBLEM.cost(optimum))
    print(f"Optimum referencyjne (ILP): {optimum_cost:.2f} zł")

    ga1 = ga_config("AG zad. 1: turniej k=3 · bez elity · jednopunktowe p_c=0,8 · reset p_m=0,05", GA_TASK1)
    ga2 = ga_config("AG zad. 2: turniej k=3 · elita 1 · jednopunktowe p_c=1,0 · inwersja p_m=0,8", GA_TASK2)
    standard = dict(method="pso", **STANDARD_PSO)

    # --- Stage 1: screening ------------------------------------------------------------------
    configs = grid_configs()
    print(f"Etap 1: {len(configs)} konfiguracji PSO × {RUNS} uruchomień ...")
    results = run_many(configs + [ga1, ga2], list(range(RUNS)), optimum_cost)
    summaries = [summarize(c, r[0], optimum_cost) for c, r in zip(configs + [ga1, ga2], results)]
    screening, ga_screen = summaries[:len(configs)], summaries[len(configs):]
    for s in screening:
        s["convergent"] = stability(s)
    random_mean = np.mean([random_search(seed) for seed in range(RUNS)])
    write_csv(OUT / "screening.csv", screening)
    ranked = sorted(screening, key=lambda s: (s["obj_mean"], -s["optimal_rate"]))
    print(markdown_table(ranked[:5]))

    # --- Stage 2: validation -----------------------------------------------------------------
    candidates = ranked[:TOP_VALIDATED]
    for _, key, levels, _ in FACTORS:
        candidates += [min((s for s in screening if key(s) == lv), key=lambda s: s["obj_mean"])
                       for lv in levels]
    validated_cfgs, seen = [], set()
    for c in [standard] + [dict(method="pso", **{k: s[k] for k in PSO_KEYS}) for s in candidates]:
        if config_key(c) not in seen:
            seen.add(config_key(c))
            validated_cfgs.append(c)
    validated_cfgs += [ga1, ga2]
    print(f"\nEtap 2: walidacja {len(validated_cfgs)} konfiguracji × {VALIDATION_RUNS} uruchomień ...")
    val_seeds = list(range(VALIDATION_SEED0, VALIDATION_SEED0 + VALIDATION_RUNS))
    val_results = run_many(validated_cfgs, val_seeds, optimum_cost)
    validated = [summarize(c, r[0], optimum_cost) for c, r in zip(validated_cfgs, val_results)]
    screen_by_label = {s["label"]: s for s in screening + ga_screen}
    for s in validated:
        s["screening_obj_mean"] = screen_by_label[s["label"]]["obj_mean"]
    pso_idx = [i for i, s in enumerate(validated) if s["method"] == "pso"]
    win_i = min(pso_idx, key=lambda i: (validated[i]["obj_mean"], -validated[i]["optimal_rate"]))
    winner = validated[win_i]
    win_cfg = validated_cfgs[win_i]
    by_label = {s["label"]: (s, r) for s, r in zip(validated, val_results)}
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
    ga2_s, ga1_s, std_s = (by_label[label(c)][0] for c in (ga2, ga1, standard))
    ga2_obj = [r["objective"] for r in by_label[label(ga2)][1][0]]
    p_pso_better = mannwhitneyu(win_obj, ga2_obj, alternative="less").pvalue
    p_ga_better = mannwhitneyu(ga2_obj, win_obj, alternative="less").pvalue

    # --- Stage 3: budget ---------------------------------------------------------------------
    pso_name = f"PSO: {winner['label']}"
    std_name = f"PSO standardowe: {std_s['label']}"
    budget_methods = [(pso_name, win_cfg), (std_name, standard), (ga2["name"], ga2), (ga1["name"], ga1)]
    print(f"\nEtap 3: budżety {BUDGETS} ...")
    budget_rows = []
    for b in BUDGETS:
        res = run_many([c for _, c in budget_methods], val_seeds, optimum_cost, evaluations=b)
        for (name, c), r in zip(budget_methods, res):
            s = summarize(c, r[0], optimum_cost)
            s.update(method_name=name, budget=b)
            budget_rows.append(s)
    write_csv(OUT / "budget.csv", budget_rows)

    # --- Stage 4: analysis -------------------------------------------------------------------
    print("Etap 4: analiza dynamiki ...")
    names = [name for name, _ in budget_methods]
    with ProcessPoolExecutor() as ex:
        traces = list(ex.map(trace_config, [(c, val_seeds) for _, c in budget_methods]))
    dists = [final_distribution(by_label[label(c)][1][0]) for _, c in budget_methods]

    # --- Report ------------------------------------------------------------------------------
    best_run = min(by_label[winner["label"]][1][0], key=lambda r: r["objective"])
    best_x = np.array(list(map(int, best_run["solution"].split())))
    ga_best_screen = ga_screen[1]["obj_mean"]
    checkpoints = [500, 1500, 3000, 6000]

    def at(size, curve, e, offset=0):
        return curve[min(len(curve) - 1, max(0, round(e / size) - 1 - offset))]

    report = [
        "# Wyniki eksperymentów (zadanie 3: PSO)\n",
        f"Optimum referencyjne (ILP): **{num(optimum_cost)} zł**. Budżet: ok. {EVALUATIONS} ocen funkcji "
        f"celu na uruchomienie (jak AG z zadań 1–2: N = {GA_POP}, 300 pokoleń).\n",
        f"## Etap 1: przegląd siatki ({len(screening)} konfiguracji × {RUNS} uruchomień)\n",
        f"Dla porównania AG na tych samych ziarnach: zadanie 1 – {num(ga_screen[0]['obj_mean'])} zł, "
        f"zadanie 2 – {num(ga_screen[1]['obj_mean'])} zł. Czyste losowanie ({EVALUATIONS} losowych "
        f"jadłospisów, najlepszy z nich): {num(random_mean)} zł.\n",
        f"Średnia wszystkich konfiguracji PSO: {num(np.mean([s['obj_mean'] for s in screening]))} zł; "
        f"konfiguracji gorszych od czystego losowania: "
        f"{sum(s['obj_mean'] > random_mean for s in screening)}.\n",
    ]
    for name, key, levels, level_name in FACTORS:
        report += [f"### {name[0].upper() + name[1:]}\n",
                   factor_table(screening, name, key, levels, level_name), ""]
    report += [
        "### Rój zbieżny i niezbieżny\n",
        "| zachowanie roju | liczba konfiguracji | średnia [zł] | najlepsza konfiguracja [zł] | "
        "trafienia opt. (najlepsza) |",
        "|---|---|---|---|---|",
    ]
    for name, flag in (("zbieżny", True), ("niezbieżny", False)):
        group = [s for s in screening if s["convergent"] == flag]
        if group:
            best = min(group, key=lambda s: s["obj_mean"])
            report.append(f"| {name} | {len(group)} | {num(np.mean([s['obj_mean'] for s in group]))} | "
                          f"{num(best['obj_mean'])} | {best['optimal_rate'] * 100:.0f}% |")
    report += [
        "", "### Ranking: 20 najlepszych konfiguracji\n", markdown_table(ranked[:20]), "",
        "### 5 najgorszych konfiguracji\n", markdown_table(ranked[-5:]), "",
        f"## Etap 2: walidacja ({VALIDATION_RUNS} uruchomień, ziarna {val_seeds[0]}–{val_seeds[-1]})\n",
        "Kandydaci: 10 najlepszych konfiguracji PSO z etapu 1, najlepsza konfiguracja dla każdej "
        "wartości każdego parametru, standardowe PSO oraz AG z zadań 1 i 2. Kolumna *p* to wynik "
        "jednostronnego testu Manna–Whitneya „najlepsze PSO daje mniejsze f”.\n",
        "| # | metoda | konfiguracja | śr. f [zł] (etap 1) | śr. f [zł] | odch. std | mediana | min | max | "
        "dopuszczalne | trafienia opt. | p |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(validated_sorted, 1):
        p = "—" if s is winner else pval(s["p_value_vs_winner"])
        method = "AG" if s["method"] == "ga" else "PSO"
        report.append(f"| {i} | {method} | {s['label']} | {num(s['screening_obj_mean'])} | {num(s['obj_mean'])} | "
                      f"{num(s['obj_std'])} | {num(s['obj_median'])} | {num(s['obj_min'])} | "
                      f"{num(s['obj_max'])} | {s['feasible_rate'] * 100:.0f}% | "
                      f"{s['optimal_rate'] * 100:.0f}% | {p} |")
    report += [
        "", "### Porównanie najlepszych konfiguracji\n",
        markdown_table([winner, std_s, ga2_s, ga1_s], "metoda",
                       lambda s: {winner['label']: "PSO (najlepsze)", std_s['label']: "PSO standardowe",
                                  ga2_s['label']: "AG zad. 2", ga1_s['label']: "AG zad. 1"}[s["label"]]), "",
        f"Test Manna–Whitneya (najlepsze PSO vs AG zad. 2): p(PSO lepsze) = "
        f"{pval(p_pso_better)}, p(AG lepszy) = {pval(p_ga_better)}.\n",
        f"## Etap 3: budżet obliczeń ({VALIDATION_RUNS} uruchomień)\n",
        "| metoda | " + " | ".join(f"{b} ocen" for b in BUDGETS) + " |",
        "|---|" + "---|" * len(BUDGETS),
    ]
    for name, _ in budget_methods:
        rs = [r for r in budget_rows if r["method_name"] == name]
        report.append(f"| {name} | " + " | ".join(f"{num(r['obj_mean'])} zł ({r['optimal_rate'] * 100:.0f}%)"
                                                  for r in rs) + " |")
    report += [
        "", "W nawiasach: odsetek uruchomień, które znalazły optimum.\n",
        "## Etap 4: analiza\n",
        f"### Dynamika populacji (średnio z {VALIDATION_RUNS} uruchomień)\n",
        "| metoda | wskaźnik | " + " | ".join(f"{e} ocen" for e in checkpoints) + " |",
        "|---|---|" + "---|" * len(checkpoints),
    ]
    for name, (size, best, div, new, step) in zip(names, traces):
        report.append(f"| {name} | najlepsze dotychczas [zł] | " +
                      " | ".join(num(at(size, best, e)) for e in checkpoints) + " |")
        report.append(f"| | różnorodność [produkty] | " +
                      " | ".join(num(at(size, div, e), 1) for e in checkpoints) + " |")
        report.append(f"| | nowe rozwiązania | " +
                      " | ".join(f"{100 * at(size, new, e, 1):.0f}%" for e in checkpoints) + " |")
        report.append(f"| | długość kroku [produkty] | " +
                      " | ".join(num(at(size, step, e, 1), 1) for e in checkpoints) + " |")
    report += [
        "", "### Rozkład wyników końcowych (walidacja)\n",
        "| metoda | " + " | ".join(b[2] for b in FINAL_BINS) + " |",
        "|---|" + "---|" * len(FINAL_BINS),
    ]
    for name, d in zip(names, dists):
        report.append(f"| {name} | " + " | ".join(f"{v:.0f}%" for v in d) + " |")
    report += [
        "", "## Najlepsza konfiguracja PSO\n",
        f"**{winner['label']}**\n",
        f"- średnia f: {num(winner['obj_mean'])} zł (AG zad. 2: {num(ga2_s['obj_mean'])} zł, "
        f"AG zad. 1: {num(ga1_s['obj_mean'])} zł)",
        f"- trafienia optimum: {winner['optimal_rate'] * 100:.0f}% (AG zad. 2: {ga2_s['optimal_rate'] * 100:.0f}%)\n",
        f"Najlepsze rozwiązanie (ziarno {best_run['seed']}):\n", "```", describe(PROBLEM, best_x), "```", "",
        "## Rozwiązanie optymalne (ILP)\n", "```", describe(PROBLEM, optimum), "```",
    ]
    (OUT / "summary.md").write_text("\n".join(report), encoding="utf-8")

    plot_main_effects(screening, optimum_cost, ga_best_screen)
    plot_inertia_coefficients(screening)
    plot_swarm_topology_vmax(screening)
    plot_validation_box(validated, val_results)
    plot_budget(budget_rows, names, optimum_cost)
    plot_dynamics(traces, names, optimum_cost)
    plot_final_distribution(dists, names)
    print(f"\nNajlepsze PSO: {winner['label']}  (śr. f = {winner['obj_mean']:.2f} zł, "
          f"AG zad. 2: {ga2_s['obj_mean']:.2f} zł, p = {p_pso_better:.3g})")
    print(f"Wyniki zapisane w {OUT}")


if __name__ == "__main__":
    main()
