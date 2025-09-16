import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Relocate:
    """
    Relocate local search operator that moves a single customer from one route to another.
    This is one of the most fundamental local search operators in vehicle routing problems.
    """
    
    def __init__(self, instance: Instance, max_iter: int = 10):
        self.instance = instance
        self.max_iter = max_iter

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply relocate local search to improve the solution.
        Moves customers between routes to reduce total cost.
        
        Args:
            solution: The solution to improve
            
        Returns:
            bool: True if any improvement was made, False otherwise
        """
        if len(solution.routes) < 2:
            return False
            
        improved = False
        iteration = 0
        
        while iteration < self.max_iter:
            if self._relocate_customers(solution):
                improved = True
                solution.evaluate()
            else:
                break
            iteration += 1
            
        return improved

    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply relocate perturbation to diversify the solution.
        
        Args:
            solution: The solution to perturb
            
        Returns:
            Solution: The perturbed solution
        """
        for _ in range(self.max_iter):
            self._relocate_customers(solution, force_move=True)
        
        solution.evaluate()
        return solution

    def _relocate_customers(self, solution: 'Solution', force_move: bool = False) -> bool:
        """
        Try to relocate customers between routes to improve the solution.
        
        Args:
            solution: The solution to improve
            force_move: If True, perform a random move even if not improving
            
        Returns:
            bool: True if a move was made, False otherwise
        """
        best_move = None
        best_improvement = 0
        
        # Try all possible customer relocations
        for source_route_idx, source_route in enumerate(solution.routes):
            for customer_idx, customer_node in enumerate(source_route.nodes):
                if customer_node.type != NodeType.CUSTOMER:
                    continue
                
                # Try inserting this customer into other routes
                for target_route_idx, target_route in enumerate(solution.routes):
                    if target_route_idx == source_route_idx:
                        continue
                    
                    # Try different insertion positions in target route
                    for insert_pos in range(1, len(target_route.nodes)):  # Skip depot at position 0
                        move = self._evaluate_relocate_move(
                            solution, source_route_idx, customer_idx, target_route_idx, insert_pos
                        )
                        
                        if move and move['improvement'] > best_improvement:
                            best_move = move
                            best_improvement = move['improvement']
        
        # If no improving move found but force_move is True, select a random move
        if not best_move and force_move:
            best_move = self._select_random_move(solution)
        
        # Apply the best move if found
        if best_move:
            self._apply_relocate_move(solution, best_move)
            return True
            
        return False

    def _evaluate_relocate_move(self, solution: 'Solution', source_route_idx: int, 
                               customer_idx: int, target_route_idx: int, 
                               insert_pos: int) -> dict:
        """
        Evaluate a specific relocate move.
        
        Args:
            solution: The current solution
            source_route_idx: Index of the source route
            customer_idx: Index of the customer in the source route
            target_route_idx: Index of the target route
            insert_pos: Position to insert the customer in the target route
            
        Returns:
            dict: Move information with improvement value, or None if infeasible
        """
        source_route = solution.routes[source_route_idx]
        target_route = solution.routes[target_route_idx]
        customer_node = source_route.nodes[customer_idx]
        
        # Create temporary copies to test the move
        temp_solution = self._copy_solution(solution)
        temp_source = temp_solution.routes[source_route_idx]
        temp_target = temp_solution.routes[target_route_idx]
        
        # Remove customer from source route
        temp_source.nodes.pop(customer_idx)
        
        # Insert customer into target route
        temp_target.nodes.insert(insert_pos, customer_node)
        
        # Evaluate both routes
        temp_source.evaluate(self.instance)
        temp_target.evaluate(self.instance)
        
        # Check if both routes are feasible
        if not temp_source.is_feasible or not temp_target.is_feasible:
            return None
        
        # Calculate improvement
        original_cost = source_route.total_cost + target_route.total_cost
        new_cost = temp_source.total_cost + temp_target.total_cost
        improvement = original_cost - new_cost
        
        return {
            'source_route_idx': source_route_idx,
            'customer_idx': customer_idx,
            'target_route_idx': target_route_idx,
            'insert_pos': insert_pos,
            'customer_node': customer_node,
            'improvement': improvement
        }

    def _select_random_move(self, solution: 'Solution') -> dict:
        """
        Select a random relocate move for perturbation.
        
        Args:
            solution: The current solution
            
        Returns:
            dict: Random move information, or None if no valid moves
        """
        valid_moves = []
        
        # Collect all valid moves
        for source_route_idx, source_route in enumerate(solution.routes):
            for customer_idx, customer_node in enumerate(source_route.nodes):
                if customer_node.type != NodeType.CUSTOMER:
                    continue
                
                for target_route_idx, target_route in enumerate(solution.routes):
                    if target_route_idx == source_route_idx:
                        continue
                    
                    for insert_pos in range(1, len(target_route.nodes)):
                        move = self._evaluate_relocate_move(
                            solution, source_route_idx, customer_idx, target_route_idx, insert_pos
                        )
                        
                        if move:  # Only consider feasible moves
                            valid_moves.append(move)
        
        # Return a random move if any exist
        return random.choice(valid_moves) if valid_moves else None

    def _apply_relocate_move(self, solution: 'Solution', move: dict) -> None:
        """
        Apply a relocate move to the solution.
        
        Args:
            solution: The solution to modify
            move: The move to apply
        """
        source_route_idx = move['source_route_idx']
        customer_idx = move['customer_idx']
        target_route_idx = move['target_route_idx']
        insert_pos = move['insert_pos']
        customer_node = move['customer_node']
        
        # Get the actual route objects
        source_route = solution.routes[source_route_idx]
        target_route = solution.routes[target_route_idx]
        
        # Remove customer from source route
        source_route.nodes.pop(customer_idx)
        
        # Insert customer into target route
        target_route.nodes.insert(insert_pos, customer_node)
        
        # Remove empty routes (if source route only has depot)
        if len(source_route.nodes) <= 2:  # Only depot nodes
            solution.routes.pop(source_route_idx)

    def _copy_solution(self, solution: 'Solution') -> 'Solution':
        """
        Create a deep copy of the solution for testing moves.
        
        Args:
            solution: The solution to copy
            
        Returns:
            Solution: A deep copy of the solution
        """
        from EVRP.solution import Solution
        
        new_solution = Solution(solution.instance)
        new_solution.routes = []
        
        for route in solution.routes:
            new_route = Route()
            new_route.nodes = route.nodes.copy()
            new_route.charging_decisions = route.charging_decisions.copy()
            new_solution.routes.append(new_route)
        
        return new_solution
