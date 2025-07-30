import random
from typing import Dict, List
from EVRP.classes.customer import Customer
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.classes.route import Route
from EVRP.classes.station import Station
from EVRP.solution import Solution

class ConstructiveHeuristic:
    def __init__(self, instance: Instance):
        self.instance = instance
    
    def build_initial_solution(self, y=0.1) -> Solution:
        solution = Solution(self.instance)
        unvisited_customers: List[Customer] = [n for n in self.instance.nodes if n.type == NodeType.CUSTOMER]
        
        while unvisited_customers:
            route = Route()
            depot = self.instance.nodes[0]
            route.nodes.append(depot)
            current_position = 0
            current_battery = self.instance.vehicle.battery_capacity
            current_load = 0
            current_time = 0
            
            while unvisited_customers:
                best_customer = None
                best_score = float('inf')
                need_charging = False
                best_charging_plan = None
                
                for customer in unvisited_customers:
                    customer_id = customer.id
                    
                    if current_load + customer.demand > self.instance.vehicle.capacity:
                        continue
                    
                    dist_to_customer = self.instance.distance_matrix[current_position][customer_id]
                    dist_to_depot = self.instance.distance_matrix[customer_id][0]
                    energy_needed = (dist_to_customer + dist_to_depot) * self.instance.vehicle.consumption_rate
                    
                    charging_plan = None
                    if current_battery < energy_needed:
                        charging_plan = self._find_best_charging_station(
                            current_position, customer_id, current_battery, energy_needed
                        )
                        if not charging_plan:
                            continue
                    
                    score = dist_to_customer
                    if charging_plan:
                        score += charging_plan['additional_cost'] * 10
                    
                    if score < best_score:
                        best_score = score
                        best_customer = customer
                        best_charging_plan = charging_plan
                        need_charging = charging_plan is not None
                
                if best_customer is None:
                    break
                
                if need_charging and best_charging_plan:
                    station = best_charging_plan['station']
                    route.nodes.append(station)
                    route.charging_decisions[station.id] = (
                        best_charging_plan['tech'], 
                        best_charging_plan['energy_to_charge']
                    )
                    
                    current_battery = min(
                        current_battery + best_charging_plan['energy_to_charge'],
                        self.instance.vehicle.battery_capacity
                    )
                    current_position = station.id
                
                route.nodes.append(best_customer)
                
                travel_dist = self.instance.distance_matrix[current_position][best_customer.id]
                energy_consumed = travel_dist * self.instance.vehicle.consumption_rate
                current_battery -= energy_consumed
                current_load += customer.demand
                current_time += self.instance.time_matrix[current_position][best_customer.id] + customer.service_time
                current_position = best_customer.id
                
                unvisited_customers.remove(best_customer)
                
                if random.random() < y:
                    break
            
            route.nodes.append(depot)

            if route.nodes:
                solution.routes.append(route)
        
        solution.evaluate()
        return solution
    
    def _find_best_charging_station(self, current_pos: int, target_customer: int, 
                                   current_battery: float, energy_needed: float) -> Dict:
        best_plan = None
        best_cost = float('inf')

        charging_stations: List[Station] = [n for n in self.instance.nodes if n.type == NodeType.STATION]
        
        for station in charging_stations:
            station_id = station.id
            
            dist_to_station = self.instance.distance_matrix[current_pos][station_id]
            energy_to_station = dist_to_station * self.instance.vehicle.consumption_rate
            
            if current_battery < energy_to_station:
                continue
            
            battery_at_station = current_battery - energy_to_station
            
            dist_station_to_customer = self.instance.distance_matrix[station_id][target_customer]
            dist_customer_to_depot = self.instance.distance_matrix[target_customer][0]
            energy_from_station = (dist_station_to_customer + dist_customer_to_depot) * self.instance.vehicle.consumption_rate
            
            min_energy_required = energy_from_station
            energy_shortage = max(0, min_energy_required - battery_at_station)
            
            energy_to_charge = max(energy_shortage, 
                                 min(energy_needed * 0.8, self.instance.vehicle.battery_capacity - battery_at_station))
            
            if energy_to_charge > self.instance.vehicle.battery_capacity - battery_at_station:
                energy_to_charge = self.instance.vehicle.battery_capacity - battery_at_station
            
            if battery_at_station + energy_to_charge < min_energy_required:
                continue
            
            best_tech_cost = float('inf')
            best_tech = None
            
            for tech in station.technologies:
                if energy_to_charge > 0:
                    cost = energy_to_charge * tech.cost_per_kwh + self.instance.battery_depreciation_cost
                else:
                    cost = 0
                    
                if cost < best_tech_cost:
                    best_tech_cost = cost
                    best_tech = tech
            
            total_cost = best_tech_cost + dist_to_station * 0.1
            
            if total_cost < best_cost:
                best_cost = total_cost
                best_plan = {
                    'station': station,
                    'tech': best_tech,
                    'energy_to_charge': energy_to_charge,
                    'additional_cost': best_tech_cost
                }
        
        return best_plan
