from typing import List
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.classes.route import Route

class Solution:
    def __init__(self, instance: Instance):
        self.instance = instance
        self.routes: List[Route] = []
        self.total_distance: float = 0
        self.total_cost: float = 0
        self.num_vehicles_used: int = 0
        self.is_feasible: bool = True
        
    def evaluate(self):
        """Evaluate the complete solution"""
        self.total_distance = 0
        self.total_cost = 0
        self.num_vehicles_used = len(self.routes)
        self.is_feasible = True
        
        # Check if we have too many vehicles
        if self.num_vehicles_used > self.instance.num_vehicles:
            self.is_feasible = False
            print(f"Too many vehicles used: {self.num_vehicles_used} > {self.instance.num_vehicles}")
        
        for route_id, route in enumerate(self.routes):
            self._evaluate_route(route_id, route)
            self.total_distance += route.total_distance
            self.total_cost += route.total_cost
            if not route.is_feasible:
                self.is_feasible = False
        
        # Check if all customers are served
        served_customers = set()
        for route in self.routes:
            for node in route.nodes:
                if node.type == NodeType.CUSTOMER:
                    served_customers.add(node.id)
        
        all_customers = {node.id for node in self.instance.nodes if node.type == NodeType.CUSTOMER}
        if served_customers != all_customers:
            self.is_feasible = False
            unserved = all_customers - served_customers
            print(f"Unserved customers: {unserved}")
    
    def _evaluate_route(self, route_id: int, route: Route):
        """Evaluate a single route for feasibility and compute metrics"""
        if not route.nodes:
            route.is_feasible = False
            print(f"Route {route_id}: Empty route")
            return
        
        # Initialize route metrics
        route.total_distance = 0
        route.total_cost = 0
        route.total_time = 0
        route.is_feasible = True
        
        # Initialize state variables
        current_battery = self.instance.vehicle.battery_capacity
        current_load = 0
        current_time = 0
        
        # Get depot ID
        depot_id = next((n.id for n in self.instance.nodes if n.type == NodeType.DEPOT), None)
        if depot_id is None:
            route.is_feasible = False
            print(f"Route {route_id}: No depot found")
            return
        
        # Route must start and end at depot
        if route.nodes[0].id != depot_id or route.nodes[-1].id != depot_id:
            route.is_feasible = False
            print(f"Route {route_id}: Route must start and end at depot")
            return
        
        prev_node_id = depot_id
        
        for i, node in enumerate(route.nodes[1:], 1):  # Skip first depot
            node_id = node.id
            
            # Calculate travel metrics
            travel_dist = self.instance.distance_matrix[prev_node_id][node_id]
            travel_time = self.instance.time_matrix[prev_node_id][node_id]
            energy_consumed = travel_dist * self.instance.vehicle.consumption_rate
            
            # Check battery constraint
            if current_battery < energy_consumed:
                route.is_feasible = False
                print(f"Route {route_id}, Node {i}: Insufficient battery: {current_battery:.2f} < {energy_consumed:.2f}")
                return
            
            # Update state after travel
            current_battery -= energy_consumed
            current_time += travel_time
            route.total_distance += travel_dist
            
            # Process node based on type
            if node.type == NodeType.CUSTOMER:
                # Add demand and service time
                current_load += node.demand
                current_time += node.service_time
                
                # Check capacity constraint
                if current_load > self.instance.vehicle.capacity:
                    route.is_feasible = False
                    print(f"Route {route_id}, Node {i}: Capacity exceeded: {current_load:.2f} > {self.instance.vehicle.capacity:.2f}")
                    return
            
            elif node.type == NodeType.STATION or (node.type == NodeType.DEPOT and i < len(route.nodes) - 1):
                # Handle charging at stations or intermediate depot visits
                if node_id in route.charging_decisions:
                    tech, energy_to_charge = route.charging_decisions[node_id]
                    
                    # Validate technology exists
                    tech_found = False
                    if node.type == NodeType.STATION:
                        tech_found = any(t.id == tech.id for t in node.technologies)
                    elif node.type == NodeType.DEPOT:
                        depot_node = next((n for n in self.instance.nodes if n.type == NodeType.DEPOT), None)
                        if depot_node:
                            tech_found = any(t.id == tech.id for t in depot_node.technologies)
                    
                    if not tech_found:
                        route.is_feasible = False
                        print(f"Route {route_id}, Node {i}: Technology {tech.id} not available at node {node_id}")
                        return
                    
                    # Calculate charging time and cost
                    charging_time = energy_to_charge / tech.power
                    current_time += self.instance.charging_fixed_time + charging_time
                    current_battery = min(current_battery + energy_to_charge, self.instance.vehicle.battery_capacity)
                    
                    # Add charging cost
                    route.total_cost += energy_to_charge * tech.cost_per_kwh
                    if hasattr(self.instance, 'battery_depreciation_cost'):
                        route.total_cost += self.instance.battery_depreciation_cost
            
            # Update previous node
            prev_node_id = node_id
        
        # Set final route metrics
        route.total_time = current_time
        
        # Check time constraint
        if current_time > self.instance.max_route_duration:
            route.is_feasible = False
            print(f"Route {route_id}: Time limit exceeded: {current_time:.2f} > {self.instance.max_route_duration:.2f}")
        
        # Ensure route ends with reasonable battery level (not necessarily zero)
        if current_battery < -0.001:  # Small tolerance for floating point
            route.is_feasible = False
            print(f"Route {route_id}: Negative battery at end: {current_battery:.2f}")
        
        # Add vehicle cost if applicable
        if hasattr(self.instance, 'vehicle_cost_per_route'):
            route.total_cost += self.instance.vehicle_cost_per_route
    
    def print_solution_summary(self):
        """Print a summary of the solution"""
        print(f"\n=== Solution Summary ===")
        print(f"Feasible: {self.is_feasible}")
        print(f"Number of routes: {len(self.routes)}")
        print(f"Total distance: {self.total_distance:.2f}")
        print(f"Total cost: {self.total_cost:.2f}")
        
        for i, route in enumerate(self.routes):
            customer_count = sum(1 for node in route.nodes if node.type == NodeType.CUSTOMER)
            charging_count = len(route.charging_decisions)
            print(f"Route {i}: {customer_count} customers, {charging_count} charges, "
                  f"distance: {route.total_distance:.2f}, time: {route.total_time:.2f}, "
                  f"feasible: {route.is_feasible}")