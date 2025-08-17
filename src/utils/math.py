# import numpy as np
from EVRP.classes.instance import Matrix
from EVRP.classes.node import Node
from typing import  List, Tuple, TypeAlias
import math

DistanceTimeMatrices: TypeAlias = Tuple[Matrix, Matrix]

def euclidean_distance(node1: Node, node2: Node) -> float:
    return math.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)

def build_matrices(nodes: List[Node], avg_speed: float = 25.0) -> DistanceTimeMatrices:
    distance_matrix = {}
    time_matrix = {}

    for node_i in nodes:
        distance_matrix[node_i.id] = {}
        time_matrix[node_i.id] = {}

        for node_j in nodes:
            if node_i.id != node_j.id:
                dist = math.sqrt((node_i.x - node_j.x) ** 2 + (node_i.y - node_j.y) ** 2)
                distance_matrix[node_i.id][node_j.id] = dist
                time_matrix[node_i.id][node_j.id] = dist / avg_speed
            else:
                distance_matrix[node_i.id][node_j.id] = 0.0
                time_matrix[node_i.id][node_j.id] = 0.0

    return distance_matrix, time_matrix


def energy_consumed(distance: float, consumption_rate: float) -> float:
    return distance * consumption_rate

def time_to_charge(energy_needed: float, charging_power: float) -> float:
    return energy_needed / charging_power