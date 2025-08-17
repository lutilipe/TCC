from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Reinsertion:
    def __init__(self, instance: Instance):
        self.instance = instance

    def run(self, solution: 'Solution') -> bool:
        pass