import os
import glob
from EVRP.constructive_heuristic import ConstructiveHeuristic
from EVRP.create_instance import create_evrp_instance
from EVRP.local_search.recharge_realocation import RechargeRealocation
from EVRP.local_search.two_opt import TwoOpt
from EVRP.local_search.two_opt_star import TwoOptStar
from EVRP.local_search.depot_reassignment import DepotReassignment
from EVRP.local_search.exchange import Exchange
from EVRP.local_search.route_split import RouteSplit
from EVRP.local_search.eliminate_route import EliminateRoute
from EVRP.GVNS import GVNS
from utils.plot_solution import plot_solution
from utils.summary import print_instance_summary

def process_all_instances():
    """
    Processa todas as instâncias disponíveis no diretório data/
    e salva os resultados no diretório output/
    """
    print("Processando todas as instâncias disponíveis...")
    print("=" * 70)
    
    # Cria diretório output se não existir
    os.makedirs("output", exist_ok=True)
    
    # Encontra todas as instâncias
    data_dirs = ["data/100", "data/200", "data/400"]
    all_instances = []
    
    for data_dir in data_dirs:
        if os.path.exists(data_dir):
            instance_files = glob.glob(f"{data_dir}/datos-*.txt")
            all_instances.extend(instance_files)
    
    print(f"Total de instâncias encontradas: {len(all_instances)}")
    
    # Processa cada instância
    for i, instance_file in enumerate(all_instances, 1):
        print(f"\n[{i}/{len(all_instances)}] Processando: {instance_file}")
        print("-" * 50)
        
        try:
            # Cria instância
            instance = create_evrp_instance(instance_file)
            print_instance_summary(instance)
            
            # Inicializa heurísticas
            constructiveHeuristic = ConstructiveHeuristic(instance)
            twoOpt = TwoOpt(instance, max_pert=5)
            twoOptStar = TwoOptStar(instance)
            exchangeOp = Exchange(instance)
            rechargeRealocation = RechargeRealocation(instance)
            routeSplit = RouteSplit(instance)
            
            # Cria população inicial de soluções
            print("Criando população inicial...")
            initial_solutions = []
            while len(initial_solutions) < 50:
                solution = constructiveHeuristic.build_initial_solution()
                while not solution.is_feasible:
                    solution = constructiveHeuristic.build_initial_solution()
                """ improved = twoOpt.run(solution)
                solution.evaluate() """
                initial_solutions.append(solution)
                
                if len(initial_solutions) % 10 == 0:
                    print(f"  {len(initial_solutions)} soluções criadas...")
            
            print(f"População inicial criada com {len(initial_solutions)} soluções")
            
            # Executa o algoritmo GVNS
            print("Executando GVNS...")
            gvns = GVNS(
                instance=instance,
                ns=5,           # Número de soluções por busca local
                na=50,          # Tamanho máximo do arquivo A
                ls_max_iter=500, # Máximo de tentativas de busca local
                max_evaluations=80,  # Máximo de avaliações,
                local_search=[twoOpt, twoOptStar, exchangeOp, rechargeRealocation, routeSplit],
                perturbation=[
                    DepotReassignment(instance, k=2),  # Depot reassignment shake operator
                    twoOpt, 
                    twoOptStar,
                    Exchange(instance, max_iter=10, select_best=False),
                    RouteSplit(instance, max_iter=5, select_best=False),
                    EliminateRoute(instance, max_iter=1, select_best=False)
                ]
            )
            
            final_solutions = gvns.run(initial_solutions)
            
            # Salva resultados
            if final_solutions:
                # Ordena soluções por qualidade
                final_solutions.sort(key=lambda x: (x.total_distance, x.num_vehicles_used, x.total_cost))
                
                # Gera nome do arquivo de saída
                instance_name = os.path.basename(instance_file).replace('.txt', '')
                output_file = f"output/{instance_name}_solutions.txt"
                
                # Salva soluções
                with open(output_file, "w") as f:
                    f.write(f"Soluções para instância: {instance_name}\n")
                    f.write("="*50 + "\n\n")
                    f.write(f"Total de soluções não-dominadas: {len(final_solutions)}\n\n")
                    
                    for i, sol in enumerate(final_solutions):
                        f.write(f"Solução {i+1}:\n")
                        f.write(f"  Distância total: {sol.total_distance:.2f}\n")
                        f.write(f"  Veículos usados: {sol.num_vehicles_used}\n")
                        f.write(f"  Custo total: {sol.total_cost:.2f}\n")
                        f.write(f"  Solução factível: {'Sim' if sol.is_feasible else 'Não'}\n")
                        f.write(f"  Número de rotas: {len(sol.routes)}\n")
                        f.write("\n")
                
                print(f"✓ {len(final_solutions)} soluções salvas em {output_file}")
                
                # Salva melhor solução
                best_solution = final_solutions[0]
                print(f"  Melhor solução: Dist={best_solution.total_distance:.2f}, "
                      f"Veículos={best_solution.num_vehicles_used}, "
                      f"Custo={best_solution.total_cost:.2f}")
                
                # Gera visualizações para todas as soluções
                try:
                    # Cria diretório específico para esta instância
                    instance_output_dir = f"output/{instance_name}"
                    os.makedirs(instance_output_dir, exist_ok=True)
                    
                    # Plota cada solução
                    for i, sol in enumerate(final_solutions):
                        rank = i + 1
                        plot_file = f"{instance_output_dir}/rank{rank}.png"
                        plot_solution(instance, sol, save_path=plot_file)
                        print(f"  Rank {rank}: Visualização salva em {plot_file}")
                    
                    print(f"  ✓ Todas as {len(final_solutions)} visualizações salvas em {instance_output_dir}/")
                except Exception as e:
                    print(f"  Erro ao gerar visualizações: {e}")
                    
            else:
                print("✗ Nenhuma solução encontrada")
                
        except Exception as e:
            print(f"✗ Erro ao processar {instance_file}: {e}")
            continue
    
    print(f"\n" + "="*70)
    print("PROCESSAMENTO CONCLUÍDO!")
    print(f"Resultados salvos no diretório 'output/'")
    print("="*70)
