import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType

def plot_gvrp_instance(instance: Instance):
    """
    Plota a instância do problema GVRP com estilo aprimorado.

    Args:
        instance (Instance): Instância do problema GVRP
    """
    depot = [n for n in instance.nodes if n.type == NodeType.DEPOT][0]
    customers = [n for n in instance.nodes if n.type == NodeType.CUSTOMER]
    stations = [n for n in instance.nodes if n.type == NodeType.STATION]

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(12, 10))

    customer_x = [c.x for c in customers]
    customer_y = [c.y for c in customers]
    ax.scatter(customer_x, customer_y, c="#1f77b4", marker="o", s=50, label="Clientes", edgecolor="black")

    station_x = [s.x for s in stations]
    station_y = [s.y for s in stations]
    ax.scatter(station_x, station_y, c="#d62728", marker="^", s=90, label="Estações de Recarga", edgecolor="black")

    ax.scatter(depot.x, depot.y, c="#2ca02c", marker="s", s=150, label="Depósito", edgecolor="black")
    ax.annotate("Depósito", (depot.x, depot.y), textcoords="offset points", xytext=(0,10),
                ha="center", fontsize=10, weight="bold", path_effects=[pe.withStroke(linewidth=3, foreground="white")])

    ax.set_title("Instância do Problema GVRP", fontsize=16, weight="bold")
    ax.set_xlabel("Coordenada X", fontsize=12)
    ax.set_ylabel("Coordenada Y", fontsize=12)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_aspect("equal", "box")

    plt.tight_layout()
    plt.savefig("./assets/teste.png")
    plt.close()


def print_instance_summary(instance: Instance) -> None:
    """
    Imprime um resumo da instância do problema GVRP.

    Args:
        instance (Instance): Instância do problema GVRP
    """
    print("===== Instância EVRP Sumário =====")
    print(f"Total de Nós: {len(instance.nodes)}")

    depot = next((n for n in instance.nodes if n.type == NodeType.DEPOT), None)
    customers = [n for n in instance.nodes if n.type == NodeType.CUSTOMER]
    stations = [n for n in instance.nodes if n.type == NodeType.STATION]

    print(f"- Depósito: ID {depot.id} at ({depot.x:.2f}, {depot.y:.2f}) | Tecnologias: {depot.technologies[0].id}")
    print(f"- Clientes: {len(customers)}")
    for c in customers[:3]:
        print(f"  · ID {c.id} em ({c.x:.2f}, {c.y:.2f}) | Demanda: {c.demand} | Tempo de Serviço: {c.service_time} h")

    print(f"- Estação de Recarga: {len(stations)}")
    for s in stations:
        techs = ", ".join(t.id for t in s.technologies)
        print(f"  · ID {s.id} em ({s.x:.2f}, {s.y:.2f}) | Tecnologias: {techs}")

    print("\nTecnologias:")
    for t in instance.technologies:
        print(f"· {t.id.capitalize()} — Velocidade: {t.power} kWh/h, Custo: €{t.cost_per_kwh:.3f}/kWh")

    print(f"\nVeículos: {len(instance.vehicles)}")
    for i, v in enumerate(instance.vehicles[:1]):
        print(f"- Capacidade={v.capacity} kg, Bateria={v.battery_capacity} kWh, Consumo={v.consumption_rate} kWh/km")

    print("\nParâmetros:")
    print(f"· Tempo máximo de duração da rota: {instance.max_route_duration} h")
    print(f"· Tempo fixo para recarga: {instance.charging_fixed_time} h")
    print(f"· Custo de depreciação da bateria: €{instance.battery_depreciation_cost}/cycle")
    print(f"· Custo recarga noturna: €{instance.night_charging_cost}/kWh")

    print("\nMatrix de distância (truncada):")
    for row in instance.distance_matrix[:5]:
        print("  ", ["{:.1f}".format(d) for d in row[:5]])

    print("\nMatrix de tempo (truncada):")
    for row in instance.time_matrix[:5]:
        print("  ", ["{:.2f}".format(t) for t in row[:5]])

    print("=================================\n")
