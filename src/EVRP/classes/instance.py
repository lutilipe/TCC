from typing import Dict, List, TypeAlias
from EVRP.classes.node import Node
from EVRP.classes.technology import Technology
from EVRP.classes.vehicle import Vehicle

Matrix: TypeAlias = Dict[int, Dict[int, float]]

class Instance:
    def __init__(self):
        self.nodes: List[Node] = []
        self.vehicle: Vehicle = None
        self.num_vehicles = 0
        self.distance_matrix: Matrix = None
        self.time_matrix: Matrix = None
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
