from enum import Enum

class NodeType(Enum):
    DEPOT = 1
    CUSTOMER = 2
    STATION = 3

class Node:
    def __init__(self, id: int, node_type: NodeType, x: float, y: float):
        self.id = id
        self.type = node_type
        self.x = x
        self.y = y