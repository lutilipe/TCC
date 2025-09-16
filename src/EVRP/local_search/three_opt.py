import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class ThreeOpt:
    """
    3-opt local search operator that removes three edges and reconnects the segments
    in a different way to improve the route. This is a more complex operator than 2-opt
    and can find improvements that 2-opt might miss.
    """
    
    def __init__(self, instance: Instance, max_iter: int = 5):
        self.instance = instance
        self.max_iter = max_iter

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply 3-opt local search to improve the solution.
        Optimizes individual routes by trying different 3-opt reconnections.
        
        Args:
            solution: The solution to improve
            
        Returns:
            bool: True if any improvement was made, False otherwise
        """
        if not solution.routes:
            return False
            
        improved = False
        
        for route in solution.routes:
            if self._three_opt_route(route):
                improved = True
        
        if improved:
            solution.evaluate()
            
        return improved

    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply 3-opt perturbation to diversify the solution.
        
        Args:
            solution: The solution to perturb
            
        Returns:
            Solution: The perturbed solution
        """
        for route in solution.routes:
            for _ in range(self.max_iter):
                self._three_opt_route(route, force_move=True)
        
        solution.evaluate()
        return solution

    def _three_opt_route(self, route: Route, force_move: bool = False) -> bool:
        """
        Apply 3-opt optimization to a single route.
        
        Args:
            route: The route to optimize
            force_move: If True, perform a random move even if not improving
            
        Returns:
            bool: True if the route was improved, False otherwise
        """
        if len(route.nodes) <= 4:  # Need at least depot + 2 nodes + depot
            return False
            
        best_route = copy.deepcopy(route)
        improved = True
        current_route = copy.deepcopy(route)
        iteration = 0

        while improved and iteration < self.max_iter:
            improved = False
            iteration += 1
            
            # Try all possible 3-opt moves
            for i in range(1, len(current_route.nodes) - 3):  # First cut
                for j in range(i + 1, len(current_route.nodes) - 2):  # Second cut
                    for k in range(j + 1, len(current_route.nodes) - 1):  # Third cut
                        
                        # Try different 3-opt reconnections
                        for reconnection_type in range(1, 8):  # 7 different 3-opt reconnections
                            new_route = self._apply_three_opt_reconnection(
                                current_route, i, j, k, reconnection_type
                            )
                            
                            if new_route is None:
                                continue
                            
                            # Evaluate the new route
                            new_route.evaluate(self.instance)
                            
                            # Check if the new route is better
                            if new_route.is_feasible and self._is_better_route(new_route, best_route):
                                best_route = new_route
                                current_route = new_route
                                improved = True
                                break
                        
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
        
        # If no improvement found but force_move is True, try a random 3-opt move
        if not improved and force_move:
            random_move = self._select_random_three_opt_move(route)
            if random_move:
                self._apply_three_opt_move(route, random_move)
                route.evaluate(self.instance)
                return True
        
        # Update the original route if improvement was found
        if self._is_better_route(best_route, route):
            route.nodes = best_route.nodes
            route.charging_decisions = best_route.charging_decisions
            route.evaluate(self.instance)
            return True
        
        return False

    def _apply_three_opt_reconnection(self, route: Route, i: int, j: int, k: int, 
                                    reconnection_type: int) -> Route:
        """
        Apply a specific 3-opt reconnection to a route.
        
        Args:
            route: The route to modify
            i, j, k: The three cut positions
            reconnection_type: The type of reconnection (1-7)
            
        Returns:
            Route: The new route with the reconnection applied, or None if invalid
        """
        if i >= j or j >= k or k >= len(route.nodes) - 1:
            return None
        
        new_route = copy.deepcopy(route)
        nodes = new_route.nodes
        
        # Split the route into segments
        segment1 = nodes[:i]  # Before first cut
        segment2 = nodes[i:j]  # Between first and second cut
        segment3 = nodes[j:k]  # Between second and third cut
        segment4 = nodes[k:]   # After third cut
        
        # Apply different reconnections based on type
        if reconnection_type == 1:
            # Original: A-B-C-D -> A-B-C-D (no change)
            return None
        elif reconnection_type == 2:
            # A-B-C-D -> A-C-B-D
            new_route.nodes = segment1 + segment3 + segment2 + segment4
        elif reconnection_type == 3:
            # A-B-C-D -> A-C-D-B
            new_route.nodes = segment1 + segment3 + segment4[:-1] + segment2 + segment4[-1:]
        elif reconnection_type == 4:
            # A-B-C-D -> A-D-B-C
            new_route.nodes = segment1 + segment4[:-1] + segment2 + segment3 + segment4[-1:]
        elif reconnection_type == 5:
            # A-B-C-D -> A-D-C-B
            new_route.nodes = segment1 + segment4[:-1] + segment3 + segment2 + segment4[-1:]
        elif reconnection_type == 6:
            # A-B-C-D -> A-B-D-C
            new_route.nodes = segment1 + segment2 + segment4[:-1] + segment3 + segment4[-1:]
        elif reconnection_type == 7:
            # A-B-C-D -> A-D-B-C (reverse of type 4)
            new_route.nodes = segment1 + segment4[:-1] + segment2 + segment3 + segment4[-1:]
        
        return new_route

    def _select_random_three_opt_move(self, route: Route) -> dict:
        """
        Select a random 3-opt move for perturbation.
        
        Args:
            route: The route to modify
            
        Returns:
            dict: Random move information, or None if no valid moves
        """
        if len(route.nodes) <= 4:
            return None
        
        # Generate random cut positions
        i = random.randint(1, len(route.nodes) - 4)
        j = random.randint(i + 1, len(route.nodes) - 3)
        k = random.randint(j + 1, len(route.nodes) - 2)
        
        # Select random reconnection type
        reconnection_type = random.randint(2, 7)  # Skip type 1 (no change)
        
        return {
            'i': i,
            'j': j,
            'k': k,
            'reconnection_type': reconnection_type
        }

    def _apply_three_opt_move(self, route: Route, move: dict) -> None:
        """
        Apply a 3-opt move to the route.
        
        Args:
            route: The route to modify
            move: The move to apply
        """
        i = move['i']
        j = move['j']
        k = move['k']
        reconnection_type = move['reconnection_type']
        
        new_route = self._apply_three_opt_reconnection(route, i, j, k, reconnection_type)
        
        if new_route is not None:
            route.nodes = new_route.nodes
            route.charging_decisions = new_route.charging_decisions

    def _is_better_route(self, route1: Route, route2: Route) -> bool:
        """
        Check if route1 is better than route2.
        A route is better if it's feasible and has lower total distance or cost.
        
        Args:
            route1: The first route
            route2: The second route
            
        Returns:
            bool: True if route1 is better than route2
        """
        if not route1.is_feasible:
            return False
        
        if not route2.is_feasible:
            return True
        
        return route1.dominates(route2)
