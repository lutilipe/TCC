import random
from typing import Dict, List, Tuple, Optional
from EVRP.classes.customer import Customer
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.classes.route import Route
from EVRP.classes.station import Station
from EVRP.classes.depot import Depot
from EVRP.classes.technology import Technology
from EVRP.classes.vehicle import Vehicle
from EVRP.solution import Solution

class ConstructiveHeuristic:
    def __init__(self, instance: Instance, k: int = 5):
        self.instance = instance
        self.k = k
        self.closest_customers_cache = {}
        self.closest_stations_cache = {}
        
        self.customers = {}
        self.stations = {}
        self.depot = None
        
        for node in instance.nodes:
            if node.type == NodeType.CUSTOMER:
                self.customers[node.id] = node
            elif node.type == NodeType.STATION:
                self.stations[node.id] = node
            elif node.type == NodeType.DEPOT:
                self.depot = node
        
    def _precompute_closest_lists(self):
        all_node_ids = [node.id for node in self.instance.nodes]
        
        for node_id in all_node_ids:
            customer_distances = []
            for cust_id, customer in self.customers.items():
                if cust_id != node_id:
                    dist = self.instance.distance_matrix[node_id][cust_id]
                    customer_distances.append((dist, customer))
            customer_distances.sort(key=lambda x: x[0])
            self.closest_customers_cache[node_id] = [customer for _, customer in customer_distances]
            
            station_distances = []
            for station_id, station in self.stations.items():
                if station_id != node_id:
                    dist = self.instance.distance_matrix[node_id][station_id]
                    station_distances.append((dist, station))
            station_distances.sort(key=lambda x: x[0])
            self.closest_stations_cache[node_id] = [station for _, station in station_distances]
    
    def _can_reach_directly(self, from_id: int, to_id: int, current_battery: float, 
                           current_load: float, current_time: float) -> bool:
        """Check if we can reach destination directly without violating any constraint"""
        # Check capacity constraint if destination is customer
        additional_demand = 0
        service_time = 0
        
        if to_id in self.customers:
            additional_demand = self.customers[to_id].demand
            service_time = self.customers[to_id].service_time
            
            if current_load + additional_demand > self.instance.vehicle.capacity:
                return False
        
        # Check battery constraint
        distance = self.instance.distance_matrix[from_id][to_id]
        energy_needed = distance * self.instance.vehicle.consumption_rate
        if current_battery < energy_needed:
            return False
            
        # Check time constraint
        travel_time = self.instance.time_matrix[from_id][to_id]
        new_time = current_time + travel_time + service_time
        
        if new_time > self.instance.max_route_duration:
            return False
            
        return True
    
    def _can_reach_depot_via_station(self, from_id: int, station_id: int, current_battery: float, 
                                   current_load: float, current_time: float) -> bool:
        """Check if we can reach depot via a specific recharge station"""
        # Check if we can reach the station
        if not self._can_reach_directly(from_id, station_id, current_battery, current_load, current_time):
            return False
            
        # Calculate state at station (after travel)
        dist_to_station = self.instance.distance_matrix[from_id][station_id]
        energy_to_station = dist_to_station * self.instance.vehicle.consumption_rate
        time_to_station = self.instance.time_matrix[from_id][station_id]
        
        battery_at_station = current_battery - energy_to_station
        time_at_station = current_time + time_to_station
        
        # Get available technologies at station
        if station_id == self.depot.id and self.depot.technologies:
            available_techs = self.depot.technologies
        elif station_id in self.stations:
            available_techs = self.stations[station_id].technologies
        else:
            return False
        
        if not available_techs:
            return False
            
        # Try each technology to see if any allows reaching depot
        for tech in available_techs:
            # Calculate maximum feasible recharge considering time constraint
            max_time_for_recharge = self.instance.max_route_duration - time_at_station - self.instance.charging_fixed_time
            if max_time_for_recharge <= 0:
                continue
                
            max_energy_by_time = max_time_for_recharge * tech.power
            max_energy_by_capacity = self.instance.vehicle.battery_capacity - battery_at_station
            
            energy_to_recharge = min(max_energy_by_time, max_energy_by_capacity)
            if energy_to_recharge <= 0:
                continue
                
            battery_after_recharge = battery_at_station + energy_to_recharge
            recharge_time = energy_to_recharge / tech.power
            time_after_recharge = time_at_station + self.instance.charging_fixed_time + recharge_time
            
            # Check if we can reach depot with this recharge
            if self._can_reach_directly(station_id, self.depot.id, battery_after_recharge, 
                                      current_load, time_after_recharge):
                return True
                
        return False
    
    def _find_best_recharge_station_to_depot(self, from_id: int, current_battery: float, 
                                           current_load: float, current_time: float) -> Optional[Tuple[Station, Technology, float]]:
        """Find the best recharge station to reach depot from current position"""
        recharge_locations = list(self.stations.values())
        if self.depot and self.depot.technologies:
            recharge_locations.append(self.depot)
            
        # Sort by distance from current position (closest first)
        recharge_distances = []
        for node in recharge_locations:
            dist = self.instance.distance_matrix[from_id][node.id]
            recharge_distances.append((dist, node))
        recharge_distances.sort(key=lambda x: x[0])
        
        for _, station in recharge_distances:
            if not self._can_reach_depot_via_station(from_id, station.id, current_battery, current_load, current_time):
                continue
                
            # Calculate optimal recharge at this station
            dist_to_station = self.instance.distance_matrix[from_id][station.id]
            energy_to_station = dist_to_station * self.instance.vehicle.consumption_rate
            time_to_station = self.instance.time_matrix[from_id][station.id]
            
            battery_at_station = current_battery - energy_to_station
            time_at_station = current_time + time_to_station
            
            # Get available technologies
            if station.id == self.depot.id:
                available_techs = self.depot.technologies
            else:
                available_techs = self.stations[station.id].technologies
            
            # Find best technology and recharge amount
            best_option = None
            min_cost = float('inf')
            
            for tech in available_techs:
                # Calculate maximum feasible recharge
                max_time_for_recharge = self.instance.max_route_duration - time_at_station - self.instance.charging_fixed_time
                if max_time_for_recharge <= 0:
                    continue
                    
                max_energy_by_time = max_time_for_recharge * tech.power
                max_energy_by_capacity = self.instance.vehicle.battery_capacity - battery_at_station
                
                # Find minimum energy needed to reach depot
                energy_to_depot = self.instance.distance_matrix[station.id][self.depot.id] * self.instance.vehicle.consumption_rate
                min_energy_needed = max(0, energy_to_depot - battery_at_station)
                
                # Recharge amount should be at least minimum needed, but not exceed limits
                energy_to_recharge = min(max_energy_by_time, max_energy_by_capacity)
                energy_to_recharge = max(energy_to_recharge, min_energy_needed)
                
                if energy_to_recharge < min_energy_needed:
                    continue
                    
                recharge_time = energy_to_recharge / tech.power
                time_after_recharge = time_at_station + self.instance.charging_fixed_time + recharge_time
                battery_after_recharge = battery_at_station + energy_to_recharge
                
                # Verify we can reach depot
                if self._can_reach_directly(station.id, self.depot.id, battery_after_recharge, 
                                          current_load, time_after_recharge):
                    cost = energy_to_recharge * tech.cost_per_kwh
                    if cost < min_cost:
                        min_cost = cost
                        best_option = (station, tech, energy_to_recharge)
            
            if best_option:
                return best_option
                
        return None
    
    def _get_k_closest_feasible_customers(self, current_pos: int, visited: set, route: Route) -> List[Customer]:
        """Get up to k closest unvisited customers that are reachable according to capacity, autonomy and time"""
        feasible_customers = []
        
        if current_pos not in self.closest_customers_cache:
            return []
            
        for customer in self.closest_customers_cache[current_pos]:
            if customer in visited:
                continue
                
            # Check if customer is reachable and we can still reach depot (directly or via station)
            if not self._can_reach_directly(current_pos, customer.id, route.current_battery, 
                                          route.current_load, route.current_time):
                continue
            
            # Calculate state after visiting customer
            distance_to_customer = self.instance.distance_matrix[current_pos][customer.id]
            energy_consumed = distance_to_customer * self.instance.vehicle.consumption_rate
            travel_time = self.instance.time_matrix[current_pos][customer.id]
            
            battery_after_customer = route.current_battery - energy_consumed
            load_after_customer = route.current_load + customer.demand
            time_after_customer = route.current_time + travel_time + customer.service_time
            
            # Check if we can reach depot directly or via station after visiting customer
            can_reach_depot = (self._can_reach_directly(customer.id, self.depot.id, 
                                                      battery_after_customer, load_after_customer, time_after_customer) or
                             self._find_best_recharge_station_to_depot(customer.id, battery_after_customer, 
                                                                      load_after_customer, time_after_customer) is not None)
            
            if can_reach_depot:
                feasible_customers.append(customer)
                if len(feasible_customers) >= self.k:
                    break
                    
        return feasible_customers
    
    def build_initial_solution(self) -> Solution:
        """k-PseudoGreedy Algorithm with guaranteed feasibility"""
        self._precompute_closest_lists()
        
        solution = Solution(self.instance)
        visited_customers = set()
        
        # Step 1: Initialize solution by setting h := 1 and i := 0
        h = 1  # route number
        
        # Step 13: until all customers are served
        while len(visited_customers) < len(self.customers):
            # Initialize new route h
            route = Route()
            route.nodes = [self.depot]
            route.current_battery = self.instance.vehicle.battery_capacity
            route.current_load = 0.0
            route.current_time = 0.0
            i = self.depot.id  # start from depot

            route.charging_decisions[self.depot.id] = (self.instance.technologies[0], route.current_battery)
            
            # Step 2: repeat
            while True:
                # Step 3: Find up to k unvisited customers that are closest to i and are reachable 
                feasible_customers = self._get_k_closest_feasible_customers(i, visited_customers, route)
                
                if not feasible_customers:
                    break  # No more feasible customers for this route
                    
                j = random.choice(feasible_customers)  # select customer j at random
                
                # Add customer j to route and update route state
                distance_to_customer = self.instance.distance_matrix[i][j.id]
                energy_consumed = distance_to_customer * self.instance.vehicle.consumption_rate
                travel_time = self.instance.time_matrix[i][j.id]
                
                route.nodes.append(j)
                route.current_battery -= energy_consumed
                route.current_load += j.demand
                route.current_time += travel_time + j.service_time
                visited_customers.add(j)
                i = j.id  # set current position to j
                
                # Step 4: if (it is possible to reach the depot directly from j) then
                if self._can_reach_directly(i, self.depot.id, route.current_battery, 
                                          route.current_load, route.current_time):
                    # Continue to next iteration to potentially add more customers
                    continue
                else:
                    # Step 7: if (it is possible to reach the depot from j by visiting a recharge node r in between) then
                    recharge_option = self._find_best_recharge_station_to_depot(i, route.current_battery, 
                                                                               route.current_load, route.current_time)
                    if recharge_option is not None:
                        station, tech, energy_to_recharge = recharge_option
                        
                        # Add station to route
                        route.nodes.append(station)
                        
                        # Move to recharge station
                        dist_to_station = self.instance.distance_matrix[i][station.id]
                        energy_to_station = dist_to_station * self.instance.vehicle.consumption_rate
                        time_to_station = self.instance.time_matrix[i][station.id]
                        
                        route.current_battery -= energy_to_station
                        route.current_time += time_to_station
                        
                        # Perform recharge
                        recharge_time = energy_to_recharge / tech.power
                        route.current_battery += energy_to_recharge
                        route.current_time += self.instance.charging_fixed_time + recharge_time
                        route.charging_decisions[station.id] = (tech, energy_to_recharge)
                        
                        i = station.id  # set i := station
                        continue  # Go back to step 2 (repeat)
                    else:
                        break
            
            route.nodes.append(self.depot)
            
            # Update final time and battery to depot
            if i != self.depot.id:  # if not already at depot
                final_distance = self.instance.distance_matrix[i][self.depot.id]
                final_energy = final_distance * self.instance.vehicle.consumption_rate
                final_time = self.instance.time_matrix[i][self.depot.id]
                
                route.current_battery -= final_energy
                route.current_time += final_time
            
            solution.routes.append(route)
            h += 1  # increment route number
            
            # Safety check - if we can't serve remaining customers with current vehicle fleet
            if len(solution.routes) >= self.instance.num_vehicles and len(visited_customers) < len(self.customers):
                print(f"Warning: Cannot serve all customers with {self.instance.num_vehicles} vehicles")
                break
        
        solution.evaluate()
        return solution