"""Single GA run for the diet planning problem.

Usage: python main.py [--pop 20] [--gen 200] [--pc 0.8] [--pm 0.05] [--k 3] [--seed 1]
"""

import argparse
import sys

from ga import DietProblem, GAConfig, describe, exact_optimum, run_ga


def main():
    parser = argparse.ArgumentParser(description="Genetic algorithm - diet planning")
    parser.add_argument("--pop", type=int, default=20, help="population size")
    parser.add_argument("--gen", type=int, default=200, help="number of generations (stop condition)")
    parser.add_argument("--pc", type=float, default=0.8, help="crossover probability")
    parser.add_argument("--pm", type=float, default=0.05, help="mutation probability (per gene)")
    parser.add_argument("--k", type=int, default=3, help="tournament size")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    problem = DietProblem()
    cfg = GAConfig(pop_size=args.pop, generations=args.gen, p_crossover=args.pc,
                   p_mutation=args.pm, tournament_size=args.k, seed=args.seed)
    result = run_ga(problem, cfg)

    print(f"Parametry: {cfg}")
    print(f"Najlepsze rozwiązanie znalezione w pokoleniu {result.best_generation}")
    print(f"Chromosom: {result.best_chromosome.tolist()}\n")
    print(describe(problem, result.best_chromosome))

    optimum = exact_optimum(problem)
    if optimum is not None:
        print(f"\nOptimum referencyjne (ILP): {problem.cost(optimum):.2f} zł, "
              f"strata GA: {problem.cost(result.best_chromosome) - problem.cost(optimum):+.2f} zł")


if __name__ == "__main__":
    main()
