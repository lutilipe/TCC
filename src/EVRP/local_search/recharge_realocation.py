from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route
from EVRP.classes.station import Station
from EVRP.classes.technology import Technology

if TYPE_CHECKING:
    from EVRP.solution import Solution

""" 
if one route of a feasible solution visits at least one recharge station, it may be improved by optimally locating one single
recharge at a certain point. Following this idea, the operator Recharge Relocation is intended to ﬁnd, if needed (and possible),
the optimal location of a single recharge point in a route, without modifying the sequence of visits to the customers. This is
explained in Algorithm.
\begin{algorithm}[H]
\caption{Recharge Relocation (RR)}
\begin{algorithmic}[1]
\REQUIRE $S$: Initial feasible solution.
\ENSURE $S'$: Feasible solution produced.
\STATE Set $S' \gets S$.
\FOR{each route $r$ in $S$}
    \STATE Let $(p_1, \cdots, p_h)$ be the sequence of customers of route $r$, excluding recharge stations ($p_1$ and $p_h$ are necessarily the depot).
    \STATE Calculate $l := \sum_{i=1}^{h-1} d(p_i, p_{i+1})$ and set $r' \gets r$.
    \IF{$l > AT$}
        \STATE Calculate the interval $[a, b]$ in which a single recharge station could be located, where
        \[
        a := \min\{s = 1, \cdots, h-1 \mid \sum_{i=h-s+1}^{h} d(p_{i-1}, p_i) \leq AT \}, \quad
        b := \max\{u = 2, \cdots, h \mid \sum_{i=1}^{u-1} d(p_i, p_{i+1}) \leq AT \}.
        \]
        \IF{$a \leq b$}
            \STATE For each $i \in [a, b]$ and each recharge station $c$ reachable from $p_i$, calculate the minimum amount of recharge needed to complete the route $(p_1, \cdots, p_i, c, p_{i+1}, \cdots, p_h)$, using the cheapest technology available verifying the maximum duration constraint. Choose the cheapest alternative and update $r'$.
        \ENDIF
    \ENDIF
\ENDFOR
\end{algorithmic}
\end{algorithm}
"""

class RechargeRealocation:
    def __init__(self, instance: Instance):
        self.instance = instance

    def perturbation(self, solution: 'Solution') -> bool:
        """
        Apply recharge relocation to optimize recharge station placement in routes.
        
        Args:
            solution: The solution to optimize
            
        Returns:
            bool: True if any improvement was made, False otherwise
        """
        improved = False
        
        for route in solution.routes:
            if self._optimize_route(route):
                improved = True
        
        if improved:
            # Re-evaluate the entire solution to ensure all routes are feasible
            solution.evaluate()
            
            # Double-check that the solution is still feasible after all modifications
            if not solution.is_feasible:
                print("Warning: Recharge relocation made solution infeasible")
        
        return solution

    def local_search(self, solution: 'Solution') -> bool:
        """
        Apply recharge relocation to optimize recharge station placement in routes.
        
        Args:
            solution: The solution to optimize
            
        Returns:
            bool: True if any improvement was made, False otherwise
        """
        improved = False
        
        for route in solution.routes:
            if self._optimize_route(route):
                improved = True
        
        if improved:
            # Re-evaluate the entire solution to ensure all routes are feasible
            solution.evaluate()
            
            # Double-check that the solution is still feasible after all modifications
            if not solution.is_feasible:
                print("Warning: Recharge relocation made solution infeasible")
        
        return improved
    
    def _optimize_route(self, route: Route) -> bool:
        """
        Optimize a single route by relocating recharge stations.
        
        Args:
            route: The route to optimize
            
        Returns:
            bool: True if the route was improved, False otherwise
        """
        # Extract customer sequence (excluding recharge stations)
        customer_sequence = self._extract_customer_sequence(route)
        
        if len(customer_sequence) < 3:  # Need at least depot, customer, depot
            return False
        
        # Calculate total distance between consecutive customers
        total_distance = self._calculate_total_distance(customer_sequence)
        
        # AT is the maximum range (battery capacity / consumption rate)
        AT = self.instance.vehicle.max_range
        
        if total_distance <= AT:
            for idx, node in enumerate(route.nodes):
                if node.type == NodeType.STATION:
                    route.nodes.remove(node)
                    route.charging_decisions.pop(node.id)
                    route.evaluate(self.instance)
                    if not route.is_feasible:
                        route.nodes.insert(idx, node)
                        route.charging_decisions[node.id] = (node.technologies[0], node.technologies[0].power)
                        route.evaluate(self.instance)
                        return False
                    return True
            return False 
        
        a, b = self._find_recharge_interval(customer_sequence, AT)
        
        if a > b:
            return False
        
        best_improvement = self._find_best_recharge_option(customer_sequence, a, b, route)
        
        if best_improvement:
            # Apply the optimization
            self._apply_recharge_optimization(route, customer_sequence, best_improvement)
            
            # Verify that the modified route is still feasible
            if not self._verify_route_feasibility(route):
                # If not feasible, revert the changes
                self._revert_recharge_optimization(route, customer_sequence, best_improvement)
                return False
            
            return True
        
        return False
    
    def _extract_customer_sequence(self, route: Route) -> List[Node]:
        """Extract the sequence of customers (including depot) from a route, excluding recharge stations."""
        sequence = []
        for node in route.nodes:
            if node.type in [NodeType.CUSTOMER, NodeType.DEPOT]:
                sequence.append(node)
        return sequence
    
    def _calculate_total_distance(self, customer_sequence: List[Node]) -> float:
        """Calculate the total distance between consecutive customers in the sequence."""
        total_distance = 0
        for i in range(len(customer_sequence) - 1):
            from_node = customer_sequence[i]
            to_node = customer_sequence[i + 1]
            total_distance += self.instance.distance_matrix[from_node.id][to_node.id]
        return total_distance
    
    def _find_recharge_interval(self, customer_sequence: List[Node], AT: float) -> Tuple[int, int]:
        """
        Find the interval [a, b] where a recharge station can be optimally placed.
        
        Args:
            customer_sequence: Sequence of customers (including depot)
            AT: Maximum range (battery capacity / consumption rate)
            
        Returns:
            Tuple[int, int]: The interval [a, b] where a <= b indicates feasible placement
        """
        h = len(customer_sequence)
        
        # Find 'a': minimum s such that sum from h-s+1 to h <= AT
        a = h
        cumulative_distance = 0
        for s in range(1, h):
            cumulative_distance += self.instance.distance_matrix[customer_sequence[h-s-1].id][customer_sequence[h-s].id]
            if cumulative_distance <= AT:
                a = h - s
                break
        
        # Find 'b': maximum u such that sum from 1 to u-1 <= AT
        b = 1
        cumulative_distance = 0
        for u in range(2, h + 1):
            cumulative_distance += self.instance.distance_matrix[customer_sequence[u-2].id][customer_sequence[u-1].id]
            if cumulative_distance <= AT:
                b = u
            else:
                break
        
        return a, b
    
    def _find_best_recharge_option(self, customer_sequence: List[Node], a: int, b: int, route: Route) -> dict:
        """
        Find the best recharge station and technology for the given interval.
        
        Args:
            customer_sequence: Sequence of customers (including depot)
            a, b: The interval [a, b] for recharge placement
            route: The current route
            
        Returns:
            dict: Best recharge option with station, position, technology, and energy, or None if not found
        """
        best_option = None
        best_cost = float('inf')
        
        # Check each position in the interval [a, b]
        for i in range(a, b + 1):
            if i >= len(customer_sequence) - 1:
                continue
                
            # Check each recharge station
            for station in self.instance.stations:
                # Check if station is reachable from position i
                if not self._is_station_reachable(customer_sequence, i, station):
                    continue
                
                # Check each available technology
                for tech in station.technologies:
                    # Calculate minimum energy needed
                    min_energy = self._calculate_min_energy_needed(customer_sequence, i, station)
                    
                    if min_energy is None:
                        continue
                    
                    # Check if this option is feasible and cheaper
                    option_cost = min_energy * tech.cost_per_kwh
                    
                    if option_cost < best_cost:
                        # Verify time constraint
                        if self._verify_time_constraint(customer_sequence, i, station, tech, min_energy):
                            best_option = {
                                'station': station,
                                'position': i,
                                'technology': tech,
                                'energy': min_energy
                            }
                            best_cost = option_cost
        
        return best_option
    
    def _is_station_reachable(self, customer_sequence: List[Node], position: int, station: 'Station') -> bool:
        """Check if a recharge station is reachable from a given position."""
        if position >= len(customer_sequence) - 1:
            return False
        
        # Check if we can reach the station from the current position
        current_node = customer_sequence[position]
        next_node = customer_sequence[position + 1]
        
        # Calculate distances
        dist_to_station = self.instance.distance_matrix[current_node.id][station.id]
        dist_from_station = self.instance.distance_matrix[station.id][next_node.id]
        
        # Check if the detour is reasonable (not too long)
        direct_distance = self.instance.distance_matrix[current_node.id][next_node.id]
        detour_distance = dist_to_station + dist_from_station
        
        # Allow some reasonable detour (e.g., 50% more than direct)
        return detour_distance <= direct_distance * 1.5
    
    def _calculate_min_energy_needed(self, customer_sequence: List[Node], position: int, station: 'Station') -> float:
        """
        Calculate the minimum energy needed to complete the route after visiting the recharge station.
        
        Args:
            customer_sequence: Sequence of customers (including depot)
            position: Position where recharge station would be inserted
            station: The recharge station
            
        Returns:
            float: Minimum energy needed, or None if not feasible
        """
        # Simulate the route with the recharge station
        # Calculate energy consumption from station to end
        energy_consumed = 0
        current_node = station
        
        for i in range(position + 1, len(customer_sequence)):
            next_node = customer_sequence[i]
            distance = self.instance.distance_matrix[current_node.id][next_node.id]
            energy_consumed += distance * self.instance.vehicle.consumption_rate
            current_node = next_node
        
        # Check if this energy consumption is within battery capacity
        if energy_consumed > self.instance.vehicle.battery_capacity:
            return None
        
        # Also check if we can reach the station from the start with current battery
        # Calculate energy needed from start to station
        energy_to_station = 0
        current_node = customer_sequence[0]  # Start from depot
        
        for i in range(1, position + 1):
            next_node = customer_sequence[i]
            distance = self.instance.distance_matrix[current_node.id][next_node.id]
            energy_to_station += distance * self.instance.vehicle.consumption_rate
            current_node = next_node
        
        # Check if we can reach the station
        if energy_to_station > self.instance.vehicle.battery_capacity:
            return None
        
        return energy_consumed
    
    def _verify_time_constraint(self, customer_sequence: List[Node], position: int, station: 'Station', 
                               technology: 'Technology', energy: float) -> bool:
        """
        Verify that adding the recharge station doesn't violate time constraints.
        
        Args:
            customer_sequence: Sequence of customers (including depot)
            position: Position where recharge station would be inserted
            station: The recharge station
            technology: The charging technology
            energy: Energy to be charged
            
        Returns:
            bool: True if time constraint is satisfied, False otherwise
        """
        # Calculate additional time for the detour and charging
        current_node = customer_sequence[position]
        next_node = customer_sequence[position + 1]
        
        # Time for detour
        direct_time = self.instance.time_matrix[current_node.id][next_node.id]
        detour_time = (self.instance.time_matrix[current_node.id][station.id] + 
                      self.instance.time_matrix[station.id][next_node.id])
        
        # Additional travel time
        additional_travel_time = detour_time - direct_time
        
        # Charging time
        charging_time = energy / technology.power
        total_additional_time = additional_travel_time + self.instance.charging_fixed_time + charging_time
        
        # Check if this additional time would exceed the maximum route duration
        # We need to estimate the current route time and add the additional time
        estimated_current_time = self._estimate_route_time(customer_sequence)
        total_time = estimated_current_time + total_additional_time
        
        return total_time <= self.instance.max_route_duration
    
    def _estimate_route_time(self, customer_sequence: List[Node]) -> float:
        """Estimate the total time for the customer sequence."""
        total_time = 0
        
        for i in range(len(customer_sequence) - 1):
            from_node = customer_sequence[i]
            to_node = customer_sequence[i + 1]
            
            # Travel time
            total_time += self.instance.time_matrix[from_node.id][to_node.id]
            
            # Service time for customers
            if to_node.type == NodeType.CUSTOMER:
                total_time += to_node.service_time
        
        return total_time
    
    def _apply_recharge_optimization(self, route: Route, customer_sequence: List[Node], 
                                   recharge_option: dict) -> None:
        """
        Apply the recharge optimization to the route.
        
        Args:
            route: The route to modify
            customer_sequence: Sequence of customers (including depot)
            recharge_option: The best recharge option found
        """
        station = recharge_option['station']
        position = recharge_option['position']
        technology = recharge_option['technology']
        energy = recharge_option['energy']
        
        # Find the actual position in the route nodes
        route_position = self._find_route_position(route, customer_sequence[position])
        
        if route_position == -1:
            return
        
        # Insert the recharge station
        route.nodes.insert(route_position + 1, station)
        
        # Update charging decisions
        route.charging_decisions[station.id] = (technology, energy)
        
        # Clear the route evaluation to force re-evaluation
        route.total_distance = 0
        route.total_cost = 0
        route.total_time = 0
        route.is_feasible = False  # Don't assume feasibility until verified
    
    def _find_route_position(self, route: Route, target_node: Node) -> int:
        """Find the position of a target node in the route."""
        for i, node in enumerate(route.nodes):
            if node.id == target_node.id:
                return i
        return -1
    
    def _verify_route_feasibility(self, route: Route) -> bool:
        """
        Verify that a route is feasible after modification.
        This checks all constraints: battery, capacity, time, and structure.
        
        Args:
            route: The route to verify
            
        Returns:
            bool: True if the route is feasible, False otherwise
        """
        if not route.nodes:
            return False
        
        # Check route structure (must start and end at depot)
        depot_id = next((n.id for n in self.instance.nodes if n.type == NodeType.DEPOT), None)
        if depot_id is None or route.nodes[0].id != depot_id or route.nodes[-1].id != depot_id:
            return False
        
        # Simulate the route to check all constraints
        current_battery = self.instance.vehicle.battery_capacity
        current_load = 0
        current_time = 0
        prev_node_id = depot_id
        
        for i, node in enumerate(route.nodes[1:], 1):
            node_id = node.id
            
            # Check travel distance and energy consumption
            travel_dist = self.instance.distance_matrix[prev_node_id][node_id]
            travel_time = self.instance.time_matrix[prev_node_id][node_id]
            energy_consumed = travel_dist * self.instance.vehicle.consumption_rate
            
            # Check battery constraint
            if current_battery < energy_consumed:
                return False
            
            current_battery -= energy_consumed
            current_time += travel_time
            
            # Handle customer or recharge station
            if node.type == NodeType.CUSTOMER:
                current_load += node.demand
                current_time += node.service_time
                
                # Check capacity constraint
                if current_load > self.instance.vehicle.capacity:
                    return False
                    
            elif node.type == NodeType.STATION:
                if node_id in route.charging_decisions:
                    tech, energy_to_charge = route.charging_decisions[node_id]
                    
                    # Check if technology is available at this station
                    tech_found = any(t.id == tech.id for t in node.technologies)
                    if not tech_found:
                        return False
                    
                    # Apply charging
                    charging_time = energy_to_charge / tech.power
                    current_time += self.instance.charging_fixed_time + charging_time
                    current_battery = min(current_battery + energy_to_charge, self.instance.vehicle.battery_capacity)
            
            prev_node_id = node_id
        
        # Check time constraint
        if current_time > self.instance.max_route_duration:
            return False
        
        return True
    
    def _revert_recharge_optimization(self, route: Route, customer_sequence: List[Node], 
                                    recharge_option: dict) -> None:
        """
        Revert the recharge optimization if it made the route infeasible.
        
        Args:
            route: The route to revert
            customer_sequence: Sequence of customers (including depot)
            recharge_option: The recharge option that was applied
        """
        station = recharge_option['station']
        position = recharge_option['position']
        
        # Find and remove the inserted recharge station
        route_position = self._find_route_position(route, customer_sequence[position])
        if route_position != -1:
            # Remove the recharge station
            if route_position + 1 < len(route.nodes) and route.nodes[route_position + 1].id == station.id:
                route.nodes.pop(route_position + 1)
            
            # Remove charging decision
            if station.id in route.charging_decisions:
                del route.charging_decisions[station.id]
        
        # Reset route evaluation
        route.total_distance = 0
        route.total_cost = 0
        route.total_time = 0
        route.is_feasible = False