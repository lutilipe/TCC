from typing import List, Dict, Tuple

from EVRP.classes.node import Node
from EVRP.classes.technology import Technology

class Route:
    def __init__(self):
        self.nodes: List[Node] = []
        self.charging_decisions: Dict[int, Tuple[Technology, float]] = {}
        self.total_distance: float = 0
        self.total_cost: float = 0
        self.total_time: float = 0
        self.is_feasible: bool = True