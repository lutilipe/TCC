from typing import List, Dict, Tuple

from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.technology import Technology

class Route:
    def __init__(self, penalty_weight: float = 1000.0):
        self.nodes: List[Node] = []
        self.charging_decisions: Dict[int, Tuple[Technology, float]] = {}
        self.total_distance: float = 0
        self.total_cost: float = 0
        self.total_time: float = 0
        self.is_feasible: bool = True
        self.penalty_weight: float = penalty_weight
        self.total_penalties: float = 0.0
        self.violations: dict = {
            'battery_violations': 0,
            'capacity_violations': 0,
            'time_window_violations': 0,
            'duration_violations': 0,
            'technology_violations': 0
        }

    def evaluate(self, instance: Instance):
        if not self.nodes:
            self.is_feasible = False
            self.total_penalties = self.penalty_weight  # Empty route penalty
            return
        
        self.total_distance = 0
        self.total_cost = 0
        self.total_time = 0
        self.is_feasible = True
        self.total_penalties = 0.0
        self.violations = {
            'battery_violations': 0,
            'capacity_violations': 0,
            'time_window_violations': 0,
            'duration_violations': 0,
            'technology_violations': 0
        }
        
        current_battery = instance.vehicle.battery_capacity
        current_load = 0
        current_time = 0
        
        # First and last nodes must be depots
        if not self.nodes or self.nodes[0].type != NodeType.DEPOT or self.nodes[-1].type != NodeType.DEPOT:
            self.is_feasible = False
            self.total_penalties += self.penalty_weight  # Depot structure violation
            return

        start_depot_id = self.nodes[0].id
        prev_node_id = start_depot_id
        
        for i, node in enumerate(self.nodes[1:], 1):
            node_id = node.id
            
            travel_dist = instance.distance_matrix[prev_node_id][node_id]
            travel_time = instance.time_matrix[prev_node_id][node_id]
            energy_consumed = travel_dist * instance.vehicle.consumption_rate
            
            # Check battery constraint - now with penalty instead of failure
            if current_battery < energy_consumed:
                self.is_feasible = False
                battery_deficit = energy_consumed - current_battery
                self.violations['battery_violations'] += 1
                self.total_penalties += battery_deficit * self.penalty_weight
                current_battery = 0
            
            current_battery -= energy_consumed
            current_time += travel_time
            self.total_distance += travel_dist
            
            if node.type == NodeType.CUSTOMER:
                current_load += node.demand
                
                if hasattr(node, 'ready_time') and hasattr(node, 'due_date'):
                    if current_time < node.ready_time:
                        current_time = node.ready_time
                    
                    if current_time > node.due_date:
                        self.is_feasible = False
                        time_excess = current_time - node.due_date
                        self.violations['time_window_violations'] += 1
                        self.total_penalties += time_excess * self.penalty_weight
                
                current_time += node.service_time
                
                # Capacity violation - now with penalty
                if current_load > instance.vehicle.capacity:
                    self.is_feasible = False
                    capacity_excess = current_load - instance.vehicle.capacity
                    self.violations['capacity_violations'] += 1
                    self.total_penalties += capacity_excess * self.penalty_weight
                    # Continue execution
            else:
                if node_id in self.charging_decisions:
                    tech, energy_to_charge = self.charging_decisions[node_id]
                    
                    tech_found = any(t.id == tech.id for t in node.technologies)
                    
                    # Technology violation - now with penalty
                    if not tech_found:
                        self.is_feasible = False
                        self.violations['technology_violations'] += 1
                        self.total_penalties += self.penalty_weight
                        # Skip charging but continue
                    else:
                        charging_time = energy_to_charge / tech.power
                        current_time += instance.charging_fixed_time + charging_time
                        current_battery = min(current_battery + energy_to_charge, instance.vehicle.battery_capacity)
                        
                        self.total_cost += energy_to_charge * tech.cost_per_kwh
                        if hasattr(instance, 'battery_depreciation_cost'):
                            self.total_cost += instance.battery_depreciation_cost
            
            prev_node_id = node_id
        
        self.total_time = current_time
        
        # Duration violation - now with penalty
        if current_time > instance.max_route_duration:
            self.is_feasible = False
            duration_excess = current_time - instance.max_route_duration
            self.violations['duration_violations'] += 1
            self.total_penalties += duration_excess * self.penalty_weight
    
    def dominates(self, new_route: "Route") -> bool:
        """
        Verifica se sol1 domina sol2 (critério de dominância de Pareto)
        Now considers penalties as a separate objective
        """
        # Para o EVRP, consideramos múltiplos objetivos
        # Objetivo 1: Minimizar distância total
        # Objetivo 2: Minimizar custo total
        # Objetivo 3: Minimizar penalidades totais
        # Verifica se sol1 é melhor ou igual em todos os objetivos
        
        if (self.total_distance <= new_route.total_distance and
            self.total_cost <= new_route.total_cost and
            self.total_penalties <= new_route.total_penalties):
            # Verifica se sol1 é melhor em pelo menos um objetivo
            if (self.total_distance < new_route.total_distance or
                self.total_cost < new_route.total_cost or
                self.total_penalties < new_route.total_penalties):
                return True
        return False
    
    def get_total_violations(self) -> int:
        """
        Returns total number of constraint violations
        """
        return sum(self.violations.values())