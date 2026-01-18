"""
Kleinberg's Burst Detection Algorithm Implementation
Pure algorithm without CSV dependencies
"""

import numpy as np
import math
from typing import List, Tuple, Dict, Any


class KleinbergBurstDetector:
    """
    Implementation of Kleinberg's burst detection algorithm for event streams.
    
    Based on: "Bursty and Hierarchical Structure in Streams" by Jon Kleinberg (2002)
    
    This is a pure algorithmic implementation with no external dependencies.
    """
    
    def __init__(self, s: float = 2, gamma: float = 1.0):
        """
        Initialize the burst detector.
        
        Args:
            s: Base for exponential distribution of state transitions (s > 1)
            gamma: Parameter controlling cost of state transitions
        """
        if s <= 1:
            raise ValueError("s must be greater than 1")
        if gamma <= 0:
            raise ValueError("gamma must be positive")
            
        self.s = s
        self.gamma = gamma
        
    def _compute_inter_arrival_times(self, timestamps: List[float]) -> List[float]:
        """Convert timestamps to inter-arrival times."""
        if len(timestamps) <= 1:
            return []
        
        # Ensure timestamps are sorted
        sorted_timestamps = sorted(timestamps)
        return [sorted_timestamps[i] - sorted_timestamps[i-1] 
                for i in range(1, len(sorted_timestamps))]
    
    def _estimate_rates(self, inter_arrival_times: List[float], s: float, k: int) -> List[float]:
        """
        Estimate rates for each state using the geometric distribution.
        
        The rate for state j is: r_j = (s^j) * r
        where r is the overall rate of events.
        """
        if not inter_arrival_times:
            return []
        
        # Overall rate (events per time unit)
        total_time = sum(inter_arrival_times)
        if total_time <= 0:
            total_time = 1e-10
        overall_rate = len(inter_arrival_times) / total_time
        
        # Rates for each state (exponentially increasing)
        rates = [overall_rate * (s ** j) for j in range(k)]
        return rates
    
    def _compute_observation_cost(self, delta_t: float, rate: float) -> float:
        """
        Compute negative log-likelihood for an inter-arrival time.
        
        Using exponential distribution: f(delta_t; r) = r * exp(-r * delta_t)
        Cost = -log(f(delta_t; r))
        """
        if rate <= 0:
            return float('inf')
        if delta_t <= 0:
            delta_t = 1e-10
            
        # Compute probability and avoid numerical underflow
        log_prob = math.log(rate) - rate * delta_t
        return -log_prob
    
    def detect_bursts(self, timestamps: List[float], k: int = 3) -> Dict[str, Any]:
        """
        Detect bursts in a sequence of timestamps.
        
        Args:
            timestamps: List of event timestamps (any unit, but must be consistent)
            k: Number of states (including quiescent state)
            
        Returns:
            Dictionary containing:
                - bursts: List of detected bursts with metadata
                - states: Optimal state sequence for each interval
                - rates: Estimated rates for each state
                - cost: Total optimal cost
                - inter_arrivals: Inter-arrival times
        """
        if len(timestamps) < 2:
            return {
                "bursts": [],
                "states": [],
                "rates": [],
                "cost": 0,
                "inter_arrivals": [],
                "num_events": len(timestamps)
            }
        
        # Sort and compute inter-arrival times
        sorted_timestamps = sorted(timestamps)
        inter_arrivals = self._compute_inter_arrival_times(sorted_timestamps)
        n = len(inter_arrivals)
        
        # Estimate rates for each state
        rates = self._estimate_rates(inter_arrivals, self.s, k)
        
        # Dynamic programming tables
        cost = np.full((n, k), float('inf'))  # Minimum cost to reach state j at interval i
        prev_state = np.full((n, k), -1, dtype=int)  # Backpointer for reconstruction
        
        # Base case: first interval
        for j in range(k):
            cost[0][j] = self._compute_observation_cost(inter_arrivals[0], rates[j])
        
        # Main DP recurrence
        for i in range(1, n):
            for j in range(k):
                # Consider all possible previous states
                for prev_j in range(k):
                    transition_cost = self.gamma * abs(j - prev_j)
                    total_cost = (cost[i-1][prev_j] + 
                                self._compute_observation_cost(inter_arrivals[i], rates[j]) + 
                                transition_cost)
                    
                    if total_cost < cost[i][j]:
                        cost[i][j] = total_cost
                        prev_state[i][j] = prev_j
        
        # Backtrack to find optimal state sequence
        optimal_states = np.zeros(n, dtype=int)
        optimal_states[-1] = np.argmin(cost[-1])
        total_cost = cost[-1][optimal_states[-1]]
        
        for i in range(n-2, -1, -1):
            optimal_states[i] = prev_state[i+1][optimal_states[i+1]]
        
        # Convert state sequence to burst segments
        bursts = self._extract_bursts_from_states(optimal_states, sorted_timestamps, rates)
        
        return {
            "bursts": bursts,
            "states": optimal_states.tolist(),
            "rates": rates,
            "cost": float(total_cost),
            "inter_arrivals": inter_arrivals,
            "timestamps": sorted_timestamps,
            "num_events": len(timestamps)
        }
    
    def _extract_bursts_from_states(self, states: np.ndarray, timestamps: List[float], 
                                   rates: List[float]) -> List[Dict]:
        """
        Extract burst segments from state sequence.
        
        Args:
            states: Optimal state sequence for each interval
            timestamps: Sorted event timestamps
            rates: Estimated rates for each state
            
        Returns:
            List of dictionaries describing each burst
        """
        if len(states) == 0:
            return []
        
        bursts = []
        current_state = states[0]
        start_idx = 0
        
        for i in range(1, len(states)):
            if states[i] != current_state:
                # Segment ended
                if current_state > 0:  # This was a burst state
                    burst = self._create_burst_info(
                        start_idx=start_idx,
                        end_idx=i,
                        state=current_state,
                        timestamps=timestamps,
                        rates=rates
                    )
                    bursts.append(burst)
                
                current_state = states[i]
                start_idx = i
        
        # Handle the last segment
        if current_state > 0:
            burst = self._create_burst_info(
                start_idx=start_idx,
                end_idx=len(states),
                state=current_state,
                timestamps=timestamps,
                rates=rates
            )
            bursts.append(burst)
        
        # Merge adjacent bursts of same state
        return self._merge_adjacent_bursts(bursts)
    
    def _create_burst_info(self, start_idx: int, end_idx: int, state: int,
                          timestamps: List[float], rates: List[float]) -> Dict:
        """Create burst metadata dictionary."""
        return {
            "start_time": timestamps[start_idx],
            "end_time": timestamps[end_idx],
            "start_index": start_idx,
            "end_index": end_idx,
            "state": int(state),
            "intensity": rates[state],
            "num_events": end_idx - start_idx + 1,
            "duration": timestamps[end_idx] - timestamps[start_idx]
        }
    
    def _merge_adjacent_bursts(self, bursts: List[Dict]) -> List[Dict]:
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
                current_burst["duration"] = current_burst["end_time"] - current_burst["start_time"]
            else:
                merged.append(current_burst)
                current_burst = burst.copy()
        
        merged.append(current_burst)
        return merged
    
    def get_burst_summary(self, burst_results: Dict[str, Any]) -> str:
        """Generate a human-readable summary of detected bursts."""
        bursts = burst_results.get("bursts", [])
        
        if not bursts:
            return "No bursts detected."
        
        summary_lines = [f"Detected {len(bursts)} burst(s):", "-" * 50]
        
        for i, burst in enumerate(bursts, 1):
            summary_lines.extend([
                f"Burst {i}:",
                f"  Time: {burst['start_time']:.2f} to {burst['end_time']:.2f}",
                f"  Duration: {burst['duration']:.2f}",
                f"  Events: {burst['num_events']}",
                f"  Intensity level: {burst['state']}",
                f"  Rate: {burst['intensity']:.4f} events/unit time",
                "-" * 50
            ])
        
        return "\n".join(summary_lines)


def normalize_timestamps(timestamps: List[float]) -> List[float]:
    """
    Normalize timestamps to start at 0.
    
    Useful when you have absolute timestamps but want relative timing.
    """
    if not timestamps:
        return []
    
    min_time = min(timestamps)
    return [t - min_time for t in timestamps]