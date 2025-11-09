import os
import numpy as np
import json
import matplotlib.pyplot as plt
from EVRP import GVNS
from EVRP.constructive_heuristic import ConstructiveHeuristic
from EVRP.create_instance import create_evrp_instance
from EVRP.local_search.recharge_realocation import RechargeRealocation
from EVRP.local_search.relocate import Relocate
from EVRP.local_search.two_opt import TwoOpt
from EVRP.local_search.two_opt_star import TwoOptStar
from EVRP.local_search.depot_reassignment import DepotReassignment
from EVRP.local_search.exchange import Exchange
from EVRP.local_search.route_split import RouteSplit
from EVRP.local_search.eliminate_route import EliminateRoute
from EVRP.metrics import EVRPMetrics
from utils import plot_solution, print_instance_summary

def process_single_instance(instance_file):
    """
    Processa uma única instância (código original do main)
    """
    print("EVRP Solver using General Variable Neighborhood Search (GVNS)")
    print("=" * 70)
    
    instance = create_evrp_instance(instance_file)
    print_instance_summary(instance)

    constructiveHeuristic = ConstructiveHeuristic(instance)
    
    # Cria população inicial de soluções
    print("\nCriando população inicial...")
    initial_solutions = []
    while len(initial_solutions) < 50:
        solution = constructiveHeuristic.build_initial_solution()
        while not solution.is_feasible:
            solution = constructiveHeuristic.build_initial_solution()
        initial_solutions.append(solution)
        if len(initial_solutions) % 10 == 0:
            print(f"  {len(initial_solutions)} soluções criadas...")
    
    print(f"População inicial criada com {len(initial_solutions)} soluções")
    
    print("\n" + "="*70)
    gvns = GVNS(
        instance=instance,
        ns=5,           # Número de soluções por busca local
        na=50,          # Tamanho máximo do arquivo A
        ls_max_iter=5, # Máximo de tentativas de busca local
        max_evaluations=(2000 if len(instance.customers) < 50 else 1000),  # Máximo de avaliações,
        local_search=[
            TwoOpt(instance),
            Relocate(instance, is_intra_route=True),
            Exchange(instance, is_intra_route=True),
            Relocate(instance, is_intra_route=False),
            Exchange(instance, is_intra_route=False),
            TwoOptStar(instance),
            RechargeRealocation(instance),
        ],
        perturbation=[
            EliminateRoute(instance, max_iter=1),
            RouteSplit(instance, max_iter=1, select_best=False),
            DepotReassignment(instance, k=1),
        ],
        track_metrics=True
    )
            
    
    final_solutions = gvns.run(initial_solutions)

    print("\n" + "="*70)
    print("ANÁLISE DE MÉTRICAS PARETO")
    print("="*70)
    
    metrics = EVRPMetrics()

    instance_name = os.path.basename(instance_file).replace('.txt', '')
    instance_output_dir = f"output/{instance_name}"
    
    # Analisa soluções finais
    if final_solutions and len(final_solutions) > 1:
        final_metrics = metrics.evaluate_solution_set(final_solutions)
        
        print(f"📊 Métricas de Qualidade Pareto:")
        print(f"  Medida de Dispersão (Δ): {final_metrics['spread_measure']:.4f}")
        print(f"  Hypervolume (HV): {final_metrics['hypervolume']:.4f}")
        print(f"  Soluções factíveis: {final_metrics['num_feasible']}/{final_metrics['num_solutions']}")
        print(f"  Soluções inviáveis: {final_metrics['num_solutions'] - final_metrics['num_feasible']}/{final_metrics['num_solutions']}")
        print(f"  Ponto Utopiano: {final_metrics['utopian_point']}")
        print(f"  Ponto Nadir: {final_metrics['nadir_point']}")
        
        # Plota fronteira Pareto
        print(f"\nGerando visualização da fronteira Pareto...")

        if os.path.exists(instance_output_dir):
            import shutil
            shutil.rmtree(instance_output_dir)
            print(f" ✓ Diretório {instance_output_dir} limpo")
        
        os.makedirs(instance_output_dir, exist_ok=True)

        try:
            
            pareto_fig = metrics.plot_evrp_pareto_front(final_solutions, 
                                                       f"EVRP Pareto Front - {instance_name}", False)
            pareto_file = f"{instance_output_dir}/pareto_front.png"
            pareto_fig.savefig(pareto_file, dpi=300, bbox_inches='tight')
            print(f"  Fronteira Pareto salva em: {pareto_file}")
            plt.close(pareto_fig)
            
        except Exception as e:
            print(f"  Erro ao gerar fronteira Pareto: {e}")
        
        # Plota convergência se disponível
        if gvns.track_metrics:
            print(f"\nGerando gráficos de convergência...")
            try:
                convergence_data = gvns.get_convergence_data()
                if convergence_data:
                    # Spread
                    fig_spread = metrics.plot_convergence_spread(convergence_data, f"Convergência Δ - {instance_name}")
                    file_spread = f"{instance_output_dir}/convergence_spread.png"
                    fig_spread.savefig(file_spread, dpi=300, bbox_inches='tight')
                    print(f"  Gráfico salvo: {file_spread}")
                    plt.close(fig_spread)

                    # Hypervolume
                    fig_hv = metrics.plot_convergence_hv(convergence_data, f"Convergência HV - {instance_name}")
                    file_hv = f"{instance_output_dir}/convergence_hv.png"
                    fig_hv.savefig(file_hv, dpi=300, bbox_inches='tight')
                    print(f"  Gráfico salvo: {file_hv}")
                    plt.close(fig_hv)

                    # Solution counts
                    fig_counts = metrics.plot_convergence_solution_counts(convergence_data, f"Evolução de Soluções - {instance_name}")
                    file_counts = f"{instance_output_dir}/convergence_solutions.png"
                    fig_counts.savefig(file_counts, dpi=300, bbox_inches='tight')
                    print(f"  Gráfico salvo: {file_counts}")
                    plt.close(fig_counts)

                    # Combined normalized
                    fig_combined = metrics.plot_convergence_combined_normalized(convergence_data, f"Métricas Normalizadas - {instance_name}")
                    file_combined = f"{instance_output_dir}/convergence_combined.png"
                    fig_combined.savefig(file_combined, dpi=300, bbox_inches='tight')
                    print(f"  Gráfico salvo: {file_combined}")
                    plt.close(fig_combined)
            
            except Exception as e:
                print(f"  Erro ao gerar gráficos de convergência: {e}")
        
        # Salva métricas em arquivo JSON
        print(f"\nSalvando métricas em arquivo...")
        try:
            metrics_data = final_metrics.copy()
            # Converte arrays numpy para listas para serialização JSON
            for key, value in metrics_data.items():
                if hasattr(value, 'tolist'):
                    metrics_data[key] = value.tolist()
            # Estatísticas agregadas entre as soluções finais
            distances_json = np.array([sol.total_distance for sol in final_solutions], dtype=float)
            costs_json = np.array([sol.total_cost for sol in final_solutions], dtype=float)
            avg_distance_json = float(np.mean(distances_json)) if distances_json.size > 0 else 0.0
            std_distance_json = float(np.std(distances_json, ddof=0)) if distances_json.size > 1 else 0.0
            avg_cost_json = float(np.mean(costs_json)) if costs_json.size > 0 else 0.0
            std_cost_json = float(np.std(costs_json, ddof=0)) if costs_json.size > 1 else 0.0
            metrics_data.update({
                'avg_distance': avg_distance_json,
                'std_distance': std_distance_json,
                'avg_cost': avg_cost_json,
                'std_cost': std_cost_json,
            })
            
            metrics_file = f"{instance_output_dir}/metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            print(f"  Métricas salvas em: {metrics_file}")
            
        except Exception as e:
            print(f"  Erro ao salvar métricas: {e}")

    # Mostra resultados finais
    print("\n" + "="*70)
    print("RESULTADOS FINAIS")
    print("="*70)
    
    if final_solutions:
        print(f"Soluções não-dominadas encontradas: {len(final_solutions)}")
        
        # Ordena soluções por qualidade (using penalized cost)
        final_solutions.sort(key=lambda x: (x.total_distance, x.total_cost, x.total_penalties))
        
        # Estatísticas agregadas entre as soluções finais
        distances = np.array([sol.total_distance for sol in final_solutions], dtype=float)
        costs = np.array([sol.total_cost for sol in final_solutions], dtype=float)
        avg_distance = float(np.mean(distances)) if distances.size > 0 else 0.0
        std_distance = float(np.std(distances, ddof=0)) if distances.size > 1 else 0.0
        avg_cost = float(np.mean(costs)) if costs.size > 0 else 0.0
        std_cost = float(np.std(costs, ddof=0)) if costs.size > 1 else 0.0

        print("\nTop melhores soluções:")
        print("Rank | Distância | Veículos | Custo   | Penaliz.| Factível")
        print("-" * 60)
        
        for i, sol in enumerate(final_solutions):
            cost_str = f"{sol.total_cost:6.2f}"
            penalty_str = f"{sol.total_penalties:7.2f}" if not sol.is_feasible else "    0.00"
            print(f"{i+1:4d} | {sol.total_distance:9.2f} | {sol.num_vehicles_used:8d} | {cost_str} | {penalty_str} | {'Sim' if sol.is_feasible else 'Não'}")
        
        # Exibe estatísticas agregadas
        print("\nEstatísticas agregadas entre soluções:")
        print(f"  Distância média: {avg_distance:.2f}")
        print(f"  Desvio padrão da distância: {std_distance:.2f}")
        print(f"  Custo médio: {avg_cost:.2f}")
        print(f"  Desvio padrão do custo: {std_cost:.2f}")
        
        best_solution = final_solutions[0]
        print(f"\nMelhor solução encontrada:")
        print(f"  Distância total: {best_solution.total_distance:.2f}")
        print(f"  Veículos usados: {best_solution.num_vehicles_used}")
        print(f"  Custo total: {best_solution.total_cost:.2f}")
        print(f"  Penalidades: {best_solution.total_penalties:.2f}")
        print(f"  Solução factível: {'Sim' if best_solution.is_feasible else 'Não'}")
        if not best_solution.is_feasible:
            print(f"  Violações: {best_solution.get_total_violations()}")
            print(f"  Detalhes: {best_solution.violations}")
        
        # Plota todas as soluções
        print(f"\nGerando visualizações para todas as soluções...")
        try:            
            for i, sol in enumerate(final_solutions):
                rank = i + 1
                plot_file = f"{instance_output_dir}/rank{rank}.png"
                plot_solution(instance, sol, save_path=plot_file)
                print(f" Rank {rank}: Visualização salva em {plot_file}")
            
            print(f" ✓ Todas as {len(final_solutions)} visualizações salvas em {instance_output_dir}/")
            
        except Exception as e:
            print(f" Erro ao gerar visualizações: {e}")
        
        print(f"\nSalvando soluções em arquivo...")
        try:
            solutions_file = f"{instance_output_dir}/gvns_solutions.txt"
            with open(solutions_file, "w") as f:
                f.write("Soluções não-dominadas encontradas pelo GVNS\n")
                f.write("="*50 + "\n\n")
                f.write("Resumo estatístico das soluções\n")
                f.write("-"*50 + "\n")
                f.write(f"Distância média: {avg_distance:.2f}\n")
                f.write(f"Desvio padrão da distância: {std_distance:.2f}\n")
                f.write(f"Custo médio: {avg_cost:.2f}\n")
                f.write(f"Desvio padrão do custo: {std_cost:.2f}\n\n")
                
                for i, sol in enumerate(final_solutions):
                    f.write(f"Solução {i+1}:\n")
                    f.write(f"  Distância total: {sol.total_distance:.2f}\n")
                    f.write(f"  Veículos usados: {sol.num_vehicles_used}\n")
                    f.write(f"  Custo total: {sol.total_cost:.2f}\n")
                    f.write(f"  Penalidade: {sol.total_penalties:.2f}\n")
                    f.write(f"  Solução factível: {'Sim' if sol.is_feasible else 'Não'}\n")
                    f.write(f"  Número de rotas: {len(sol.routes)}\n")
                    if not sol.is_feasible:
                        f.write(f"  Violações: {sol.get_total_violations()}\n")
                        f.write(f"  Detalhes das violações: {sol.violations}\n")
                    f.write("\n")
            
            print("Soluções salvas em 'gvns_solutions.txt'")
        except Exception as e:
            print(f"Erro ao salvar soluções: {e}")
    
    else:
        print("Nenhuma solução foi encontrada pelo algoritmo GVNS.")
    
    print("\nExecução finalizada!")
