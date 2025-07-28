import numpy as np
from EVRP.classes.node import Node
from typing import List

def euclidean_distance(node1: Node, node2: Node) -> float:
    return np.sqrt((node1.x - node2.x)**2 + (node1.y - node2.y)**2)

def build_distance_matrix(nodes: List[Node]) -> List[List[float]]:
    n = len(nodes)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = euclidean_distance(nodes[i], nodes[j])
    return matrix

def build_time_matrix(distance_matrix: List[List[float]], avg_speed: float) -> List[List[float]]:
    return [[d / avg_speed for d in row] for row in distance_matrix]

def energy_consumed(distance: float, consumption_rate: float) -> float:
    return distance * consumption_rate

def time_to_charge(energy_needed: float, charging_power: float) -> float:
    return energy_needed / charging_power