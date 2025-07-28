class Vehicle:
    def __init__(self, capacity: float, battery_capacity: float, consumption_rate: float):
        self.capacity = capacity  # kg
        self.battery_capacity = battery_capacity  # kWh
        self.consumption_rate = consumption_rate  # kWh/km
        self.max_range = battery_capacity / consumption_rate  # km
