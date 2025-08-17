from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class TwoOpt:
    def __init__(self, instance: Instance):
        self.instance = instance

    def run(self, solution: 'Solution') -> bool:
        """
        Apply 2-opt to all routes in a solution.
        Returns True if any improvement was made, False otherwise.
        """
        improved = False
        
        for route in solution.routes:
            route_improved = self.two_opt(route)
            if route_improved:
                improved = True
        
        return improved
    
    def two_opt(self, route: Route) -> bool:
        """
        Apply 2-opt local search to improve the route.
        Returns True if any improvement was made, False otherwise.
        """
        if not route.nodes or len(route.nodes) < 4:
            return False
        
        # Ensure route has valid structure
        if route.nodes[0].type != NodeType.DEPOT or route.nodes[-1].type != NodeType.DEPOT:
            return False
        
        # Ensure we have enough nodes for 2-opt to work
        if len(route.nodes) < 4:
            return False
        
        # Additional safety check for node types
        for node in route.nodes:
            if not hasattr(node, 'type') or not hasattr(node, 'id'):
                return False
        
        improved = False
        
        # Get route legs (segments between depot and recharge stations or between recharge stations)
        legs = self._get_route_legs(route)
        
        # Filter out invalid legs
        valid_legs = []
        for leg_start, leg_end in legs:
            if (leg_start >= 0 and leg_end < len(route.nodes) and 
                leg_start < leg_end and leg_end - leg_start >= 2):
                valid_legs.append((leg_start, leg_end))
        
        # Apply 2-opt to each valid leg
        for leg_start, leg_end in valid_legs:
            leg_improved = self._two_opt_leg(route, leg_start, leg_end)
            if leg_improved:
                improved = True
                # Re-evaluate the route after modification to ensure feasibility
                try:
                    route.evaluate(self.instance)
                    if not route.is_feasible:
                        # If route becomes infeasible, revert the change
                        # This is a simplified approach - in practice you might want to implement
                        # a more sophisticated rollback mechanism
                        return False
                except Exception as e:
                    # If evaluation fails, return False
                    return False
        
        return improved
    
    def _get_route_legs(self, route: Route) -> List[Tuple[int, int]]:
        """
        Get the legs of a route. A leg is a segment between:
        - depot and a recharge station
        - two recharge stations
        - depot and depot (if no recharge stations)
        """
        if not route.nodes:
            return []
            
        legs = []
        leg_start = 0
        
        for i, node in enumerate(route.nodes):
            # Check if this is a recharge station (excluding depot)
            if (node.type == NodeType.STATION and 
                i > 0 and i < len(route.nodes) - 1):
                # End current leg and start new one
                legs.append((leg_start, i))
                leg_start = i
        
        # Add the last leg (from last station to depot, or from depot to depot)
        # Ensure the leg has at least 3 nodes for 2-opt to work
        if leg_start < len(route.nodes) - 2:
            legs.append((leg_start, len(route.nodes) - 1))
        elif len(route.nodes) >= 4:  # Need at least 4 nodes for 2-opt
            # If no stations, create a single leg for the entire route
            legs.append((0, len(route.nodes) - 1))
        
        return legs
    
    def _two_opt_leg(self, route: Route, start_idx: int, end_idx: int) -> bool:
        """
        Apply 2-opt to a specific leg of the route.
        Returns True if any improvement was made, False otherwise.
        """
        if end_idx - start_idx < 2:
            return False
        
        # Additional safety checks
        if start_idx < 0 or end_idx >= len(route.nodes):
            return False
        
        improved = False
        
        while True:
            best_improvement = 0
            best_i, best_j = -1, -1
            
            # Evaluate all possible 2-opt moves on this leg
            for i in range(start_idx, end_idx):
                for j in range(i + 2, end_idx):
                    # Additional safety checks
                    if j >= len(route.nodes) - 1 or i + 1 >= len(route.nodes):
                        continue
                    improvement = self._evaluate_2opt_move(route, i, j)
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_i, best_j = i, j
            
            # If no improvement found, stop
            if best_improvement <= 0:
                break
            
            # Additional safety check before applying the move
            if (best_i < 0 or best_j < 0 or 
                best_i >= len(route.nodes) - 1 or best_j >= len(route.nodes) - 1):
                break
            
            # Apply the best move
            self._apply_2opt_move(route, best_i, best_j)
            improved = True
            
            # Re-evaluate to ensure feasibility
            try:
                route.evaluate(self.instance)
                if not route.is_feasible:
                    # Revert the move if it makes the route infeasible
                    self._apply_2opt_move(route, best_i, best_j)
                    route.evaluate(self.instance)
                    improved = False
                    break
            except Exception as e:
                # If evaluation fails, revert the move
                self._apply_2opt_move(route, best_i, best_j)
                improved = False
                break
        
        return improved
    
    def _evaluate_2opt_move(self, route: Route, i: int, j: int) -> float:
        """
        Evaluate the cost improvement of a 2-opt move.
        Returns the improvement in total distance (positive means improvement).
        """
        if i >= j or i < 0 or j >= len(route.nodes) - 1:
            return 0
        
        # Additional safety checks
        if i + 1 >= len(route.nodes) or j + 1 >= len(route.nodes):
            return 0
        
        # Current edges: (i, i+1) and (j, j+1)
        # New edges: (i, j) and (i+1, j+1)
        
        try:
            # Additional safety checks for node access
            if (i >= len(route.nodes) or i + 1 >= len(route.nodes) or 
                j >= len(route.nodes) or j + 1 >= len(route.nodes)):
                return 0
            
            # Check if node IDs exist in distance matrix
            node_ids = [route.nodes[i].id, route.nodes[i+1].id, 
                       route.nodes[j].id, route.nodes[j+1].id]
            
            for node_id in node_ids:
                if node_id not in self.instance.distance_matrix:
                    return 0
                for other_id in node_ids:
                    if other_id not in self.instance.distance_matrix[node_id]:
                        return 0
                
            current_dist = (self.instance.distance_matrix[route.nodes[i].id][route.nodes[i+1].id] +
                           self.instance.distance_matrix[route.nodes[j].id][route.nodes[j+1].id])
            
            new_dist = (self.instance.distance_matrix[route.nodes[i].id][route.nodes[j].id] +
                       self.instance.distance_matrix[route.nodes[i+1].id][route.nodes[j+1].id])
            
            return current_dist - new_dist
        except (KeyError, IndexError):
            return 0
    
    def _apply_2opt_move(self, route: Route, i: int, j: int):
        """
        Apply a 2-opt move by reversing the segment from i+1 to j.
        """
        if i >= j or i < 0 or j >= len(route.nodes) - 1:
            return
        
        # Additional safety checks
        if i + 1 >= len(route.nodes) or j >= len(route.nodes):
            return
        
        # Reverse the segment from i+1 to j
        left = i + 1
        right = j
        
        # Additional safety check
        if left >= len(route.nodes) or right >= len(route.nodes):
            return
            
        while left < right:
            route.nodes[left], route.nodes[right] = route.nodes[right], route.nodes[left]
            left += 1
            right -= 1