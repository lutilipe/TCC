from EVRP.constructive_heuristic import ConstructiveHeuristic
from EVRP.create_instance import create_evrp_instance
from utils.plot_solution import plot_solution
from utils.summary import print_instance_summary

if __name__ == "__main__":
    print("EVRP Solver using General Variable Neighborhood Search (GVNS)")
    print("=" * 70)
    
    instance = create_evrp_instance("./data/datos-10-N100.txt")
    print_instance_summary(instance)

    constructiveHeuristic = ConstructiveHeuristic(instance)
    pop = []
    while len(pop) < 50:
        solution = constructiveHeuristic.build_initial_solution()
        while not solution.is_feasible:
            solution = constructiveHeuristic.build_initial_solution()
        print(solution.total_cost, solution.total_distance)
        pop.append(solution)
    