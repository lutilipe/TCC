""" algoritmo 3 Busca em Vizinhança Variável Multiobjetivo
1: Crie uma população P inicial (ja foi feito)
7: Inicialize um arquivo de soluções A vazio.
8: para cada solução x em P faça
9: Obtenha um conjunto S de NS soluções obtidos através
de NS buscas locais em x.
10: Atualize o arquivo A com as soluções de S mantendo
em A até NA soluções não-dominadas.
11: fim para
12: enquanto o número máximo de avaliações não for al-
cançado faça
13: Escolha uma solução x do arquivo A aleatoriamente.
14: enquanto não houver mudança em A e não ultrapas-
sar um número máximo de tentativas de busca local
(LSMaxIter) e o número máximo de avaliações não for
alcançado faça
15: Faça uma pertubação aleatória em x através de
um número fixo de operações 2-opt, definido pelo
parâmetro MaxPert obtendo uma solução final x′.
16: Obtenha uma população S de NS soluções obtidos
através de NS buscas locais em x′.
17: Atualize o arquivo A com as soluções em S man-
tendo um conjunto não-dominado.
18: fim enquanto
19: fim enquanto
20: retorne o arquivo A de soluções não-dominadas. """

import random
import copy
from typing import List, Tuple
from EVRP.solution import Solution
from EVRP.local_search.two_opt import TwoOpt

class GVNS:
    def __init__(self, instance, two_opt: TwoOpt, 
                 ns: int = 5, na: int = 50, ls_max_iter: int = 10, 
                 max_pert: int = 3, max_evaluations: int = 10000):
        """
        Inicializa o algoritmo GVNS
        
        Args:
            instance: Instância do problema EVRP
            two_opt: Objeto TwoOpt para busca local
            ns: Número de soluções a serem geradas por busca local
            na: Número máximo de soluções no arquivo A
            ls_max_iter: Número máximo de tentativas de busca local
            max_pert: Número máximo de perturbações 2-opt
            max_evaluations: Número máximo de avaliações
        """
        self.instance = instance
        self.two_opt = two_opt
        self.ns = ns
        self.na = na
        self.ls_max_iter = ls_max_iter
        self.max_pert = max_pert
        self.max_evaluations = max_evaluations
        self.evaluation_count = 0
        
    def dominates(self, sol1: Solution, sol2: Solution) -> bool:
        """
        Verifica se sol1 domina sol2 (critério de dominância de Pareto)
        """
        # Para o EVRP, consideramos múltiplos objetivos
        # Objetivo 1: Minimizar distância total
        # Objetivo 2: Minimizar número de veículos
        # Objetivo 3: Minimizar custo total
        
        # Verifica se sol1 é melhor ou igual em todos os objetivos
        if (sol1.total_distance <= sol2.total_distance and 
            sol1.total_cost <= sol2.total_cost):
            
            # Verifica se sol1 é melhor em pelo menos um objetivo
            if (sol1.total_distance < sol2.total_distance or 
                sol1.total_cost < sol2.total_cost):
                return True
                
        return False
    
    def is_non_dominated(self, solution: Solution, archive: List[Solution]) -> bool:
        """
        Verifica se uma solução é não-dominada em relação ao arquivo
        """
        # Uma solução factível só pode ser dominada por outras soluções factíveis
        for archived_sol in archive:
            # Se a solução arquivada é factível e domina a solução atual
            if archived_sol.is_feasible and self.dominates(archived_sol, solution):
                return False
        return True
    
    def update_archive(self, archive: List[Solution], new_solutions: List[Solution]) -> List[Solution]:
        """
        Atualiza o arquivo A mantendo apenas soluções não-dominadas e factíveis
        """
        # Adiciona novas soluções ao arquivo
        archive.extend(new_solutions)
        
        # Remove soluções dominadas e mantém apenas soluções factíveis
        non_dominated = []
        for sol in archive:
            # Verifica se a solução é factível
            if not sol.is_feasible:
                continue
                
            # Verifica se é não-dominada
            if self.is_non_dominated(sol, archive):
                non_dominated.append(sol)
        
        # Limita o tamanho do arquivo
        if len(non_dominated) > self.na:
            # Ordena por qualidade e mantém as melhores
            non_dominated.sort(key=lambda x: (x.total_distance, x.num_vehicles_used, x.total_cost))
            non_dominated = non_dominated[:self.na]
        
        return non_dominated
    
    def local_search(self, solution: Solution) -> List[Solution]:
        """
        Aplica busca local (two_opt) NS vezes para gerar um conjunto de soluções
        """
        solutions = []
        
        for _ in range(self.ns):
            # Cria uma cópia da solução
            current_sol = copy.deepcopy(solution)
            
            # Aplica two_opt
            improved = self.two_opt.run(current_sol)
            
            if improved:
                # Reavalia a solução
                current_sol.evaluate()
                self.evaluation_count += 1
            
            # Só adiciona soluções factíveis
            if current_sol.is_feasible:
                solutions.append(current_sol)
            
            # Verifica limite de avaliações
            if self.evaluation_count >= self.max_evaluations:
                break
        
        return solutions
    
    def perturbation(self, solution: Solution) -> Solution:
        """
        Aplica perturbação aleatória usando operações 2-opt
        """
        perturbed_sol = copy.deepcopy(solution)
        
        # Aplica MaxPert operações 2-opt aleatórias
        for _ in range(self.max_pert):
            if len(perturbed_sol.routes) > 0:
                # Escolhe uma rota aleatória
                route_idx = random.randint(0, len(perturbed_sol.routes) - 1)
                route = perturbed_sol.routes[route_idx]
                
                if len(route.nodes) >= 4:
                    # Aplica uma operação 2-opt aleatória
                    self._random_two_opt(route)
        
        # Reavalia a solução perturbada
        perturbed_sol.evaluate()
        self.evaluation_count += 1
        
        # Se a solução perturbada não for factível, retorna a original
        if not perturbed_sol.is_feasible:
            return solution
        
        return perturbed_sol
    
    def _random_two_opt(self, route):
        """
        Aplica uma operação 2-opt aleatória em uma rota
        """
        if len(route.nodes) < 4:
            return
        
        # Escolhe dois índices aleatórios para 2-opt
        i = random.randint(0, len(route.nodes) - 3)
        j = random.randint(i + 2, len(route.nodes) - 1)
        
        if i < j and j < len(route.nodes) - 1:
            # Aplica a operação 2-opt
            self._apply_2opt_move(route, i, j)
    
    def _apply_2opt_move(self, route, i: int, j: int):
        """
        Aplica uma operação 2-opt específica
        """
        if i >= j or i < 0 or j >= len(route.nodes) - 1:
            return
        
        # Inverte o segmento de i+1 a j
        left = i + 1
        right = j
        
        while left < right:
            route.nodes[left], route.nodes[right] = route.nodes[right], route.nodes[left]
            left += 1
            right -= 1
    
    def run(self, initial_population: List[Solution]) -> List[Solution]:
        """
        Executa o algoritmo GVNS
        
        Args:
            initial_population: População inicial de soluções
            
        Returns:
            Lista de soluções não-dominadas
        """
        print("Iniciando algoritmo GVNS...")
        
        # Passo 7-8: Inicializa arquivo A vazio e processa população inicial
        archive = []
        
        print(f"Processando população inicial de {len(initial_population)} soluções...")
        for i, solution in enumerate(initial_population):
            print(f"Processando solução {i+1}/{len(initial_population)}")
            
            # Só processa soluções factíveis
            if not solution.is_feasible:
                print(f"  Solução {i+1} não é factível, pulando...")
                continue
            
            # Passo 9: Aplica busca local NS vezes
            local_solutions = self.local_search(solution)
            
            # Passo 10: Atualiza arquivo A
            archive = self.update_archive(archive, local_solutions)
            
            print(f"  Soluções geradas: {len(local_solutions)}, Arquivo A: {len(archive)}")
            
            # Verifica limite de avaliações
            if self.evaluation_count >= self.max_evaluations:
                print("Limite de avaliações atingido na população inicial")
                break
        
        print(f"Arquivo A inicial criado com {len(archive)} soluções")
        
        # Verifica se o arquivo inicial tem soluções factíveis
        if len(archive) == 0:
            print("❌ Nenhuma solução factível encontrada na população inicial!")
            print("Verifique se as soluções iniciais são factíveis.")
            return []
        
        # Passo 12-19: Loop principal do GVNS
        iteration = 0
        while self.evaluation_count < self.max_evaluations:
            iteration += 1
            print(f"\nIteração {iteration} - Avaliações: {self.evaluation_count}/{self.max_evaluations}")
            
            if len(archive) == 0:
                print("Arquivo A vazio, parando algoritmo")
                break
            
            # Passo 13: Escolhe solução aleatória do arquivo A
            # Filtra apenas soluções factíveis para escolha
            feasible_solutions = [sol for sol in archive if sol.is_feasible]
            if not feasible_solutions:
                print("  ❌ Nenhuma solução factível no arquivo, parando algoritmo")
                break
                
            x = random.choice(feasible_solutions)
            
            # Passo 14: Loop de busca local
            ls_iter = 0
            archive_changed = False
            
            while (not archive_changed and 
                   ls_iter < self.ls_max_iter and 
                   self.evaluation_count < self.max_evaluations):
                
                ls_iter += 1
                print(f"  Tentativa de busca local {ls_iter}/{self.ls_max_iter}")
                
                # Passo 15: Aplica perturbação
                x_prime = self.perturbation(x)
                
                # Passo 16: Aplica busca local NS vezes
                local_solutions = self.local_search(x_prime)
                
                # Passo 17: Atualiza arquivo A
                old_size = len(archive)
                archive = self.update_archive(archive, local_solutions)
                new_size = len(archive)
                
                if new_size != old_size:
                    archive_changed = True
                    print(f"    Arquivo A atualizado: {old_size} -> {new_size}")
                
                print(f"    Soluções geradas: {len(local_solutions)}, Avaliações: {self.evaluation_count}")
            
            if not archive_changed:
                print(f"  Nenhuma melhoria encontrada em {ls_iter} tentativas")
            
            # Verifica se ainda há avaliações disponíveis
            if self.evaluation_count >= self.max_evaluations:
                print("Limite de avaliações atingido no loop principal")
                break
        
        print(f"\nAlgoritmo GVNS finalizado!")
        print(f"Total de iterações: {iteration}")
        print(f"Total de avaliações: {self.evaluation_count}")
        print(f"Soluções não-dominadas encontradas: {len(archive)}")
        
        return archive