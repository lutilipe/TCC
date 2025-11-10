from typing import List
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.classes.route import Route

class Solution:
    def __init__(self, instance: Instance, penalty_weight: float = 1000.0):
        self.instance = instance
        self.routes: List[Route] = []
        self.total_distance: float = 0
        self.total_cost: float = 0
        self.num_vehicles_used: int = 0
        self.is_feasible: bool = True
        self.penalty_weight: float = penalty_weight
        self.total_penalties: float = 0.0
        self.violations: dict = {
            'vehicle_excess': 0,
            'unserved_customers': 0,
            'route_violations': 0
        }
        
    def evaluate(self):
        """Evaluate the complete solution with separate penalty tracking"""
        self.total_distance = 0
        self.total_cost = 0
        self.num_vehicles_used = len(self.routes)
        self.is_feasible = True
        self.total_penalties = 0.0
        self.violations = {
            'vehicle_excess': 0,
            'unserved_customers': 0,
            'route_violations': 0
        }
        
        # Check if we have too many vehicles
        if self.num_vehicles_used > self.instance.num_vehicles:
            self.is_feasible = False
            vehicle_excess = self.num_vehicles_used - self.instance.num_vehicles
            self.violations['vehicle_excess'] = vehicle_excess
            self.total_penalties += vehicle_excess * self.penalty_weight
            print(f"Too many vehicles used: {self.num_vehicles_used} > {self.instance.num_vehicles} (penalty: {vehicle_excess * self.penalty_weight})")
        
        # Evaluate all routes
        route_violations = 0
        for _, route in enumerate(self.routes):
            route.evaluate(self.instance)
            self.total_distance += route.total_distance
            self.total_cost += route.total_cost
            self.total_penalties += route.total_penalties
            if not route.is_feasible and route.total_cost > 0:
                self.is_feasible = False
                route_violations += 1
        
        self.violations['route_violations'] = route_violations
        
        # Check customer service
        served_customers = set()
        for route in self.routes:
            for node in route.nodes:
                if node.type == NodeType.CUSTOMER:
                    served_customers.add(node.id)
        
        all_customers = {node.id for node in self.instance.nodes if node.type == NodeType.CUSTOMER}
        unserved_customers = all_customers - served_customers
        
        if unserved_customers:
            self.is_feasible = False
            self.violations['unserved_customers'] = len(unserved_customers)
            self.total_penalties += len(unserved_customers) * self.penalty_weight
            print(f"Unserved customers: {unserved_customers} (penalty: {len(unserved_customers) * self.penalty_weight})")

    def dominates(self, new_sol: "Solution") -> bool:
        """
        Verifica se a solucao domina new_sol (critério de dominância de Pareto)
        Now considers penalties as a separate objective
        """
        # Para o EVRP, consideramos múltiplos objetivos
        # Objetivo 1: Minimizar distância total
        # Objetivo 2: Minimizar custo total
        # Objetivo 3: Minimizar penalidades totais
        # Verifica se sol1 é melhor ou igual em todos os objetivos
        
        if (self.total_distance <= new_sol.total_distance and
            self.total_cost <= new_sol.total_cost and
            self.total_penalties <= new_sol.total_penalties):
            # Verifica se sol1 é melhor em pelo menos um objetivo
            if (self.total_distance < new_sol.total_distance or
                self.total_cost < new_sol.total_cost or
                self.total_penalties < new_sol.total_penalties):
                return True
        return False
    
    def get_total_violations(self) -> int:
        """
        Returns total number of constraint violations
        """
        return sum(self.violations.values())
