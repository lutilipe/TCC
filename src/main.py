from EVRP.create_instance import create_evrp_instance
from utils.summary import print_instance_summary

if __name__ == "__main__":
    print("EVRP Solver using General Variable Neighborhood Search (GVNS)")
    print("=" * 70)
    
    instance = create_evrp_instance("./data/datos-10-N100.txt")
    print_instance_summary(instance)
    