import os
import glob
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import time
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
from process_single import process_single_instance
from utils.plot_solution import plot_solution
from utils.summary import print_instance_summary


def process_instance_wrapper(args):
    """
    Wrapper function for parallel processing
    Returns: (instance_file, success, error_message)
    """
    instance_file, index, total = args
    try:
        print(f"[{index}/{total}] Starting: {instance_file}")
        process_single_instance(instance_file)
        return (instance_file, True, None)
    except Exception as e:
        return (instance_file, False, str(e))


def process_all_instances(max_workers=None):
    """
    Processa todas as instâncias disponíveis no diretório data/
    em paralelo e salva os resultados no diretório output/
    
    Args:
        max_workers: Número máximo de processos paralelos. 
                     Se None, usa cpu_count() - 1
    """
    print("Processando todas as instâncias disponíveis em PARALELO...")
    print("=" * 70)
    
    # Criar diretório de saída
    os.makedirs("output", exist_ok=True)
    
    # Coletar todas as instâncias
    data_dir = "data"
    all_instances = []
    skipped_instances = []
    
    if os.path.exists(data_dir):
        instance_files = glob.glob(f"{data_dir}/*.txt")
        for instance_file in instance_files:
            # Extrair o nome da instância (sem extensão .txt)
            instance_name = os.path.basename(instance_file).replace('.txt', '')
            instance_output_dir = f"output/{instance_name}"
            
            # Verificar se o diretório de saída já existe
            if os.path.exists(instance_output_dir) and os.path.isdir(instance_output_dir):
                skipped_instances.append(instance_file)
                print(f"⊘ Pulando {instance_name} (diretório já existe)")
            else:
                all_instances.append(instance_file)
    
    if not all_instances and not skipped_instances:
        print("Nenhuma instância encontrada!")
        return
    
    total_instances = len(all_instances)
    total_skipped = len(skipped_instances)
    print(f"Total de instâncias encontradas: {total_instances + total_skipped}")
    if total_skipped > 0:
        print(f"Instâncias puladas (já processadas): {total_skipped}")
    print(f"Instâncias a processar: {total_instances}")
    print(all_instances)
    # Se não houver instâncias para processar, retornar
    if total_instances == 0:
        print("\nTodas as instâncias já foram processadas!")
        return [], []
    
    # Determinar número de workers
    if max_workers is None:
        max_workers = min(4, cpu_count() - 1)
    
    print(f"Usando {max_workers} processos paralelos")
    print("-" * 70)
    
    # Preparar argumentos para processamento paralelo
    process_args = [
        (instance, i+1, total_instances) 
        for i, instance in enumerate(all_instances)
    ]
    
    # Rastrear resultados
    successful = []
    failed = []
    
    start_time = time.time()
    
    # Processar em paralelo
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as tarefas
        futures = {
            executor.submit(process_instance_wrapper, args): args[0] 
            for args in process_args
        }
        
        # Processar resultados conforme completam
        for future in as_completed(futures):
            instance_file = futures[future]
            try:
                result = future.result()
                instance_name, success, error = result
                
                if success:
                    successful.append(instance_name)
                    print(f"✓ Concluído: {instance_name}")
                else:
                    failed.append((instance_name, error))
                    print(f"✗ Erro em {instance_name}: {error}")
                    
            except Exception as e:
                failed.append((instance_file, str(e)))
                print(f"✗ Exceção ao processar {instance_file}: {e}")
    
    elapsed_time = time.time() - start_time
    
    # Imprimir resumo
    print(f"\n" + "="*70)
    print("PROCESSAMENTO CONCLUÍDO!")
    print(f"Tempo total: {elapsed_time:.2f} segundos")
    if total_skipped > 0:
        print(f"Instâncias puladas (já processadas): {total_skipped}")
    print(f"Sucesso: {len(successful)}/{total_instances}")
    print(f"Falhas: {len(failed)}/{total_instances}")
    
    if failed:
        print(f"\nInstâncias com erro:")
        for instance, error in failed:
            print(f"  - {instance}: {error}")
    
    print(f"\nResultados salvos no diretório 'output/'")
    print("="*70)
    
    return successful, failed
