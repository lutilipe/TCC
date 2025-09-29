from typing import List, Tuple, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import Node, NodeType
from EVRP.classes.route import Route
from EVRP.classes.station import Station
from EVRP.classes.technology import Technology

if TYPE_CHECKING:
    from EVRP.solution import Solution

class RechargeRealocation:
    def __init__(self, instance: Instance):
        self.instance = instance

    def local_search(self, solution: 'Solution') -> bool:
        improved = False
        
        for route in solution.routes:
            if self._optimize_route(route):
                improved = True
        
        if improved:
            solution.evaluate()
            
            if not solution.is_feasible:
                print("Warning: Recharge relocation made solution infeasible")
        
        return improved
    
    def _optimize_route(self, route: Route) -> bool:
        customer_sequence = self._extract_customer_sequence(route)
        
        if len(customer_sequence) < 3: 
            return False
        
        original_cost = route.total_cost
        original_distance = route.total_distance
        
        total_distance = self._calculate_total_distance(customer_sequence)
        
        AT = self.instance.vehicle.max_range

        if total_distance <= AT:
            stations_to_remove = []
            for idx, node in enumerate(route.nodes):
                if node.type == NodeType.STATION:
                    stations_to_remove.append((idx, node))
            
            if not stations_to_remove:
                return False
            
            for original_idx, station_node in stations_to_remove:
                route.nodes.remove(station_node)
                if station_node.id in route.charging_decisions:
                    route.charging_decisions.pop(station_node.id)
            
            route.evaluate(self.instance)
            
            if not route.is_feasible:
                for original_idx, station_node in reversed(stations_to_remove):
                    route.nodes.insert(original_idx, station_node)
                    route.charging_decisions[station_node.id] = (station_node.technologies[0], station_node.technologies[0].power)
                route.evaluate(self.instance)
                return False
            else:
                improvement = (route.total_cost < original_cost or 
                              route.total_distance < original_distance)
                return improvement
        
        a, b = self._find_recharge_interval(customer_sequence, AT)
        if a > b:
            return False
        
        best_improvement = self._find_best_recharge_option(customer_sequence, a, b, route)
        
        if best_improvement:
            self._apply_recharge_optimization(route, customer_sequence, best_improvement)
            route.evaluate(self.instance)
            
            if not route.is_feasible:
                self._revert_recharge_optimization(route, customer_sequence, best_improvement)
                route.evaluate(self.instance)
                return False
            
            improvement = (route.total_cost < original_cost or 
                          route.total_distance < original_distance)
            return improvement
        
        return False
    
    def _extract_customer_sequence(self, route: Route) -> List[Node]:
        sequence = []
        for node in route.nodes:
            if node.type in [NodeType.CUSTOMER, NodeType.DEPOT]:
                sequence.append(node)
        return sequence
    
    def _calculate_total_distance(self, customer_sequence: List[Node]) -> float:
        total_distance = 0
        for i in range(len(customer_sequence) - 1):
            from_node = customer_sequence[i]
            to_node = customer_sequence[i + 1]
            total_distance += self.instance.distance_matrix[from_node.id][to_node.id]
        return total_distance
    
    def _find_recharge_interval(self, customer_sequence: List[Node], AT: float) -> Tuple[int, int]:
        h = len(customer_sequence)
        
        a = h
        for start_segment in range(1, h-1):
            cumulative_distance = 0
            for i in range(start_segment, h):
                cumulative_distance += self.instance.distance_matrix[customer_sequence[i-1].id][customer_sequence[i].id]
            
            if cumulative_distance <= AT:
                a = start_segment
                break
            
        
        b = 1
        for start_segment in range(2, h):
            cumulative_distance = 0
            for i in range(1, start_segment):
                cumulative_distance += self.instance.distance_matrix[customer_sequence[i].id][customer_sequence[i+1].id]
            
            if cumulative_distance <= AT:
                b = start_segment
        
        if a > b:
            return h, 0  # Return invalid interval
        
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
        
        for i in range(a, b + 1):
            if i >= len(customer_sequence) - 1:
                continue
                
            for station in self.instance.stations:
                if not self._is_station_reachable(customer_sequence, i, station):
                    continue
                
                for tech in station.technologies:
                    min_energy = self._calculate_min_energy_needed(customer_sequence, i, station)
                    
                    if min_energy is None:
                        continue
                    
                    option_cost = min_energy * tech.cost_per_kwh
                    
                    if option_cost < best_cost:
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
        
        current_node = customer_sequence[position]
        next_node = customer_sequence[position + 1]
        
        dist_to_station = self.instance.distance_matrix[current_node.id][station.id]
        dist_from_station = self.instance.distance_matrix[station.id][next_node.id]
        
        direct_distance = self.instance.distance_matrix[current_node.id][next_node.id]
        detour_distance = dist_to_station + dist_from_station
        
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