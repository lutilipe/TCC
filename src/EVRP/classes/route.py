from typing import List, Dict, Tuple

from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.technology import Technology

class Route:
    def __init__(self):
        self.nodes: List[Node] = []
        self.charging_decisions: Dict[int, Tuple[Technology, float]] = {}
        self.total_distance: float = 0
        self.total_cost: float = 0
        self.total_time: float = 0
        self.is_feasible: bool = True

    def evaluate(self, instance: Instance):
        """Evaluate a single route for feasibility and compute metrics"""
        if not self.nodes:
            self.is_feasible = False
            return
        
        self.total_distance = 0
        self.total_cost = 0
        self.total_time = 0
        self.is_feasible = True
        
        current_battery = instance.vehicle.battery_capacity
        current_load = 0
        current_time = 0
        
        depot_id = next((n.id for n in instance.nodes if n.type == NodeType.DEPOT), None)
        if depot_id is None:
            self.is_feasible = False
            ##print(f"Route: No depot found")
            return
        
        if self.nodes[0].id != depot_id or self.nodes[-1].id != depot_id:
            self.is_feasible = False
            #print(f"Route: Route must start and end at depot")
            return
        
        prev_node_id = depot_id
        
        for i, node in enumerate(self.nodes[1:], 1):
            node_id = node.id
            
            travel_dist = instance.distance_matrix[prev_node_id][node_id]
            travel_time = instance.time_matrix[prev_node_id][node_id]
            energy_consumed = travel_dist * instance.vehicle.consumption_rate
            
            if current_battery < energy_consumed:
                self.is_feasible = False
                #print(f"Route, Node {i}: Insufficient battery: {current_battery:.2f} < {energy_consumed:.2f}")
                return
            
            current_battery -= energy_consumed
            current_time += travel_time
            self.total_distance += travel_dist
            
            if node.type == NodeType.CUSTOMER:
                current_load += node.demand
                current_time += node.service_time
                
                if current_load > instance.vehicle.capacity:
                    self.is_feasible = False
                    #print(f"Route, Node {i}: Capacity exceeded: {current_load:.2f} > {instance.vehicle.capacity:.2f}")
                    return
            else:
                if node_id in self.charging_decisions:
                    tech, energy_to_charge = self.charging_decisions[node_id]
                    
                    tech_found = any(t.id == tech.id for t in node.technologies)
                    
                    if not tech_found:
                        self.is_feasible = False
                        #print(f"Route, Node {i}: Technology {tech.id} not available at node {node_id}")
                        return
                    
                    charging_time = energy_to_charge / tech.power
                    current_time += instance.charging_fixed_time + charging_time
                    current_battery = min(current_battery + energy_to_charge, instance.vehicle.battery_capacity)
                    
                    self.total_cost += energy_to_charge * tech.cost_per_kwh
                    if hasattr(instance, 'battery_depreciation_cost'):
                        self.total_cost += instance.battery_depreciation_cost
            
            prev_node_id = node_id
        
        self.total_time = current_time
        
        if current_time > instance.max_route_duration:
            self.is_feasible = False
            #print(f"Route: Time limit exceeded: {current_time:.2f} > {instance.max_route_duration:.2f}")
    
    def dominates(self, new_route: "Route") -> bool:
        """
        Verifica se sol1 domina sol2 (critério de dominância de Pareto)
        """
        # Para o EVRP, consideramos múltiplos objetivos
        # Objetivo 1: Minimizar distância total
        # Objetivo 2: Minimizar custo total
        # Verifica se sol1 é melhor ou igual em todos os objetivos
        if (self.total_distance <= new_route.total_distance and
            self.total_cost <= new_route.total_cost):
            # Verifica se sol1 é melhor em pelo menos um objetivo
            if (self.total_distance < new_route.total_distance or
                self.total_cost < new_route.total_cost):
                return True
        return False