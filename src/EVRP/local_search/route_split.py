import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class RouteSplit:
    """
    Route Split operator that splits a route into multiple routes.
    This operator can help diversify the search by creating new route structures
    and potentially reducing route duration or improving feasibility.
    """
    
    def __init__(self, instance: Instance, max_iter: int = 1, select_best: bool = True):
        """
        Initialize the Route Split Operator.
        
        Args:
            instance: EVRP instance
            max_iter: Maximum number of iterations for perturbation
            select_best: Whether to select the best improvement or accept any improvement
        """
        self.instance = instance
        self.max_iter = max_iter
        self.select_best = select_best

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply route split operator to improve the solution.
        Tries to split routes that are too long or have high costs.
        Returns True if any improvement was made, False otherwise.
        """
        improved = False
        
        for route in solution.routes:
            if self._should_split_route(route):
                if self._split_route(solution, route):
                    improved = True
        
        return improved
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply route split operator as perturbation (random moves).
        Returns the modified solution.
        """
        for _ in range(self.max_iter):
            # Select a random route to potentially split
            if not solution.routes:
                break
                
            route = random.choice(solution.routes)
            
            # Randomly decide whether to split this route
            if self._can_split_route(route):
                self._split_route_random(solution, route)
        
        return solution
    
    def _should_split_route(self, route: Route) -> bool:
        """
        Determine if a route should be split based on various criteria.
        
        Args:
            route: The route to evaluate
            
        Returns:
            bool: True if the route should be split
        """
        if not route.nodes or len(route.nodes) <= 4:
            return False
        
        # Count customers in the route
        customer_count = sum(1 for node in route.nodes[1:-1] if node.type == NodeType.CUSTOMER)
        
        # Split if route has too many customers or is too long
        if customer_count >= 8:  # Split routes with 8+ customers
            return True
            
        # Split if route duration is close to maximum
        if hasattr(route, 'total_time') and route.total_time > self.instance.max_route_duration * 0.8:
            return True
            
        # Split if route distance is very high (heuristic)
        if route.total_distance > 200:  # Arbitrary threshold
            return True
            
        return False
    
    def _can_split_route(self, route: Route) -> bool:
        """
        Check if a route can be split (has enough customers).
        
        Args:
            route: The route to check
            
        Returns:
            bool: True if the route can be split
        """
        if not route.nodes or len(route.nodes) <= 4:
            return False
            
        customer_count = sum(1 for node in route.nodes[1:-1] if node.type == NodeType.CUSTOMER)
        return customer_count >= 4  # Need at least 4 customers to split meaningfully
    
    def _split_route(self, solution: 'Solution', route_to_split: Route) -> bool:
        """
        Split a route into two routes at the best possible position.
        
        Args:
            solution: The solution containing the route
            route_to_split: The route to split
            
        Returns:
            bool: True if the split was successful and improved the solution
        """
        if not self._can_split_route(route_to_split):
            return False
        
        # Find the best split position
        best_split_pos = self._find_best_split_position(route_to_split)
        
        if best_split_pos is None:
            return False
        
        # Create new routes from the split
        new_routes = self._create_split_routes(route_to_split, best_split_pos)
        
        if not new_routes or len(new_routes) != 2:
            return False
        
        # Evaluate both new routes
        new_routes[0].evaluate(self.instance)
        new_routes[1].evaluate(self.instance)
        
        # Check if both routes are feasible
        if not new_routes[0].is_feasible or not new_routes[1].is_feasible:
            return False
        
        # Check if the split improves the solution
        if self._is_better_split(route_to_split, new_routes):
            # Replace the original route with the two new routes
            route_index = solution.routes.index(route_to_split)
            solution.routes.remove(route_to_split)
            solution.routes.insert(route_index, new_routes[0])
            solution.routes.insert(route_index + 1, new_routes[1])
            return True
        
        return False
    
    def _split_route_random(self, solution: 'Solution', route_to_split: Route) -> bool:
        """
        Split a route randomly for perturbation purposes.
        
        Args:
            solution: The solution containing the route
            route_to_split: The route to split
            
        Returns:
            bool: True if the split was successful
        """
        if not self._can_split_route(route_to_split):
            return False
        
        # Find valid split positions
        valid_positions = self._get_valid_split_positions(route_to_split)
        
        if not valid_positions:
            return False
        
        # Randomly select a split position
        split_pos = random.choice(valid_positions)
        
        # Create new routes from the split
        new_routes = self._create_split_routes(route_to_split, split_pos)
        
        if not new_routes or len(new_routes) != 2:
            return False
        
        # Evaluate both new routes
        new_routes[0].evaluate(self.instance)
        new_routes[1].evaluate(self.instance)
        
        # Accept the split if both routes are feasible
        if new_routes[0].is_feasible and new_routes[1].is_feasible:
            # Replace the original route with the two new routes
            route_index = solution.routes.index(route_to_split)
            solution.routes.remove(route_to_split)
            solution.routes.insert(route_index, new_routes[0])
            solution.routes.insert(route_index + 1, new_routes[1])
            return True
        
        return False
    
    def _find_best_split_position(self, route: Route) -> int:
        """
        Find the best position to split the route.
        Uses a greedy approach to minimize the impact on total distance/cost.
        
        Args:
            route: The route to split
            
        Returns:
            int: The best split position, or None if no good position found
        """
        valid_positions = self._get_valid_split_positions(route)
        
        if not valid_positions:
            return None
        
        best_pos = None
        best_score = float('inf')
        
        for pos in valid_positions:
            # Create temporary routes to evaluate this split
            temp_routes = self._create_split_routes(route, pos)
            
            if not temp_routes or len(temp_routes) != 2:
                continue
            
            # Evaluate both routes
            temp_routes[0].evaluate(self.instance)
            temp_routes[1].evaluate(self.instance)
            
            # Only consider feasible splits
            if not temp_routes[0].is_feasible or not temp_routes[1].is_feasible:
                continue
            
            # Calculate score (lower is better)
            total_distance = temp_routes[0].total_distance + temp_routes[1].total_distance
            total_cost = temp_routes[0].total_cost + temp_routes[1].total_cost
            
            # Combined score (can be adjusted based on priorities)
            score = total_distance * 0.7 + total_cost * 0.3
            
            if score < best_score:
                best_score = score
                best_pos = pos
        
        return best_pos
    
    def _get_valid_split_positions(self, route: Route) -> List[int]:
        """
        Get all valid positions where the route can be split.
        
        Args:
            route: The route to analyze
            
        Returns:
            List[int]: List of valid split positions
        """
        valid_positions = []
        
        if not route.nodes or len(route.nodes) <= 4:
            return valid_positions
        
        # Find customer positions (excluding first and last depot)
        customer_positions = []
        for i in range(1, len(route.nodes) - 1):
            if route.nodes[i].type == NodeType.CUSTOMER:
                customer_positions.append(i)
        
        # Split positions should be after customer positions
        # Ensure both resulting routes have at least 2 customers
        for i in range(2, len(customer_positions) - 1):
            split_pos = customer_positions[i] + 1  # Split after this customer
            if split_pos < len(route.nodes) - 1:  # Don't split after the last depot
                valid_positions.append(split_pos)
        
        return valid_positions
    
    def _create_split_routes(self, route: Route, split_pos: int) -> List[Route]:
        """
        Create two new routes by splitting the original route at the given position.
        
        Args:
            route: The original route to split
            split_pos: The position to split at
            
        Returns:
            List[Route]: List containing two new routes, or empty list if invalid
        """
        try:
            if split_pos < 2 or split_pos >= len(route.nodes) - 1:
                return []
            
            # Get the depot (first and last nodes should be the same)
            depot = route.nodes[0]
            end_depot = route.nodes[-1]
            
            # Create first route: depot -> customers up to split_pos -> depot
            route1 = Route()
            route1.nodes = [depot] + route.nodes[1:split_pos] + [depot]
            route1.charging_decisions = {}
            
            # Create second route: depot -> customers from split_pos -> depot
            route2 = Route()
            route2.nodes = [end_depot] + route.nodes[split_pos:-1] + [end_depot]
            route2.charging_decisions = {}
            
            # Copy relevant charging decisions
            for node_id, charging_info in route.charging_decisions.items():
                # Check if this charging station is in route1
                route1_node_ids = [node.id for node in route1.nodes]
                if node_id in route1_node_ids:
                    route1.charging_decisions[node_id] = charging_info
                
                # Check if this charging station is in route2
                route2_node_ids = [node.id for node in route2.nodes]
                if node_id in route2_node_ids:
                    route2.charging_decisions[node_id] = charging_info
            
            # Verify both routes have valid structure
            if (len(route1.nodes) < 3 or len(route2.nodes) < 3 or
                route1.nodes[0].type != NodeType.DEPOT or route1.nodes[-1].type != NodeType.DEPOT or
                route2.nodes[0].type != NodeType.DEPOT or route2.nodes[-1].type != NodeType.DEPOT):
                return []
            
            return [route1, route2]
            
        except (IndexError, AttributeError):
            return []
    
    def _is_better_split(self, original_route: Route, new_routes: List[Route]) -> bool:
        """
        Check if the split results in a better solution.
        
        Args:
            original_route: The original route before splitting
            new_routes: The two new routes after splitting
            
        Returns:
            bool: True if the split is better
        """
        if not self.select_best:
            return True
        
        if len(new_routes) != 2:
            return False
        
        route1, route2 = new_routes
        
        # Calculate original metrics
        original_distance = original_route.total_distance
        original_cost = original_route.total_cost
        
        # Calculate new metrics
        new_distance = route1.total_distance + route2.total_distance
        new_cost = route1.total_cost + route2.total_cost
        
        # The split is better if it reduces total distance or cost
        # while maintaining feasibility
        if (new_distance <= original_distance and new_cost <= original_cost):
            if (new_distance < original_distance or new_cost < original_cost):
                return True
        
        # Also consider if the split improves route balance
        # (reduces the maximum route duration)
        if hasattr(route1, 'total_time') and hasattr(route2, 'total_time'):
            max_new_time = max(route1.total_time, route2.total_time)
            if hasattr(original_route, 'total_time'):
                original_time = original_route.total_time
                if max_new_time < original_time * 0.9:  # 10% improvement threshold
                    return True
        
        return False
