import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Relocate:
    def __init__(
            self,
            instance: Instance,
            max_iter: int = 1, 
            select_best: bool = True,
            is_inter_route = False):
        """
        Initialize the Relocate Operator.
        
        Args:
            instance: EVRP instance
            max_iter: Maximum number of iterations for perturbation
            select_best: Whether to select the best improvement or accept any improvement
        """
        self.instance = instance
        self.max_iter = max_iter
        self.select_best = select_best
        self.is_inter_route = is_inter_route

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply relocate operator to improve the solution.
        Tries both intra-route and inter-route relocations.
        Returns True if any improvement was made, False otherwise.
        """
        for route_idx, route in enumerate(solution.routes):
            if not self.is_inter_route:
                if self._intra_route_relocate(route):
                    return True
            else:
                other_indices = [i for i in range(len(solution.routes)) if i != route_idx]
                if not other_indices:
                    continue

                other_idx = random.choice(other_indices)
                route2 = solution.routes[other_idx]

                if self._inter_route_relocate(route, route2):
                    return True

        return False
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply relocate operator as perturbation (random moves).
        Returns the modified solution.
        """
        for _ in range(self.max_iter):
            route = random.choice(solution.routes)
            self._intra_route_relocate_random(route)

            route1_idx, route2_idx = random.sample(range(len(solution.routes)), 2)
            self._inter_route_relocate_random(solution.routes[route1_idx], solution.routes[route2_idx])
        
        return solution
    
    def _intra_route_relocate(self, route: Route) -> bool:
        """
        Apply intra-route relocate optimization.
        Moves one customer to a different position within the same route.
        Returns True if any improvement was made, False otherwise.
        """
        if len(route.nodes) <= 4:
            return False
        
        customer_positions = []
        for i in range(1, len(route.nodes) - 1):
            if route.nodes[i].type == NodeType.CUSTOMER:
                customer_positions.append(i)
        
        if len(customer_positions) < 2:
            return False
        
        best_route = copy.deepcopy(route)
        
        for customer_pos in customer_positions:
            for new_pos in range(1, len(route.nodes) - 1):
                if new_pos == customer_pos:
                    continue
                
                new_route = self._create_relocated_route(route, customer_pos, new_pos)
                if new_route is None:
                    continue
                
                new_route.evaluate(self.instance)
                
                if new_route.is_feasible and self._is_better_route(new_route, best_route):
                    best_route = new_route
                    route.nodes = best_route.nodes
                    route.charging_decisions = best_route.charging_decisions
                    route.evaluate(self.instance)
                    return True
        
        return False
    
    def _intra_route_relocate_random(self, route: Route) -> bool:
        """
        Apply random intra-route relocate.
        Randomly selects a customer and a new position to move it to.
        Returns True if improvement was made, False otherwise.
        """
        if len(route.nodes) <= 4:
            return False
        
        customer_positions = []
        for i in range(1, len(route.nodes) - 1):
            if route.nodes[i].type == NodeType.CUSTOMER:
                customer_positions.append(i)
        
        if len(customer_positions) == 0:
            return False
        
        customer_pos = random.choice(customer_positions)
        
        available_positions = [i for i in range(1, len(route.nodes) - 1) if i != customer_pos]
        if not available_positions:
            return False
        
        new_pos = random.choice(available_positions)
        
        new_route = self._create_relocated_route(route, customer_pos, new_pos)
        if new_route is None:
            return False
        
        new_route.evaluate(self.instance)
        
        if new_route.is_feasible and self._is_better_route(new_route, route):
            route.nodes = new_route.nodes
            route.charging_decisions = new_route.charging_decisions
            route.evaluate(self.instance)
            return True
        
        return False
    
    def _inter_route_relocate(self, source_route: Route, target_route: Route) -> bool:
        """
        Apply inter-route relocate optimization.
        Moves one customer from source route to target route.
        Returns True if any improvement was made, False otherwise.
        """
        # Find customer positions in source route
        source_customers = self._get_customer_positions(source_route)
        
        if len(source_customers) == 0:
            return False
        
        best_source = copy.deepcopy(source_route)
        best_target = copy.deepcopy(target_route)
        
        for customer_pos in source_customers:
            for target_pos in range(1, len(target_route.nodes) - 1):
                new_source, new_target = self._create_inter_route_relocation(
                    source_route, target_route, customer_pos, target_pos
                )
                
                if new_source is None or new_target is None:
                    continue
                
                new_source.evaluate(self.instance)
                new_target.evaluate(self.instance)
                
                if (new_source.is_feasible and new_target.is_feasible and
                    self._is_better_solution(new_source, new_target, best_source, best_target)):
                    best_source = new_source
                    best_target = new_target
                    source_route.nodes = best_source.nodes
                    source_route.charging_decisions = best_source.charging_decisions
                    source_route.evaluate(self.instance)
                    
                    target_route.nodes = best_target.nodes
                    target_route.charging_decisions = best_target.charging_decisions
                    target_route.evaluate(self.instance)
                    return True
        
        return False
    
    def _inter_route_relocate_random(self, source_route: Route, target_route: Route) -> bool:
        """
        Apply random inter-route relocate.
        Randomly selects a customer from source route and moves it to target route.
        Returns True if improvement was made, False otherwise.
        """
        source_customers = self._get_customer_positions(source_route)
        
        if len(source_customers) == 0:
            return False
        
        customer_pos = random.choice(source_customers)
        
        target_pos = random.randint(1, len(target_route.nodes))
        
        new_source, new_target = self._create_inter_route_relocation(
            source_route, target_route, customer_pos, target_pos
        )
        
        if new_source is None or new_target is None:
            return False
        
        new_source.evaluate(self.instance)
        new_target.evaluate(self.instance)
        
        if (new_source.is_feasible and new_target.is_feasible and
            self._is_better_solution(new_source, new_target, source_route, target_route)):
            source_route.nodes = new_source.nodes
            source_route.charging_decisions = new_source.charging_decisions
            source_route.evaluate(self.instance)
            
            target_route.nodes = new_target.nodes
            target_route.charging_decisions = new_target.charging_decisions
            target_route.evaluate(self.instance)
            return True
        
        return False
    
    def _get_customer_positions(self, route: Route) -> List[int]:
        """
        Get positions of all customers in a route (excluding depot).
        Returns list of positions where customers are located.
        """
        customer_positions = []
        for i in range(1, len(route.nodes) - 1):
            if route.nodes[i].type == NodeType.CUSTOMER:
                customer_positions.append(i)
        return customer_positions
    
    def _create_relocated_route(self, route: Route, customer_pos: int, new_pos: int) -> Route:
        """
        Create a new route by relocating a customer from customer_pos to new_pos.
        
        Args:
            route: Original route
            customer_pos: Current position of the customer to move
            new_pos: New position to insert the customer
        
        Returns:
            New route with relocated customer, or None if invalid
        """
        try:
            if customer_pos < 1 or customer_pos >= len(route.nodes) - 1:
                return None
            if new_pos < 1 or new_pos >= len(route.nodes) - 1:
                return None
            
            new_route = Route()
            new_route.nodes = route.nodes.copy()
            
            customer = new_route.nodes.pop(customer_pos)
            
            if new_pos > customer_pos:
                new_pos -= 1
            
            new_route.nodes.insert(new_pos, customer)
            
            new_route.charging_decisions = route.charging_decisions.copy()
            
            if (new_route.nodes[0].type != NodeType.DEPOT or 
                new_route.nodes[-1].type != NodeType.DEPOT):
                return None
            
            return new_route
            
        except (IndexError, AttributeError):
            return None
    
    def _create_inter_route_relocation(self, source_route: Route, target_route: Route,
                                     customer_pos: int, target_pos: int) -> Tuple[Route, Route]:
        """
        Create new routes by moving a customer from source route to target route.
        
        Args:
            source_route: Route to remove customer from
            target_route: Route to insert customer into
            customer_pos: Position of customer in source route
            target_pos: Position to insert customer in target route
        
        Returns:
            Tuple of new routes, or (None, None) if invalid
        """
        try:
            if customer_pos < 1 or customer_pos >= len(source_route.nodes) - 1:
                return None, None
            if target_pos < 1 or target_pos > len(target_route.nodes):
                return None, None
            
            new_source = Route()
            new_source.nodes = source_route.nodes.copy()
            customer = new_source.nodes.pop(customer_pos)
            
            new_target = Route()
            new_target.nodes = target_route.nodes.copy()
            new_target.nodes.insert(target_pos, customer)
            
            new_source.charging_decisions = source_route.charging_decisions.copy()
            new_target.charging_decisions = target_route.charging_decisions.copy()
            
            if (new_source.nodes[0].type != NodeType.DEPOT or 
                new_source.nodes[-1].type != NodeType.DEPOT or
                new_target.nodes[0].type != NodeType.DEPOT or 
                new_target.nodes[-1].type != NodeType.DEPOT):
                return None, None
            
            return new_source, new_target
            
        except (IndexError, AttributeError):
            return None, None
    
    def _is_better_route(self, route1: Route, route2: Route) -> bool:
        """
        Check if route1 is better than route2.
        A route is better if it's feasible and has lower total distance or cost.
        """
        if not self.select_best:
            return True

        if not route1.is_feasible:
            return False
        
        if not route2.is_feasible:
            return True
        
        return route1.dominates(route2)
    
    def _is_better_solution(self, new_source: Route, new_target: Route,
                           current_source: Route, current_target: Route) -> bool:
        """
        Check if the new route pair is better than the current route pair.
        
        A solution is better if:
        1. Both routes are feasible
        2. The total distance or cost is reduced
        """
        if not self.select_best:
            return True

        if not new_source.is_feasible or not new_target.is_feasible:
            return False
        
        if not current_source.is_feasible or not current_target.is_feasible:
            return True
        
        new_total_distance = new_source.total_distance + new_target.total_distance
        new_total_cost = new_source.total_cost + new_target.total_cost
        
        current_total_distance = current_source.total_distance + current_target.total_distance
        current_total_cost = current_source.total_cost + current_target.total_cost
        
        if (new_total_distance <= current_total_distance and
            new_total_cost <= current_total_cost):
            if (new_total_distance < current_total_distance or
                new_total_cost < current_total_cost):
                return True
        
        return False
