def read_gvrp_file(filename: str):
    """
    Le o arquivo de GVRP e retorna um dicionário com os dados lidos.

    Args:
        filename (str): Caminho para o arquivo de GVRP

    Returns:
        dict: Dados:
            - name: Nome da instancia do problema
            - parameters: Dict com parâmetros globais do problema
            - customers: Lista com dicionários contendo informações dos clientes
            - recharge_points: Lista com dicionários contendo informações dos pontos de recarga
            - technologies: Lista com dicionários contendo informações das tecnologias
    """
    with open(filename, "r") as file:
        lines = [line.strip() for line in file.readlines()]

    data = {}
    i = 0

    while i < len(lines) and not lines[i].strip().startswith("NAME:"):
        i += 1
    if i < len(lines):
        data["name"] = lines[i].split(":", 1)[1].strip()
        i += 1

    while i < len(lines) and not lines[i].strip().startswith("$ DATA SECTIONS"):
        i += 1
    i += 1

    while i < len(lines) and ("NN" not in lines[i] or "NK" not in lines[i]):
        i += 1
    i += 1

    params = lines[i].split()
    data["parameters"] = {
        "NN": int(params[0]),
        "NK": int(params[1]),
        "NR": int(params[2]),
        "NTR": int(params[3]),
        "VEL": float(params[4]),
        "BMAX": float(params[5]),
        "CPOW": float(params[6]),
        "TIMEMAX": float(params[7]),
        "QMAX": float(params[8]),
        "F0CHAR": float(params[9]),
        "F0VEHIC": float(params[10])
    }

    i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1

    while i < len(lines) and not lines[i].strip().startswith("CUSTOMERS:"):
        i += 1
    i += 1
    if i < len(lines) and "NO." in lines[i]:
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    customers = []
    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("RECHARGE"):
        parts = lines[i].split()
        if len(parts) >= 5:
            customers.append({
                "id": int(parts[0]),
                "x": float(parts[1]),
                "y": float(parts[2]),
                "demand": float(parts[3]),
                "service_time": float(parts[4])
            })
        i += 1
    data["customers"] = customers

    while i < len(lines) and not lines[i].strip().startswith("RECHARGE POINTS:"):
        i += 1
    i += 1
    if i < len(lines) and "NO." in lines[i]:
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    recharge_points = []
    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("TECHNOLOGY"):
        parts = lines[i].split()
        if len(parts) >= 4:
            recharge_points.append({
                "id": int(parts[0]),
                "x": float(parts[1]),
                "y": float(parts[2]),
                "t0_char": float(parts[3]),
                "technologies": [int(float(x)) for x in parts[4:]]
            })
        i += 1
    data["recharge_points"] = recharge_points

    while i < len(lines) and not lines[i].strip().startswith("TECHNOLOGY KINDS:"):
        i += 1
    i += 1
    if i < len(lines) and "KIND" in lines[i]:
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    technologies = []
    while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("END"):
        parts = lines[i].split()
        if len(parts) >= 3:
            technologies.append({
                "kind": int(parts[0]),
                "speed_recharge": float(parts[1]),
                "unit_cost": float(parts[2])
            })
        i += 1
    data["technologies"] = technologies

    return data
