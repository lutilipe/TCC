import copy
import random
from typing import List, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class DepotReassignmentSame:
    """
    Depot Reassignment shake operator that reassigns k random routes to different depots.
    This operator helps diversify the search by changing the depot assignments of routes,
    which can lead to different route structures and potentially better solutions.
    
    The operator can be configured to allow different start and end depots for routes,
    providing more flexibility in route construction.
    """
    
    def __init__(self, instance: Instance, k: int = 2, allow_different_depots: bool = True):
        """
        Initialize the depot reassignment operator.
        
        Args:
            instance: The EVRP instance
            k: Number of random routes to reassign to different depots
            allow_different_depots: Whether to allow different start and end depots for routes
        """
        self.instance = instance
        self.k = k
        self.allow_different_depots = allow_different_depots

    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply depot reassignment perturbation to diversify the solution.
        Reassigns k random routes to different depots while ensuring feasibility.
        
        Args:
            solution: The solution to perturb
            
        Returns:
            Solution: The perturbed solution
        """
        if not solution.routes or len(solution.routes) < 2:
            return solution
            
        perturbed_solution = copy.deepcopy(solution)
        
        routes_to_reassign = random.sample(
            perturbed_solution.routes, 
            min(self.k, len(perturbed_solution.routes))
        )
        
        successful_reassignments = 0
        for route in routes_to_reassign:
            # Store original state before reassignment
            original_start_depot = route.nodes[0]
            original_end_depot = route.nodes[-1]
            
            self._reassign_route_to_different_depot(route)
            
            # Check if the reassignment was successful (route changed)
            if (route.nodes[0] != original_start_depot or 
                route.nodes[-1] != original_end_depot):
                successful_reassignments += 1
        
        # Evaluate the entire solution to ensure all routes are still feasible
        perturbed_solution.evaluate()
        
        # If the solution is not feasible, return the original solution
        if not perturbed_solution.is_feasible:
            return solution
        
        return perturbed_solution

    def _reassign_route_to_different_depot(self, route: Route) -> None:
        """
        Reassign a route to different depot(s) by changing the start and/or end depot nodes.
        Ensures the route remains feasible after reassignment.
        
        Args:
            route: The route to reassign
        """
        if not route.nodes or len(route.nodes) < 2:
            return
            
        # Store original state for rollback if needed
        original_start_depot = route.nodes[0]
        original_end_depot = route.nodes[-1]
        original_charging_decisions = route.charging_decisions.copy()
        
        current_start_depot = route.nodes[0]
        current_end_depot = route.nodes[-1]
        
        available_depots = [
            depot for depot in self.instance.depots 
            if depot.id != current_start_depot.id and depot.id != current_end_depot.id
        ]
        
        if not available_depots:
            return
        
        # Try different depot combinations until we find a feasible one
        max_attempts = min(10, len(available_depots) * 2)  # Limit attempts to avoid infinite loops
        
        for attempt in range(max_attempts):
            if self.allow_different_depots:
                new_start_depot = random.choice(available_depots)
                
                if len(available_depots) > 1 and random.random() < 0.5:
                    remaining_depots = [d for d in available_depots if d.id != new_start_depot.id]
                    if remaining_depots:
                        new_end_depot = random.choice(remaining_depots)
                    else:
                        new_end_depot = new_start_depot
                else:
                    new_end_depot = new_start_depot
            else:
                new_start_depot = random.choice(available_depots)
                new_end_depot = new_start_depot
            
            # Apply the depot changes temporarily
            route.nodes[0] = new_start_depot
            route.nodes[-1] = new_end_depot
            
            # Update charging decisions
            if current_start_depot.id in route.charging_decisions:
                del route.charging_decisions[current_start_depot.id]
            if current_end_depot.id in route.charging_decisions and current_end_depot.id != current_start_depot.id:
                del route.charging_decisions[current_end_depot.id]
            
            route.charging_decisions[new_start_depot.id] = (
                self.instance.technologies[0],
                self.instance.vehicle.battery_capacity
            )
            
            if new_end_depot.id != new_start_depot.id:
                route.charging_decisions[new_end_depot.id] = (
                    self.instance.technologies[0],
                    self.instance.vehicle.battery_capacity
                )
            
            # Check if the route is still feasible
            if self._is_route_feasible(route):
                return  # Success! Route is feasible with new depot assignment
            
            # If not feasible, rollback and try again
            route.nodes[0] = original_start_depot
            route.nodes[-1] = original_end_depot
            route.charging_decisions = original_charging_decisions.copy()
        
        # If we couldn't find a feasible depot assignment, keep original
        route.nodes[0] = original_start_depot
        route.nodes[-1] = original_end_depot
        route.charging_decisions = original_charging_decisions

    def _is_route_feasible(self, route: Route) -> bool:
        """
        Check if a route is feasible by evaluating it and checking constraints.
        
        Args:
            route: The route to check
            
        Returns:
            bool: True if the route is feasible, False otherwise
        """
        if not route.nodes or len(route.nodes) < 2:
            return False
        
        # Check basic structure constraints
        if (route.nodes[0].type != NodeType.DEPOT or 
            route.nodes[-1].type != NodeType.DEPOT):
            return False
        
        # Evaluate the route to check all constraints
        route.evaluate(self.instance)
        
        return route.is_feasible

    def _get_route_depot(self, route: Route):
        """
        Get the depot(s) assigned to a route.
        
        Args:
            route: The route to check
            
        Returns:
            tuple: (start_depot, end_depot) or None if invalid
        """
        if not route.nodes or len(route.nodes) < 2:
            return None
            
        if (route.nodes[0].type != NodeType.DEPOT or 
            route.nodes[-1].type != NodeType.DEPOT):
            return None
            
        return (route.nodes[0], route.nodes[-1])
