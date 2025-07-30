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
        self.total_distance = 0
        self.total_cost = 0
        self.num_vehicles_used = self.instance.num_vehicles
        self.is_feasible = True
        
        for route in self.routes:
            self._evaluate_route(route)
            self.total_distance += route.total_distance
            self.total_cost += route.total_cost
            if not route.is_feasible:
                self.is_feasible = False
    
    def _evaluate_route(self, route: Route):
        if not route.nodes:
            route.is_feasible = False
            return
        
        route.total_distance = 0
        route.total_cost = 0
        route.total_time = 0
        route.is_feasible = True
        
        current_battery = self.instance.vehicle.battery_capacity
        current_load = 0
        current_time = 0
        
        depotId = [n for n in self.instance.nodes if n.type == NodeType.DEPOT][0].id
        prev_node = depotId
        
        for node in route.nodes:
            node_id = node.id
            travel_dist = self.instance.distance_matrix[prev_node][node_id]
            travel_time = self.instance.time_matrix[prev_node][node_id]
            energy_consumed = travel_dist * self.instance.vehicle.consumption_rate
            
            if current_battery < energy_consumed:
                route.is_feasible = False
                return
            
            current_battery -= energy_consumed
            current_time += travel_time
            route.total_distance += travel_dist
            
            if node.type == NodeType.CUSTOMER:
                current_load += node.demand
                current_time += node.service_time
                
                if current_load > self.instance.vehicle.capacity:
                    route.is_feasible = False
                    return
            
            elif node.type == NodeType.STATION:
                if node_id in route.charging_decisions:
                    tech, energy_to_charge = route.charging_decisions[node_id]
                    charging_time = energy_to_charge / self.instance.technologies[tech.id].power
                    current_time += charging_time + self.instance.charging_fixed_time
                    current_battery = min(current_battery + energy_to_charge, self.instance.vehicle.battery_capacity)
                    
                    route.total_cost += energy_to_charge * self.instance.technologies[tech.id].cost_per_kwh
                    route.total_cost += self.instance.battery_depreciation_cost
            
            prev_node = node_id
        
        if current_battery < energy_consumed:
            route.is_feasible = False
            return
        
        current_time += travel_time
        route.total_distance += travel_dist
        route.total_time = current_time
        
        if current_time > self.instance.max_route_duration:
            route.is_feasible = False
