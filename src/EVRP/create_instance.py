
from math import floor
from EVRP.classes.customer import Customer
from EVRP.classes.depot import Depot
from EVRP.classes.instance import Instance
from EVRP.classes.station import Station
from EVRP.classes.technology import Technology
from EVRP.classes.vehicle import Vehicle
from utils.math import build_matrices
from utils.read_file import read_gvrp_file

def create_evrp_instance(filename: str) -> Instance:
    """
    Cria uma instância do problema EVRP a partir de um dicionário de dados lido com `read_gvrp_file`.

    Args:
        filename (str): Caminho para o arquivo de EVRP

    Returns:
        Instance: Objeto da instância do problema pronto para uso
    """
    data = read_gvrp_file(filename)
    instance = Instance()

    instance.technologies = [
        Technology(0, power=3.6, cost_per_kwh=0.160),   # Slow (only at depot)
        Technology(1, power=20, cost_per_kwh=0.176),  # Medium (CHAdeMO)
        Technology(2, power=45, cost_per_kwh=0.192)   # Fast (wireless)
    ]

    # Create depot
    depot_data = data["depot"]
    depot = Depot(
        id=depot_data["id"], 
        x=depot_data["x"], 
        y=depot_data["y"],
    )
    depot.technologies = [instance.technologies[0]]
    instance.nodes.append(depot)
    instance.depots.append(depot)

    for customer in data["customers"]:
        node = Customer(
            id=customer["id"],
            x=customer["x"],
            y=customer["y"],
            demand=customer["demand"],
            service_time=customer["service_time"],
            ready_time=customer["ready_time"],
            due_date=customer["due_date"]
        )
        instance.nodes.append(node)
        instance.customers.append(node)

    # Create recharge stations
    for point in data["recharge_points"]:
        node = Station(
            id=point["id"],
            x=point["x"],
            y=point["y"],
        )
        # Assign all technologies to stations (simplified approach)
        node.technologies = [instance.technologies[1], instance.technologies[2]]
        instance.nodes.append(node)
        instance.stations.append(node)

    # Set number of vehicles (heuristic: based on number of customers)
    instance.num_vehicles = floor(max(1, len(data["customers"]) / 4))
    
    # Create vehicle with parameters from file
    vehicle_params = data["vehicle_params"]
    instance.vehicle = Vehicle(
        capacity=vehicle_params.get("capacity", vehicle_params.get("capacity", 200)),
        battery_capacity=vehicle_params.get("battery_capacity", vehicle_params.get("battery_capacity", 79.79)),
        consumption_rate=vehicle_params.get("consumption_rate", 0.125),
    )

    # Set time-related parameters
    instance.max_route_duration = 8 * 60 * 1000 # Use depot's due date as max route duration
    instance.charging_fixed_time = vehicle_params.get("refueling_rate", 3.39)  # horas
    instance.battery_depreciation_cost = 2.27  # €/ciclo

    instance.distance_matrix, instance.time_matrix = build_matrices(instance.nodes)

    return instance
