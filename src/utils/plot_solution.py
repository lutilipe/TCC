from matplotlib import pyplot as plt
from matplotlib.patheffects import withStroke
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import os
import warnings

from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.solution import Solution

def plot_solution(instance: Instance, solution: Solution, save_path: str = None):
    """
    Plota uma solução do problema GVRP com rotas destacadas e exibe métricas,
    incluindo o número de carros (rotas) utilizados. Legenda e resumo por rota
    são posicionados fora do grid para não sobrepor os pontos.
    
    Args:
        instance: Instância do problema EVRP
        solution: Solução a ser plotada
        save_path: Caminho opcional para salvar a figura (se None, usa o padrão)
    """
    depots = [n for n in instance.nodes if n.type == NodeType.DEPOT]
    customers = [n for n in instance.nodes if n.type == NodeType.CUSTOMER]
    stations = [n for n in instance.nodes if n.type == NodeType.STATION]

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(14, 11))

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

    def add_image_to_plot(img, ax, x, y, zoom=0.05, zorder=7):
        """Add an image to the plot at specified coordinates"""
        im = OffsetImage(img, zoom=zoom)
        ab = AnnotationBbox(im, (x, y), frameon=False, zorder=zorder)
        ax.add_artist(ab)
        return ab

    cmap = plt.get_cmap('cividis')

    colors = [cmap(i / len(solution.routes)) for i in range(len(solution.routes))]
    route_metrics = []
    for i, route in enumerate(solution.routes):
        color = colors[i]
        route_metrics.append(
            f"Rota {i+1}: {len([n for n in route.nodes if n.type==NodeType.CUSTOMER])} clientes | "
            f"€{route.total_cost:.2f} | {route.total_distance:.2f}km"
        )

        xs = [n.x for n in route.nodes]
        ys = [n.y for n in route.nodes]
        ax.plot(xs, ys, 'o-', linewidth=2.5, markersize=7,
                color=color, alpha=0.9, label=f'Rota {i+1}', zorder=3)
        for j in range(1, len(route.nodes)):
            start, end = route.nodes[j-1], route.nodes[j]
            dx, dy = end.x - start.x, end.y - start.y
            ax.arrow(start.x, start.y, dx*0.85, dy*0.85,
                     head_width=0.7, head_length=1.0,
                     fc=color, ec=color, length_includes_head=True,
                     alpha=0.9, zorder=2)

        for idx, node in enumerate(route.nodes):
            if node.type == NodeType.STATION and node.id in route.charging_decisions:
                tech, energy = route.charging_decisions[node.id]
                ax.scatter(node.x, node.y, s=220, marker='*',
                           color='gold', edgecolor='black', zorder=6)
                ax.annotate(f"{tech.id} ({energy:.1f}kWh)", (node.x, node.y),
                            textcoords="offset points", xytext=(0,12),
                            ha='center', fontsize=9, weight='bold',
                            path_effects=[withStroke(linewidth=2, foreground="white")],
                            bbox=dict(boxstyle="round,pad=0.2", fc="yellow",
                                      ec="black", alpha=0.7))

    # Plot icons on top of everything (after routes)
    # Plot customers
    for c in customers:
        add_image_to_plot(client_img, ax, c.x, c.y, zoom=0.03, zorder=8)

    # Plot stations
    for s in stations:
        add_image_to_plot(station_img, ax, s.x, s.y, zoom=0.05, zorder=8)

    # Plot depots
    for d in depots:
        add_image_to_plot(depot_img, ax, d.x, d.y, zoom=0.07, zorder=9)
        ax.annotate(f"D{d.id}", (d.x, d.y), textcoords="offset points", xytext=(0,15),
                    ha='center', fontsize=11, weight='bold',
                    path_effects=[withStroke(linewidth=3, foreground="white")], zorder=10)

    ax.set_xlabel("Coordenada X", fontsize=12)
    ax.set_ylabel("Coordenada Y", fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_aspect('equal', 'box')

    # Save at high resolution
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.savefig("./assets/solution.png", dpi=300, bbox_inches='tight')
    plt.close()
