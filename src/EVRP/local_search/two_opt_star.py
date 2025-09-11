import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class TwoOptStar:
    def __init__(self, instance: Instance, max_iter = 3):
        self.instance = instance
        self.max_iter = max_iter

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply 2-opt star to all route pairs in a solution.
        Returns True if any improvement was made, False otherwise.
        """
        if len(solution.routes) < 2:
            return False
        
        return self.two_opt_star(solution)
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply 2-opt star perturbation to all route pairs in a solution.
        """
        for _ in range(self.max_iter):
            self.local_search(solution)
        
        return solution
    
    def two_opt_star(self, solution: 'Solution') -> bool:
        """
        Apply 2-opt star inter-route optimization using random selection.
        Swaps tails between two routes to improve the solution.
        Returns True if any improvement was made, False otherwise.
        """
        if len(solution.routes) < 2:
            return False
        
        improved = True
        total_improvements = 0
        max_attempts = 50  # Maximum number of random attempts per iteration
        
        while improved:
            improved = False
            attempts = 0
            
            while attempts < max_attempts and not improved:
                attempts += 1
                
                # Randomly select two different routes
                route_indices = random.sample(range(len(solution.routes)), 2)
                i, j = route_indices[0], route_indices[1]
                
                route_a = solution.routes[i]
                route_b = solution.routes[j]
                
                # Skip if routes are too short (need at least depot + 1 node + depot)
                if len(route_a.nodes) <= 3 or len(route_b.nodes) <= 3:
                    continue
                
                # Randomly select cut positions in both routes
                cut_a = random.randint(1, len(route_a.nodes) - 2)  # Skip depot positions
                cut_b = random.randint(1, len(route_b.nodes) - 2)  # Skip depot positions
                
                # Create new routes by swapping tails
                new_route_a, new_route_b = self._swap_tails(route_a, route_b, cut_a, cut_b)
                
                # Evaluate the new routes
                new_route_a.evaluate(self.instance)
                new_route_b.evaluate(self.instance)
                
                # Check if both routes are feasible and better
                if (new_route_a.is_feasible and new_route_b.is_feasible and
                    self._is_improvement(route_a, route_b, new_route_a, new_route_b)):
                    
                    # Accept the swap
                    route_a.nodes = new_route_a.nodes
                    route_a.charging_decisions = new_route_a.charging_decisions
                    route_a.evaluate(self.instance)
                    
                    route_b.nodes = new_route_b.nodes
                    route_b.charging_decisions = new_route_b.charging_decisions
                    route_b.evaluate(self.instance)
                    
                    improved = True
                    total_improvements += 1
        
        return total_improvements > 0
    
    def _swap_tails(self, route_a: Route, route_b: Route, cut_a: int, cut_b: int) -> Tuple[Route, Route]:
        """
        Create new routes by swapping tails after cut positions.
        """
        new_route_a = copy.deepcopy(route_a)
        new_route_b = copy.deepcopy(route_b)
        
        # Swap tails: route_a gets head of route_a + tail of route_b
        # route_b gets head of route_b + tail of route_a
        new_route_a.nodes = route_a.nodes[:cut_a] + route_b.nodes[cut_b:]
        new_route_b.nodes = route_b.nodes[:cut_b] + route_a.nodes[cut_a:]
        
        return new_route_a, new_route_b
    
    def _is_improvement(self, old_route_a: Route, old_route_b: Route, 
                       new_route_a: Route, new_route_b: Route) -> bool:
        """
        Check if the new route pair is better than the old one.
        """
        old_total_cost = old_route_a.total_cost + old_route_b.total_cost
        old_total_distance = old_route_a.total_distance + old_route_b.total_distance
        
        new_total_cost = new_route_a.total_cost + new_route_b.total_cost
        new_total_distance = new_route_a.total_distance + new_route_b.total_distance
        
        # Check if new solution is better (lower cost or distance)
        return (new_total_cost < old_total_cost or 
                (new_total_cost == old_total_cost and new_total_distance < old_total_distance))
   