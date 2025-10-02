"""
EVRP-specific implementation of Pareto quality metrics.
Adapts the general ParetoMetrics class for Electric Vehicle Routing Problem solutions.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional, Dict
from scipy.spatial.distance import euclidean
import sys
import os

# Add parent directory to path to import from metrics.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from metrics import ParetoMetrics
from EVRP.solution import Solution
from EVRP.classes.instance import Instance


class EVRPMetrics(ParetoMetrics):
    """
    EVRP-specific implementation of Pareto quality metrics.
    
    For EVRP, we consider the following objectives:
    1. Distância Total (minimize)
    2. Custo Total (minimize)
    """
    
    def __init__(self):
        super().__init__()
        self.objective_names = ["Distância Total", "Custo Total"]
        self.objective_weights = [1.0, 1.0]  # Equal weights for now
    
    def solution_to_objectives(self, solution: Solution) -> np.ndarray:
        """
        Convert an EVRP Solution to objective array.
        
        Args:
            solution: EVRP Solution object
            
        Returns:
            np.ndarray: Array of shape (2,) with [distance, cost]
        """
        if not solution.is_feasible:
            # Return very large values for infeasible solutions
            return np.array([float('inf'), float('inf')])
        
        return np.array([
            solution.total_distance,
            solution.total_cost,
        ])
    
    def solutions_to_pareto_front(self, solutions: List[Solution]) -> np.ndarray:
        """
        Convert a list of EVRP solutions to Pareto front array.
        
        Args:
            solutions: List of EVRP Solution objects
            
        Returns:
            np.ndarray: Array of shape (n_solutions, 2) with objectives
        """
        if not solutions:
            return np.array([]).reshape(0, 2)
        
        objectives = []
        for solution in solutions:
            obj = self.solution_to_objectives(solution)
            objectives.append(obj)
        
        return np.array(objectives)
    
    def calculate_utopian_point(self, solutions: List[Solution]) -> np.ndarray:
        """
        Calculate utopian point from a set of solutions.
        For minimization: utopian = minimum value for each objective.
        
        Args:
            solutions: List of EVRP Solution objects
            
        Returns:
            np.ndarray: Utopian point of shape (2,)
        """
        if not solutions:
            return np.array([0.0, 0.0])
        
        pareto_front = self.solutions_to_pareto_front(solutions)
        
        feasible_mask = np.all(np.isfinite(pareto_front), axis=1)
        if not np.any(feasible_mask):
            return np.array([0.0, 0.0])
        
        feasible_front = pareto_front[feasible_mask]
        return np.min(feasible_front, axis=0)
    
    def calculate_nadir_point(self, solutions: List[Solution]) -> np.ndarray:
        """
        Calculate nadir point from a set of solutions.
        For minimization: nadir = maximum value for each objective.
        
        Args:
            solutions: List of EVRP Solution objects
            
        Returns:
            np.ndarray: Nadir point of shape (2,)
        """
        if not solutions:
            return np.array([1.0, 1.0])
        
        pareto_front = self.solutions_to_pareto_front(solutions)
        
        # Filter out infeasible solutions (infinite values)
        feasible_mask = np.all(np.isfinite(pareto_front), axis=1)
        if not np.any(feasible_mask):
            return np.array([1.0, 1.0])
        
        feasible_front = pareto_front[feasible_mask]
        return np.max(feasible_front, axis=0)
    
    def evaluate_solution_set(self, solutions: List[Solution]) -> Dict[str, float]:
        """
        Evaluate a set of EVRP solutions using Pareto quality metrics.
        
        Args:
            solutions: List of EVRP Solution objects
            
        Returns:
            Dict containing metric values
        """
        if not solutions:
            return {
                'spread_measure': 0.0,
                'hypervolume': 0.0,
                'num_solutions': 0,
                'num_feasible': 0
            }
        
        # Filter feasible solutions
        feasible_solutions = [sol for sol in solutions if sol.is_feasible]
        
        if len(feasible_solutions) < 2:
            return {
                'spread_measure': 0.0,
                'hypervolume': 0.0,
                'num_solutions': len(solutions),
                'num_feasible': len(feasible_solutions)
            }
        
        # Convert to Pareto front
        pareto_front = self.solutions_to_pareto_front(feasible_solutions)
        
        # Calculate reference points
        utopian = self.calculate_utopian_point(feasible_solutions)
        nadir = self.calculate_nadir_point(feasible_solutions)
        
        # Ensure nadir is strictly greater than utopian
        nadir = np.maximum(nadir, utopian * 1.1)
        
        # Calculate metrics
        spread = self.spread_measure(pareto_front, utopian, nadir)
        
        # For hypervolume, use nadir as reference point
        reference_point = nadir * 1.1  # Slightly worse than nadir
        hv = self.hypervolume(pareto_front, reference_point)
        
        return {
            'spread_measure': spread,
            'hypervolume': hv,
            'num_solutions': len(solutions),
            'num_feasible': len(feasible_solutions),
            'utopian_point': utopian,
            'nadir_point': nadir,
            'reference_point': reference_point
        }
    
    def plot_evrp_pareto_front(self, solutions: List[Solution], 
                              title: str = "Fronteira Pareto",
                              show_metrics: bool = True,
                              show_reference_points: bool = True) -> plt.Figure:
        """
        Plot EVRP Pareto front in 2D projections with nadir and utopic points.
        """
        feasible_solutions = [sol for sol in solutions if sol.is_feasible]
        
        if len(feasible_solutions) < 2:
            fig, ax = plt.subplots(1, 1, figsize=(8, 6))
            ax.text(0.5, 0.5, 'Not enough feasible solutions to plot', 
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title)
            return fig
        
        # Convert to objectives
        objectives = self.solutions_to_pareto_front(feasible_solutions)
        
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        ax.scatter(objectives[:, 0], objectives[:, 1], 
                c='blue', alpha=0.7, s=50, label='Soluções', zorder=3)
        
        if show_reference_points:
            metrics = self.evaluate_solution_set(solutions)
            utopian = metrics['utopian_point']
            nadir = metrics['nadir_point']
            
            ax.scatter(utopian[0], utopian[1], 
                    c='green', marker='*', s=200, 
                    label='Ponto Utopico', zorder=4, edgecolors='darkgreen', linewidth=2)
            
            ax.scatter(nadir[0], nadir[1], 
                    c='red', marker='*', s=200, 
                    label='Ponto Nadir', zorder=4, edgecolors='darkred', linewidth=2)
            
            # Bounding box
            ax.plot([utopian[0], nadir[0]], [utopian[1], utopian[1]], 'k--', alpha=0.5, linewidth=1)
            ax.plot([utopian[0], nadir[0]], [nadir[1], nadir[1]], 'k--', alpha=0.5, linewidth=1)
            ax.plot([utopian[0], utopian[0]], [utopian[1], nadir[1]], 'k--', alpha=0.5, linewidth=1)
            ax.plot([nadir[0], nadir[0]], [utopian[1], nadir[1]], 'k--', alpha=0.5, linewidth=1)
        
        ax.set_xlabel('Distância Total', fontsize=12)
        ax.set_ylabel('Custo Total', fontsize=12)
        ax.set_title('Distância x Custo', fontsize=14)
        
        # Legend outside plot
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=10, frameon=False)
        
        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        if show_metrics:
            metrics = self.evaluate_solution_set(solutions)
            metrics_text = f"""
            Spread Measure (Δ): {metrics['spread_measure']:.4f}
            Hypervolume (HV): {metrics['hypervolume']:.4f}
            Feasible Solutions: {metrics['num_feasible']}/{metrics['num_solutions']}
            """
            fig.text(0.02, 0.02, metrics_text, fontsize=10, 
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        plt.tight_layout(rect=[0, 0.05, 1, 1])  # leave space for legend
        return fig

    
    def track_convergence(self, archive_history: List[List[Solution]], 
                         iterations: List[int]) -> Dict[str, List[float]]:
        """
        Track convergence of metrics over iterations.
        
        Args:
            archive_history: List of solution archives at each iteration
            iterations: List of iteration numbers
            
        Returns:
            Dict with metric evolution over iterations
        """
        spread_values = []
        hv_values = []
        num_solutions = []
        num_feasible = []
        
        for archive in archive_history:
            metrics = self.evaluate_solution_set(archive)
            spread_values.append(metrics['spread_measure'])
            hv_values.append(metrics['hypervolume'])
            num_solutions.append(metrics['num_solutions'])
            num_feasible.append(metrics['num_feasible'])
        
        return {
            'iterations': iterations,
            'spread_measure': spread_values,
            'hypervolume': hv_values,
            'num_solutions': num_solutions,
            'num_feasible': num_feasible
        }
    
    def plot_convergence_evrp(self, convergence_data: Dict[str, List[float]], 
                             title: str = "EVRP Metrics Convergence") -> plt.Figure:
        """
        Plot convergence of EVRP metrics.
        
        Args:
            convergence_data: Data from track_convergence()
            title: Plot title
            
        Returns:
            matplotlib Figure object
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        iterations = convergence_data['iterations']
        
        # Spread Measure
        axes[0, 0].plot(iterations, convergence_data['spread_measure'], 
                       'b-', linewidth=2, marker='o', markersize=4)
        axes[0, 0].set_xlabel("Iteração")
        axes[0, 0].set_ylabel('Spread Measure (Δ)')
        axes[0, 0].set_title('Spread Measure Convergence')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Hypervolume
        axes[0, 1].plot(iterations, convergence_data['hypervolume'], 
                       'r-', linewidth=2, marker='s', markersize=4)
        axes[0, 1].set_xlabel("Iteração")
        axes[0, 1].set_ylabel('Hypervolume (HV)')
        axes[0, 1].set_title('Hypervolume Convergence')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Number of Solutions
        axes[1, 0].plot(iterations, convergence_data['num_solutions'], 
                       'g-', linewidth=2, marker='^', markersize=4, label='Total')
        axes[1, 0].plot(iterations, convergence_data['num_feasible'], 
                       'orange', linewidth=2, marker='v', markersize=4, label='Feasible')
        axes[1, 0].set_xlabel("Iteração")
        axes[1, 0].set_ylabel('Number of Solutions')
        axes[1, 0].set_title('Solution Count Evolution')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Combined metrics (normalized)
        ax_combined = axes[1, 1]
        
        # Normalize metrics to [0, 1] for comparison
        spread_norm = np.array(convergence_data['spread_measure'])
        hv_norm = np.array(convergence_data['hypervolume'])
        
        if len(spread_norm) > 0 and np.max(spread_norm) > 0:
            spread_norm = spread_norm / np.max(spread_norm)
        if len(hv_norm) > 0 and np.max(hv_norm) > 0:
            hv_norm = hv_norm / np.max(hv_norm)
        
        ax_combined.plot(iterations, spread_norm, 'b-', linewidth=2, 
                       marker='o', markersize=4, label='Spread (norm)')
        ax_combined.plot(iterations, hv_norm, 'r-', linewidth=2, 
                       marker='s', markersize=4, label='HV (norm)')
        ax_combined.set_xlabel("Iteração")
        ax_combined.set_ylabel('Normalized Metric Value')
        ax_combined.set_title('Normalized Metrics Comparison')
        ax_combined.legend()
        ax_combined.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
