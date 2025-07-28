from typing import List
from EVRP.classes.node import Node
from EVRP.classes.technology import Technology
from EVRP.classes.vehicle import Vehicle

class Instance:
    def __init__(self):
        self.nodes: List[Node] = []
        self.vehicles: List[Vehicle] = []
        self.distance_matrix: List[List[float]] = None
        self.time_matrix: List[List[float]] = None
        self.technologies: List[Technology] = []
        self.max_route_duration = 0
        self.charging_fixed_time = 0
        self.battery_depreciation_cost = 0
        self.night_charging_cost = 0

    def get_node_by_id(self, id: int):
        for node in self.nodes:
            if node.id == id:
                return node
        return None
