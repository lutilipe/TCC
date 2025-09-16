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

class GVNS:
    def __init__(self, instance, 
                 ns: int = 5, na: int = 50, ls_max_iter: int = 10,  max_evaluations: int = 10000, 
                 perturbation = None, local_search = None):
        """
        Inicializa o algoritmo GVNS
        
        Args:
            instance: Instância do problema EVRP
            ns: Número de soluções a serem geradas por busca local
            na: Número máximo de soluções no arquivo A
            ls_max_iter: Número máximo de tentativas de busca local
            max_evaluations: Número máximo de avaliações
            perturbation: Lista de algoritmos de perturbação (se None, usa padrão)
            local_search: Lista de algoritmos de busca local (se None, usa padrão)
        """
        self.instance = instance
        self.ns = ns
        self.na = na
        self.ls_max_iter = ls_max_iter
        self.max_evaluations = max_evaluations
        self.evaluation_count = 0
        
        self.pertubation_algorithms = perturbation
        self.local_search_algorithms = local_search

    def is_non_dominated(self, solution: Solution, archive: List[Solution]) -> bool:
        """
        Verifica se uma solução é não-dominada em relação ao arquivo
        """
        # Uma solução factível só pode ser dominada por outras soluções factíveis
        for archived_sol in archive:
            # Se a solução arquivada é factível e domina a solução atual
            if archived_sol.is_feasible and archived_sol.dominates(solution):
                return False
        return True

    # Alternative approach using hash-based duplicate detection
    def get_solution_hash(self, solution: Solution) -> tuple:
        """
        Retorna uma tupla hash da solução baseada nos objetivos
        Pode ser expandido para incluir mais detalhes se necessário
        """
        return (solution.total_distance, solution.total_cost)

    def update_archive(self, archive: List[Solution], new_solutions: List[Solution]) -> Tuple[List[Solution], bool]:
        """
        Versão mais eficiente usando hash para detectar duplicatas.
        Retorna (novo_arquivo, changed) onde changed indica se houve mudança.
        """
        # Cria set com hash das soluções existentes
        existing_hashes = {self.get_solution_hash(sol) for sol in archive if sol.is_feasible}
        original_feasible_count = len([sol for sol in archive if sol.is_feasible])
        
        # Filtra novas soluções
        truly_new_solutions = []
        for new_sol in new_solutions:
            if new_sol.is_feasible:
                new_hash = self.get_solution_hash(new_sol)
                if new_hash not in existing_hashes:
                    truly_new_solutions.append(new_sol)
                    existing_hashes.add(new_hash)
        
        # Adiciona novas soluções
        archive.extend(truly_new_solutions)
        
        # Remove soluções dominadas
        non_dominated = []
        processed_hashes = set()
        
        for sol in archive:
            if not sol.is_feasible:
                continue
                
            sol_hash = self.get_solution_hash(sol)
            
            # Evita processar soluções duplicadas
            if sol_hash in processed_hashes:
                continue
                
            if self.is_non_dominated(sol, archive):
                non_dominated.append(sol)
                processed_hashes.add(sol_hash)
                print(sol_hash)
        
        # Apply size limit if necessary
        if len(non_dominated) > self.na:
            non_dominated.sort(key=lambda x: (x.total_distance, x.num_vehicles_used, x.total_cost))
            non_dominated = non_dominated[:self.na]

        # Detecta mudança
        old_hashes = {self.get_solution_hash(sol) for sol in archive if sol.is_feasible}
        new_hashes = {self.get_solution_hash(sol) for sol in non_dominated if sol.is_feasible}
        changed = False

        return non_dominated, changed
    
    def _improve_solution(self, solution: Solution) -> Solution:
        candidate = copy.deepcopy(solution)
        for method in self.local_search_algorithms:
            improved = method.local_search(candidate)
            self.evaluation_count += 1
            if improved:
                candidate.evaluate()
                if candidate.is_feasible:
                    break
        return candidate

    def local_search(self, solution: Solution) -> List[Solution]:
        solutions = []
        candidate = copy.deepcopy(solution)
        for _ in range(self.ns):
            if self.evaluation_count >= self.max_evaluations:
                break

            candidate = self._improve_solution(candidate)
            candidate.evaluate()
            if candidate.is_feasible:
                solutions.append(candidate)

        if candidate.is_feasible:
            solutions.append(candidate)

        return solutions

    
    def perturbation(self, solution: Solution) -> Solution:
        perturbed_sol = copy.deepcopy(solution)
        
        # Reavalia a solução perturbada
        for method in self.pertubation_algorithms:
            new_solution = method.perturbation(perturbed_sol)
            new_solution.evaluate()
            self.evaluation_count += 1
            if new_solution.is_feasible:
                perturbed_sol = copy.deepcopy(new_solution)
                
        
        return perturbed_sol
    
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
            archive, _ = self.update_archive(archive, local_solutions)
            
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
                archive, changed = self.update_archive(archive, local_solutions)
                new_size = len(archive)
                
                if changed:
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