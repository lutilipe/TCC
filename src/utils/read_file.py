def read_gvrp_file(filename: str):
    """
    Le o arquivo de EVRP no novo formato e retorna um dicionário com os dados lidos.

    Args:
        filename (str): Caminho para o arquivo de EVRP

    Returns:
        dict: Dados:
            - name: Nome da instancia do problema (extraído do nome do arquivo)
            - customers: Lista com dicionários contendo informações dos clientes
            - recharge_points: Lista com dicionários contendo informações dos pontos de recarga
            - depot: Dicionário com informações do depósito
            - vehicle_params: Dicionário com parâmetros do veículo
    """
    with open(filename, "r") as file:
        lines = [line.strip() for line in file.readlines()]

    data = {}
    
    # Extract instance name from filename
    import os
    data["name"] = os.path.splitext(os.path.basename(filename))[0]
    
    customers = []
    recharge_points = []
    depot = None
    vehicle_params = {}
    
    i = 0
    
    # Skip header line
    if i < len(lines) and lines[i].startswith("StringID"):
        i += 1
    
    # Parse locations
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # Check if we've reached vehicle parameters
        if line.startswith("Q Vehicle fuel tank capacity"):
            break
            
        parts = line.split()
        if len(parts) < 8:
            i += 1
            continue
            
        string_id = parts[0]
        location_type = parts[1]
        x = float(parts[2])
        y = float(parts[3])
        demand = float(parts[4])
        ready_time = float(parts[5])
        due_date = float(parts[6])
        service_time = float(parts[7])
        
        # Extract numeric ID from string ID
        if string_id.startswith('D'):
            numeric_id = 0
        elif string_id.startswith('S'):
            numeric_id = int(string_id[1:]) + 1  # S0 becomes 1, S1 becomes 2, etc.
        elif string_id.startswith('C'):
            numeric_id = int(string_id[1:])
        else:
            i += 1
            continue
        
        if location_type == 'd':  # Depot
            depot = {
                "id": numeric_id,
                "x": x,
                "y": y,
                "demand": demand,
                "ready_time": ready_time,
                "due_date": due_date,
                "service_time": service_time
            }
        elif location_type == 'f':  # Recharge station
            recharge_points.append({
                "id": numeric_id,
                "x": x,
                "y": y,
                "demand": demand,
                "ready_time": ready_time,
                "due_date": due_date,
                "service_time": service_time
            })
        elif location_type == 'c':  # Customer
            customers.append({
                "id": numeric_id,
                "x": x,
                "y": y,
                "demand": demand,
                "ready_time": ready_time,
                "due_date": due_date,
                "service_time": service_time
            })
        
        i += 1
    
    # Parse vehicle parameters
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        if "Q Vehicle fuel tank capacity" in line:
            # Extract value between slashes
            start = line.find('/') + 1
            end = line.rfind('/')
            if start > 0 and end > start:
                vehicle_params["battery_capacity"] = float(line[start:end])
        elif "C Vehicle load capacity" in line:
            start = line.find('/') + 1
            end = line.rfind('/')
            if start > 0 and end > start:
                vehicle_params["capacity"] = float(line[start:end])
        elif "r fuel consumption rate" in line:
            start = line.find('/') + 1
            end = line.rfind('/')
            if start > 0 and end > start:
                vehicle_params["consumption_rate"] = float(line[start:end])
        elif "g inverse refueling rate" in line:
            start = line.find('/') + 1
            end = line.rfind('/')
            if start > 0 and end > start:
                vehicle_params["refueling_rate"] = float(line[start:end])
        elif "v average Velocity" in line:
            start = line.find('/') + 1
            end = line.rfind('/')
            if start > 0 and end > start:
                vehicle_params["velocity"] = float(line[start:end])
        
        i += 1
    
    data["customers"] = customers
    data["recharge_points"] = recharge_points
    data["depot"] = depot
    data["vehicle_params"] = vehicle_params
    
    return data
