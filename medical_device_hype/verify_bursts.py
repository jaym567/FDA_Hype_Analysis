
import numpy as np
import sys
import pandas as pd
from rich.console import Console

# Add src to path
sys.path.append('src')

from fda_device_hype_analysis import FDADeviceHypeAnalyzer

console = Console()

def test_burst_detection():
    analyzer = FDADeviceHypeAnalyzer(verbose=False)
    
    scenarios = [
        {
            "name": "Flatline",
            "counts": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "expected_bursts": 0
        },
        {
            "name": "Steady State (High)",
            "counts": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
            "expected_bursts": 0 # Should count as baseline
        },
        {
            "name": "Single Spike",
            "counts": [1, 1, 1, 1, 50, 50, 1, 1, 1, 1],
            "expected_bursts": 1
        },
        {
            "name": "Ramp Up (Sustained)",
            "counts": [1, 1, 2, 5, 10, 20, 30, 40, 50, 50],
            "expected_bursts": 1 # Should eventually trigger burst state
        },
        {
            "name": "Two Bursts",
            "counts": [1, 1, 20, 20, 1, 1, 1, 30, 30, 1],
            "expected_bursts": 2
        }
    ]
    
    print("\n--- Testing Burst Detection Logic ---")
    
    for s in scenarios:
        # Create time series (Year, Count) start year 2000
        time_series = [(2000 + i, count) for i, count in enumerate(s['counts'])]
        
        # Run detection
        # Gamma=1.0 for stability, s=2.0 for 2x multiplier
        bursts = analyzer.kleinberg_burst_detection(time_series, gamma=1.0, s=2.0, n_states=2)
        
        n_bursts = len(bursts)
        match = n_bursts == s['expected_bursts']
        status = "PASS" if match else f"FAIL (Expected {s['expected_bursts']}, got {n_bursts})"
        
        print(f"\nScenario: {s['name']}")
        print(f"Data: {s['counts']}")
        print(f"Status: {status}")
        for b in bursts:
            print(f"  - Detected Burst: {b['start']} to {b['end']} (Intensity: {b['intensity']:.2f})")

if __name__ == "__main__":
    test_burst_detection()
