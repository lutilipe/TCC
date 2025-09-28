import copy
import random
from typing import List, Tuple, TYPE_CHECKING, Optional
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Relocate:
    def __init__(self, instance: Instance, max_iter: int = 1, 
                 use_incremental_eval: bool = True, 
                 early_termination: bool = True,
                 max_neighbors: int = 3):
        """
        Initialize the Relocate operator for EVRP with performance optimizations.
        
        Args:
            instance: EVRP instance containing problem data
            max_iter: Maximum number of iterations for local search
            use_incremental_eval: Use incremental evaluation instead of full route recalculation
            early_termination: Stop search early when no improvement is found
            max_neighbors: Maximum number of neighbors to consider for each node
        """
        self.instance = instance
        self.max_iter = max_iter
        self.use_incremental_eval = use_incremental_eval
        self.early_termination = early_termination
        self.max_neighbors = max_neighbors
        
        # Precompute distance-based node ordering for faster neighbor selection
        self._precompute_neighbors()

    def _precompute_neighbors(self):
        """Precompute closest neighbors for each node to speed up node selection."""
        self.node_neighbors = {}
        all_nodes = self.instance.nodes
        
        for node in all_nodes:
            distances = []
            for other_node in all_nodes:
                if node.id != other_node.id:
                    dist = self.instance.distance_matrix[node.id][other_node.id]
                    distances.append((other_node, dist))
            
            # Sort by distance and keep only top neighbors
            distances.sort(key=lambda x: x[1])
            self.node_neighbors[node.id] = [node for node, _ in distances[:self.max_neighbors]]

    def run(self, solution: 'Solution') -> bool:
        """
        Apply relocate operator to a random route in the solution.
        Returns True if any improvement was made, False otherwise.
        """
        if not solution.routes:
            return False
            
        # Choose a random route to apply relocate
        route_idx = random.randint(0, len(solution.routes) - 1)
        route = solution.routes[route_idx]
        
        # Try intra-route relocate first
        if self._intra_route_relocate(route):
            return True
            
        # Try inter-route relocate if intra-route didn't improve
        if len(solution.routes) > 1:
            return self._inter_route_relocate(solution, route_idx)
            
        return False
    
    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply relocate local search to the solution.
        Returns True if any improvement was made, False otherwise.
        """
        improved = False
        for _ in range(self.max_iter):
            if self.run(solution):
                improved = True
                if self.early_termination:
                    # Continue searching for more improvements
                    continue
        
        return improved
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply relocate perturbation to the solution.
        Returns the perturbed solution.
        """
        for _ in range(self.max_iter):
            self.run(solution)
        
        return solution
    
    def _intra_route_relocate(self, route: Route) -> bool:
        """
        Apply intra-route relocate operator with optimizations.
        Moves a node to a different position within the same route.
        
        Args:
            route: Route to apply relocate to
            
        Returns:
            True if improvement was found, False otherwise
        """
        if len(route.nodes) <= 3:  # Need at least depot + customer + depot
            return False
            
        original_distance = route.total_distance
        best_improvement = 0
        best_move = None
        
        # Try relocating each non-depot node to different positions
        for i in range(1, len(route.nodes) - 1):  # Skip first and last (depots)
            node_to_move = route.nodes[i]
            
            # Skip if this node doesn't have promising neighbors (optimization)
            if not self._has_promising_neighbors(node_to_move, route.nodes, i):
                continue
            
            # Try inserting at different positions
            for j in range(1, len(route.nodes)):  # Skip first depot
                if i == j or i == j - 1:  # Skip same position and adjacent positions
                    continue
                
                if self.use_incremental_eval:
                    # Use incremental evaluation for speed
                    improvement = self._evaluate_move_incremental(route, i, j)
                else:
                    # Use full evaluation for accuracy
                    improvement = self._evaluate_move_full(route, i, j)
                
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_move = (i, j)
                    
                    # Early termination if improvement is significant
                    if self.early_termination and improvement > original_distance * 0.01:
                        break
            
            if self.early_termination and best_improvement > 0:
                break
        
        # Apply the best move if found
        if best_move and best_improvement > 0:
            i, j = best_move
            self._apply_move_in_place(route, i, j)
            route.evaluate(self.instance)  # Final evaluation
            return True
            
        return False
    
    def _inter_route_relocate(self, solution: 'Solution', source_route_idx: int) -> bool:
        """
        Apply inter-route relocate operator.
        Moves a node from one route to another route.
        
        Args:
            solution: Complete solution
            source_route_idx: Index of the source route
            
        Returns:
            True if improvement was found, False otherwise
        """
        source_route = solution.routes[source_route_idx]
        if len(source_route.nodes) <= 2:  # Need at least depot + customer + depot
            return False
            
        best_improvement = False
        
        # Try moving each non-depot node from source route
        for i in range(1, len(source_route.nodes) - 1):  # Skip first and last (depots)
            node_to_move = source_route.nodes[i]
            
            # Try inserting into all other routes
            for target_route_idx, target_route in enumerate(solution.routes):
                if target_route_idx == source_route_idx:
                    continue
                    
                # Try inserting at different positions in target route
                for j in range(1, len(target_route.nodes)):  # Skip first depot
                    new_solution = self._move_node_between_routes(
                        solution, source_route_idx, i, target_route_idx, j
                    )
                    
                    if new_solution:
                        new_solution.evaluate()
                        
                        if new_solution.is_feasible and self._is_better_solution(new_solution, solution):
                            # Apply the improvement
                            solution.routes = new_solution.routes
                            solution.evaluate()
                            best_improvement = True
                            return True
        
        return best_improvement
    
    def _move_node_within_route(self, route: Route, from_pos: int, to_pos: int) -> Route:
        """
        Move a node within the same route from one position to another.
        
        Args:
            route: Original route
            from_pos: Position to move from (0-based)
            to_pos: Position to move to (0-based)
            
        Returns:
            New route with node moved, or None if invalid
        """
        if (from_pos < 1 or from_pos >= len(route.nodes) - 1 or  # Can't move depots
            to_pos < 1 or to_pos > len(route.nodes) or  # Can't insert at depot position
            from_pos == to_pos or from_pos == to_pos - 1):  # Skip same/adjacent positions
            return None
            
        new_route = copy.deepcopy(route)
        node_to_move = new_route.nodes.pop(from_pos)
        new_route.nodes.insert(to_pos, node_to_move)
        
        return new_route
    
    def _move_node_between_routes(self, solution: 'Solution', 
                                 source_route_idx: int, from_pos: int,
                                 target_route_idx: int, to_pos: int) -> 'Solution':
        """
        Move a node from one route to another route.
        
        Args:
            solution: Original solution
            source_route_idx: Index of source route
            from_pos: Position in source route to move from
            target_route_idx: Index of target route
            to_pos: Position in target route to move to
            
        Returns:
            New solution with node moved, or None if invalid
        """
        if (source_route_idx == target_route_idx or
            from_pos < 1 or from_pos >= len(solution.routes[source_route_idx].nodes) - 1 or
            to_pos < 1 or to_pos > len(solution.routes[target_route_idx].nodes)):
            return None
            
        new_solution = copy.deepcopy(solution)
        source_route = new_solution.routes[source_route_idx]
        target_route = new_solution.routes[target_route_idx]
        
        # Remove node from source route
        node_to_move = source_route.nodes.pop(from_pos)
        
        # Insert node into target route
        target_route.nodes.insert(to_pos, node_to_move)
        
        return new_solution
    
    def _is_better_route(self, route1: Route, route2: Route) -> bool:
        """
        Check if route1 is better than route2.
        A route is better if it's feasible and dominates the other route.
        
        Args:
            route1: First route to compare
            route2: Second route to compare
            
        Returns:
            True if route1 is better than route2
        """
        if not route1.is_feasible:
            return False
        
        if not route2.is_feasible:
            return True
        
        return route1.dominates(route2)
    
    def _is_better_solution(self, solution1: 'Solution', solution2: 'Solution') -> bool:
        """
        Check if solution1 is better than solution2.
        A solution is better if it's feasible and dominates the other solution.
        
        Args:
            solution1: First solution to compare
            solution2: Second solution to compare
            
        Returns:
            True if solution1 is better than solution2
        """
        if not solution1.is_feasible:
            return False
        
        if not solution2.is_feasible:
            return True
        
        return solution1.dominates(solution2)
    
    def _has_promising_neighbors(self, node: Node, route_nodes: List[Node], current_pos: int) -> bool:
        """
        Check if a node has promising neighbors in the route for potential improvements.
        """
        if node.id not in self.node_neighbors:
            return True  # Default to True if no precomputed neighbors
        
        # Check if any neighbors are close to current position
        neighbors = self.node_neighbors[node.id]
        for neighbor in neighbors[:5]:  # Check only closest 5 neighbors
            if any(n.id == neighbor.id for n in route_nodes):
                return True
        
        return False
    
    def _evaluate_move_incremental(self, route: Route, from_pos: int, to_pos: int) -> float:
        """
        Evaluate a move using incremental calculation instead of full route evaluation.
        """
        if from_pos == to_pos or from_pos == to_pos - 1:
            return 0
        
        # Calculate the change in distance for this specific move
        nodes = route.nodes
        
        # Distance before move
        old_dist = 0
        if from_pos > 0:
            old_dist += self.instance.distance_matrix[nodes[from_pos-1].id][nodes[from_pos].id]
        if from_pos < len(nodes) - 1:
            old_dist += self.instance.distance_matrix[nodes[from_pos].id][nodes[from_pos+1].id]
        
        # Distance after move
        new_dist = 0
        if from_pos > 0 and from_pos < len(nodes) - 1:
            new_dist += self.instance.distance_matrix[nodes[from_pos-1].id][nodes[from_pos+1].id]
        
        # Add distance from new position
        if to_pos > 0:
            new_dist += self.instance.distance_matrix[nodes[to_pos-1].id][nodes[from_pos].id]
        if to_pos < len(nodes):
            new_dist += self.instance.distance_matrix[nodes[from_pos].id][nodes[to_pos].id]
        
        # Remove distance that was at the old position
        if to_pos > 0 and to_pos < len(nodes):
            new_dist -= self.instance.distance_matrix[nodes[to_pos-1].id][nodes[to_pos].id]
        
        return old_dist - new_dist  # Positive means improvement
    
    def _evaluate_move_full(self, route: Route, from_pos: int, to_pos: int) -> float:
        """
        Evaluate a move using full route evaluation.
        """
        if from_pos == to_pos or from_pos == to_pos - 1:
            return 0
        
        # Create temporary route
        temp_route = copy.deepcopy(route)
        node_to_move = temp_route.nodes.pop(from_pos)
        temp_route.nodes.insert(to_pos, node_to_move)
        
        # Evaluate the temporary route
        temp_route.evaluate(self.instance)
        
        if not temp_route.is_feasible:
            return 0
        
        # Calculate improvement
        original_distance = route.total_distance
        new_distance = temp_route.total_distance
        
        return original_distance - new_distance  # Positive means improvement
    
    def _apply_move_in_place(self, route: Route, from_pos: int, to_pos: int):
        """
        Apply a move in-place without creating new objects.
        """
        node_to_move = route.nodes.pop(from_pos)
        route.nodes.insert(to_pos, node_to_move)
