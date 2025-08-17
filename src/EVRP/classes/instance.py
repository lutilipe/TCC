from typing import Dict, List, TypeAlias
from EVRP.classes.customer import Customer
from EVRP.classes.depot import Depot
from EVRP.classes.node import Node
from EVRP.classes.station import Station
from EVRP.classes.technology import Technology
from EVRP.classes.vehicle import Vehicle

Matrix: TypeAlias = Dict[int, Dict[int, float]]

class Instance:
    def __init__(self):
        self.nodes: List[Node] = []
        self.customers: List[Customer] = []
        self.stations: List[Station] = []
        self.depots: List[Depot] = []
        self.vehicle: Vehicle = None
        self.num_vehicles = 0
        self.distance_matrix: Matrix = None
        self.time_matrix: Matrix = None
        self.technologies: List[Technology] = []
        self.max_route_duration = 0
        self.charging_fixed_time = 0
        self.battery_depreciation_cost = 0

    def get_node_by_id(self, id: int):
        for node in self.nodes:
            if node.id == id:
                return node
        return None
