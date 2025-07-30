from typing import List
from EVRP.classes.node import Node, NodeType
from EVRP.classes.technology import Technology

class Depot(Node):
    def __init__(
            self, 
            id: int,
            x: float,
            y: float,
        ):
        super().__init__(id=id, x=x, y=y, node_type = NodeType.DEPOT)
        self.technologies: List[Technology] = []
