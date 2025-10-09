import copy
import random
from typing import List, TYPE_CHECKING
from EVRP.classes.instance import Instance
from EVRP.classes.node import NodeType
from EVRP.classes.route import Route

if TYPE_CHECKING:
    from EVRP.solution import Solution

class DepotReassignment:
    """
    Depot Reassignment shake operator that reassigns k random routes to different depots.
    This operator helps diversify the search by changing the depot assignments of routes,
    which can lead to different route structures and potentially better solutions.
    """
    
    def __init__(self, instance: Instance, k: int = 2):
        """
        Initialize the depot reassignment operator.
        
        Args:
            instance: The EVRP instance
            k: Number of random routes to reassign to different depots
        """
        self.instance = instance
        self.k = k

    def local_search(self, solution: 'Solution') -> bool:
        """
        Depot reassignment is primarily a shake operator, not a local search operator.
        This method returns False as it's not designed for local improvement.
        
        Args:
            solution: The solution to improve
            
        Returns:
            bool: Always False as this is a shake operator
        """
        return False

    def perturbation(self, solution: 'Solution') -> 'Solution':
        """
        Apply depot reassignment perturbation to diversify the solution.
        Reassigns k random routes to different depots.
        
        Args:
            solution: The solution to perturb
            
        Returns:
            Solution: The perturbed solution
        """
        if not solution.routes or len(solution.routes) < 2:
            return solution
            
        # Create a deep copy of the solution
        perturbed_solution = copy.deepcopy(solution)
        
        # Select k random routes to reassign (without replacement)
        routes_to_reassign = random.sample(
            perturbed_solution.routes, 
            min(self.k, len(perturbed_solution.routes))
        )
        
        for route in routes_to_reassign:
            self._reassign_route_to_different_depot(route)
        
        # Re-evaluate the perturbed solution
        perturbed_solution.evaluate()
        
        return perturbed_solution

    def _reassign_route_to_different_depot(self, route: Route) -> None:
        """
        Try to reassign a route to a different pair of depots by changing
        the start and end depot nodes. Keep the change only if the route
        remains feasible after evaluation.

        Args:
            route: The route to reassign
        """
        if not route.nodes or len(route.nodes) < 2:
            return

        original_start = route.nodes[0]
        original_end = route.nodes[-1]
        
        # Store original state for restoration
        original_charging = route.charging_decisions.copy()
        
        # Find available depots (different from current ones)
        available_start_depots = [
            depot for depot in self.instance.depots
            if depot.id != original_start.id
        ]

        available_end_depots = [
            depot for depot in self.instance.depots
            if depot.id != original_end.id
        ]

        if not available_start_depots or not available_end_depots:
            return
        
        random.shuffle(available_start_depots)
        random.shuffle(available_end_depots)

        # Try different depot combinations
        for new_start in available_start_depots:
            for new_end in available_end_depots:
                # Update depot nodes
                route.nodes[0] = new_start
                route.nodes[-1] = new_end

                # Update charging decisions
                route.charging_decisions = original_charging.copy()
                
                # Remove charging decisions for original depots
                if original_start.id in route.charging_decisions:
                    del route.charging_decisions[original_start.id]
                if original_end.id in route.charging_decisions:
                    del route.charging_decisions[original_end.id]
                
                # Add charging decisions for new depots
                route.charging_decisions[new_start.id] = (
                    self.instance.technologies[0],
                    self.instance.vehicle.battery_capacity
                )
                route.charging_decisions[new_end.id] = (
                    self.instance.technologies[0],
                    self.instance.vehicle.battery_capacity
                )

                # Evaluate feasibility
                route.evaluate(self.instance)
                if route.is_feasible:
                    return  # Success - keep the changes

        # If no feasible reassignment found, restore original state
        route.nodes[0] = original_start
        route.nodes[-1] = original_end
        route.charging_decisions = original_charging
        route.evaluate(self.instance)


    def _get_route_depot(self, route: Route):
        """
        Get the depot assigned to a route.
        
        Args:
            route: The route to check
            
        Returns:
            Depot: The depot assigned to the route, or None if invalid
        """
        if not route.nodes or len(route.nodes) < 2:
            return None
            
        # First and last nodes should be depots
        if (route.nodes[0].type != NodeType.DEPOT or 
            route.nodes[-1].type != NodeType.DEPOT):
            return None
            
        return route.nodes[0]

    def _is_valid_depot_reassignment(self, route: Route, new_depot) -> bool:
        """
        Check if reassigning a route to a new depot is valid.
        
        Args:
            route: The route to check
            new_depot: The new depot to assign
            
        Returns:
            bool: True if the reassignment is valid
        """
        if not route.nodes or len(route.nodes) < 2:
            return False
            
        # Check if new depot is different from current
        current_depot = route.nodes[0]
        if current_depot.id == new_depot.id:
            return False
            
        # Check if new depot has required technology
        if not new_depot.technologies:
            return False
            
        return True

    def _calculate_depot_distance_impact(self, route: Route, new_depot) -> float:
        """
        Calculate the distance impact of reassigning a route to a new depot.
        
        Args:
            route: The route to analyze
            new_depot: The new depot to assign
            
        Returns:
            float: The distance difference (positive means increase)
        """
        if not route.nodes or len(route.nodes) < 3:
            return 0.0
            
        current_depot = route.nodes[0]
        
        # Calculate current total distance
        current_distance = 0.0
        prev_node = current_depot
        for node in route.nodes[1:]:
            current_distance += self.instance.distance_matrix[prev_node.id][node.id]
            prev_node = node
        
        # Calculate new total distance with new depot
        new_distance = 0.0
        prev_node = new_depot
        for node in route.nodes[1:]:
            new_distance += self.instance.distance_matrix[prev_node.id][node.id]
            prev_node = node
        
        return new_distance - current_distance
