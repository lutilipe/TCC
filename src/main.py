from process_all import process_all_instances
from process_single import process_single_instance

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # Processa todas as instâncias
            process_all_instances()
        else:
            # Processa instância específica
            process_single_instance(sys.argv[1])
    else:
        # Processa instância padrão
        process_single_instance("./data/100/datos-20-N100.txt")
