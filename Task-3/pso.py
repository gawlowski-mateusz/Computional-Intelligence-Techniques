"""Particle swarm optimisation (PSO) for the diet planning problem (Task 3).

The problem, the penalised objective and the fitness are the same as in Tasks 1 and 2
(DietProblem from ga.py). PSO works in a continuous space, so every particle has a real-valued
position and velocity, and the menu is obtained by rounding:

Position    : z = (z_1, ..., z_n), z_i in [-0.5, max_i + 0.5]
Decoding    : x_i = round(z_i), clipped to {0, ..., max_i}  -> number of portions of product i
              (every integer value gets an interval of the same length 1)
Velocity    : v_i = w v_i + c1 r1 (p_i - z_i) + c2 r2 (g_i - z_i),  r1, r2 ~ U(0, 1) per dimension
              p = personal best position of the particle, g = best position of its neighbourhood
              |v_i| <= v_max * (max_i + 1)   (velocity clamping)
Move        : z = z + v; a coordinate that leaves the box is set to the bound and its velocity
              to 0 (absorbing walls)
Inertia     : constant w, or decreasing linearly from w_start to w_end over the run
Topology    : global (gbest: every particle sees the best of the whole swarm) or
              ring (lbest: a particle sees itself and its two neighbours i-1, i+1)
Stop        : fixed number of iterations

One iteration evaluates every particle once, so a swarm of S particles run for T iterations uses
S (T + 1) evaluations, exactly like a GA with population S and T generations.
"""

from dataclasses import dataclass

import numpy as np

from ga import DietProblem


@dataclass
class PSOConfig:
    swarm_size: int = 20
    iterations: int = 300
    w_start: float = 0.729          # inertia weight (at the start of the run)
    w_end: float | None = None      # None = constant inertia; otherwise linear w_start -> w_end
    c1: float = 1.49445             # cognitive coefficient (pull towards the personal best)
    c2: float = 1.49445             # social coefficient (pull towards the neighbourhood best)
    topology: str = "global"        # "global" | "ring"
    v_max: float = 0.5              # velocity limit as a fraction of the range of the variable
    seed: int | None = None


@dataclass
class PSOResult:
    best_solution: np.ndarray       # best menu found (integer vector)
    best_fitness: float
    best_iteration: int
    history_best_so_far: np.ndarray # best fitness found up to the given iteration
    history_mean: np.ndarray        # mean fitness of the current positions
    history_unique: np.ndarray      # fraction of distinct menus in the swarm (diversity)
    history_moved: np.ndarray       # fraction of particles whose menu changed in the iteration
    history_distance: np.ndarray    # mean distance of the menus from the best menu [portions]


def decode(z, max_portions):
    """Continuous positions -> integer menus."""
    return np.clip(np.rint(z), 0, max_portions).astype(int)


def neighbourhood_best(pbest_f, topology):
    """Index of the best personal best in the neighbourhood of every particle."""
    n = len(pbest_f)
    if topology == "global":
        return np.full(n, int(np.argmin(pbest_f)))
    if topology == "ring":
        idx = np.arange(n)
        neigh = np.stack([(idx - 1) % n, idx, (idx + 1) % n])      # (3, n)
        return neigh[np.argmin(pbest_f[neigh], axis=0), idx]
    raise ValueError(f"unknown topology: {topology}")


def run_pso(problem: DietProblem, cfg: PSOConfig) -> PSOResult:
    rng = np.random.default_rng(cfg.seed)
    s, n, maxp = cfg.swarm_size, problem.n_genes, problem.max_portions
    lo, hi = np.full(n, -0.5), maxp + 0.5
    v_max = cfg.v_max * (hi - lo)

    z = rng.uniform(lo, hi, size=(s, n))
    v = rng.uniform(-v_max, v_max, size=(s, n))
    x = decode(z, maxp)
    f = problem.objective(x)
    pbest, pbest_f = z.copy(), f.copy()

    i0 = int(np.argmin(f))
    best_x, best_f, best_it = x[i0].copy(), f[i0], 0
    hist_best, hist_mean, hist_unique, hist_moved, hist_dist = [], [], [], [np.nan], []

    for it in range(cfg.iterations + 1):
        i = int(np.argmin(f))
        if f[i] < best_f:
            best_x, best_f, best_it = x[i].copy(), f[i], it
        hist_best.append(1.0 / (1.0 + best_f))
        hist_mean.append(np.mean(1.0 / (1.0 + f)))
        hist_unique.append(len(np.unique(x, axis=0)) / s)
        hist_dist.append(np.mean(np.linalg.norm(x - best_x, axis=1)))

        if it == cfg.iterations:  # stop condition: maximum number of iterations
            break

        if cfg.w_end is None:
            w = cfg.w_start
        else:
            w = cfg.w_start + (cfg.w_end - cfg.w_start) * it / max(cfg.iterations - 1, 1)
        attractor = pbest[neighbourhood_best(pbest_f, cfg.topology)]
        r1, r2 = rng.random((s, n)), rng.random((s, n))
        v = w * v + cfg.c1 * r1 * (pbest - z) + cfg.c2 * r2 * (attractor - z)
        np.clip(v, -v_max, v_max, out=v)
        z = z + v
        outside = (z < lo) | (z > hi)
        z = np.clip(z, lo, hi)
        v[outside] = 0.0

        x_prev = x
        x = decode(z, maxp)
        f = problem.objective(x)
        hist_moved.append(np.mean(np.any(x != x_prev, axis=1)))
        improved = f < pbest_f
        pbest[improved], pbest_f[improved] = z[improved], f[improved]

    return PSOResult(
        best_solution=best_x,
        best_fitness=float(1.0 / (1.0 + best_f)),
        best_iteration=best_it,
        history_best_so_far=np.array(hist_best),
        history_mean=np.array(hist_mean),
        history_unique=np.array(hist_unique),
        history_moved=np.array(hist_moved),
        history_distance=np.array(hist_dist),
    )
