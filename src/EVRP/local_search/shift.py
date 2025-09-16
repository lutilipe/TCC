import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Shift:
    """
    Shift local search operator that moves a single customer to a different position
    within the same route. This is a simpler intra-route operator that can be used
    for fine-tuning customer positions within routes.
    """
    
    def __init__(self, instance: Instance, max_iter: int = 10):
        self.instance = instance
        self.max_iter = max_iter

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply shift local search to improve the solution.
        Moves customers within their routes to reduce total cost.
        
        Args:
            solution: The solution to improve
            
        Returns:
            bool: True if any improvement was made, False otherwise
        """
        if not solution.routes:
            return False
            
        improved = False
        
        for route in solution.routes:
            if self._shift_customers_in_route(route):
                improved = True
        
        if improved:
            solution.evaluate()
            
        return improved

    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply shift perturbation to diversify the solution.
        
        Args:
            solution: The solution to perturb
            
        Returns:
            Solution: The perturbed solution
        """
        for route in solution.routes:
            for _ in range(self.max_iter):
                self._shift_customers_in_route(route, force_move=True)
        
        solution.evaluate()
        return solution

    def _shift_customers_in_route(self, route: Route, force_move: bool = False) -> bool:
        """
        Try to shift customers within a single route to improve it.
        
        Args:
            route: The route to improve
            force_move: If True, perform a random move even if not improving
            
        Returns:
            bool: True if the route was improved, False otherwise
        """
        if len(route.nodes) <= 3:  # Need at least depot + customer + depot
            return False
            
        best_route = copy.deepcopy(route)
        improved = True
        current_route = copy.deepcopy(route)
        iteration = 0

        while improved and iteration < self.max_iter:
            improved = False
            iteration += 1
            
            # Try all possible customer shifts
            for customer_idx in range(1, len(current_route.nodes) - 1):  # Skip depot nodes
                customer = current_route.nodes[customer_idx]
                if customer.type != NodeType.CUSTOMER:
                    continue
                
                for target_idx in range(1, len(current_route.nodes) - 1):
                    if target_idx == customer_idx:
                        continue
                    
                    # Create new route by shifting the customer
                    new_route = self._create_shifted_route(current_route, customer_idx, target_idx)
                    
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
        
        # If no improvement found but force_move is True, try a random shift
        if not improved and force_move:
            random_shift = self._select_random_shift(route)
            if random_shift:
                self._apply_shift(route, random_shift)
                route.evaluate(self.instance)
                return True
        
        # Update the original route if improvement was found
        if self._is_better_route(best_route, route):
            route.nodes = best_route.nodes
            route.charging_decisions = best_route.charging_decisions
            route.evaluate(self.instance)
            return True
        
        return False

    def _create_shifted_route(self, route: Route, customer_idx: int, target_idx: int) -> Route:
        """
        Create a new route by shifting a customer to a different position.
        
        Args:
            route: The original route
            customer_idx: Index of the customer to shift
            target_idx: Target position for the customer
            
        Returns:
            Route: The new route with the customer shifted, or None if invalid
        """
        if (customer_idx < 1 or customer_idx >= len(route.nodes) - 1 or
            target_idx < 1 or target_idx >= len(route.nodes) - 1 or
            customer_idx == target_idx):
            return None
        
        new_route = copy.deepcopy(route)
        nodes = new_route.nodes
        
        # Remove the customer from its current position
        customer = nodes.pop(customer_idx)
        
        # Adjust target index if necessary
        if target_idx > customer_idx:
            target_idx -= 1
        
        # Insert the customer at the target position
        nodes.insert(target_idx, customer)
        
        return new_route

    def _select_random_shift(self, route: Route) -> dict:
        """
        Select a random shift move for perturbation.
        
        Args:
            route: The route to modify
            
        Returns:
            dict: Random shift information, or None if no valid shifts
        """
        if len(route.nodes) <= 3:
            return None
        
        # Find all customer positions
        customer_positions = []
        for i, node in enumerate(route.nodes):
            if node.type == NodeType.CUSTOMER:
                customer_positions.append(i)
        
        if len(customer_positions) < 2:
            return None
        
        # Select random customer and target position
        customer_idx = random.choice(customer_positions)
        target_positions = [i for i in range(1, len(route.nodes) - 1) if i != customer_idx]
        
        if not target_positions:
            return None
        
        target_idx = random.choice(target_positions)
        
        return {
            'customer_idx': customer_idx,
            'target_idx': target_idx
        }

    def _apply_shift(self, route: Route, shift: dict) -> None:
        """
        Apply a shift move to the route.
        
        Args:
            route: The route to modify
            shift: The shift to apply
        """
        customer_idx = shift['customer_idx']
        target_idx = shift['target_idx']
        
        # Remove the customer from its current position
        customer = route.nodes.pop(customer_idx)
        
        # Adjust target index if necessary
        if target_idx > customer_idx:
            target_idx -= 1
        
        # Insert the customer at the target position
        route.nodes.insert(target_idx, customer)

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
