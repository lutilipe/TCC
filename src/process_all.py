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
from process_single import process_single_instance
from utils.plot_solution import plot_solution
from utils.summary import print_instance_summary

def process_all_instances():
    """
    Processa todas as instâncias disponíveis no diretório data/
    e salva os resultados no diretório output/
    """
    print("Processando todas as instâncias disponíveis...")
    print("=" * 70)
    
    os.makedirs("output", exist_ok=True)
    
    data_dir = "data"
    all_instances = []
    
    if os.path.exists(data_dir):
        instance_files = glob.glob(f"{data_dir}/*.txt")
        all_instances.extend(instance_files)
    
    print(f"Total de instâncias encontradas: {len(all_instances)}")
    
    for i, instance_file in enumerate(all_instances, 1):
        print(f"\n[{i}/{len(all_instances)}] Processando: {instance_file}")
        print("-" * 50)
        
        try:
            process_single_instance(instance_file)
        except Exception as e:
            print(f"✗ Erro ao processar {instance_file}: {e}")
            continue
    
    print(f"\n" + "="*70)
    print("PROCESSAMENTO CONCLUÍDO!")
    print(f"Resultados salvos no diretório 'output/'")
    print("="*70)
