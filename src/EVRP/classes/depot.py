from EVRP.classes.node import Node, NodeType

class Depot(Node):
    def __init__(
            self, 
            id: int,
            x: float,
            y: float,
        ):
        super().__init__(id=id, x=x, y=y, node_type = NodeType.DEPOT)
        self.technologies = []
