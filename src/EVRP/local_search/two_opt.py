import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class TwoOpt:
    def __init__(self, instance: Instance, max_iter = 1):
        self.instance = instance
        self.max_iter = max_iter

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply 2-opt perturbation to all routes in a solution.
        Returns True if any improvement was made, False otherwise.
        """
        improved = False
        for _ in range(self.max_iter):
            route_idx = random.randint(0, len(solution.routes) - 1)
            route = solution.routes[route_idx]
            if self.two_opt(route):
                improved = True
        
        return improved
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply 2-opt perturbation to all routes in a solution.
        Returns True if any improvement was made, False otherwise.
        """
        for _ in range(self.max_iter):
            route_idx = random.randint(0, len(solution.routes) - 1)
            route = solution.routes[route_idx]
            self.two_opt_random(route)
        
        return solution
    
    def two_opt(self, route: Route) -> bool:
        """
        Apply 2-opt intra-route optimization to a single route.
        Returns True if any improvement was made, False otherwise.
        """
        if len(route.nodes) <= 3:  # Need at least depot + 2 nodes + depot
            return False
            
        best_route = copy.deepcopy(route)
        improved = True
        current_route = copy.deepcopy(route)

        while improved:
            improved = False
            
            for i in range(1, len(current_route.nodes) - 2):
                for j in range(i + 1, len(current_route.nodes) - 1):
                    if j - i == 1:
                        continue
                    
                    new_route = copy.deepcopy(current_route)
                    new_route.nodes = (current_route.nodes[:i] + 
                                     current_route.nodes[i:j+1][::-1] + 
                                     current_route.nodes[j+1:])
                    
                    new_route.evaluate(self.instance)
                    
                    if new_route.is_feasible and self._is_better_route(new_route, best_route):
                        best_route = new_route
                        current_route = new_route
                        improved = True
                        break
                if improved:
                    break
        
        if self._is_better_route(best_route, route):
            route.nodes = best_route.nodes
            route.charging_decisions = best_route.charging_decisions
            route.evaluate(self.instance)
            return True
        
        return False
    
    def two_opt_random(self, route: Route) -> bool:
        """
        Apply 2-opt intra-route optimization to a single route.
        Returns True if any improvement was made, False otherwise.
        """
        if len(route.nodes) <= 3:
            return False
            
        i = random.randint(1, len(route.nodes) - 3)
        j = random.randint(i + 1, len(route.nodes) - 2)

        new_route = copy.deepcopy(route)
        new_route.nodes = (
            route.nodes[:i] + 
            route.nodes[i:j+1][::-1] + 
            route.nodes[j+1:]
        )
        new_route.evaluate(self.instance)
        if self._is_better_route(new_route, route):
            route.nodes = new_route.nodes
            route.charging_decisions = new_route.charging_decisions
            route.evaluate(self.instance)
            return True

        return False
    
    def _is_better_route(self, route1: Route, route2: Route) -> bool:
        """
        Check if route1 is better than route2.
        A route is better if it's feasible and has lower total distance or cost.
        """
        if not route1.is_feasible:
            return False
        
        if not route2.is_feasible:
            return True
        
        return route1.dominates(route2)