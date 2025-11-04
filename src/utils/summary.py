import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import os
import warnings
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.classes.technology import TECH_NAME

def plot_gvrp_instance(instance: Instance):
    """
    Plota a instância do problema GVRP com estilo aprimorado.

    Args:
        instance (Instance): Instância do problema GVRP
    """
    depots = [n for n in instance.nodes if n.type == NodeType.DEPOT]
    customers = [n for n in instance.nodes if n.type == NodeType.CUSTOMER]
    stations = [n for n in instance.nodes if n.type == NodeType.STATION]

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(12, 10))

    # Load asset images
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    client_img = Image.open(os.path.join(base_path, "assets", "client.png"))
    depot_img = Image.open(os.path.join(base_path, "assets", "depot.png"))
    station_img = Image.open(os.path.join(base_path, "assets", "recharge_station.png"))

    # Collect all coordinates to set proper axis limits
    all_x = [n.x for n in instance.nodes]
    all_y = [n.y for n in instance.nodes]
    
    # Set axis limits with some padding
    x_range = max(all_x) - min(all_x)
    y_range = max(all_y) - min(all_y)
    x_padding = x_range * 0.1
    y_padding = y_range * 0.1
    ax.set_xlim(min(all_x) - x_padding, max(all_x) + x_padding)
    ax.set_ylim(min(all_y) - y_padding, max(all_y) + y_padding)

    def add_image_to_plot(img, ax, x, y, zoom=0.05):
        """Add an image to the plot at specified coordinates"""
        im = OffsetImage(img, zoom=zoom)
        ab = AnnotationBbox(im, (x, y), frameon=False)
        ax.add_artist(ab)
        return ab

    for c in customers:
        add_image_to_plot(client_img, ax, c.x, c.y, zoom=0.03)
    
    for s in stations:
        add_image_to_plot(station_img, ax, s.x, s.y, zoom=0.05)
    
    for d in depots:
        add_image_to_plot(depot_img, ax, d.x, d.y, zoom=0.07)
        ax.annotate(f"D{d.id}", (d.x, d.y), textcoords="offset points", xytext=(0,15),
                    ha='center', fontsize=11, weight='bold',
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")], zorder=10)

    ax.set_title("Instância do Problema GVRP", fontsize=16, weight="bold")
    ax.set_xlabel("Coordenada X", fontsize=12)
    ax.set_ylabel("Coordenada Y", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_aspect("equal", "box")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        plt.tight_layout(pad=2.0)
    
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

    depots = [n for n in instance.nodes if n.type == NodeType.DEPOT]
    customers = [n for n in instance.nodes if n.type == NodeType.CUSTOMER]
    stations = [n for n in instance.nodes if n.type == NodeType.STATION]

    print(f"- Depósitos: {len(depots)}")
    for d in depots:
        techs = ", ".join(TECH_NAME[t.id] for t in getattr(d, 'technologies', [])) if getattr(d, 'technologies', []) else "-"
        print(f"  · ID {d.id} em ({d.x:.2f}, {d.y:.2f}) | Tecnologias: {techs}")
    print(f"- Clientes: {len(customers)}")
    for c in customers[:3]:
        print(f"  · ID {c.id} em ({c.x:.2f}, {c.y:.2f}) | Demanda: {c.demand} | Tempo de Serviço: {c.service_time} h")

    print(f"- Estação de Recarga: {len(stations)}")
    for s in stations:
        techs = ", ".join(TECH_NAME[t.id] for t in s.technologies)
        print(f"  · ID {s.id} em ({s.x:.2f}, {s.y:.2f}) | Tecnologias: {techs}")

    print("\nTecnologias:")
    for t in instance.technologies:
        print(f"· {TECH_NAME[t.id].capitalize()} — Velocidade: {t.power} kWh/h, Custo: €{t.cost_per_kwh:.3f}/kWh")

    print(f"\nVeículos: {instance.num_vehicles}")
    print(f"- Capacidade={instance.vehicle.capacity} kg, Bateria={instance.vehicle.battery_capacity} kWh, Consumo={instance.vehicle.consumption_rate} kWh/km")
        

    print("\nParâmetros:")
    print(f"· Tempo máximo de duração da rota: {instance.max_route_duration} h")
    print(f"· Tempo fixo para recarga: {instance.charging_fixed_time} h")
    print(f"· Custo de depreciação da bateria: €{instance.battery_depreciation_cost}/cycle")

    print("=================================\n")
    plot_gvrp_instance(instance)
