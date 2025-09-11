from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

"""
Reinsertion
In most real cases the autonomy of the vehicles, together with the limited average speed of traveling and the maximum
duration of routes, make that feasible routes visit one recharge station at most. So for most instances assuming this property
of the routes is not unrealistic and it provides remarkable advantages from the computational viewpoint. The Reinsertion
neighborhood is then explored when this assumption can be made. Customers are relocated from one route to another with
the purpose of eliminating routes, eliminating recharges or just decreasing energy consumption.
First, the savings achieved by removing each customer from its route are calculated. To do this, the lengths of the links that
are not traversed after removing the corresponding node are subtracted and the length of the new link needed to reconnect the
route is added, as it is done in standard vehicle routing problems. However, now we must also check if the removal of the cus-
tomer allows to eliminate any recharge along the route, due to the energy saved; in that case, additional savings are obtained by
skipping the corresponding recharge station. This information should be updated every time the solution is modiﬁed.
Algorithm 4. Reinsertionub ðRub Þ
Input.
 S: Initial feasible solution.
 n: Number of iterations.
Output.
 S0 : New solution produced.
Pseudocode.
1: Set S0 :¼ S.
2: Calculate the savings g i produced by the removal of each customer i of S0 and sort them.
3: for ðj :¼ 1; nÞ do
4: Consider the customers in decreasing order of g i . For each of these customers c, select the route r of the customer
that is closest to c and visited by a different vehicle and calculate the total cost saving that would be obtained if
customer c is removed from its current route and inserted in route r without modifying the sequence of the other
customers already being served by r.
5: if (b ¼ 1) then
6:
Select the move v involving customer i with the highest saving.
7: else
8:
Select the ﬁrst move v found involving customer i with a positive saving.
9: end if
10: if (no improving move v is found) then
11:
return
12: else
13:
Perform move v on S0 .
14:
if (u ¼ 1) then
15:
Update the savings g i concerning the customers i belonging to routes being affected by the move performed
and sort them again.
16:
else
17:
Eliminate g i from the list of savings.
18:
end if
19: end if
20: end for
"""

class Reinsertion:
    def __init__(self, instance: Instance):
        self.instance = instance

    def run(self, solution: 'Solution', max_iterations: int = 10, best_improvement: bool = True, update_savings: bool = True) -> bool:
        """
        Run the reinsertion local search algorithm
        
        Args:
            solution: The solution to improve
            max_iterations: Maximum number of iterations (n in the algorithm)
            best_improvement: If True, select best move (b=1), else first improving move (b=0)
            update_savings: If True, update savings after each move (u=1), else remove from list (u=0)
            
        Returns:
            True if the solution was improved, False otherwise
        """
        if not solution.routes:
            return False
            
        improved = False
        iteration = 0
        
        while iteration < max_iterations:
            # Calculate savings for each customer
            customer_savings = self._calculate_customer_savings(solution)
            
            if not customer_savings:
                break
                
            # Sort customers by savings (decreasing order)
            customer_savings.sort(key=lambda x: x[1], reverse=True)
            
            best_move = None
            best_saving = 0
            
            # Find the best reinsertion move
            for customer_id, current_saving in customer_savings:
                move = self._find_best_reinsertion_move(solution, customer_id)
                
                if move and move['total_saving'] > 0:
                    if best_improvement:
                        # Select the move with highest saving
                        if move['total_saving'] > best_saving:
                            best_move = move
                            best_saving = move['total_saving']
                    else:
                        # Select the first improving move
                        best_move = move
                        break
            
            # If no improving move found, stop
            if not best_move:
                break
                
            # Perform the best move
            self._perform_move(solution, best_move)
            improved = True
            
            # Update solution evaluation
            solution.evaluate()
            
            # Update or remove savings based on parameter
            if update_savings:
                # Update savings for affected routes
                self._update_savings_after_move(customer_savings, best_move, solution)
                # Resort the savings
                customer_savings.sort(key=lambda x: x[1], reverse=True)
            else:
                # Remove the customer from savings list
                customer_savings[:] = [(c, s) for c, s in customer_savings if c != best_move['customer_id']]
            
            iteration += 1
            
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
    
    def _find_best_reinsertion_move(self, solution: 'Solution', customer_id: int) -> dict:
        """Find the best reinsertion move for a customer"""
        best_move = None
        best_saving = 0
        
        # Find the route containing the customer
        source_route_idx = None
        customer_idx = None
        for route_idx, route in enumerate(solution.routes):
            for node_idx, node in enumerate(route.nodes):
                if node.id == customer_id and node.type == NodeType.CUSTOMER:
                    source_route_idx = route_idx
                    customer_idx = node_idx
                    break
            if source_route_idx is not None:
                break
        
        if source_route_idx is None:
            return None
            
        source_route = solution.routes[source_route_idx]
        
        # Try inserting into other routes
        for target_route_idx, target_route in enumerate(solution.routes):
            if target_route_idx == source_route_idx:
                continue
                
            # Try different insertion positions
            for insert_pos in range(1, len(target_route.nodes)):  # Skip depot at position 0
                move = self._evaluate_insertion_move(
                    solution, customer_id, source_route_idx, target_route_idx, insert_pos
                )
                
                if move and move['total_saving'] > best_saving:
                    best_move = move
                    best_saving = move['total_saving']
        
        return best_move
    
    def _evaluate_insertion_move(self, solution: 'Solution', customer_id: int, 
                               source_route_idx: int, target_route_idx: int, 
                               insert_pos: int) -> dict:
        """Evaluate a specific insertion move"""
        # Create temporary copies to test the move
        temp_solution = self._copy_solution(solution)
        
        # Remove customer from source route
        source_route = temp_solution.routes[source_route_idx]
        customer_node = None
        customer_idx = None
        
        for node_idx, node in enumerate(source_route.nodes):
            if node.id == customer_id and node.type == NodeType.CUSTOMER:
                customer_node = node
                customer_idx = node_idx
                break
        
        if customer_idx is None:
            return None
            
        # Remove customer from source route
        source_route.nodes.pop(customer_idx)
        
        # Insert customer into target route
        target_route = temp_solution.routes[target_route_idx]
        target_route.nodes.insert(insert_pos, customer_node)
        
        # Evaluate both routes
        source_route.evaluate(self.instance)
        target_route.evaluate(self.instance)
        
        # Check if both routes are feasible
        if not source_route.is_feasible or not target_route.is_feasible:
            return None
            
        # Calculate total saving including recharge elimination
        original_source_cost = solution.routes[source_route_idx].total_cost
        original_target_cost = solution.routes[target_route_idx].total_cost
        original_total = original_source_cost + original_target_cost
        
        new_total = source_route.total_cost + target_route.total_cost
        total_saving = original_total - new_total
        
        return {
            'customer_id': customer_id,
            'source_route_idx': source_route_idx,
            'target_route_idx': target_route_idx,
            'insert_pos': insert_pos,
            'total_saving': total_saving,
            'customer_node': customer_node
        }
    
    def _perform_move(self, solution: 'Solution', move: dict):
        """Perform the reinsertion move on the solution"""
        customer_id = move['customer_id']
        source_route_idx = move['source_route_idx']
        target_route_idx = move['target_route_idx']
        insert_pos = move['insert_pos']
        customer_node = move['customer_node']
        
        # Get the actual route objects from the solution using indices
        source_route = solution.routes[source_route_idx]
        target_route = solution.routes[target_route_idx]
        
        # Remove customer from source route
        for node_idx, node in enumerate(source_route.nodes):
            if node.id == customer_id and node.type == NodeType.CUSTOMER:
                source_route.nodes.pop(node_idx)
                break
        
        # Insert customer into target route
        target_route.nodes.insert(insert_pos, customer_node)
        
        # Remove empty routes (if source route only has depot)
        if len(source_route.nodes) <= 2:  # Only depot nodes
            solution.routes.pop(source_route_idx)
    
    def _update_savings_after_move(self, customer_savings: List[Tuple[int, float]], move: dict, solution: 'Solution'):
        """Update savings after a move is performed"""
        # Remove the moved customer from savings
        customer_savings[:] = [(c, s) for c, s in customer_savings if c != move['customer_id']]
        
        # Recalculate savings for all customers in affected routes
        affected_routes = set()
        if move['source_route_idx'] < len(solution.routes):
            affected_routes.add(move['source_route_idx'])
        if move['target_route_idx'] < len(solution.routes):
            affected_routes.add(move['target_route_idx'])
        
        # Remove old savings for affected routes
        customer_savings[:] = [(c, s) for c, s in customer_savings 
                              if not self._is_customer_in_routes(c, solution, affected_routes)]
        
        # Add new savings for affected routes
        for route_idx in affected_routes:
            if route_idx < len(solution.routes):
                route = solution.routes[route_idx]
                for node_idx, node in enumerate(route.nodes):
                    if node.type == NodeType.CUSTOMER:
                        customer_id = node.id
                        saving = self._calculate_removal_saving(route, node_idx)
                        customer_savings.append((customer_id, saving))
    
    def _is_customer_in_routes(self, customer_id: int, solution: 'Solution', route_indices: set) -> bool:
        """Check if a customer is in any of the specified routes"""
        for route_idx in route_indices:
            if route_idx < len(solution.routes):
                route = solution.routes[route_idx]
                for node in route.nodes:
                    if node.id == customer_id and node.type == NodeType.CUSTOMER:
                        return True
        return False
    
    def _copy_solution(self, solution: 'Solution') -> 'Solution':
        """Create a deep copy of the solution for testing moves"""
        from EVRP.solution import Solution
        
        new_solution = Solution(solution.instance)
        new_solution.routes = []
        
        for route in solution.routes:
            new_route = Route()
            new_route.nodes = route.nodes.copy()
            new_route.charging_decisions = route.charging_decisions.copy()
            new_solution.routes.append(new_route)
        
        return new_solution