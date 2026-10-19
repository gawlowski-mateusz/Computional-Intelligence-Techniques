"""Basic genetic algorithm for the diet planning problem.

Chromosome  : integer vector x = (x_1, ..., x_n), x_i in {0, ..., max_i}
              -> number of portions of product i in the daily menu.
Fitness     : F(x) = 1 / (1 + cost(x) + W * violation(x))   (maximised, F in (0, 1])
Selection   : tournament selection (size k)
Crossover   : one-point crossover with probability p_c
Mutation    : per-gene random reset with probability p_m
Stop        : fixed number of generations
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
    p_crossover: float = 0.8
    p_mutation: float = 0.05
    tournament_size: int = 3
    seed: int | None = None


@dataclass
class GAResult:
    best_chromosome: np.ndarray
    best_fitness: float
    best_generation: int
    history_best: np.ndarray        # best fitness in the current population, per generation
    history_mean: np.ndarray        # mean fitness of the population, per generation
    history_best_so_far: np.ndarray # best fitness found up to the given generation


def tournament_selection(pop, fit, n_select, k, rng):
    """Pick n_select parents; each one is the fittest of k randomly drawn individuals."""
    contestants = rng.integers(0, len(pop), size=(n_select, k))
    winners = contestants[np.arange(n_select), np.argmax(fit[contestants], axis=1)]
    return pop[winners].copy()


def one_point_crossover(parents, p_crossover, rng):
    children = parents.copy()
    n_genes = parents.shape[1]
    for i in range(0, len(parents) - 1, 2):
        if rng.random() < p_crossover:
            cut = rng.integers(1, n_genes)  # cut point between genes, both parts non-empty
            children[i, cut:] = parents[i + 1, cut:]
            children[i + 1, cut:] = parents[i, cut:]
    return children


def mutation(pop, p_mutation, max_portions, rng):
    """Each gene is, with probability p_mutation, replaced by a random allowed value."""
    mask = rng.random(pop.shape) < p_mutation
    new_values = rng.integers(0, max_portions + 1, size=pop.shape)
    pop[mask] = new_values[mask]
    return pop


def run_ga(problem: DietProblem, cfg: GAConfig) -> GAResult:
    rng = np.random.default_rng(cfg.seed)

    pop = problem.random_population(cfg.pop_size, rng)
    fit = problem.fitness(pop)

    hist_best, hist_mean, hist_best_so_far = [], [], []
    best_idx = int(np.argmax(fit))
    best_chrom, best_fit, best_gen = pop[best_idx].copy(), fit[best_idx], 0

    for gen in range(cfg.generations + 1):
        idx = int(np.argmax(fit))
        if fit[idx] > best_fit:
            best_chrom, best_fit, best_gen = pop[idx].copy(), fit[idx], gen
        hist_best.append(fit[idx])
        hist_mean.append(fit.mean())
        hist_best_so_far.append(best_fit)

        if gen == cfg.generations:  # stop condition: maximum number of generations
            break

        parents = tournament_selection(pop, fit, cfg.pop_size, cfg.tournament_size, rng)
        children = one_point_crossover(parents, cfg.p_crossover, rng)
        pop = mutation(children, cfg.p_mutation, problem.max_portions, rng)
        fit = problem.fitness(pop)

    return GAResult(
        best_chromosome=best_chrom,
        best_fitness=float(best_fit),
        best_generation=best_gen,
        history_best=np.array(hist_best),
        history_mean=np.array(hist_mean),
        history_best_so_far=np.array(hist_best_so_far),
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
