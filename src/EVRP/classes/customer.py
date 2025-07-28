from .node import Node, NodeType

class Customer(Node):
    def __init__(self, 
            id: int,
            x: float,
            y: float,
            demand: float = 0,
            service_time: float = 0
        ):
        super().__init__(id=id, x=x, y=y, node_type = NodeType.CUSTOMER)
        self.demand = demand
        self.service_time = service_time
