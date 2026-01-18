"""
Usage Examples for Kleinberg Burst Detection with CSV Interface
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Import our modules
from kleinberg_burst import KleinbergBurstDetector, normalize_timestamps
from csv_burst_detector import CSVBurstDetector, create_sample_csv, validate_csv_structure


def example_1_basic_usage():
    """Basic example with a sample CSV file."""
    print("=" * 60)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 60)
    
    # Create a sample CSV file
    create_sample_csv('sample_events.csv')
    
    # Initialize CSV detector
    detector = CSVBurstDetector('sample_events.csv')
    
    # Configure detector
    detector.configure(
        timestamp_column='timestamp',
        datetime_format='%Y-%m-%d %H:%M:%S',
        filter_expression="event_type == 'click'",  # Only analyze clicks
        normalize_time=True  # Shift timestamps to start at 0
    )
    
    # Get data summary
    summary = detector.get_data_summary()
    print(f"Data Summary:")
    print(f"  Total events: {summary['total_events']}")
    print(f"  Time range: {summary['time_range']['start']} to {summary['time_range']['end']}")
    print(f"  Duration: {summary['duration_seconds']:.0f} seconds")
    print()
    
    # Detect bursts
    print("Detecting bursts...")
    results = detector.detect_bursts(
        s=2.0,      # State multiplier
        gamma=0.8,  # Transition cost
        k=3         # Number of states
    )
    
    # Print summary
    if 'error' in results:
        print(f"Error: {results['error']}")
    else:
        kleinberg = KleinbergBurstDetector()
        print(kleinberg.get_burst_summary(results))
    
    # Export results to CSV
    detector.export_results(results, 'burst_results_example1.csv')
    
    # Convert to DataFrame for further analysis
    burst_df = detector.bursts_to_dataframe(results)
    if not burst_df.empty:
        print("\nBursts DataFrame:")
        print(burst_df[['start_datetime', 'end_datetime', 'state', 'num_events', 'duration']])
    
    return results


def example_2_advanced_analysis():
    """Advanced analysis with synthetic financial data."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Financial Trading Data")
    print("=" * 60)
    
    # Create synthetic financial trading data
    np.random.seed(123)
    
    data = []
    current_time = datetime(2024, 3, 15, 9, 30, 0)  # Market open
    
    # Market phases
    phases = [
        ('quiet', 30, 5.0),   # 30 events, avg 5 sec apart
        ('burst', 50, 0.5),   # 50 events, avg 0.5 sec apart (high frequency)
        ('quiet', 40, 3.0),   # 40 events, avg 3 sec apart
        ('burst', 30, 0.3),   # 30 events, avg 0.3 sec apart
        ('quiet', 35, 4.0),   # 35 events, avg 4 sec apart
    ]
    
    for phase, n_events, avg_interval in phases:
        for _ in range(n_events):
            # Add random variation
            interval = np.random.exponential(avg_interval)
            current_time += timedelta(seconds=interval)
            
            # Simulate trade
            data.append({
                'trade_time': current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'symbol': 'AAPL',
                'price': 175 + np.random.normal(0, 0.5),
                'volume': int(np.random.exponential(100)),
                'side': np.random.choice(['BUY', 'SELL'])
            })
    
    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv('financial_trades.csv', index=False)
    print("Created financial_trades.csv with synthetic data")
    
    # Analyze with burst detection
    detector = CSVBurstDetector('financial_trades.csv')
    
    # Configure for high-frequency data
    detector.configure(
        timestamp_column='trade_time',
        datetime_format='%Y-%m-%d %H:%M:%S.%f',
        filter_expression="side == 'BUY'",  # Analyze only buy orders
        event_weight_column='volume',       # Weight by trade volume
        aggregation_method='direct'
    )
    
    # Detect bursts with aggressive parameters for HF data
    results = detector.detect_bursts(
        s=3.0,      # Larger s for more distinct states
        gamma=0.5,  # Lower gamma for more state changes
        k=4         # More states for finer granularity
    )
    
    # Display results
    kleinberg = KleinbergBurstDetector()
    print(kleinberg.get_burst_summary(results))
    
    # Visualize
    visualize_burst_timeline(results, title="Financial Trading Bursts")
    
    return results


def example_3_social_media_analysis():
    """Social media post analysis."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Social Media Posts")
    print("=" * 60)
    
    # Create synthetic social media data
    np.random.seed(456)
    
    # Simulate a viral event
    base_time = datetime(2024, 2, 1, 10, 0, 0)
    posts = []
    
    # Normal activity (10 posts/hour)
    for hour in range(24):
        n_posts = np.random.poisson(10)
        for post in range(n_posts):
            post_time = base_time + timedelta(hours=hour, 
                                            minutes=np.random.uniform(0, 60))
            posts.append({
                'post_time': post_time.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': f'user_{np.random.randint(1, 100)}',
                'likes': int(np.random.exponential(10)),
                'shares': int(np.random.exponential(2)),
                'content_type': np.random.choice(['text', 'image', 'video'], 
                                                p=[0.6, 0.3, 0.1])
            })
    
    # Viral burst (additional 100 posts in 2 hours)
    burst_start = base_time + timedelta(hours=6)
    for _ in range(100):
        burst_time = burst_start + timedelta(minutes=np.random.uniform(0, 120))
        posts.append({
            'post_time': burst_time.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': f'user_{np.random.randint(1, 200)}',  # New users join
            'likes': int(np.random.exponential(100)),  # More likes during burst
            'shares': int(np.random.exponential(20)),  # More shares
            'content_type': 'video'  # Viral content is usually video
        })
    
    # Save to CSV
    df = pd.DataFrame(posts)
    df.to_csv('social_media_posts.csv', index=False)
    
    # Analyze
    detector = CSVBurstDetector('social_media_posts.csv')
    detector.configure(
        timestamp_column='post_time',
        event_weight_column='likes',  # Weight by engagement
        filter_expression="content_type == 'video'",  # Focus on videos
        normalize_time=True
    )
    
    # Run burst detection
    results = detector.detect_bursts(s=2.5, gamma=1.2, k=4)
    
    # Display
    kleinberg = KleinbergBurstDetector()
    print(kleinberg.get_burst_summary(results))
    
    # Compare weighted vs unweighted
    print("\nComparing weighted vs unweighted detection:")
    
    # Unweighted detection
    detector.configure(event_weight_column=None)
    results_unweighted = detector.detect_bursts(s=2.5, gamma=1.2, k=4)
    
    print(f"Weighted: {len(results['bursts'])} bursts")
    print(f"Unweighted: {len(results_unweighted['bursts'])} bursts")
    
    return results


def example_4_real_csv_validation():
    """Validate and analyze a user-provided CSV file."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: CSV Validation")
    print("=" * 60)
    
    # Replace with your CSV file path
    csv_file = 'your_data.csv'  # Change this to your file
    
    try:
        # Validate CSV structure
        validation = validate_csv_structure(csv_file)
        
        if not validation['file_exists']:
            print(f"File not found: {csv_file}")
            print("Creating a sample file instead...")
            create_sample_csv('sample_for_validation.csv')
            csv_file = 'sample_for_validation.csv'
            validation = validate_csv_structure(csv_file)
        
        print("CSV Validation Results:")
        print(f"  File: {csv_file}")
        print(f"  Rows: {validation['num_rows']}")
        print(f"  Columns: {validation['columns']}")
        print(f"  Has timestamp: {validation['has_timestamp']}")
        
        if validation['timestamp_candidates']:
            print(f"  Timestamp candidates: {validation['timestamp_candidates']}")
            
            # Use first candidate
            timestamp_col = validation['timestamp_candidates'][0]
            
            # Initialize detector
            detector = CSVBurstDetector(csv_file)
            detector.configure(timestamp_column=timestamp_col)
            
            # Get data summary
            summary = detector.get_data_summary()
            print(f"\nData Summary:")
            print(f"  Events after processing: {summary['total_events']}")
            
            if summary['total_events'] > 1:
                # Try burst detection with different parameters
                print("\nTesting burst detection parameters:")
                
                param_sets = [
                    {'s': 2.0, 'gamma': 1.0, 'k': 3, 'label': 'Default'},
                    {'s': 1.5, 'gamma': 0.5, 'k': 4, 'label': 'Sensitive'},
                    {'s': 3.0, 'gamma': 2.0, 'k': 3, 'label': 'Conservative'},
                ]
                
                for params in param_sets:
                    results = detector.detect_bursts(**{k: v for k, v in params.items() if k != 'label'})
                    bursts = len(results.get('bursts', []))
                    print(f"  {params['label']}: {bursts} bursts (s={params['s']}, γ={params['gamma']})")
                
                # Use best parameters
                final_results = detector.detect_bursts(s=2.0, gamma=1.0, k=3)
                
                if final_results.get('bursts'):
                    print("\nDetected bursts:")
                    for burst in final_results['bursts']:
                        duration = burst['end_time'] - burst['start_time']
                        print(f"  State {burst['state']}: {duration:.1f}s, {burst['num_events']} events")
            
            else:
                print("Insufficient data for burst detection.")
                
        else:
            print("No timestamp column found. Cannot perform burst detection.")
            
    except Exception as e:
        print(f"Error: {str(e)}")


def visualize_burst_timeline(results: dict, title: str = "Burst Detection Results"):
    """Visualize burst detection results."""
    if not results.get('bursts'):
        print("No bursts to visualize")
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[1, 3])
    
    # Plot 1: Event timeline
    timestamps = results.get('timestamps', [])
    if timestamps:
        # Normalize for display
        if timestamps[0] != 0:
            timestamps = [t - timestamps[0] for t in timestamps]
        
        ax1.eventplot([timestamps], colors='black', linewidths=0.5, alpha=0.7)
        ax1.set_ylabel('Events')
        ax1.set_title(f'{title} - Event Timeline')
        ax1.grid(True, alpha=0.3)
        ax1.get_yaxis().set_visible(False)
    
    # Plot 2: Bursts
    bursts = results['bursts']
    
    # Color map for states
    colors = ['green', 'orange', 'red', 'purple', 'brown']
    
    for burst in bursts:
        state = burst['state']
        color = colors[min(state, len(colors)-1)]
        
        ax2.axvspan(burst['start_time'], burst['end_time'], 
                   alpha=0.3, color=color,
                   label=f'State {state}' if f'State {state}' not in [l.get_label() for l in ax2.collections] else "")
        
        # Add annotation
        mid_point = (burst['start_time'] + burst['end_time']) / 2
        ax2.text(mid_point, 0.5, f"{burst['num_events']} events", 
                ha='center', va='center', fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
    
    # Plot state sequence if available
    states = results.get('states', [])
    if states and timestamps and len(states) == len(timestamps) - 1:
        # Map states to y positions
        state_times = timestamps[1:]  # States correspond to intervals
        ax2.plot(state_times, [s * 0.2 for s in states], 'b-', linewidth=1, alpha=0.7, label='State level')
    
    ax2.set_xlabel('Time (seconds from start)')
    ax2.set_ylabel('Burst Intensity')
    ax2.set_title('Detected Bursts')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('burst_visualization.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("Visualization saved as 'burst_visualization.png'")


def main():
    """Run all examples or select one."""
    print("Kleinberg Burst Detection with CSV Interface")
    print("=" * 60)
    
    # Run all examples
    results1 = example_1_basic_usage()
    results2 = example_2_advanced_analysis()
    results3 = example_3_social_media_analysis()
    example_4_real_csv_validation()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Examples completed successfully!")
    print("\nGenerated files:")
    print("  - sample_events.csv (Example 1)")
    print("  - financial_trades.csv (Example 2)")
    print("  - social_media_posts.csv (Example 3)")
    print("  - burst_results_example1.csv (Example 1 results)")
    print("  - burst_visualization.png (Visualization)")
    
    print("\nNext steps:")
    print("  1. Place your CSV file in the same directory")
    print("  2. Modify example_4_real_csv_validation() to use your file")
    print("  3. Adjust parameters (s, gamma, k) for your data")
    print("  4. Use visualize_burst_timeline() to visualize results")


if __name__ == "__main__":
    main()