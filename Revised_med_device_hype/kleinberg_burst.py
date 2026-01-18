import numpy as np
import math
from collections import defaultdict
from typing import List, Tuple, Dict, Any
import matplotlib.pyplot as plt
import random

class KleinbergBurstDetector:
    """
    Implementation of Kleinberg's burst detection algorithm for event streams.
    
    Based on: "Bursty and Hierarchical Structure in Streams" by Jon Kleinberg (2002)
    """
    
    def __init__(self, s: float = 2, gamma: float = 1.0):
        """
        Initialize the burst detector.
        
        Args:
            s: Base for exponential distribution of state transitions (s > 1)
            gamma: Parameter controlling cost of state transitions
        """
        self.s = s
        self.gamma = gamma
        
    def _compute_inter_arrival_times(self, timestamps: List[float]) -> List[float]:
        """Convert timestamps to inter-arrival times."""
        timestamps = sorted(timestamps)
        if len(timestamps) <= 1:
            return []
        return [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
    
    def _estimate_rates(self, inter_arrival_times: List[float], s: float, k: int) -> List[float]:
        """
        Estimate rates for each state using the geometric distribution.
        
        The rate for state j is: r_j = (s^j) * r
        where r is the overall rate of events.
        """
        if not inter_arrival_times:
            return []
        
        # Overall rate
        total_time = sum(inter_arrival_times)
        if total_time == 0:
            total_time = 1e-10
        overall_rate = len(inter_arrival_times) / total_time
        
        # Rates for each state
        rates = [overall_rate * (s ** j) for j in range(k)]
        return rates
    
    def _compute_cost(self, delta_t: float, r: float) -> float:
        """
        Compute cost for an inter-arrival time delta_t with rate r.
        
        Using exponential distribution: f(delta_t; r) = r * exp(-r * delta_t)
        Cost = -log(f(delta_t; r))
        """
        if r <= 0:
            return float('inf')
        if delta_t <= 0:
            delta_t = 1e-10
        # Avoid numerical issues with very small probabilities
        prob = r * math.exp(-r * delta_t)
        if prob <= 0:
            return float('inf')
        return -math.log(prob)
    
    def detect_bursts(self, timestamps: List[float], k: int = 3) -> Dict[str, Any]:
        """
        Detect bursts in a sequence of timestamps.
        
        Args:
            timestamps: List of event timestamps
            k: Number of states (including quiescent state)
            
        Returns:
            Dictionary containing bursts, state sequence, and other information
        """
        if len(timestamps) < 2:
            return {"bursts": [], "states": [], "num_events": len(timestamps)}
        
        # Sort timestamps and compute inter-arrival times
        timestamps = sorted(timestamps)
        inter_arrivals = self._compute_inter_arrival_times(timestamps)
        n = len(inter_arrivals)
        
        # Estimate rates for each state
        rates = self._estimate_rates(inter_arrivals, self.s, k)
        
        # Initialize DP tables
        cost = np.full((n, k), float('inf'))
        prev_state = np.full((n, k), -1, dtype=int)
        
        # Base case: first interval
        for j in range(k):
            cost[0][j] = self._compute_cost(inter_arrivals[0], rates[j])
        
        # Dynamic programming
        for i in range(1, n):
            for j in range(k):
                # Consider all possible previous states
                for prev_j in range(k):
                    transition_cost = self.gamma * abs(j - prev_j)
                    total_cost = cost[i-1][prev_j] + self._compute_cost(inter_arrivals[i], rates[j]) + transition_cost
                    
                    if total_cost < cost[i][j]:
                        cost[i][j] = total_cost
                        prev_state[i][j] = prev_j
        
        # Backtrack to find optimal state sequence
        optimal_states = np.zeros(n, dtype=int)
        optimal_states[-1] = np.argmin(cost[-1])
        
        for i in range(n-2, -1, -1):
            optimal_states[i] = prev_state[i+1][optimal_states[i+1]]
        
        # Convert state sequence to bursts
        bursts = []
        current_state = optimal_states[0]
        start_idx = 0
        
        for i in range(1, n):
            if optimal_states[i] != current_state:
                if current_state > 0:  # This was a burst state
                    burst_info = {
                        "start_time": timestamps[start_idx],
                        "end_time": timestamps[i],
                        "start_index": start_idx,
                        "end_index": i,
                        "state": int(current_state),
                        "intensity": rates[current_state],
                        "num_events": i - start_idx + 1
                    }
                    bursts.append(burst_info)
                
                current_state = optimal_states[i]
                start_idx = i
        
        # Handle the last segment
        if current_state > 0:
            burst_info = {
                "start_time": timestamps[start_idx],
                "end_time": timestamps[-1],
                "start_index": start_idx,
                "end_index": len(timestamps) - 1,
                "state": int(current_state),
                "intensity": rates[current_state],
                "num_events": len(timestamps) - start_idx
            }
            bursts.append(burst_info)
        
        # Merge overlapping or adjacent bursts of same state
        bursts = self._merge_bursts(bursts)
        
        return {
            "bursts": bursts,
            "states": optimal_states.tolist(),
            "rates": rates,
            "inter_arrivals": inter_arrivals,
            "timestamps": timestamps,
            "num_events": len(timestamps)
        }
    
    def _merge_bursts(self, bursts: List[Dict]) -> List[Dict]:
        """Merge adjacent bursts of the same state."""
        if not bursts:
            return []
        
        merged = []
        current_burst = bursts[0].copy()
        
        for burst in bursts[1:]:
            if (burst["state"] == current_burst["state"] and 
                burst["start_index"] == current_burst["end_index"] + 1):
                # Merge with current burst
                current_burst["end_time"] = burst["end_time"]
                current_burst["end_index"] = burst["end_index"]
                current_burst["num_events"] += burst["num_events"]
            else:
                merged.append(current_burst)
                current_burst = burst.copy()
        
        merged.append(current_burst)
        return merged
    
    def get_burst_summary(self, burst_results: Dict[str, Any]) -> str:
        """Generate a human-readable summary of detected bursts."""
        bursts = burst_results["bursts"]
        
        if not bursts:
            return "No bursts detected."
        
        summary = f"Detected {len(bursts)} burst(s):\n"
        summary += "-" * 50 + "\n"
        
        for i, burst in enumerate(bursts, 1):
            duration = burst["end_time"] - burst["start_time"]
            summary += f"Burst {i}:\n"
            summary += f"  Time: {burst['start_time']:.2f} to {burst['end_time']:.2f}\n"
            summary += f"  Duration: {duration:.2f}\n"
            summary += f"  Events: {burst['num_events']}\n"
            summary += f"  Intensity level: {burst['state']}\n"
            summary += f"  Rate: {burst['intensity']:.4f} events/unit time\n"
            summary += "-" * 50 + "\n"
        
        return summary


# Example usage and visualization
def example_usage():
    """Example demonstrating how to use the burst detector."""
    
    # Generate sample data with bursts
    np.random.seed(42)
    
    # Create timestamps: some quiet periods and some bursts
    timestamps = []
    current_time = 0
    
    # Quiet period
    for _ in range(50):
        current_time += np.random.exponential(5.0)
        timestamps.append(current_time)
    
    # Burst period
    for _ in range(30):
        current_time += np.random.exponential(0.5)
        timestamps.append(current_time)
    
    # Quiet period
    for _ in range(40):
        current_time += np.random.exponential(4.0)
        timestamps.append(current_time)
    
    # Another burst
    for _ in range(25):
        current_time += np.random.exponential(0.3)
        timestamps.append(current_time)
    
    # Create detector and detect bursts
    detector = KleinbergBurstDetector(s=2, gamma=1.0)
    results = detector.detect_bursts(timestamps, k=4)
    
    # Print summary
    print(detector.get_burst_summary(results))
    
    # Visualize the results
    visualize_bursts(timestamps, results)


def visualize_bursts(timestamps: List[float], results: Dict[str, Any]):
    """Visualize timestamps and detected bursts."""
    plt.figure(figsize=(12, 6))
    
    # Plot events
    plt.eventplot([timestamps], colors='black', linewidths=0.5, alpha=0.7)
    
    # Highlight bursts
    bursts = results["bursts"]
    states = results["states"]
    
    # Color map for different states
    colors = ['green', 'orange', 'red', 'purple']
    
    # Plot background for bursts
    y_min, y_max = -0.5, 0.5
    for burst in bursts:
        plt.axvspan(burst["start_time"], burst["end_time"], 
                   alpha=0.3, color=colors[min(burst["state"], len(colors)-1)],
                   label=f'State {burst["state"]}')
    
    # Plot state transitions
    if len(states) > 0:
        # Map states to y positions
        unique_states = sorted(set(states))
        state_y_pos = {state: i * 0.2 for i, state in enumerate(unique_states)}
        
        # Plot state sequence
        state_times = results["timestamps"][1:]  # States correspond to intervals between events
        state_values = [state_y_pos[s] for s in states]
        
        plt.plot(state_times, state_values, 'b-', linewidth=2, label='State level')
        plt.scatter(state_times, state_values, c=states, cmap='viridis', s=50, zorder=5)
    
    plt.xlabel('Time')
    plt.ylabel('Event / State')
    plt.title('Kleinberg Burst Detection')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def advanced_example():
    """More advanced example with real-world-like data."""
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Create synthetic email data
    np.random.seed(123)
    
    # Generate base timestamps (1 month of data)
    base_date = datetime(2024, 1, 1)
    timestamps = []
    
    # Regular work pattern with bursts
    for day in range(30):
        # Work hours
        for hour in range(9, 17):
            # Base rate
            n_emails = np.random.poisson(2)
            for _ in range(n_emails):
                time_offset = np.random.uniform(0, 1)
                dt = base_date + timedelta(days=day, hours=hour, minutes=time_offset * 60)
                timestamps.append(dt.timestamp())
        
        # Add burst days (every 5 days)
        if day % 5 == 0:
            # Evening burst
            for hour in range(18, 22):
                n_emails = np.random.poisson(10)
                for _ in range(n_emails):
                    time_offset = np.random.uniform(0, 1)
                    dt = base_date + timedelta(days=day, hours=hour, minutes=time_offset * 60)
                    timestamps.append(dt.timestamp())
    
    # Convert to float for processing
    float_timestamps = [float(ts) for ts in timestamps]
    
    # Detect bursts
    detector = KleinbergBurstDetector(s=2, gamma=0.5)
    results = detector.detect_bursts(float_timestamps, k=5)
    
    # Convert back to datetime for reporting
    bursts_datetime = []
    for burst in results["bursts"]:
        burst_dt = burst.copy()
        burst_dt["start_time"] = datetime.fromtimestamp(burst["start_time"])
        burst_dt["end_time"] = datetime.fromtimestamp(burst["end_time"])
        bursts_datetime.append(burst_dt)
    
    # Display results
    print(f"Total events: {len(timestamps)}")
    print(f"Detected {len(bursts_datetime)} burst periods:\n")
    
    for i, burst in enumerate(bursts_datetime, 1):
        duration = burst["end_time"] - burst["start_time"]
        print(f"Burst {i}:")
        print(f"  Start: {burst['start_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  End: {burst['end_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Duration: {duration}")
        print(f"  Events: {burst['num_events']}")
        print(f"  Intensity level: {burst['state']}")
        print()


if __name__ == "__main__":
    print("Running Kleinberg Burst Detection Example")
    print("=" * 60)
    
    # Simple example
    #example_usage()
    
    # More advanced example
    advanced_example()