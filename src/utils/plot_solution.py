from matplotlib import pyplot as plt
from matplotlib.patheffects import withStroke

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
    depot = next((n for n in instance.nodes if n.type == NodeType.DEPOT), None)
    customers = [n for n in instance.nodes if n.type == NodeType.CUSTOMER]
    stations = [n for n in instance.nodes if n.type == NodeType.STATION]

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(14, 11))

    # Make the plot occupy all available space
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

    ax.scatter(depot.x, depot.y, c='#2ca02c', marker='s', s=180,
               label='Depósito', edgecolor='black', zorder=5)
    ax.annotate("Depósito", (depot.x, depot.y), textcoords="offset points", xytext=(0,15),
                ha='center', fontsize=11, weight='bold',
                path_effects=[withStroke(linewidth=3, foreground="white")], zorder=5)

    ax.scatter([c.x for c in customers], [c.y for c in customers],
               c='#1f77b4', marker='o', s=70, label='Clientes',
               edgecolor='black', zorder=4)

    ax.scatter([s.x for s in stations], [s.y for s in stations],
               c='#d62728', marker='^', s=100, label='Estações de Recarga',
               edgecolor='black', zorder=4)

    colors = plt.cm.tab10.colors
    route_metrics = []
    for i, route in enumerate(solution.routes):
        color = colors[i % len(colors)]
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
            if node.type == 'station' and idx in route.charging_decisions:
                tech, energy = route.charging_decisions[idx]
                ax.scatter(node.x, node.y, s=220, marker='*',
                           color='gold', edgecolor='black', zorder=6)
                ax.annotate(f"{tech.id} ({energy:.1f}kWh)", (node.x, node.y),
                            textcoords="offset points", xytext=(0,12),
                            ha='center', fontsize=9, weight='bold',
                            path_effects=[withStroke(linewidth=2, foreground="white")],
                            bbox=dict(boxstyle="round,pad=0.2", fc="yellow",
                                      ec="black", alpha=0.7))

    ax.set_xlabel("Coordenada X", fontsize=12)
    ax.set_ylabel("Coordenada Y", fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.set_aspect('equal', 'box')

    # Save at high resolution
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.savefig("./assets/solution.png", dpi=300, bbox_inches='tight')
    plt.close()
