"""Single GA run for the diet planning problem (Task 2: selectable operators).

Usage: python main.py [--pop 20] [--gen 300] [--selection tournament|roulette|ranking] [--k 3]
                      [--s 1.5] [--elite 0] [--crossover one_point|two_point|uniform] [--pc 0.8]
                      [--mutation reset|creep|inversion] [--pm 0.05] [--seed 1]
"""

import argparse
import sys

from ga import CROSSOVER_MASKS, MUTATIONS, DietProblem, GAConfig, describe, exact_optimum, run_ga


def main():
    parser = argparse.ArgumentParser(description="Genetic algorithm - diet planning (Task 2)")
    parser.add_argument("--pop", type=int, default=20, help="population size")
    parser.add_argument("--gen", type=int, default=300, help="number of generations (stop condition)")
    parser.add_argument("--selection", default="tournament", choices=["tournament", "roulette", "ranking"])
    parser.add_argument("--k", type=int, default=3, help="tournament size")
    parser.add_argument("--s", type=float, default=1.5, help="selection pressure of linear ranking, 1..2")
    parser.add_argument("--elite", type=int, default=0, help="number of elite individuals (0 = no elitism)")
    parser.add_argument("--crossover", default="one_point", choices=list(CROSSOVER_MASKS))
    parser.add_argument("--pc", type=float, default=0.8, help="crossover probability")
    parser.add_argument("--mutation", default="reset", choices=list(MUTATIONS))
    parser.add_argument("--pm", type=float, default=0.05,
                        help="mutation probability (per gene; per chromosome for inversion)")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    problem = DietProblem()
    cfg = GAConfig(pop_size=args.pop, generations=args.gen, selection=args.selection,
                   tournament_size=args.k, ranking_pressure=args.s, elite_size=args.elite,
                   crossover=args.crossover, p_crossover=args.pc, mutation=args.mutation,
                   p_mutation=args.pm, seed=args.seed)
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
