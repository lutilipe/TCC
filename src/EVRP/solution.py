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
        
        for _, route in enumerate(self.routes):
            route.evaluate(self.instance)
            self.total_distance += route.total_distance
            self.total_cost += route.total_cost
            if not route.is_feasible:
                self.is_feasible = False
        
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
