import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class OrOpt:
    """
    Or-opt local search operator that relocates segments of consecutive customers.
    This operator can move 1, 2, or 3 consecutive customers to different positions
    within the same route or to different routes.
    """
    
    def __init__(self, instance: Instance, max_iter: int = 10, max_segment_size: int = 3):
        self.instance = instance
        self.max_iter = max_iter
        self.max_segment_size = max_segment_size

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply Or-opt local search to improve the solution.
        Relocates segments of customers to reduce total cost.
        
        Args:
            solution: The solution to improve
            
        Returns:
            bool: True if any improvement was made, False otherwise
        """
        if not solution.routes:
            return False
            
        if self._relocate_segments(solution):
            solution.evaluate()
            return True
            
        return False

    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply Or-opt perturbation to diversify the solution.
        
        Args:
            solution: The solution to perturb
            
        Returns:
            Solution: The perturbed solution
        """
        for _ in range(self.max_iter):
            self._relocate_segments(solution, force_move=True)
        
        solution.evaluate()
        return solution

    def _relocate_segments(self, solution: 'Solution', force_move: bool = False) -> bool:
        """
        Try to relocate segments of customers to improve the solution.
        
        Args:
            solution: The solution to improve
            force_move: If True, perform a random move even if not improving
            
        Returns:
            bool: True if a move was made, False otherwise
        """
        best_move = None
        best_improvement = 0
        
        # Try all possible segment relocations
        for source_route_idx, source_route in enumerate(solution.routes):
            for segment_size in range(1, min(self.max_segment_size + 1, len(source_route.nodes) - 1)):
                for start_pos in range(1, len(source_route.nodes) - segment_size):  # Skip depot
                    # Check if segment contains only customers
                    segment = source_route.nodes[start_pos:start_pos + segment_size]
                    if not all(node.type == NodeType.CUSTOMER for node in segment):
                        continue
                    
                    # Try relocating to different positions in the same route
                    for target_pos in range(1, len(source_route.nodes) - segment_size + 1):
                        if target_pos == start_pos:
                            continue
                        
                        move = self._evaluate_intra_route_segment_move(
                            solution, source_route_idx, start_pos, segment_size, target_pos
                        )
                        
                        if move and move['improvement'] > best_improvement:
                            best_move = move
                            best_improvement = move['improvement']
                    
                    # Try relocating to different routes
                    for target_route_idx, target_route in enumerate(solution.routes):
                        if target_route_idx == source_route_idx:
                            continue
                        
                        for target_pos in range(1, len(target_route.nodes)):
                            move = self._evaluate_inter_route_segment_move(
                                solution, source_route_idx, start_pos, segment_size, 
                                target_route_idx, target_pos
                            )
                            
                            if move and move['improvement'] > best_improvement:
                                best_move = move
                                best_improvement = move['improvement']
        
        # If no improving move found but force_move is True, select a random move
        if not best_move and force_move:
            best_move = self._select_random_segment_move(solution)
        
        # Apply the best move if found
        if best_move:
            self._apply_segment_move(solution, best_move)
            return True
            
        return False

    def _evaluate_intra_route_segment_move(self, solution: 'Solution', route_idx: int, 
                                         start_pos: int, segment_size: int, 
                                         target_pos: int) -> dict:
        """
        Evaluate relocating a segment within the same route.
        
        Args:
            solution: The current solution
            route_idx: Index of the route
            start_pos: Starting position of the segment
            segment_size: Size of the segment
            target_pos: Target position for the segment
            
        Returns:
            dict: Move information with improvement value, or None if infeasible
        """
        # Create temporary copy to test the move
        temp_solution = self._copy_solution(solution)
        temp_route = temp_solution.routes[route_idx]
        
        # Extract the segment
        segment = temp_route.nodes[start_pos:start_pos + segment_size]
        
        # Remove the segment from its current position
        for _ in range(segment_size):
            temp_route.nodes.pop(start_pos)
        
        # Adjust target position if necessary
        if target_pos > start_pos:
            target_pos -= segment_size
        
        # Insert the segment at the target position
        for i, node in enumerate(segment):
            temp_route.nodes.insert(target_pos + i, node)
        
        # Evaluate the route
        temp_route.evaluate(self.instance)
        
        # Check if the route is feasible
        if not temp_route.is_feasible:
            return None
        
        # Calculate improvement
        original_cost = solution.routes[route_idx].total_cost
        new_cost = temp_route.total_cost
        improvement = original_cost - new_cost
        
        return {
            'type': 'intra_route',
            'route_idx': route_idx,
            'start_pos': start_pos,
            'segment_size': segment_size,
            'target_pos': target_pos,
            'segment': segment,
            'improvement': improvement
        }

    def _evaluate_inter_route_segment_move(self, solution: 'Solution', source_route_idx: int, 
                                         start_pos: int, segment_size: int, 
                                         target_route_idx: int, target_pos: int) -> dict:
        """
        Evaluate relocating a segment between different routes.
        
        Args:
            solution: The current solution
            source_route_idx: Index of the source route
            start_pos: Starting position of the segment in source route
            segment_size: Size of the segment
            target_route_idx: Index of the target route
            target_pos: Target position in the target route
            
        Returns:
            dict: Move information with improvement value, or None if infeasible
        """
        # Create temporary copies to test the move
        temp_solution = self._copy_solution(solution)
        temp_source = temp_solution.routes[source_route_idx]
        temp_target = temp_solution.routes[target_route_idx]
        
        # Extract the segment from source route
        segment = temp_source.nodes[start_pos:start_pos + segment_size]
        
        # Remove the segment from source route
        for _ in range(segment_size):
            temp_source.nodes.pop(start_pos)
        
        # Insert the segment into target route
        for i, node in enumerate(segment):
            temp_target.nodes.insert(target_pos + i, node)
        
        # Evaluate both routes
        temp_source.evaluate(self.instance)
        temp_target.evaluate(self.instance)
        
        # Check if both routes are feasible
        if not temp_source.is_feasible or not temp_target.is_feasible:
            return None
        
        # Calculate improvement
        original_cost = (solution.routes[source_route_idx].total_cost + 
                        solution.routes[target_route_idx].total_cost)
        new_cost = temp_source.total_cost + temp_target.total_cost
        improvement = original_cost - new_cost
        
        return {
            'type': 'inter_route',
            'source_route_idx': source_route_idx,
            'start_pos': start_pos,
            'segment_size': segment_size,
            'target_route_idx': target_route_idx,
            'target_pos': target_pos,
            'segment': segment,
            'improvement': improvement
        }

    def _select_random_segment_move(self, solution: 'Solution') -> dict:
        """
        Select a random segment move for perturbation.
        
        Args:
            solution: The current solution
            
        Returns:
            dict: Random move information, or None if no valid moves
        """
        valid_moves = []
        
        # Collect all valid intra-route moves
        for route_idx, route in enumerate(solution.routes):
            for segment_size in range(1, min(self.max_segment_size + 1, len(route.nodes) - 1)):
                for start_pos in range(1, len(route.nodes) - segment_size):
                    segment = route.nodes[start_pos:start_pos + segment_size]
                    if not all(node.type == NodeType.CUSTOMER for node in segment):
                        continue
                    
                    for target_pos in range(1, len(route.nodes) - segment_size + 1):
                        if target_pos == start_pos:
                            continue
                        
                        move = self._evaluate_intra_route_segment_move(
                            solution, route_idx, start_pos, segment_size, target_pos
                        )
                        
                        if move:  # Only consider feasible moves
                            valid_moves.append(move)
        
        # Collect all valid inter-route moves
        for source_route_idx, source_route in enumerate(solution.routes):
            for segment_size in range(1, min(self.max_segment_size + 1, len(source_route.nodes) - 1)):
                for start_pos in range(1, len(source_route.nodes) - segment_size):
                    segment = source_route.nodes[start_pos:start_pos + segment_size]
                    if not all(node.type == NodeType.CUSTOMER for node in segment):
                        continue
                    
                    for target_route_idx, target_route in enumerate(solution.routes):
                        if target_route_idx == source_route_idx:
                            continue
                        
                        for target_pos in range(1, len(target_route.nodes)):
                            move = self._evaluate_inter_route_segment_move(
                                solution, source_route_idx, start_pos, segment_size, 
                                target_route_idx, target_pos
                            )
                            
                            if move:  # Only consider feasible moves
                                valid_moves.append(move)
        
        # Return a random move if any exist
        return random.choice(valid_moves) if valid_moves else None

    def _apply_segment_move(self, solution: 'Solution', move: dict) -> None:
        """
        Apply a segment move to the solution.
        
        Args:
            solution: The solution to modify
            move: The move to apply
        """
        if move['type'] == 'intra_route':
            # Intra-route segment relocation
            route = solution.routes[move['route_idx']]
            start_pos = move['start_pos']
            segment_size = move['segment_size']
            target_pos = move['target_pos']
            segment = move['segment']
            
            # Remove the segment from its current position
            for _ in range(segment_size):
                route.nodes.pop(start_pos)
            
            # Adjust target position if necessary
            if target_pos > start_pos:
                target_pos -= segment_size
            
            # Insert the segment at the target position
            for i, node in enumerate(segment):
                route.nodes.insert(target_pos + i, node)
                
        elif move['type'] == 'inter_route':
            # Inter-route segment relocation
            source_route = solution.routes[move['source_route_idx']]
            target_route = solution.routes[move['target_route_idx']]
            start_pos = move['start_pos']
            segment_size = move['segment_size']
            target_pos = move['target_pos']
            segment = move['segment']
            
            # Remove the segment from source route
            for _ in range(segment_size):
                source_route.nodes.pop(start_pos)
            
            # Insert the segment into target route
            for i, node in enumerate(segment):
                target_route.nodes.insert(target_pos + i, node)
            
            # Remove empty routes (if source route only has depot)
            if len(source_route.nodes) <= 2:  # Only depot nodes
                solution.routes.pop(move['source_route_idx'])

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
