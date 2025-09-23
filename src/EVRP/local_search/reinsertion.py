from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class Reinsertion:
    def __init__(self, instance: Instance, max_iterations = 3, best_improvement = False):
        self.instance = instance
        self.max_iterations = max_iterations
        self.best_improvement = best_improvement
        self.update_savings = True

    def perturbation(self, solution: 'Solution') -> bool:
        """
        Run the reinsertion local search algorithm
        
        Args:
            solution: The solution to improve
            
        Returns:
            True if the solution was improved, False otherwise
        """
        if not solution.routes or len(solution.routes) < 2:
            return False
            
        improved = False
        
        # Main reinsertion loop: for j = 1 to n
        for iteration in range(self.max_iterations):
            # Calculate g_i (savings) for each customer
            customer_savings = self._calculate_customer_savings(solution)
            
            if not customer_savings:
                break
                
            # Sort customers by savings in decreasing order of g_i
            customer_savings.sort(key=lambda x: x[1], reverse=True)
            
            # Find all possible improving moves
            improving_moves = []
            
            # For each customer c in decreasing order of g_i
            for customer_id, g_i in customer_savings:
                # Find the current route of customer c
                current_route_idx = self._find_customer_route(solution, customer_id)
                if current_route_idx is None:
                    continue
                
                # Find the closest route r visited by a different vehicle
                closest_route_idx = self._find_closest_route(solution, customer_id, current_route_idx)
                if closest_route_idx is None:
                    continue
                
                # Calculate total cost saving for the reinsertion
                total_saving = self._calculate_reinsertion_saving(
                    solution, customer_id, current_route_idx, closest_route_idx
                )
                
                # If the move improves the solution, add it to the list
                if total_saving > 0:
                    improving_moves.append({
                        'customer_id': customer_id,
                        'current_route_idx': current_route_idx,
                        'target_route_idx': closest_route_idx,
                        'saving': total_saving
                    })
            
            # Step 6-9: Select move based on strategy
            if not improving_moves:
                # Step 10-11: No improving move found, return
                break
            
            selected_move = None
            if self.best_improvement:
                # Step 6: Select the move with the highest saving
                selected_move = max(improving_moves, key=lambda x: x['saving'])
            else:
                # Step 7-8: Select the first move with positive saving
                selected_move = improving_moves[0]
            
            # Step 13: Perform the selected move
            if self._apply_reinsertion(
                solution, 
                selected_move['customer_id'], 
                selected_move['current_route_idx'], 
                selected_move['target_route_idx']
            ):
                improved = True
                
                # Step 14-18: Update savings based on strategy
                if self.update_savings:
                    # Step 15: Update savings for affected customers and sort again
                    # Recalculate savings for customers in affected routes
                    self._update_savings_for_affected_routes(
                        solution, customer_savings, 
                        selected_move['current_route_idx'], 
                        selected_move['target_route_idx']
                    )
                else:
                    # Step 17: Eliminate g_i from the list of savings
                    # Remove the moved customer from the savings list
                    customer_savings = [(cid, g) for cid, g in customer_savings 
                                      if cid != selected_move['customer_id']]
        return solution
   
    def local_search(self, solution: 'Solution') -> bool:
        """
        Run the reinsertion local search algorithm
        
        Args:
            solution: The solution to improve
            
        Returns:
            True if the solution was improved, False otherwise
        """
        if not solution.routes or len(solution.routes) < 2:
            return False
            
        improved = False
        
        # Main reinsertion loop: for j = 1 to n
        for iteration in range(self.max_iterations):
            # Calculate g_i (savings) for each customer
            customer_savings = self._calculate_customer_savings(solution)
            
            if not customer_savings:
                break
                
            # Sort customers by savings in decreasing order of g_i
            customer_savings.sort(key=lambda x: x[1], reverse=True)
            
            # Find all possible improving moves
            improving_moves = []
            
            # For each customer c in decreasing order of g_i
            for customer_id, g_i in customer_savings:
                # Find the current route of customer c
                current_route_idx = self._find_customer_route(solution, customer_id)
                if current_route_idx is None:
                    continue
                
                # Find the closest route r visited by a different vehicle
                closest_route_idx = self._find_closest_route(solution, customer_id, current_route_idx)
                if closest_route_idx is None:
                    continue
                
                # Calculate total cost saving for the reinsertion
                total_saving = self._calculate_reinsertion_saving(
                    solution, customer_id, current_route_idx, closest_route_idx
                )
                
                # If the move improves the solution, add it to the list
                if total_saving > 0:
                    improving_moves.append({
                        'customer_id': customer_id,
                        'current_route_idx': current_route_idx,
                        'target_route_idx': closest_route_idx,
                        'saving': total_saving
                    })
            
            # Step 6-9: Select move based on strategy
            if not improving_moves:
                # Step 10-11: No improving move found, return
                break
            
            selected_move = None
            if self.best_improvement:
                # Step 6: Select the move with the highest saving
                selected_move = max(improving_moves, key=lambda x: x['saving'])
            else:
                # Step 7-8: Select the first move with positive saving
                selected_move = improving_moves[0]
            
            # Step 13: Perform the selected move
            if self._apply_reinsertion(
                solution, 
                selected_move['customer_id'], 
                selected_move['current_route_idx'], 
                selected_move['target_route_idx']
            ):
                improved = True
                
                # Step 14-18: Update savings based on strategy
                if self.update_savings:
                    # Step 15: Update savings for affected customers and sort again
                    # Recalculate savings for customers in affected routes
                    self._update_savings_for_affected_routes(
                        solution, customer_savings, 
                        selected_move['current_route_idx'], 
                        selected_move['target_route_idx']
                    )
                else:
                    # Step 17: Eliminate g_i from the list of savings
                    # Remove the moved customer from the savings list
                    customer_savings = [(cid, g) for cid, g in customer_savings 
                                      if cid != selected_move['customer_id']]
        return improved
    
    def _calculate_customer_savings(self, solution: 'Solution') -> List[Tuple[int, float]]:
        """Calculate savings for removing each customer from their route"""
        savings = []
        
        for route_idx, route in enumerate(solution.routes):
            for node_idx, node in enumerate(route.nodes):
                if node.type == NodeType.CUSTOMER:
                    customer_id = node.id
                    saving = self._calculate_removal_saving(route, node_idx)
                    savings.append((customer_id, saving))
        
        return savings
    
    def _calculate_removal_saving(self, route: Route, customer_idx: int) -> float:
        """Calculate the saving from removing a customer from a route"""
        if customer_idx == 0 or customer_idx == len(route.nodes) - 1:
            return 0.0  # Can't remove depot nodes
            
        prev_node = route.nodes[customer_idx - 1]
        customer_node = route.nodes[customer_idx]
        next_node = route.nodes[customer_idx + 1]
        
        # Current distances
        current_dist1 = self.instance.distance_matrix[prev_node.id][customer_node.id]
        current_dist2 = self.instance.distance_matrix[customer_node.id][next_node.id]
        
        # New distance after removal
        new_dist = self.instance.distance_matrix[prev_node.id][next_node.id]
        
        # Basic distance saving
        distance_saving = current_dist1 + current_dist2 - new_dist
        
        # Additional saving from potential recharge elimination
        recharge_saving = self._calculate_recharge_saving(route, customer_idx)
        
        return distance_saving + recharge_saving
    
    def _calculate_recharge_saving(self, route: Route, customer_idx: int) -> float:
        """Calculate additional saving from potential recharge elimination"""
        # Check if removing the customer allows eliminating a recharge station
        # due to energy savings
        
        # Create a temporary route without the customer
        temp_route = Route()
        temp_route.nodes = [node for i, node in enumerate(route.nodes) if i != customer_idx]
        temp_route.charging_decisions = route.charging_decisions.copy()
        
        # Evaluate the temporary route
        temp_route.evaluate(self.instance)
        
        if not temp_route.is_feasible:
            return 0.0  # Route becomes infeasible without the customer
        
        # Check if we can eliminate any recharge stations
        original_recharge_count = self._count_recharge_stations(route)
        new_recharge_count = self._count_recharge_stations(temp_route)
        
        if new_recharge_count < original_recharge_count:
            # Calculate savings from eliminated recharge stations
            eliminated_recharge_savings = 0.0
            for node_id, (tech, energy) in route.charging_decisions.items():
                if node_id not in temp_route.charging_decisions:
                    # This recharge station was eliminated
                    eliminated_recharge_savings += energy * tech.cost_per_kwh
                    if hasattr(self.instance, 'battery_depreciation_cost'):
                        eliminated_recharge_savings += self.instance.battery_depreciation_cost
            
            return eliminated_recharge_savings
        
        return 0.0
    
    def _count_recharge_stations(self, route: Route) -> int:
        """Count the number of recharge stations in a route"""
        count = 0
        for node in route.nodes:
            if node.type == NodeType.STATION and node.id in route.charging_decisions:
                count += 1
        return count
    
    def _find_customer_route(self, solution: 'Solution', customer_id: int) -> int:
        """Find the route index containing the customer"""
        for route_idx, route in enumerate(solution.routes):
            for node in route.nodes:
                if node.type == NodeType.CUSTOMER and node.id == customer_id:
                    return route_idx
        return None
    
    def _find_closest_route(self, solution: 'Solution', customer_id: int, current_route_idx: int) -> int:
        """Find the closest route visited by a different vehicle"""
        if len(solution.routes) < 2:
            return None
            
        # Get customer node
        customer_node = None
        for node in solution.routes[current_route_idx].nodes:
            if node.type == NodeType.CUSTOMER and node.id == customer_id:
                customer_node = node
                break
                
        if customer_node is None:
            return None
            
        min_distance = float('inf')
        closest_route_idx = None
        
        # Find the closest route (excluding current route)
        for route_idx, route in enumerate(solution.routes):
            if route_idx == current_route_idx:
                continue
                
            # Calculate minimum distance to any node in this route
            min_route_distance = float('inf')
            for node in route.nodes:
                if node.type in [NodeType.CUSTOMER, NodeType.STATION, NodeType.DEPOT]:
                    distance = self.instance.distance_matrix[customer_id][node.id]
                    min_route_distance = min(min_route_distance, distance)
            
            if min_route_distance < min_distance:
                min_distance = min_route_distance
                closest_route_idx = route_idx
                
        return closest_route_idx
    
    def _calculate_reinsertion_saving(self, solution: 'Solution', customer_id: int, 
                                    current_route_idx: int, target_route_idx: int) -> float:
        """Calculate total cost saving for reinserting customer from current route to target route"""
        
        # Calculate saving from removing customer from current route
        removal_saving = self._calculate_removal_saving_from_route(
            solution, customer_id, current_route_idx
        )
        
        # Calculate cost of inserting customer into target route
        insertion_cost = self._calculate_insertion_cost(
            solution, customer_id, target_route_idx
        )
        
        # Total saving = removal_saving - insertion_cost
        return removal_saving - insertion_cost
    
    def _calculate_removal_saving_from_route(self, solution: 'Solution', customer_id: int, route_idx: int) -> float:
        """Calculate saving from removing customer from specific route"""
        route = solution.routes[route_idx]
        
        # Find customer position in route
        customer_position = None
        for i, node in enumerate(route.nodes):
            if node.type == NodeType.CUSTOMER and node.id == customer_id:
                customer_position = i
                break
                
        if customer_position is None:
            return 0.0
            
        return self._calculate_removal_saving(route, customer_position)
    
    def _calculate_insertion_cost(self, solution: 'Solution', customer_id: int, target_route_idx: int) -> float:
        """Calculate cost of inserting customer into target route at best position"""
        target_route = solution.routes[target_route_idx]
        customer_node = self.instance.nodes[customer_id]
        
        if not target_route.nodes:
            return 0.0
            
        min_insertion_cost = float('inf')
        
        # Try inserting at each position in the route (excluding depot positions)
        for i in range(1, len(target_route.nodes)):
            # Calculate insertion cost at position i
            insertion_cost = self._calculate_insertion_cost_at_position(
                target_route, customer_node, i
            )
            min_insertion_cost = min(min_insertion_cost, insertion_cost)
            
        return min_insertion_cost
    
    def _calculate_insertion_cost_at_position(self, route: Route, customer_node: Node, position: int) -> float:
        """Calculate cost of inserting customer at specific position in route"""
        if position <= 0 or position >= len(route.nodes):
            return float('inf')
            
        prev_node = route.nodes[position - 1]
        next_node = route.nodes[position]
        
        # Current distance in route
        current_dist = self.instance.distance_matrix[prev_node.id][next_node.id]
        
        # New distances after insertion
        new_dist1 = self.instance.distance_matrix[prev_node.id][customer_node.id]
        new_dist2 = self.instance.distance_matrix[customer_node.id][next_node.id]
        
        # Additional distance cost
        distance_cost = new_dist1 + new_dist2 - current_dist
        
        # Additional cost from potential recharge needs
        recharge_cost = self._calculate_recharge_cost_for_insertion(route, customer_node, position)
        
        return distance_cost + recharge_cost
    
    def _calculate_recharge_cost_for_insertion(self, route: Route, customer_node: Node, position: int) -> float:
        """Calculate additional recharge cost needed for inserting customer"""
        # This is a simplified calculation - in practice, you might need to
        # check if additional recharging is needed and calculate the cost
        return 0.0  # Placeholder - implement based on energy constraints
    
    def _apply_reinsertion(self, solution: 'Solution', customer_id: int, 
                          current_route_idx: int, target_route_idx: int) -> bool:
        """Apply the reinsertion move if it's feasible"""
        
        # Create a copy of the solution to test feasibility
        temp_solution = self._copy_solution(solution)
        
        # Remove customer from current route
        if not self._remove_customer_from_route(temp_solution, customer_id, current_route_idx):
            return False
            
        # Find best insertion position in target route
        best_position = self._find_best_insertion_position(
            temp_solution, customer_id, target_route_idx
        )
        
        if best_position is None:
            return False
            
        # Insert customer into target route
        if not self._insert_customer_into_route(temp_solution, customer_id, target_route_idx, best_position):
            return False
            
        # Evaluate the new solution
        temp_solution.evaluate()
        
        # Check if the new solution is feasible and better
        if temp_solution.is_feasible and self._is_improvement(solution, temp_solution):
            # Apply the move to the original solution
            self._remove_customer_from_route(solution, customer_id, current_route_idx)
            self._insert_customer_into_route(solution, customer_id, target_route_idx, best_position)
            solution.evaluate()
            return True
            
        return False
    
    def _copy_solution(self, solution: 'Solution') -> 'Solution':
        """Create a deep copy of the solution for testing moves"""
        from copy import deepcopy
        return deepcopy(solution)
    
    def _remove_customer_from_route(self, solution: 'Solution', customer_id: int, route_idx: int) -> bool:
        """Remove customer from specified route"""
        route = solution.routes[route_idx]
        
        # Find and remove customer
        for i, node in enumerate(route.nodes):
            if node.type == NodeType.CUSTOMER and node.id == customer_id:
                route.nodes.pop(i)
                return True
                
        return False
    
    def _find_best_insertion_position(self, solution: 'Solution', customer_id: int, target_route_idx: int) -> int:
        """Find the best position to insert customer in target route"""
        target_route = solution.routes[target_route_idx]
        
        if not target_route.nodes:
            return None
            
        best_position = None
        min_cost = float('inf')
        
        # Try each possible position
        for i in range(1, len(target_route.nodes)):
            cost = self._calculate_insertion_cost_at_position(
                target_route, self.instance.nodes[customer_id], i
            )
            if cost < min_cost:
                min_cost = cost
                best_position = i
                
        return best_position
    
    def _insert_customer_into_route(self, solution: 'Solution', customer_id: int, 
                                   target_route_idx: int, position: int) -> bool:
        """Insert customer into target route at specified position"""
        target_route = solution.routes[target_route_idx]
        customer_node = self.instance.nodes[customer_id]
        
        if position <= 0 or position > len(target_route.nodes):
            return False
            
        target_route.nodes.insert(position, customer_node)
        return True
    
    def _is_improvement(self, original_solution: 'Solution', new_solution: 'Solution') -> bool:
        """Check if new solution is an improvement over original"""
        # For EVRP, we can consider multiple objectives
        # Here we use a simple weighted sum approach
        original_cost = original_solution.total_cost + original_solution.total_distance * 0.1
        new_cost = new_solution.total_cost + new_solution.total_distance * 0.1
        
        return new_cost < original_cost
    
    def _update_savings_for_affected_routes(self, solution: 'Solution', 
                                          customer_savings: List[Tuple[int, float]], 
                                          current_route_idx: int, target_route_idx: int):
        """Update savings for customers in routes affected by the move"""
        # Get customers in affected routes
        affected_customers = set()
        
        # Add customers from current route (source route)
        for node in solution.routes[current_route_idx].nodes:
            if node.type == NodeType.CUSTOMER:
                affected_customers.add(node.id)
        
        # Add customers from target route
        for node in solution.routes[target_route_idx].nodes:
            if node.type == NodeType.CUSTOMER:
                affected_customers.add(node.id)
        
        # Update savings for affected customers
        updated_savings = []
        for customer_id, old_saving in customer_savings:
            if customer_id in affected_customers:
                # Recalculate saving for this customer
                new_saving = self._calculate_removal_saving_from_route(
                    solution, customer_id, 
                    self._find_customer_route(solution, customer_id)
                )
                updated_savings.append((customer_id, new_saving))
            else:
                # Keep old saving for unaffected customers
                updated_savings.append((customer_id, old_saving))
        
        # Update the customer_savings list
        customer_savings.clear()
        customer_savings.extend(updated_savings)
        
        # Sort again by updated savings
        customer_savings.sort(key=lambda x: x[1], reverse=True)
    