import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class TwoOptStar:
    def __init__(self, instance: Instance, max_iter: int = 1, select_best = True):
        self.instance = instance
        self.max_iter = max_iter
        self.select_best = select_best

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply 2-opt* perturbation to all pairs of routes in a solution.
        Returns True if any improvement was made, False otherwise.
        """
        if len(solution.routes) < 2:
            return False
        
        route_indices = random.sample(range(len(solution.routes)), 2)
        route1_idx, route2_idx = route_indices[0], route_indices[1]
        
        route1 = solution.routes[route1_idx]
        route2 = solution.routes[route2_idx]
        
        return self.two_opt_star(route1, route2)
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply 2-opt* perturbation to all pairs of routes in a solution.
        Returns the modified solution.
        """
        for _ in range(self.max_iter):
            if len(solution.routes) < 2:
                return solution
            
            route_indices = random.sample(range(len(solution.routes)), 2)
            route1_idx, route2_idx = route_indices[0], route_indices[1]
            
            route1 = solution.routes[route1_idx]
            route2 = solution.routes[route2_idx]

            self.two_opt_star_random(route1, route2)
        
        return solution
    
    def two_opt_star_random(self, route1: Route, route2: Route) -> bool:
        """
        Apply 2-opt* inter-route optimization between two routes.
        
        The 2-opt* operator works by:
        1. Selecting two cutting points (i,j) in route1 and (k,l) in route2
        2. Creating new routes by swapping the segments:
           - New route1: [0...i] + [k...l] + [j+1...end]
           - New route2: [0...k] + [i+1...j] + [l+1...end]
        
        Returns True if any improvement was made, False otherwise.
        """
        if len(route1.nodes) <= 2 or len(route2.nodes) <= 2:
            return False
            
        best_route1 = copy.deepcopy(route1)
        best_route2 = copy.deepcopy(route2)
        
        valid_indices_r1 = list(range(1, len(route1.nodes) - 1))
        valid_indices_r2 = list(range(1, len(route2.nodes) - 1))

        i = random.choice(valid_indices_r1)
        j = random.choice(valid_indices_r2)
        
        new_route1, new_route2 = self._create_new_routes(
            route1, route2, i, j
        )
            
        if new_route1 is None or new_route2 is None:
            return False
        
        new_route1.evaluate(self.instance)
        new_route2.evaluate(self.instance)
        
        if (new_route1.is_feasible and new_route2.is_feasible and
                self._is_better_solution(new_route1, new_route2, best_route1, best_route2)):
            best_route1 = new_route1
            best_route2 = new_route2
            
            route1.nodes = best_route1.nodes
            route1.charging_decisions = best_route1.charging_decisions
            route1.evaluate(self.instance)
            
            route2.nodes = best_route2.nodes
            route2.charging_decisions = best_route2.charging_decisions
            route2.evaluate(self.instance)
            return True
        
        return False
    
    def two_opt_star(self, route1: Route, route2: Route) -> bool:
        """
        Apply 2-opt* inter-route optimization between two routes.
        
        The 2-opt* operator works by:
        1. Selecting two cutting points (i,j) in route1 and (k,l) in route2
        2. Creating new routes by swapping the segments:
           - New route1: [0...i] + [k...l] + [j+1...end]
           - New route2: [0...k] + [i+1...j] + [l+1...end]
        
        Returns True if any improvement was made, False otherwise.
        """
        if len(route1.nodes) <= 2 or len(route2.nodes) <= 2:  # Need at least depot + 1 node + depot
            return False
            
        best_route1 = copy.deepcopy(route1)
        best_route2 = copy.deepcopy(route2)
        
        for i in range(1, len(route1.nodes) - 1):
            for j in range(1, len(route2.nodes) - 1):
                new_route1, new_route2 = self._create_new_routes(
                    route1, route2, i, j
                )
                
                if new_route1 is None or new_route2 is None:
                    continue
                
                new_route1.evaluate(self.instance)
                new_route2.evaluate(self.instance)
                
                if (new_route1.is_feasible and new_route2.is_feasible and
                    self._is_better_solution(new_route1, new_route2, best_route1, best_route2)):
                    best_route1 = new_route1
                    best_route2 = new_route2
                    
                    route1.nodes = best_route1.nodes
                    route1.charging_decisions = best_route1.charging_decisions
                    route1.evaluate(self.instance)
                    
                    route2.nodes = best_route2.nodes
                    route2.charging_decisions = best_route2.charging_decisions
                    route2.evaluate(self.instance)

                    return True
        
        return False
    
    def _create_new_routes(self, route1: Route, route2: Route, 
                          i: int, j: int) -> Tuple[Route, Route]:
        """
        Create new routes by applying 2-opt* swap between segments.
        
        Args:
            route1, route2: Original routes
            i, j: Cutting points in route1 (segment [i+1...j] will be swapped)
            k, l: Cutting points in route2 (segment [k+1...l] will be swapped)
        
        Returns:
            Tuple of new routes, or (None, None) if invalid
        """
        try:
            new_route1 = Route()
            new_route1.nodes = (route1.nodes[:i] + 
                              route2.nodes[j:])
            
            new_route2 = Route()
            new_route2.nodes = (route2.nodes[:j] + 
                              route1.nodes[i:])
            
            route1_original_nodes = {node.id for node in route1.nodes}
            route2_original_nodes = {node.id for node in route2.nodes}
            
            new_route1.charging_decisions = {}
            for node in new_route1.nodes:
                if node.type == NodeType.STATION:
                    if node.id in route1_original_nodes and node.id in route1.charging_decisions:
                        new_route1.charging_decisions[node.id] = route1.charging_decisions[node.id]
                    elif node.id in route2_original_nodes and node.id in route2.charging_decisions:
                        new_route1.charging_decisions[node.id] = route2.charging_decisions[node.id]
            
            new_route2.charging_decisions = {}
            for node in new_route2.nodes:
                if node.type == NodeType.STATION:
                    if node.id in route1_original_nodes and node.id in route1.charging_decisions:
                        new_route2.charging_decisions[node.id] = route1.charging_decisions[node.id]
                    elif node.id in route2_original_nodes and node.id in route2.charging_decisions:
                        new_route2.charging_decisions[node.id] = route2.charging_decisions[node.id]
            
            def is_valid_depot_loop(route: Route) -> bool:
                if not route.nodes:
                    return False
                if route.nodes[0].type != NodeType.DEPOT or route.nodes[-1].type != NodeType.DEPOT:
                    return False
                return True

            if not is_valid_depot_loop(new_route1) or not is_valid_depot_loop(new_route2):
                return None, None
            
            return new_route1, new_route2
            
        except (IndexError, AttributeError):
            return None, None
    
    def _is_better_solution(self, new_route1: Route, new_route2: Route,
                           current_route1: Route, current_route2: Route) -> bool:
        """
        Check if the new route pair is better than the current route pair.
        
        A solution is better if:
        1. Both routes are feasible
        2. The total distance or cost is reduced
        """
        if not self.select_best:
            return True

        if not new_route1.is_feasible or not new_route2.is_feasible:
            return False
        
        if not current_route1.is_feasible or not current_route2.is_feasible:
            return True
        
        new_total_distance = new_route1.total_distance + new_route2.total_distance
        new_total_cost = new_route1.total_cost + new_route2.total_cost
        
        current_total_distance = current_route1.total_distance + current_route2.total_distance
        current_total_cost = current_route1.total_cost + current_route2.total_cost
        
        if (new_total_distance <= current_total_distance and
            new_total_cost <= current_total_cost):
            if (new_total_distance < current_total_distance or
                new_total_cost < current_total_cost):
                return True
        
        return False