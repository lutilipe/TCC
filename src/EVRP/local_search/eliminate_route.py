import copy
import random
from typing import List, Tuple, TYPE_CHECKING, Optional
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route
from EVRP.classes.technology import Technology

if TYPE_CHECKING:
    from EVRP.solution import Solution

class EliminateRoute:
    def __init__(self, instance: Instance, max_iter: int = 1):
        """
        Initialize the Eliminate Route Perturbation.
        
        This perturbation eliminates a route from a depot and redistributes its customers
        to other routes from the same depot or to other depots. All choices are made at random.
        All insertions of customers into routes need to be feasible.
        
        Args:
            instance: EVRP instance
            max_iter: Maximum number of iterations for perturbation
            select_best: Whether to select the best improvement or accept any improvement
        """
        self.instance = instance
        self.max_iter = max_iter
    
    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply eliminate route perturbation.
        Eliminates a random route and redistributes its customers to other routes.
        Returns the modified solution.
        """
        if len(solution.routes) <= 1:
            return solution  # Cannot eliminate if only one route exists
        
        for _ in range(self.max_iter):
            route_to_eliminate_idx = random.randint(0, len(solution.routes) - 1)
            route_to_eliminate = solution.routes[route_to_eliminate_idx]
            
            customers_to_redistribute = []
            for node in route_to_eliminate.nodes:
                if node.type == NodeType.CUSTOMER:
                    customers_to_redistribute.append(node)
            
            if not customers_to_redistribute:
                continue
            
            solution.routes.pop(route_to_eliminate_idx)
            
            self._redistribute_customers(solution, customers_to_redistribute)
        
        return solution
    
    def _redistribute_customers(self, solution: 'Solution', customers: List[Node]):
        """
        Redistribute customers to existing routes or create new routes.
        All insertions must be feasible.
        """
        # Shuffle customers to randomize insertion order
        random.shuffle(customers)
        
        for customer in customers:
            # Try to insert customer into an existing route
            inserted = False
            
            # Try to insert into existing routes first
            for route in solution.routes:
                if self._try_insert_customer_into_route(route, customer):
                    inserted = True
                    break
            
            if not inserted:
                new_route = self._create_new_route_for_customer(customer)
                if new_route is not None:
                    solution.routes.append(new_route)
                else:
                    if solution.routes:
                        route = random.choice(solution.routes)
                        self._force_insert_customer_into_route(route, customer)
    
    def _try_insert_customer_into_route(self, route: Route, customer: Node) -> bool:
        """
        Try to insert a customer into a route at a random feasible position.
        Returns True if insertion was successful, False otherwise.
        """
        if not route.nodes or len(route.nodes) < 2:
            return False
        
        # Try multiple random positions
        max_attempts = min(10, len(route.nodes) - 1)
        positions_tried = set()
        
        for _ in range(max_attempts):
            # Select a random position (not at depot positions)
            position = random.randint(1, len(route.nodes))
            
            if position in positions_tried:
                continue
            positions_tried.add(position)
            
            # Create new route with customer inserted
            new_route = self._create_route_with_inserted_customer(route, customer, position)
            if new_route is not None:
                new_route.evaluate(self.instance)
                if new_route.is_feasible:
                    route.nodes = new_route.nodes
                    route.charging_decisions = new_route.charging_decisions
                    route.evaluate(self.instance)
                    return True
        
        return False
    
    def _force_insert_customer_into_route(self, route: Route, customer: Node) -> bool:
        """
        Force insert a customer into a route at a random position.
        This may create an infeasible route, but it's better than losing the customer.
        """
        if not route.nodes:
            return False
        
        position = random.randint(1, len(route.nodes))
        new_route = self._create_route_with_inserted_customer(route, customer, position)
        if new_route is not None:
            route.nodes = new_route.nodes
            route.charging_decisions = new_route.charging_decisions
            route.evaluate(self.instance)
            return True
        
        return False
    
    def _create_route_with_inserted_customer(self, route: Route, customer: Node, position: int) -> Optional[Route]:
        """
        Create a new route by inserting a customer at the specified position.
        Returns the new route or None if the operation fails.
        """
        try:
            new_route = Route()
            new_route.nodes = route.nodes.copy()
            new_route.nodes.insert(position, customer)
            new_route.charging_decisions = route.charging_decisions.copy()
            
            # Verify the route structure is valid
            if (new_route.nodes and 
                new_route.nodes[0].type == NodeType.DEPOT and 
                new_route.nodes[-1].type == NodeType.DEPOT):
                return new_route
            
            return None
            
        except (IndexError, AttributeError):
            return None
    
    def _create_new_route_for_customer(self, customer: Node) -> Optional[Route]:
        """
        Create a new route for a single customer.
        Returns the new route or None if creation fails.
        """
        try:
            # Select the nearest depot as start and end
            depots = [node for node in self.instance.nodes if node.type == NodeType.DEPOT]
            if not depots:
                return None
            
            # Find the nearest depot to the customer
            depot = min(depots, key=lambda d: self.instance.distance_matrix[customer.id][d.id])
            
            # Create new route
            new_route = Route()
            new_route.nodes = [depot, customer, depot]
            new_route.charging_decisions = {}
            
            # Set initial charging decision at depot
            if depot.technologies:
                # Choose a random technology available at the depot
                tech = random.choice(depot.technologies)
                new_route.charging_decisions[depot.id] = (tech, self.instance.vehicle.battery_capacity)
            
            new_route.evaluate(self.instance)
            
            if new_route.is_feasible:
                return new_route
            else:
                # Try to make the route feasible by adding charging stations if needed
                return self._try_make_route_feasible(new_route)
                
        except Exception:
            return None
    
    def _try_make_route_feasible(self, route: Route) -> Optional[Route]:
        """
        Try to make a route feasible by adding charging stations if needed.
        This is a simplified approach - in practice, you might want more sophisticated charging planning.
        """
        try:
            # Check if route can reach depot directly from customer
            if len(route.nodes) == 3:  # depot -> customer -> depot
                depot = route.nodes[0]
                customer = route.nodes[1]
                
                # Calculate energy consumption from depot to customer and back
                energy_to_customer = self.instance.distance_matrix[depot.id][customer.id] * self.instance.vehicle.consumption_rate
                energy_from_customer = self.instance.distance_matrix[customer.id][depot.id] * self.instance.vehicle.consumption_rate
                total_energy_needed = energy_to_customer + energy_from_customer
                
                if total_energy_needed <= self.instance.vehicle.battery_capacity:
                    # Route is feasible as is
                    route.evaluate(self.instance)
                    return route if route.is_feasible else None
                
                # Try to find a charging station between customer and depot
                stations = [node for node in self.instance.nodes if node.type == NodeType.STATION]
                if not stations:
                    return None
                
                # Find closest station to customer
                closest_station = min(stations, key=lambda s: self.instance.distance_matrix[customer.id][s.id])
                
                # Create route: depot -> customer -> station -> depot
                new_route = Route()
                new_route.nodes = [depot, customer, closest_station, depot]
                new_route.charging_decisions = route.charging_decisions.copy()
                
                # Add charging decision at station
                if closest_station.technologies:
                    tech = random.choice(closest_station.technologies)
                    # Calculate energy needed to reach depot
                    energy_needed = self.instance.distance_matrix[closest_station.id][depot.id] * self.instance.vehicle.consumption_rate
                    new_route.charging_decisions[closest_station.id] = (tech, energy_needed)
                
                new_route.evaluate(self.instance)
                return new_route if new_route.is_feasible else None
            
            return None
            
        except Exception:
            return None
