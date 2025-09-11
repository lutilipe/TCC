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
        Apply 2-opt* to all routes in a solution.
        Returns True if any improvement was made, False otherwise.
        """
        if len(solution.routes) < 2:
            return False
            
        return self.two_opt_star(solution)
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply 2-opt* perturbation to all routes in a solution.
        Returns the modified solution.
        """
        self.two_opt_star(solution)
        return solution
    
    def two_opt_star(self, solution: 'Solution') -> bool:
        """
        Apply 2-opt* inter-route optimization.
        Two deliveries, gi∈Ra and gj∈Rb (a≠b), are chosen. Then, the edges connecting 
        gi to gi+1 and gj to gj+1 are removed. Two new edges are added adjoining 
        gi with gj+1 and gj with gi+1.
        
        Returns True if any improvement was made, False otherwise.
        """
        if len(solution.routes) < 2:
            return False
            
        # Find all customer positions across all routes
        customer_positions = self._get_customer_positions(solution)
        
        if len(customer_positions) < 2:
            return False
        
        best_improvement = None
        best_delta = 0
        
        # Try all possible 2-opt* moves
        for i, (route_a_idx, pos_i) in enumerate(customer_positions):
            for j, (route_b_idx, pos_j) in enumerate(customer_positions[i+1:], i+1):
                if route_a_idx == route_b_idx:
                    continue  # Skip same route
                
                # Calculate improvement for this move
                delta = self._calculate_move_delta(solution, route_a_idx, pos_i, route_b_idx, pos_j)
                
                if delta > best_delta:
                    best_improvement = (route_a_idx, pos_i, route_b_idx, pos_j)
                    best_delta = delta
        
        # Apply the best improvement if found
        if best_improvement and best_delta > 0:
            self._apply_move(solution, *best_improvement)
            solution.evaluate()
            return True
        
        return False
    
    def _get_customer_positions(self, solution: 'Solution') -> List[Tuple[int, int]]:
        """
        Get all customer positions across all routes.
        Returns list of (route_index, position_in_route) tuples.
        """
        positions = []
        for route_idx, route in enumerate(solution.routes):
            for pos, node in enumerate(route.nodes):
                if node.type == NodeType.CUSTOMER:
                    positions.append((route_idx, pos))
        return positions
    
    def _calculate_move_delta(self, solution: 'Solution', route_a_idx: int, pos_i: int, 
                           route_b_idx: int, pos_j: int) -> float:
        """
        Calculate the improvement (delta) of a 2-opt* move.
        Positive delta means improvement.
        """
        route_a = solution.routes[route_a_idx]
        route_b = solution.routes[route_b_idx]
        
        # Get the nodes involved in the move
        gi = route_a.nodes[pos_i]  # Customer i in route A
        gi_plus_1 = route_a.nodes[pos_i + 1]  # Next node after gi in route A
        
        gj = route_b.nodes[pos_j]  # Customer j in route B  
        gj_plus_1 = route_b.nodes[pos_j + 1]  # Next node after gj in route B
        
        # Calculate current edge costs
        current_cost_a = self.instance.distance_matrix[gi.id][gi_plus_1.id]
        current_cost_b = self.instance.distance_matrix[gj.id][gj_plus_1.id]
        current_total = current_cost_a + current_cost_b
        
        # Calculate new edge costs
        new_cost_a = self.instance.distance_matrix[gi.id][gj_plus_1.id]
        new_cost_b = self.instance.distance_matrix[gj.id][gi_plus_1.id]
        new_total = new_cost_a + new_cost_b
        
        # Delta is the improvement (negative means worse)
        delta = current_total - new_total
        
        # Check if the move would create feasible routes
        if not self._is_move_feasible(solution, route_a_idx, pos_i, route_b_idx, pos_j):
            return -float('inf')  # Make this move very unattractive
        
        return delta
    
    def _is_move_feasible(self, solution: 'Solution', route_a_idx: int, pos_i: int, 
                        route_b_idx: int, pos_j: int) -> bool:
        """
        Check if a 2-opt* move would result in feasible routes.
        """
        # Create temporary copies to test feasibility
        temp_solution = self._copy_solution(solution)
        
        # Apply the move to temporary solution
        self._apply_move(temp_solution, route_a_idx, pos_i, route_b_idx, pos_j)
        
        # Evaluate both affected routes
        temp_solution.routes[route_a_idx].evaluate(self.instance)
        temp_solution.routes[route_b_idx].evaluate(self.instance)
        
        # Check if both routes are feasible
        return (temp_solution.routes[route_a_idx].is_feasible and 
                temp_solution.routes[route_b_idx].is_feasible)
    
    def _apply_move(self, solution: 'Solution', route_a_idx: int, pos_i: int, 
                   route_b_idx: int, pos_j: int) -> None:
        """
        Apply a 2-opt* move to the solution.
        """
        route_a = solution.routes[route_a_idx]
        route_b = solution.routes[route_b_idx]
        
        # Get the segments to swap
        # Route A: [..., gi, gi+1, ...] -> [..., gi, gj+1, ...]
        # Route B: [..., gj, gj+1, ...] -> [..., gj, gi+1, ...]
        
        # Extract the segments
        gi = route_a.nodes[pos_i]
        gi_plus_1 = route_a.nodes[pos_i + 1]
        gj = route_b.nodes[pos_j]
        gj_plus_1 = route_b.nodes[pos_j + 1]
        
        # Apply the swap
        route_a.nodes[pos_i + 1] = gj_plus_1
        route_b.nodes[pos_j + 1] = gi_plus_1
        
        # Clear route evaluations to force re-evaluation
        route_a.total_distance = 0
        route_a.total_cost = 0
        route_a.total_time = 0
        route_a.is_feasible = False
        
        route_b.total_distance = 0
        route_b.total_cost = 0
        route_b.total_time = 0
        route_b.is_feasible = False
    
    def _copy_solution(self, solution: 'Solution') -> 'Solution':
        """Create a deep copy of the solution for testing moves."""
        from EVRP.solution import Solution
        
        new_solution = Solution(solution.instance)
        new_solution.routes = []
        
        for route in solution.routes:
            new_route = Route()
            new_route.nodes = route.nodes.copy()
            new_route.charging_decisions = route.charging_decisions.copy()
            new_solution.routes.append(new_route)
        
        return new_solution