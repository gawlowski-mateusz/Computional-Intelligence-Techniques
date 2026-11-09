"""Extended genetic algorithm for the diet planning problem (Task 2).

Extension of the basic GA from Task 1. The problem, the chromosome and the fitness function are
unchanged; the GA got new, interchangeable operators:

Chromosome  : integer vector x = (x_1, ..., x_n), x_i in {0, ..., max_i}
              -> number of portions of product i in the daily menu.
Fitness     : F(x) = 1 / (1 + cost(x) + W * violation(x))   (maximised, F in (0, 1])
Selection   : tournament (size k) | roulette (fitness proportional) | linear ranking (pressure s)
Elitism     : the e best individuals are copied unchanged to the next generation (e = 0: none)
Crossover   : one-point | two-point | uniform, applied to a pair with probability p_c
Mutation    : random reset (per gene, p_m) | creep +/-1 (per gene, p_m) |
              inversion (per chromosome, p_m)
Stop        : fixed number of generations

With the default configuration (tournament, no elitism, one-point crossover, random reset) the
algorithm and its random number stream are identical to Task 1, so seeded runs give the same
results in both tasks.
"""

from dataclasses import dataclass

import numpy as np

from diet_data import NUTRIENTS, PRODUCTS, REQUIREMENTS


class DietProblem:
    def __init__(self, products=PRODUCTS, requirements=REQUIREMENTS, penalty_weight=200.0):
        self.names = [p[0] for p in products]
        self.content = np.array([p[1:6] for p in products], dtype=float)  # (n_products, n_nutrients)
        self.prices = np.array([p[6] for p in products], dtype=float)
        self.max_portions = np.array([p[7] for p in products], dtype=int)
        self.lower = np.array([requirements[n][0] for n in NUTRIENTS], dtype=float)
        self.upper = np.array([requirements[n][1] for n in NUTRIENTS], dtype=float)
        self.penalty_weight = penalty_weight

    @property
    def n_genes(self):
        return len(self.names)

    def nutrients(self, pop):
        """Nutrient totals for one chromosome (n,) or a population (P, n)."""
        return pop @ self.content

    def cost(self, pop):
        return pop @ self.prices

    def violation(self, pop):
        """Sum of relative violations of nutrient bounds (0 for a feasible menu)."""
        totals = self.nutrients(pop)
        below = np.maximum(0.0, self.lower - totals) / self.lower
        above = np.maximum(0.0, totals - self.upper) / self.upper
        return (below + above).sum(axis=-1)

    def objective(self, pop):
        """Penalised cost to be minimised: cost [PLN] + W * relative violation."""
        return self.cost(pop) + self.penalty_weight * self.violation(pop)

    def fitness(self, pop):
        return 1.0 / (1.0 + self.objective(pop))

    def is_feasible(self, chromosome, tol=1e-9):
        return self.violation(chromosome) <= tol

    def random_population(self, size, rng):
        return rng.integers(0, self.max_portions + 1, size=(size, self.n_genes))


@dataclass
class GAConfig:
    pop_size: int = 20
    generations: int = 200
    selection: str = "tournament"   # "tournament" | "roulette" | "ranking"
    tournament_size: int = 3        # k, used by tournament selection
    ranking_pressure: float = 1.5   # s in [1, 2], used by linear ranking selection
    elite_size: int = 0             # e, number of elite individuals (0 = no elitism)
    crossover: str = "one_point"    # "one_point" | "two_point" | "uniform"
    p_crossover: float = 0.8
    mutation: str = "reset"         # "reset" | "creep" | "inversion"
    p_mutation: float = 0.05        # per gene (reset, creep) or per chromosome (inversion)
    seed: int | None = None


@dataclass
class GAResult:
    best_chromosome: np.ndarray
    best_fitness: float
    best_generation: int
    history_best: np.ndarray        # best fitness in the current population, per generation
    history_mean: np.ndarray        # mean fitness of the population, per generation
    history_best_so_far: np.ndarray # best fitness found up to the given generation
    history_unique: np.ndarray      # fraction of distinct chromosomes in the population (diversity)


# --- Selection --------------------------------------------------------------------------------

def tournament_selection(pop, fit, n_select, rng, k=3):
    """Pick n_select parents; each one is the fittest of k randomly drawn individuals."""
    contestants = rng.integers(0, len(pop), size=(n_select, k))
    winners = contestants[np.arange(n_select), np.argmax(fit[contestants], axis=1)]
    return pop[winners].copy()


def roulette_selection(pop, fit, n_select, rng):
    """Fitness proportional selection: P(i) = F_i / sum(F)."""
    idx = rng.choice(len(pop), size=n_select, p=fit / fit.sum())
    return pop[idx].copy()


def ranking_selection(pop, fit, n_select, rng, s=1.5):
    """Linear ranking selection with selection pressure s in [1, 2].

    Individuals are sorted by fitness; the worst one gets rank 0, the best rank N-1, and
    P(rank r) = (2 - s) / N + 2 r (s - 1) / (N (N - 1)).
    The best individual is expected to be selected s times, the worst one 2 - s times.
    """
    n = len(pop)
    ranks = np.empty(n)
    ranks[np.argsort(fit, kind="stable")] = np.arange(n)
    p = (2 - s) / n + 2 * ranks * (s - 1) / (n * (n - 1))
    idx = rng.choice(n, size=n_select, p=p / p.sum())
    return pop[idx].copy()


def select(pop, fit, n_select, cfg, rng):
    if cfg.selection == "tournament":
        return tournament_selection(pop, fit, n_select, rng, cfg.tournament_size)
    if cfg.selection == "roulette":
        return roulette_selection(pop, fit, n_select, rng)
    if cfg.selection == "ranking":
        return ranking_selection(pop, fit, n_select, rng, cfg.ranking_pressure)
    raise ValueError(f"unknown selection: {cfg.selection}")


# --- Crossover --------------------------------------------------------------------------------
# Each mask function returns a boolean vector: True = the gene is exchanged between the parents.

def one_point_mask(n_genes, rng):
    cut = rng.integers(1, n_genes)  # cut point between genes, both parts non-empty
    return np.arange(n_genes) >= cut


def two_point_mask(n_genes, rng):
    a, b = np.sort(rng.choice(np.arange(1, n_genes), size=2, replace=False))
    return (np.arange(n_genes) >= a) & (np.arange(n_genes) < b)  # middle segment [a, b)


def uniform_mask(n_genes, rng):
    return rng.random(n_genes) < 0.5  # every gene comes from either parent with prob. 1/2


CROSSOVER_MASKS = {"one_point": one_point_mask, "two_point": two_point_mask, "uniform": uniform_mask}


def crossover(parents, p_crossover, method, rng):
    """Parents are paired (0, 1), (2, 3), ...; a pair is crossed with probability p_crossover."""
    make_mask = CROSSOVER_MASKS[method]
    children = parents.copy()
    n_genes = parents.shape[1]
    for i in range(0, len(parents) - 1, 2):
        if rng.random() < p_crossover:
            mask = make_mask(n_genes, rng)
            children[i, mask] = parents[i + 1, mask]
            children[i + 1, mask] = parents[i, mask]
    return children


# --- Mutation ---------------------------------------------------------------------------------

def reset_mutation(pop, p_mutation, max_portions, rng):
    """Each gene is, with probability p_mutation, replaced by a random allowed value."""
    mask = rng.random(pop.shape) < p_mutation
    new_values = rng.integers(0, max_portions + 1, size=pop.shape)
    pop[mask] = new_values[mask]
    return pop


def creep_mutation(pop, p_mutation, max_portions, rng):
    """Each gene is, with probability p_mutation, changed by one portion (+1 or -1).

    A step that would leave {0, ..., max_i} is taken in the opposite direction.
    """
    mask = rng.random(pop.shape) < p_mutation
    step = rng.choice(np.array([-1, 1]), size=pop.shape)
    new = pop + step
    new = np.where((new < 0) | (new > max_portions), pop - step, new)
    pop[mask] = new[mask]
    return pop


def inversion_mutation(pop, p_mutation, max_portions, rng):
    """Each chromosome is, with probability p_mutation, inverted on a random segment.

    The order of genes in a segment [a, b] is reversed. Products have different portion limits,
    so a moved value can exceed the limit of its new position; such genes are repaired by
    clipping to max_i.
    """
    n_genes = pop.shape[1]
    for i in np.nonzero(rng.random(len(pop)) < p_mutation)[0]:
        a, b = np.sort(rng.choice(n_genes, size=2, replace=False))
        pop[i, a:b + 1] = pop[i, a:b + 1][::-1]
    np.minimum(pop, max_portions, out=pop)
    return pop


MUTATIONS = {"reset": reset_mutation, "creep": creep_mutation, "inversion": inversion_mutation}


# --- Main loop --------------------------------------------------------------------------------

def run_ga(problem: DietProblem, cfg: GAConfig) -> GAResult:
    rng = np.random.default_rng(cfg.seed)
    mutate = MUTATIONS[cfg.mutation]
    n_children = cfg.pop_size - cfg.elite_size

    pop = problem.random_population(cfg.pop_size, rng)
    fit = problem.fitness(pop)

    hist_best, hist_mean, hist_best_so_far, hist_unique = [], [], [], []
    best_idx = int(np.argmax(fit))
    best_chrom, best_fit, best_gen = pop[best_idx].copy(), fit[best_idx], 0

    for gen in range(cfg.generations + 1):
        idx = int(np.argmax(fit))
        if fit[idx] > best_fit:
            best_chrom, best_fit, best_gen = pop[idx].copy(), fit[idx], gen
        hist_best.append(fit[idx])
        hist_mean.append(fit.mean())
        hist_best_so_far.append(best_fit)
        hist_unique.append(len(np.unique(pop, axis=0)) / len(pop))

        if gen == cfg.generations:  # stop condition: maximum number of generations
            break

        # elitism: the e best individuals survive unchanged, the rest of the population is
        # replaced by children (with e = 0 this is the plain generational replacement of Task 1)
        elite = pop[np.argsort(fit)[len(pop) - cfg.elite_size:]]
        parents = select(pop, fit, n_children, cfg, rng)
        children = crossover(parents, cfg.p_crossover, cfg.crossover, rng)
        children = mutate(children, cfg.p_mutation, problem.max_portions, rng)
        pop = np.vstack([elite, children])
        fit = problem.fitness(pop)

    return GAResult(
        best_chromosome=best_chrom,
        best_fitness=float(best_fit),
        best_generation=best_gen,
        history_best=np.array(hist_best),
        history_mean=np.array(hist_mean),
        history_best_so_far=np.array(hist_best_so_far),
        history_unique=np.array(hist_unique),
    )


def exact_optimum(problem: DietProblem):
    """Reference solution: cheapest feasible menu found by integer linear programming.

    Used only to evaluate the quality of the GA results; returns None if scipy is missing.
    """
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError:
        return None
    res = milp(
        c=problem.prices,
        constraints=LinearConstraint(problem.content.T, problem.lower, problem.upper),
        integrality=np.ones(problem.n_genes),
        bounds=Bounds(0, problem.max_portions),
    )
    if not res.success:
        return None
    return np.round(res.x).astype(int)


def describe(problem: DietProblem, chromosome) -> str:
    chromosome = np.asarray(chromosome)
    lines = ["Jadłospis:"]
    for name, count, price in zip(problem.names, chromosome, problem.prices):
        if count:
            lines.append(f"  {count} x {name:<32} {count * price:6.2f} zł")
    lines.append(f"  {'Koszt łączny:':<36} {problem.cost(chromosome):6.2f} zł")
    lines.append("Wartości odżywcze (wymagany zakres):")
    totals = problem.nutrients(chromosome)
    for name, value, lo, hi in zip(NUTRIENTS, totals, problem.lower, problem.upper):
        ok = "OK" if lo <= value <= hi else "NARUSZENIE"
        lines.append(f"  {name:<8} {value:8.1f}   [{lo:g}, {hi:g}]  {ok}")
    lines.append(f"Dopuszczalne: {'tak' if problem.is_feasible(chromosome) else 'nie'}, "
                 f"przystosowanie F = {problem.fitness(chromosome):.5f}")
    return "\n".join(lines)
