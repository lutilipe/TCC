import os
from EVRP import GVNS
from EVRP.constructive_heuristic import ConstructiveHeuristic
from EVRP.create_instance import create_evrp_instance
from EVRP.local_search.recharge_realocation import RechargeRealocation
from EVRP.local_search.two_opt import TwoOpt
from EVRP.local_search.two_opt_star import TwoOptStar
from EVRP.local_search.reinsertion import Reinsertion
from EVRP.local_search.recharge_realocation import RechargeRealocation
from EVRP.local_search.relocate import Relocate
from EVRP.local_search.exchange import Exchange
from EVRP.local_search.or_opt import OrOpt
from EVRP.local_search.three_opt import ThreeOpt
from EVRP.local_search.shift import Shift
from utils import plot_solution, print_instance_summary
from utils.summary import plot_gvrp_instance

"""
Processa uma única instância (código original do main)
"""
print("EVRP Solver using General Variable Neighborhood Search (GVNS)")
print("=" * 70)

instance = create_evrp_instance("data/c101C5.txt")
print_instance_summary(instance)
plot_gvrp_instance(instance)