"""Single PSO run for the diet planning problem (Task 3).

Usage: python main.py [--swarm 20] [--iter 300] [--w 0.729] [--w-end W] [--c1 1.49445] [--c2 1.49445]
                      [--topology global|ring] [--vmax 0.5] [--seed 1]
"""

import argparse
import sys

from ga import DietProblem, describe, exact_optimum
from pso import PSOConfig, run_pso


def main():
    parser = argparse.ArgumentParser(description="Particle swarm optimisation - diet planning (Task 3)")
    parser.add_argument("--swarm", type=int, default=20, help="number of particles S")
    parser.add_argument("--iter", type=int, default=300, help="number of iterations (stop condition)")
    parser.add_argument("--w", type=float, default=0.729, help="inertia weight (at the start)")
    parser.add_argument("--w-end", type=float, default=None,
                        help="final inertia weight (linear decrease); omitted = constant w")
    parser.add_argument("--c1", type=float, default=1.49445, help="cognitive coefficient")
    parser.add_argument("--c2", type=float, default=1.49445, help="social coefficient")
    parser.add_argument("--topology", default="global", choices=["global", "ring"])
    parser.add_argument("--vmax", type=float, default=0.5,
                        help="velocity limit as a fraction of the range of a variable")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    problem = DietProblem()
    cfg = PSOConfig(swarm_size=args.swarm, iterations=args.iter, w_start=args.w, w_end=args.w_end,
                    c1=args.c1, c2=args.c2, topology=args.topology, v_max=args.vmax, seed=args.seed)
    result = run_pso(problem, cfg)

    print(f"Parametry: {cfg}")
    print(f"Ocen funkcji celu: {cfg.swarm_size * (cfg.iterations + 1)}")
    print(f"Najlepsze rozwiązanie znalezione w iteracji {result.best_iteration}")
    print(f"Rozwiązanie: {result.best_solution.tolist()}\n")
    print(describe(problem, result.best_solution))

    optimum = exact_optimum(problem)
    if optimum is not None:
        print(f"\nOptimum referencyjne (ILP): {problem.cost(optimum):.2f} zł, "
              f"strata PSO: {problem.cost(result.best_solution) - problem.cost(optimum):+.2f} zł")


if __name__ == "__main__":
    main()
