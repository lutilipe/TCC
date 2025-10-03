import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Exchange:
    def __init__(self, instance: Instance, max_iter: int = 1, select_best: bool = True):
        """
        Initialize the Exchange Operator.
        
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
        Apply exchange operator to improve the solution.
        Tries both intra-route and inter-route exchanges.
        Returns True if any improvement was made, False otherwise.
        """
        improved = False
        
        for route in solution.routes:
            if self._intra_route_exchange(route):
                improved = True

        if len(solution.routes) >= 2:
            route_indices = random.sample(range(len(solution.routes)), 2)
            route1_idx, route2_idx = route_indices[0], route_indices[1]
            
            route1 = solution.routes[route1_idx]
            route2 = solution.routes[route2_idx]
            if self._inter_route_exchange(route1, route2):
                improved = True
        
        return improved
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply exchange operator as perturbation (random moves).
        Returns the modified solution.
        """
        for _ in range(self.max_iter):
            if len(solution.routes) == 1:
                route = random.choice(solution.routes)
                self._intra_route_exchange_random(route)
            else:
                route = random.choice(solution.routes)
                self._intra_route_exchange_random(route)
                route1_idx, route2_idx = random.sample(range(len(solution.routes)), 2)
                self._inter_route_exchange_random(solution.routes[route1_idx], solution.routes[route2_idx])
        
        return solution
    
    def _intra_route_exchange(self, route: Route) -> bool:
        """
        Apply intra-route exchange optimization.
        Swaps two customers within the same route.
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
        improved = False
        
        for i in range(len(customer_positions) - 1):
            for j in range(i + 1, len(customer_positions)):
                pos1, pos2 = customer_positions[i], customer_positions[j]
                
                new_route = copy.deepcopy(route)
                new_route.nodes[pos1], new_route.nodes[pos2] = new_route.nodes[pos2], new_route.nodes[pos1]
                
                new_route.evaluate(self.instance)
                
                if new_route.is_feasible and self._is_better_route(new_route, best_route):
                    best_route = new_route
                    route.nodes = best_route.nodes
                    route.charging_decisions = best_route.charging_decisions
                    route.evaluate(self.instance)
                    return True
        
        return False
    
    def _intra_route_exchange_random(self, route: Route) -> bool:
        """
        Apply random intra-route exchange.
        Randomly selects two customers and swaps their positions.
        Returns True if improvement was made, False otherwise.
        """
        if len(route.nodes) <= 4:
            return False
        
        customer_positions = []
        for i in range(1, len(route.nodes) - 1):
            if route.nodes[i].type == NodeType.CUSTOMER:
                customer_positions.append(i)
        
        if len(customer_positions) < 2:
            return False
        
        pos1, pos2 = random.sample(customer_positions, 2)
        
        new_route = copy.deepcopy(route)
        new_route.nodes[pos1], new_route.nodes[pos2] = new_route.nodes[pos2], new_route.nodes[pos1]
        
        new_route.evaluate(self.instance)
        
        if new_route.is_feasible and self._is_better_route(new_route, route):
            route.nodes = new_route.nodes
            route.charging_decisions = new_route.charging_decisions
            route.evaluate(self.instance)
            return True
        
        return False
    
    def _inter_route_exchange(self, route1: Route, route2: Route) -> bool:
        """
        Apply inter-route exchange optimization.
        Swaps two customers between different routes.
        Returns True if any improvement was made, False otherwise.
        """
        customers1 = self._get_customer_positions(route1)
        customers2 = self._get_customer_positions(route2)
        
        if len(customers1) == 0 or len(customers2) == 0:
            return False
        
        for pos1 in customers1:
            for pos2 in customers2:
                new_route1, new_route2 = self._create_swapped_routes(route1, route2, pos1, pos2)
                
                if new_route1 is None or new_route2 is None:
                    continue
                
                new_route1.evaluate(self.instance)
                new_route2.evaluate(self.instance)
                
                if (new_route1.is_feasible and new_route2.is_feasible and
                    self._is_better_solution(new_route1, new_route2, route1, route2)):
                    route1.nodes = new_route1.nodes
                    route1.charging_decisions = new_route1.charging_decisions
                    route1.evaluate(self.instance)
                    
                    route2.nodes = new_route2.nodes
                    route2.charging_decisions = new_route2.charging_decisions
                    route2.evaluate(self.instance)
                    return True
        
        return False
    
    def _inter_route_exchange_random(self, route1: Route, route2: Route) -> bool:
        """
        Apply random inter-route exchange.
        Randomly selects one customer from each route and swaps them.
        Returns True if improvement was made, False otherwise.
        """
        customers1 = self._get_customer_positions(route1)
        customers2 = self._get_customer_positions(route2)
        
        if len(customers1) == 0 or len(customers2) == 0:
            return False
        
        pos1 = random.choice(customers1)
        pos2 = random.choice(customers2)
        
        new_route1, new_route2 = self._create_swapped_routes(route1, route2, pos1, pos2)
        
        if new_route1 is None or new_route2 is None:
            return False
        
        new_route1.evaluate(self.instance)
        new_route2.evaluate(self.instance)
        
        if (new_route1.is_feasible and new_route2.is_feasible and
            self._is_better_solution(new_route1, new_route2, route1, route2)):
            route1.nodes = new_route1.nodes
            route1.charging_decisions = new_route1.charging_decisions
            route1.evaluate(self.instance)
            
            route2.nodes = new_route2.nodes
            route2.charging_decisions = new_route2.charging_decisions
            route2.evaluate(self.instance)
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
    
    def _create_swapped_routes(self, route1: Route, route2: Route, 
                              pos1: int, pos2: int) -> Tuple[Route, Route]:
        """
        Create new routes by swapping customers at given positions.
        
        Args:
            route1, route2: Original routes
            pos1: Position of customer in route1 to swap
            pos2: Position of customer in route2 to swap
        
        Returns:
            Tuple of new routes, or (None, None) if invalid
        """
        try:
            new_route1 = Route()
            new_route1.nodes = route1.nodes.copy()
            new_route1.nodes[pos1] = route2.nodes[pos2]
            
            new_route2 = Route()
            new_route2.nodes = route2.nodes.copy()
            new_route2.nodes[pos2] = route1.nodes[pos1]
            
            new_route1.charging_decisions = route1.charging_decisions.copy()
            new_route2.charging_decisions = route2.charging_decisions.copy()
            
            if (new_route1.nodes[0].type != NodeType.DEPOT or 
                new_route1.nodes[-1].type != NodeType.DEPOT or
                new_route2.nodes[0].type != NodeType.DEPOT or 
                new_route2.nodes[-1].type != NodeType.DEPOT):
                return None, None
            
            return new_route1, new_route2
            
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
