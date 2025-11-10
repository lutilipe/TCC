"""
Modelo Gurobi para o problema EVRP (Electric Vehicle Routing Problem)
Implementa todas as restrições e funções objetivo fornecidas.
"""

import gurobipy as gp
from gurobipy import GRB
import sys
import os

# Adicionar o diretório src ao path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from EVRP.create_instance import create_evrp_instance
from EVRP.classes.node import NodeType


def solve_evrp_gurobi(instance_file, time_limit=3600, mip_gap=0.01):
    """
    Resolve o problema EVRP usando Gurobi.
    
    Args:
        instance_file: Caminho para o arquivo da instância
        time_limit: Limite de tempo em segundos (padrão: 3600)
        mip_gap: Gap de otimalidade (padrão: 0.01 = 1%)
    
    Returns:
        dict: Resultados da otimização
    """
    print("=" * 70)
    print("EVRP Solver usando Gurobi")
    print("=" * 70)
    
    # Carregar instância
    print(f"\nCarregando instância: {instance_file}")
    instance = create_evrp_instance(instance_file)
    
    # Definir conjuntos
    N = [c.id for c in instance.customers]  # Clientes
    F0 = [s.id for s in instance.stations]   # Estações de recarga
    D = [d.id for d in instance.depots]       # Depósitos
    V_prime = N + F0 + D  # Todos os nós
    
    # Parâmetros do veículo
    B = instance.vehicle.battery_capacity  # Capacidade da bateria (kWh)
    Q = instance.vehicle.capacity          # Capacidade de carga (kg)
    pi = instance.vehicle.consumption_rate  # Taxa de consumo (kWh/km)
    
    # Parâmetros de tempo
    T = instance.max_route_duration  # Tempo máximo de rota
    
    # Tecnologias
    technologies = instance.technologies
    # T_j: tecnologias disponíveis no nó j
    T_j = {}
    for depot in instance.depots:
        T_j[depot.id] = [t.id for t in depot.technologies]
    for station in instance.stations:
        T_j[station.id] = [t.id for t in station.technologies]
    
    # Custos
    gamma_star = instance.battery_depreciation_cost  # Custo de recarga no depósito
    # gamma_t: custo por kWh da tecnologia t
    gamma_t = {t.id: t.cost_per_kwh for t in technologies}
    theta = 1.0  # Custo por arco usado (pode ser ajustado)
    
    # Matrizes de distância e tempo
    d = instance.distance_matrix  # d[i][j] = distância entre i e j
    tt = instance.time_matrix      # tt[i][j] = tempo de viagem entre i e j
    
    # Dados dos clientes
    q = {c.id: c.demand for c in instance.customers}  # Demanda
    s = {c.id: c.service_time for c in instance.customers}  # Tempo de serviço
    e = {c.id: c.ready_time for c in instance.customers}  # Ready time
    l = {c.id: c.due_date for c in instance.customers}  # Due date
    
    # Tempo de serviço para estações e depósitos (0)
    for node_id in F0 + D:
        s[node_id] = 0.0
        e[node_id] = 0.0
        l[node_id] = T
    
    # Tempo fixo de recarga (f_j)
    f = {}
    for node_id in F0 + D:
        f[node_id] = instance.charging_fixed_time
    
    # Taxa de recarga (rho_t) - power da tecnologia
    rho = {t.id: t.power for t in technologies}  # kWh/h
    
    # Constantes grandes
    M1 = T * 2  # Para restrições de tempo
    M2 = Q * 2  # Para restrições de carga
    
    print(f"\nEstatísticas da instância:")
    print(f"  Clientes: {len(N)}")
    print(f"  Estações: {len(F0)}")
    print(f"  Depósitos: {len(D)}")
    print(f"  Capacidade bateria: {B} kWh")
    print(f"  Capacidade carga: {Q} kg")
    print(f"  Taxa consumo: {pi} kWh/km")
    
    # Criar modelo
    model = gp.Model("EVRP")
    model.setParam('TimeLimit', time_limit)
    model.setParam('MIPGap', mip_gap)
    model.setParam('OutputFlag', 1)
    
    # Variáveis de decisão
    print("\nCriando variáveis de decisão...")
    
    # x[i][j]: 1 se o arco (i,j) é usado, 0 caso contrário
    x = {}
    for i in V_prime:
        x[i] = {}
        for j in V_prime:
            if i != j:
                x[i][j] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")
            else:
                x[i][j] = 0  # Não permitir loops
    
    # y_L[j]: nível de bateria ao deixar o nó j
    y_L = {}
    for j in V_prime:
        y_L[j] = model.addVar(lb=0, ub=B, vtype=GRB.CONTINUOUS, name=f"y_L_{j}")
    
    # y_A[j]: nível de bateria ao chegar no nó j
    y_A = {}
    for j in V_prime:
        y_A[j] = model.addVar(lb=0, ub=B, vtype=GRB.CONTINUOUS, name=f"y_A_{j}")
    
    # z[j][t]: quantidade de energia recarregada no nó j usando tecnologia t
    z = {}
    for j in F0 + D:
        z[j] = {}
        for t in T_j.get(j, []):
            z[j][t] = model.addVar(lb=0, ub=B, vtype=GRB.CONTINUOUS, name=f"z_{j}_{t}")
    
    # g[v]: quantidade de energia recarregada no depósito v
    g = {}
    for v in D:
        g[v] = model.addVar(lb=0, ub=B, vtype=GRB.CONTINUOUS, name=f"g_{v}")
    
    # tau[j]: tempo de chegada no nó j
    tau = {}
    for j in V_prime:
        tau[j] = model.addVar(lb=0, ub=T, vtype=GRB.CONTINUOUS, name=f"tau_{j}")
    
    # c[j]: carga do veículo ao chegar no nó j
    c = {}
    for j in V_prime:
        c[j] = model.addVar(lb=0, ub=Q, vtype=GRB.CONTINUOUS, name=f"c_{j}")
    
    model.update()
    
    # Restrições
    print("\nAdicionando restrições...")
    
    # Eq. 3: Cada cliente deve ser visitado exatamente uma vez
    for i in N:
        model.addConstr(
            gp.quicksum(x[i][j] for j in V_prime if i != j) == 1,
            name=f"eq3_customer_{i}"
        )
    
    # Eq. 4: Cada estação pode ser visitada no máximo uma vez
    for i in F0:
        model.addConstr(
            gp.quicksum(x[i][j] for j in V_prime if i != j) <= 1,
            name=f"eq4_station_{i}"
        )
    
    # Eq. 5: Conservação de fluxo (balanceamento)
    for i in V_prime:
        incoming = gp.quicksum(x[j][i] for j in V_prime if j != i)
        outgoing = gp.quicksum(x[i][j] for j in V_prime if i != j)
        model.addConstr(
            incoming - outgoing == 0,
            name=f"eq5_flow_{i}"
        )
    
    # Eq. 6a: Cada depósito pode ter no máximo um arco saindo
    for v in D:
        model.addConstr(
            gp.quicksum(x[v][j] for j in V_prime if v != j) <= 1,
            name=f"eq6a_depot_out_{v}"
        )
    
    # Eq. 6b: Cada depósito pode ter no máximo um arco entrando
    for v in D:
        model.addConstr(
            gp.quicksum(x[i][v] for i in V_prime if i != v) <= 1,
            name=f"eq6b_depot_in_{v}"
        )
    
    # Eq. 7: Energia recarregada no depósito não pode exceder g_v
    for v in D:
        model.addConstr(
            y_L[v] <= g[v],
            name=f"eq7_depot_energy_{v}"
        )
    
    # Eq. 8: Restrição de tempo para clientes
    for i in N:
        for j in V_prime:
            if i != j:
                model.addConstr(
                    tau[j] >= tau[i] + tt[i][j] + s[i] - M1 * (1 - x[i][j]),
                    name=f"eq8_time_{i}_{j}"
                )
    
    # Eq. 9: Restrição de tempo para estações/depósitos
    for i in F0 + D:
        for j in V_prime:
            if i != j:
                # Calcular tempo de recarga: sum(1/rho_t * z_it)
                # Só calcular se houver tecnologias disponíveis
                if i in z and len(z[i]) > 0:
                    recharge_time = gp.quicksum(
                        (1.0 / rho[t]) * z[i][t] 
                        for t in z[i].keys()
                    )
                    model.addConstr(
                        tau[j] >= tau[i] + tt[i][j] + recharge_time + f[i] - M1 * (1 - x[i][j]),
                        name=f"eq9_time_{i}_{j}"
                    )
                else:
                    # Se não há recarga, usar apenas tempo fixo
                    model.addConstr(
                        tau[j] >= tau[i] + tt[i][j] + f[i] - M1 * (1 - x[i][j]),
                        name=f"eq9_time_{i}_{j}"
                    )
    
    # Eq. 10: Tempo de chegada a partir de depósitos
    for v in D:
        for j in V_prime:
            if v != j:
                model.addConstr(
                    tau[j] >= tt[v][j] - M1 * (1 - x[v][j]),
                    name=f"eq10_depot_time_{v}_{j}"
                )
    
    # Eq. 11: Janela de tempo para depósitos
    for v in D:
        model.addConstr(tau[v] >= 0, name=f"eq11_tau_lb_{v}")
        model.addConstr(tau[v] <= T, name=f"eq11_tau_ub_{v}")
    
    # Eq. 12: Conservação de energia (bateria ao chegar)
    # y_A[j] <= y_L[i] - pi * d[i][j] * x[i][j] + B * (1 - x[i][j])
    # Quando x[i][j] = 1: y_A[j] <= y_L[i] - pi * d[i][j]
    # Quando x[i][j] = 0: y_A[j] <= y_L[i] + B (sempre satisfeita se y_A[j] <= B)
    for i in V_prime:
        for j in V_prime:
            if i != j:
                # Usar big-M para linearizar
                model.addConstr(
                    y_A[j] <= y_L[i] - pi * d[i][j] * x[i][j] + B * (1 - x[i][j]),
                    name=f"eq12_energy_{i}_{j}"
                )
    
    # Eq. 13: Bateria ao deixar estação não pode exceder capacidade
    for j in F0:
        model.addConstr(y_L[j] <= B, name=f"eq13_battery_{j}")
    
    # Eq. 14: Energia recarregada no depósito não pode exceder capacidade
    for v in D:
        model.addConstr(g[v] <= B, name=f"eq14_depot_energy_{v}")
    
    # Eq. 15: Bateria ao chegar não pode exceder bateria ao deixar (para clientes)
    for j in N:
        model.addConstr(y_L[j] <= y_A[j], name=f"eq15_battery_{j}")
    
    # Eq. 16: Bateria ao deixar = bateria ao chegar + energia recarregada (estações)
    for j in F0:
        if j in z and len(z[j]) > 0:
            recharge_sum = gp.quicksum(
                z[j][t] for t in z[j].keys()
            )
            model.addConstr(
                y_L[j] == y_A[j] + recharge_sum,
                name=f"eq16_recharge_{j}"
            )
        else:
            # Se não há recarga disponível, y_L[j] = y_A[j]
            model.addConstr(
                y_L[j] == y_A[j],
                name=f"eq16_recharge_{j}"
            )
    
    # Eq. 17: Restrição de carga para clientes
    for i in V_prime:
        for j in N:
            if i != j:
                model.addConstr(
                    c[j] >= c[i] + q[j] - M2 * (1 - x[i][j]),
                    name=f"eq17_load_customer_{i}_{j}"
                )
    
    # Eq. 18: Restrição de carga para estações/depósitos
    for i in V_prime:
        for j in F0 + D:
            if i != j:
                model.addConstr(
                    c[j] >= c[i] - M2 * (1 - x[i][j]),
                    name=f"eq18_load_station_{i}_{j}"
                )
    
    # Eq. 19: Carga não pode exceder capacidade
    for j in V_prime:
        model.addConstr(c[j] <= Q, name=f"eq19_capacity_{j}")
    
    # Eq. 20: Janela de tempo para clientes
    for j in N:
        model.addConstr(tau[j] >= e[j], name=f"eq20_ready_{j}")
        model.addConstr(tau[j] <= l[j], name=f"eq20_due_{j}")
    
    # Inicializar carga e bateria nos depósitos
    for v in D:
        # Carga inicial = 0
        model.addConstr(c[v] == 0, name=f"init_load_{v}")
        # Bateria inicial = g_v (energia recarregada)
        model.addConstr(y_L[v] == g[v], name=f"init_battery_{v}")
    
    print(f"Total de restrições: {model.NumConstrs}")
    print(f"Total de variáveis: {model.NumVars}")
    
    # Funções objetivo
    print("\nDefinindo funções objetivo...")
    
    # Objetivo 1: Minimizar custo de energia + custo de arcos
    obj1 = (
        gp.quicksum(gamma_star * g[v] for v in D) +
        gp.quicksum(
            gamma_t[t] * z[j][t]
            for j in F0 + D
            if j in z
            for t in z[j].keys()
        ) +
        theta * gp.quicksum(
            x[i][j]
            for i in V_prime
            for j in V_prime
            if i != j and (i not in F0 + D or j not in F0 + D)
        )
    )
    
    # Objetivo 2: Minimizar distância total
    obj2 = gp.quicksum(
        d[i][j] * x[i][j]
        for i in V_prime
        for j in V_prime
        if i != j
    )
    
    # Para problema bi-objetivo, podemos usar weighted sum ou epsilon-constraint
    # Aqui usaremos weighted sum com pesos iguais
    w1, w2 = 1.0, 1.0
    model.setObjective(w1 * obj1 + w2 * obj2, GRB.MINIMIZE)
    
    print("\nOtimizando...")
    model.optimize()
    
    # Resultados
    results = {
        'status': model.status,
        'obj_value': model.ObjVal if model.status == GRB.OPTIMAL or model.status == GRB.TIME_LIMIT else None,
        'obj1_value': None,
        'obj2_value': None,
        'runtime': model.Runtime,
        'mip_gap': model.MIPGap if hasattr(model, 'MIPGap') else None,
        'solution': {}
    }
    
    if model.status == GRB.OPTIMAL or model.status == GRB.TIME_LIMIT:
        # Calcular valores dos objetivos
        obj1_val = (
            sum(gamma_star * g[v].X for v in D) +
            sum(
                gamma_t[t] * z[j][t].X
                for j in F0 + D
                if j in z
                for t in z[j].keys()
            ) +
            theta * sum(
                x[i][j].X
                for i in V_prime
                for j in V_prime
                if i != j and (i not in F0 + D or j not in F0 + D)
            )
        )
        
        obj2_val = sum(
            d[i][j] * x[i][j].X
            for i in V_prime
            for j in V_prime
            if i != j
        )
        
        results['obj1_value'] = obj1_val
        results['obj2_value'] = obj2_val
        
        # Extrair solução
        arcs = []
        for i in V_prime:
            for j in V_prime:
                if i != j and x[i][j].X > 0.5:
                    arcs.append((i, j))
        
        results['solution'] = {
            'arcs': arcs,
            'tau': {j: tau[j].X for j in V_prime},
            'y_L': {j: y_L[j].X for j in V_prime},
            'y_A': {j: y_A[j].X for j in V_prime},
            'c': {j: c[j].X for j in V_prime},
            'g': {v: g[v].X for v in D},
            'z': {
                j: {t: z[j][t].X for t in z[j].keys()}
                for j in F0 + D if j in z
            }
        }
        
        print("\n" + "=" * 70)
        print("RESULTADOS")
        print("=" * 70)
        print(f"Status: {model.status}")
        if model.status == GRB.OPTIMAL:
            print("Solução ótima encontrada!")
        elif model.status == GRB.TIME_LIMIT:
            print("Limite de tempo atingido.")
        print(f"Valor objetivo (combinado): {results['obj_value']:.2f}")
        print(f"Objetivo 1 (custo energia): {obj1_val:.2f}")
        print(f"Objetivo 2 (distância): {obj2_val:.2f}")
        print(f"Tempo de execução: {model.Runtime:.2f} segundos")
        print(f"Gap: {model.MIPGap * 100:.2f}%")
        print(f"Arcos usados: {len(arcs)}")
    
    return results


if __name__ == "__main__":
    # Exemplo de uso
    if len(sys.argv) > 1:
        instance_file = sys.argv[1]
    else:
        # Usar uma instância padrão
        # Tentar diferentes caminhos
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        instance_file = os.path.join(base_dir, "data", "c103C5.txt")
        if not os.path.exists(instance_file):
            # Tentar caminho relativo
            instance_file = "../data/c103C5.txt"
    
    # Resolver
    print(f"Resolvendo instância: {instance_file}")
    results = solve_evrp_gurobi(instance_file, time_limit=3600, mip_gap=0.01)
    
    # Imprimir solução detalhada
    if results['solution']:
        print("\nSolução detalhada:")
        print(f"Arcos: {results['solution']['arcs']}")
        print(f"\nNúmero de arcos: {len(results['solution']['arcs'])}")

