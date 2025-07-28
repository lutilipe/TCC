class Technology:
    def __init__(self, id: str, power: float, cost_per_kwh: float):
        self.id = id
        self.power = power  # kWh/h
        self.cost_per_kwh = cost_per_kwh
