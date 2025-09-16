import copy
import random
from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Exchange:
    """
    Exchange local search operator that swaps two customers between different routes
    or within the same route. This operator helps diversify the search by exchanging
    customer positions.
    """
    
    def __init__(self, instance: Instance, max_iter: int = 10):
        self.instance = instance
        self.max_iter = max_iter

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply exchange local search to improve the solution.
        Swaps customers between routes or within routes to reduce total cost.
        
        Args:
            solution: The solution to improve
            
        Returns:
            bool: True if any improvement was made, False otherwise
        """
        if len(solution.routes) < 1:
            return False
            
        improved = False
        iteration = 0
        
        while iteration < self.max_iter:
            if self._exchange_customers(solution):
                improved = True
                solution.evaluate()
            else:
                break
            iteration += 1
            
        return improved

    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply exchange perturbation to diversify the solution.
        
        Args:
            solution: The solution to perturb
            
        Returns:
            Solution: The perturbed solution
        """
        for _ in range(self.max_iter):
            self._exchange_customers(solution, force_move=True)
        
        solution.evaluate()
        return solution

    def _exchange_customers(self, solution: 'Solution', force_move: bool = False) -> bool:
        """
        Try to exchange customers between routes or within routes to improve the solution.
        
        Args:
            solution: The solution to improve
            force_move: If True, perform a random move even if not improving
            
        Returns:
            bool: True if a move was made, False otherwise
        """
        best_move = None
        best_improvement = 0
        
        # Try inter-route exchanges (between different routes)
        for route1_idx in range(len(solution.routes)):
            for route2_idx in range(route1_idx + 1, len(solution.routes)):
                move = self._find_best_inter_route_exchange(solution, route1_idx, route2_idx)
                if move and move['improvement'] > best_improvement:
                    best_move = move
                    best_improvement = move['improvement']
        
        # Try intra-route exchanges (within the same route)
        for route_idx in range(len(solution.routes)):
            move = self._find_best_intra_route_exchange(solution, route_idx)
            if move and move['improvement'] > best_improvement:
                best_move = move
                best_improvement = move['improvement']
        
        # If no improving move found but force_move is True, select a random move
        if not best_move and force_move:
            best_move = self._select_random_exchange_move(solution)
        
        # Apply the best move if found
        if best_move:
            self._apply_exchange_move(solution, best_move)
            return True
            
        return False

    def _find_best_inter_route_exchange(self, solution: 'Solution', 
                                      route1_idx: int, route2_idx: int) -> dict:
        """
        Find the best exchange between two different routes.
        
        Args:
            solution: The current solution
            route1_idx: Index of the first route
            route2_idx: Index of the second route
            
        Returns:
            dict: Best exchange move, or None if no improvement found
        """
        route1 = solution.routes[route1_idx]
        route2 = solution.routes[route2_idx]
        
        best_move = None
        best_improvement = 0
        
        # Try exchanging each customer from route1 with each customer from route2
        for customer1_idx, customer1 in enumerate(route1.nodes):
            if customer1.type != NodeType.CUSTOMER:
                continue
                
            for customer2_idx, customer2 in enumerate(route2.nodes):
                if customer2.type != NodeType.CUSTOMER:
                    continue
                
                move = self._evaluate_inter_route_exchange(
                    solution, route1_idx, customer1_idx, route2_idx, customer2_idx
                )
                
                if move and move['improvement'] > best_improvement:
                    best_move = move
                    best_improvement = move['improvement']
        
        return best_move

    def _find_best_intra_route_exchange(self, solution: 'Solution', route_idx: int) -> dict:
        """
        Find the best exchange within a single route.
        
        Args:
            solution: The current solution
            route_idx: Index of the route
            
        Returns:
            dict: Best exchange move, or None if no improvement found
        """
        route = solution.routes[route_idx]
        
        best_move = None
        best_improvement = 0
        
        # Try exchanging each pair of customers in the route
        for customer1_idx in range(1, len(route.nodes) - 1):  # Skip depot nodes
            customer1 = route.nodes[customer1_idx]
            if customer1.type != NodeType.CUSTOMER:
                continue
                
            for customer2_idx in range(customer1_idx + 1, len(route.nodes) - 1):
                customer2 = route.nodes[customer2_idx]
                if customer2.type != NodeType.CUSTOMER:
                    continue
                
                move = self._evaluate_intra_route_exchange(
                    solution, route_idx, customer1_idx, customer2_idx
                )
                
                if move and move['improvement'] > best_improvement:
                    best_move = move
                    best_improvement = move['improvement']
        
        return best_move

    def _evaluate_inter_route_exchange(self, solution: 'Solution', route1_idx: int, 
                                     customer1_idx: int, route2_idx: int, 
                                     customer2_idx: int) -> dict:
        """
        Evaluate an inter-route exchange move.
        
        Args:
            solution: The current solution
            route1_idx: Index of the first route
            customer1_idx: Index of customer in first route
            route2_idx: Index of the second route
            customer2_idx: Index of customer in second route
            
        Returns:
            dict: Move information with improvement value, or None if infeasible
        """
        # Create temporary copies to test the move
        temp_solution = self._copy_solution(solution)
        temp_route1 = temp_solution.routes[route1_idx]
        temp_route2 = temp_solution.routes[route2_idx]
        
        # Get the customers to exchange
        customer1 = temp_route1.nodes[customer1_idx]
        customer2 = temp_route2.nodes[customer2_idx]
        
        # Perform the exchange
        temp_route1.nodes[customer1_idx] = customer2
        temp_route2.nodes[customer2_idx] = customer1
        
        # Evaluate both routes
        temp_route1.evaluate(self.instance)
        temp_route2.evaluate(self.instance)
        
        # Check if both routes are feasible
        if not temp_route1.is_feasible or not temp_route2.is_feasible:
            return None
        
        # Calculate improvement
        original_cost = (solution.routes[route1_idx].total_cost + 
                        solution.routes[route2_idx].total_cost)
        new_cost = temp_route1.total_cost + temp_route2.total_cost
        improvement = original_cost - new_cost
        
        return {
            'type': 'inter_route',
            'route1_idx': route1_idx,
            'customer1_idx': customer1_idx,
            'route2_idx': route2_idx,
            'customer2_idx': customer2_idx,
            'customer1': customer1,
            'customer2': customer2,
            'improvement': improvement
        }

    def _evaluate_intra_route_exchange(self, solution: 'Solution', route_idx: int, 
                                     customer1_idx: int, customer2_idx: int) -> dict:
        """
        Evaluate an intra-route exchange move.
        
        Args:
            solution: The current solution
            route_idx: Index of the route
            customer1_idx: Index of first customer
            customer2_idx: Index of second customer
            
        Returns:
            dict: Move information with improvement value, or None if infeasible
        """
        # Create temporary copy to test the move
        temp_solution = self._copy_solution(solution)
        temp_route = temp_solution.routes[route_idx]
        
        # Get the customers to exchange
        customer1 = temp_route.nodes[customer1_idx]
        customer2 = temp_route.nodes[customer2_idx]
        
        # Perform the exchange
        temp_route.nodes[customer1_idx] = customer2
        temp_route.nodes[customer2_idx] = customer1
        
        # Evaluate the route
        temp_route.evaluate(self.instance)
        
        # Check if the route is feasible
        if not temp_route.is_feasible:
            return None
        
        # Calculate improvement
        original_cost = solution.routes[route_idx].total_cost
        new_cost = temp_route.total_cost
        improvement = original_cost - new_cost
        
        return {
            'type': 'intra_route',
            'route_idx': route_idx,
            'customer1_idx': customer1_idx,
            'customer2_idx': customer2_idx,
            'customer1': customer1,
            'customer2': customer2,
            'improvement': improvement
        }

    def _select_random_exchange_move(self, solution: 'Solution') -> dict:
        """
        Select a random exchange move for perturbation.
        
        Args:
            solution: The current solution
            
        Returns:
            dict: Random move information, or None if no valid moves
        """
        valid_moves = []
        
        # Collect all valid inter-route moves
        for route1_idx in range(len(solution.routes)):
            for route2_idx in range(route1_idx + 1, len(solution.routes)):
                route1 = solution.routes[route1_idx]
                route2 = solution.routes[route2_idx]
                
                for customer1_idx, customer1 in enumerate(route1.nodes):
                    if customer1.type != NodeType.CUSTOMER:
                        continue
                        
                    for customer2_idx, customer2 in enumerate(route2.nodes):
                        if customer2.type != NodeType.CUSTOMER:
                            continue
                        
                        move = self._evaluate_inter_route_exchange(
                            solution, route1_idx, customer1_idx, route2_idx, customer2_idx
                        )
                        
                        if move:  # Only consider feasible moves
                            valid_moves.append(move)
        
        # Collect all valid intra-route moves
        for route_idx in range(len(solution.routes)):
            route = solution.routes[route_idx]
            
            for customer1_idx in range(1, len(route.nodes) - 1):
                customer1 = route.nodes[customer1_idx]
                if customer1.type != NodeType.CUSTOMER:
                    continue
                    
                for customer2_idx in range(customer1_idx + 1, len(route.nodes) - 1):
                    customer2 = route.nodes[customer2_idx]
                    if customer2.type != NodeType.CUSTOMER:
                        continue
                    
                    move = self._evaluate_intra_route_exchange(
                        solution, route_idx, customer1_idx, customer2_idx
                    )
                    
                    if move:  # Only consider feasible moves
                        valid_moves.append(move)
        
        # Return a random move if any exist
        return random.choice(valid_moves) if valid_moves else None

    def _apply_exchange_move(self, solution: 'Solution', move: dict) -> None:
        """
        Apply an exchange move to the solution.
        
        Args:
            solution: The solution to modify
            move: The move to apply
        """
        if move['type'] == 'inter_route':
            # Inter-route exchange
            route1 = solution.routes[move['route1_idx']]
            route2 = solution.routes[move['route2_idx']]
            
            route1.nodes[move['customer1_idx']] = move['customer2']
            route2.nodes[move['customer2_idx']] = move['customer1']
            
        elif move['type'] == 'intra_route':
            # Intra-route exchange
            route = solution.routes[move['route_idx']]
            
            route.nodes[move['customer1_idx']] = move['customer2']
            route.nodes[move['customer2_idx']] = move['customer1']

    def _copy_solution(self, solution: 'Solution') -> 'Solution':
        """
        Create a deep copy of the solution for testing moves.
        
        Args:
            solution: The solution to copy
            
        Returns:
            Solution: A deep copy of the solution
        """
        from EVRP.solution import Solution
        
        new_solution = Solution(solution.instance)
        new_solution.routes = []
        
        for route in solution.routes:
            new_route = Route()
            new_route.nodes = route.nodes.copy()
            new_route.charging_decisions = route.charging_decisions.copy()
            new_solution.routes.append(new_route)
        
        return new_solution
