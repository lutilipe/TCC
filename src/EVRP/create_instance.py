
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
    Cria uma instância do problema GVRP a partir de um dicionário de dados lido com `read_gvrp_file`.

    Args:
        data (dict): Saída da função read_gvrp_file

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

    depot_data = data["recharge_points"][0]
    depot = Depot(id=depot_data["id"], x=depot_data["x"], y=depot_data["y"])
    depot.technologies = [instance.technologies[0]]
    instance.nodes.append(depot)
    instance.depots.append(depot)

    for customer in data["customers"]:
        node = Customer(
            id=customer["id"],
            x=customer["x"],
            y=customer["y"],
            demand=customer["demand"],
            service_time=customer["service_time"]
        )
        instance.nodes.append(node)
        instance.customers.append(node)

    for point in data["recharge_points"]:
        if point["id"] == 0:
            continue
        node = Station(
            id=point["id"],
            x=point["x"],
            y=point["y"]
        )
        node.technologies = [
            instance.technologies[idx]
            for idx, flag in enumerate(point["technologies"])
            if flag == 1 and idx < len(instance.technologies)
        ]
        instance.nodes.append(node)
        instance.stations.append(node)

    instance.num_vehicles = int(data["parameters"]["NN"] / 4)
    instance.vehicle = Vehicle(
        capacity=2300,
        battery_capacity=20,
        consumption_rate=0.125
    )

    instance.max_route_duration = 8 * 60  # horas
    instance.charging_fixed_time = 0.1  # horas
    instance.battery_depreciation_cost = 2.27  # €/ciclo

    instance.distance_matrix, instance.time_matrix = build_matrices(instance.nodes)

    return instance
