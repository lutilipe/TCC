import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional
from scipy.spatial.distance import euclidean

class ParetoMetrics:
    """
    Implementation of quality metrics for Pareto frontiers:
    - Spread Measure (Δ): Measures distribution uniformity
    - Hypervolume (HV): Measures dominated volume
    """
    
    def __init__(self):
        pass
    
    def spread_measure(self, pareto_front: np.ndarray, 
                      utopian: np.ndarray, 
                      nadir: np.ndarray) -> float:
        """
        Calculate Spread Measure (Δ) for a Pareto front.
        
        Formula from the paper:
        Δ(A) = (d_f + d_l + Σ|d_i - d̄|) / (d_f + d_l + (N-1)d̄)
        
        Args:
            pareto_front: Array of shape (n_solutions, n_objectives)
            utopian: Array of shape (n_objectives,) - ideal point
            nadir: Array of shape (n_objectives,) - worst point
            
        Returns:
            float: Spread measure value (closer to 0 is better)
        """
        if len(pareto_front) < 2:
            return 0.0
            
        # Sort solutions by first objective for consistent ordering
        sorted_front = pareto_front[np.argsort(pareto_front[:, 0])]
        
        # Calculate distances between consecutive solutions
        distances = []
        for i in range(len(sorted_front) - 1):
            dist = euclidean(sorted_front[i], sorted_front[i + 1])
            distances.append(dist)
        
        if not distances:
            return 0.0
            
        # Mean distance between consecutive solutions
        d_mean = np.mean(distances)
        
        # Distance from extreme solutions to utopian/nadir
        # d_f: distance from first solution to utopian
        # d_l: distance from last solution to nadir
        d_f = euclidean(sorted_front[0], utopian)
        d_l = euclidean(sorted_front[-1], nadir)
        
        # Calculate spread measure
        numerator = d_f + d_l + sum(abs(d - d_mean) for d in distances)
        denominator = d_f + d_l + (len(distances)) * d_mean
        
        if denominator == 0:
            return 0.0
            
        return numerator / denominator
    
    def hypervolume(self, pareto_front: np.ndarray, 
                   reference_point: np.ndarray) -> float:
        """
        Calculate Hypervolume (HV) for a Pareto front.
        
        For minimization problems, we need to transform the problem
        or use the reference point appropriately.
        
        Args:
            pareto_front: Array of shape (n_solutions, n_objectives)
            reference_point: Array of shape (n_objectives,) - reference point
            
        Returns:
            float: Hypervolume value (higher is better)
        """
        if len(pareto_front) == 0:
            return 0.0
            
        # Check if any solution dominates the reference point
        # For minimization: solution dominates ref if all objectives are smaller
        dominates_ref = np.all(pareto_front <= reference_point, axis=1)
        
        if not np.any(dominates_ref):
            return 0.0  # No solution dominates reference point
            
        # Filter solutions that dominate reference point
        valid_solutions = pareto_front[dominates_ref]
        
        # Simple hypervolume calculation for 2D case
        if pareto_front.shape[1] == 2:
            return self._hypervolume_2d(valid_solutions, reference_point)
        else:
            # For higher dimensions, use inclusion-exclusion principle
            return self._hypervolume_nd(valid_solutions, reference_point)
    
    def _hypervolume_2d(self, solutions: np.ndarray, 
                       reference_point: np.ndarray) -> float:
        """
        Calculate 2D hypervolume using sweep line algorithm.
        """
        if len(solutions) == 0:
            return 0.0
            
        # Sort by first objective (ascending for minimization)
        sorted_solutions = solutions[np.argsort(solutions[:, 0])]
        
        hypervolume = 0.0
        prev_x = reference_point[0]
        
        for i, solution in enumerate(sorted_solutions):
            x, y = solution
            
            # Add rectangular area
            width = prev_x - x
            height = reference_point[1] - y
            
            if width > 0 and height > 0:
                hypervolume += width * height
            
            prev_x = x
            
            # Update reference point y-coordinate for next iteration
            reference_point = np.array([reference_point[0], 
                                      min(reference_point[1], y)])
        
        return hypervolume
    
    def _hypervolume_nd(self, solutions: np.ndarray, 
                       reference_point: np.ndarray) -> float:
        """
        Calculate n-dimensional hypervolume using inclusion-exclusion.
        Simplified implementation for demonstration.
        """
        if len(solutions) == 0:
            return 0.0
            
        # For simplicity, use bounding box approach
        # This is not the exact hypervolume but gives a reasonable approximation
        min_vals = np.min(solutions, axis=0)
        volume = np.prod(reference_point - min_vals)
        
        return max(0.0, volume)
    
    def calculate_nadir_from_utopian_factor(self, utopian: np.ndarray, 
                                          factor: float = 1.1) -> np.ndarray:
        """
        Calculate nadir point as utopian * factor (as mentioned in the paper).
        """
        return utopian * factor
    
    def plot_convergence(self, iterations: List[int], 
                        hv_values: List[float], 
                        delta_values: List[float],
                        title: str = "Convergence of Quality Metrics") -> plt.Figure:
        """
        Plot convergence of both metrics over iterations.
        
        Args:
            iterations: List of iteration numbers
            hv_values: List of hypervolume values
            delta_values: List of spread measure values
            title: Plot title
            
        Returns:
            matplotlib Figure object
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Plot Hypervolume convergence
        ax1.plot(iterations, hv_values, 'b-', linewidth=2, marker='o', 
                markersize=4, label='Hypervolume')
        ax1.set_xlabel('Iteration')
        ax1.set_ylabel('Hypervolume (HV)')
        ax1.set_title('Hypervolume Convergence')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Plot Spread Measure convergence
        ax2.plot(iterations, delta_values, 'r-', linewidth=2, marker='s', 
                markersize=4, label='Spread Measure')
        ax2.set_xlabel('Iteration')
        ax2.set_ylabel('Spread Measure (Δ)')
        ax2.set_title('Spread Measure Convergence')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        return fig
    
    def plot_metrics_statistics(self, hv_data: List[List[float]], 
                               delta_data: List[List[float]],
                               iterations: List[int]) -> plt.Figure:
        """
        Plot metrics statistics (quantiles, median, mean) as shown in the paper.
        
        Args:
            hv_data: List of hypervolume evolution for each run
            delta_data: List of spread measure evolution for each run  
            iterations: Iteration points to sample
            
        Returns:
            matplotlib Figure object
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Process hypervolume data
        hv_stats = self._calculate_statistics(hv_data, iterations)
        self._plot_statistics(ax1, iterations, hv_stats, 'Hypervolume', 'blue')
        
        # Process spread measure data  
        delta_stats = self._calculate_statistics(delta_data, iterations)
        self._plot_statistics(ax2, iterations, delta_stats, 'Spread Measure (Δ)', 'red')
        
        plt.suptitle('Quality Metrics Evolution - Statistical Analysis', 
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        return fig
    
    def _calculate_statistics(self, data: List[List[float]], 
                            iterations: List[int]) -> dict:
        """Calculate statistical measures for metric evolution."""
        data_array = np.array(data)
        
        return {
            'mean': np.mean(data_array, axis=0),
            'median': np.median(data_array, axis=0),
            'q25': np.percentile(data_array, 25, axis=0),
            'q75': np.percentile(data_array, 75, axis=0),
            'min': np.min(data_array, axis=0),
            'max': np.max(data_array, axis=0)
        }
    
    def _plot_statistics(self, ax, iterations: List[int], stats: dict, 
                        ylabel: str, color: str):
        """Plot statistical evolution of a metric."""
        # Plot quantile bands
        ax.fill_between(iterations, stats['min'], stats['max'], 
                       alpha=0.1, color=color, label='Min-Max Range')
        ax.fill_between(iterations, stats['q25'], stats['q75'], 
                       alpha=0.3, color=color, label='Q25-Q75 Range')
        
        # Plot median and mean
        ax.plot(iterations, stats['median'], '--', color=color, 
               linewidth=2, label='Median')
        ax.plot(iterations, stats['mean'], '-', color=color, 
               linewidth=3, label='Mean')
        
        ax.set_xlabel('Iteration Percentage')
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend()

# Example usage and testing
def test_metrics():
    """Test the implemented metrics with sample data."""
    
    # Create sample Pareto front (for minimization problem)
    np.random.seed(42)
    pareto_front = np.array([
        [1701.3, 29.6],  # S1 from the paper
        [1811.2, 27.5],  # S2 from the paper  
        [1828.6, 27.4],  # S3 from the paper
    ])
    
    # Define utopian and nadir points (from mono-objective solutions)
    utopian = np.array([1600, 24])  # Best values for each objective
    nadir = np.array([2000, 36])    # Worst values for each objective
    
    # Initialize metrics calculator
    metrics = ParetoMetrics()
    
    # Calculate metrics
    spread = metrics.spread_measure(pareto_front, utopian, nadir)
    reference_point = metrics.calculate_nadir_from_utopian_factor(nadir, 1.1)
    hv = metrics.hypervolume(pareto_front, reference_point)
    
    print("Pareto Front Quality Metrics:")
    print(f"Spread Measure (Δ): {spread:.4f}")
    print(f"Hypervolume (HV): {hv:.4f}")
    print(f"Reference Point: {reference_point}")
    
    # Generate sample convergence data for plotting
    iterations = list(range(0, 101, 10))
    
    # Simulate 5 runs as mentioned in the paper
    hv_runs = []
    delta_runs = []
    
    for run in range(5):
        # Simulate convergence with some randomness
        hv_evolution = [max(0, hv * (0.1 + 0.9 * i/100) + np.random.normal(0, hv*0.1)) 
                       for i in iterations]
        delta_evolution = [spread + np.random.normal(0, 0.1) for _ in iterations]
        
        hv_runs.append(hv_evolution)
        delta_runs.append(delta_evolution)
    
    # Plot convergence for single run
    fig1 = metrics.plot_convergence(iterations, hv_runs[0], delta_runs[0])
    plt.show()
    
    # Plot statistical analysis for all runs
    fig2 = metrics.plot_metrics_statistics(hv_runs, delta_runs, iterations)
    plt.show()
    
    return metrics

if __name__ == "__main__":
    test_metrics()