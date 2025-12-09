#!/usr/bin/env python3
"""
Example usage of the FDA Device Hype Analyzer

This script demonstrates various ways to use the analyzer for different research scenarios.
"""

from fda_device_hype_analysis import FDADeviceHypeAnalyzer
import pandas as pd

def example_1_single_device_analysis():
    """Example 1: Analyze a single device in detail"""
    print("=" * 60)
    print("EXAMPLE 1: Single Device Analysis")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = FDADeviceHypeAnalyzer()
    
    # Analyze the Da Vinci Surgical System
    device_name = "Da Vinci Surgical System"
    approval_date = "2000-07-11"
    
    print(f"Analyzing {device_name}...")
    results = analyzer.analyze_device_hype(device_name, approval_date)
    
    # Print detailed results
    print(f"\nDevice: {results['device_name']}")
    print(f"Total Publications: {results['total_publications']}")
    print(f"Total Citations: {results['total_citations']}")
    print(f"Average Citations: {results['avg_citations']:.2f}")
    print(f"Hype Score: {results['hype_score']:.3f}")
    print(f"Peak Year: {results['peak_year']}")
    print(f"Sustained Interest: {results['sustained_interest']}")
    
    # Show burst periods
    if results['burst_periods']:
        print(f"\nBurst Periods Detected: {len(results['burst_periods'])}")
        for i, burst in enumerate(results['burst_periods'], 1):
            print(f"  Burst {i}: {burst['start']} - {burst['end']} (Intensity: {burst['intensity']:.2f})")
    else:
        print("\nNo burst periods detected")
    
    return results

def example_2_comparative_analysis():
    """Example 2: Compare multiple devices"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Comparative Analysis")
    print("=" * 60)
    
    analyzer = FDADeviceHypeAnalyzer()
    
    # Define devices to compare
    devices = [
        ("Da Vinci Surgical System", "2000-07-11", "Surgical Robot"),
        ("HeartMate II LVAD", "2008-04-21", "Ventricular Assist Device"),
        ("CyberKnife System", "2001-08-22", "Radiosurgery")
    ]
    
    comparison_results = []
    
    for device_name, approval_date, device_type in devices:
        print(f"\nAnalyzing {device_name}...")
        try:
            results = analyzer.analyze_device_hype(device_name, approval_date)
            results['device_type'] = device_type
            comparison_results.append(results)
            print(f"  Hype Score: {results['hype_score']:.3f}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Create comparison table
    if comparison_results:
        comparison_df = pd.DataFrame([
            {
                'Device': r['device_name'],
                'Type': r['device_type'],
                'Hype Score': r['hype_score'],
                'Publications': r['total_publications'],
                'Citations': r['total_citations'],
                'Bursts': len(r['burst_periods'])
            }
            for r in comparison_results
        ])
        
        print(f"\nComparison Table:")
        print(comparison_df.to_string(index=False))
        
        # Find the highest hype device
        best_device = comparison_df.loc[comparison_df['Hype Score'].idxmax()]
        print(f"\nHighest Hype Device: {best_device['Device']} (Score: {best_device['Hype Score']:.3f})")
    
    return comparison_results

def example_3_hype_prediction():
    """Example 3: Predict hype for new devices"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Hype Prediction")
    print("=" * 60)
    
    analyzer = FDADeviceHypeAnalyzer()
    
    # Define hypothetical new devices
    new_devices = [
        {
            'name': 'Next-Gen Surgical Robot',
            'device_type': 'Surgical Robot',
            'approval_year': 2024,
            'features': ['AI-assisted', 'minimally invasive', 'high precision']
        },
        {
            'name': 'Smart Insulin Pump',
            'device_type': 'Diabetes Management',
            'approval_year': 2024,
            'features': ['closed-loop', 'continuous monitoring', 'mobile app']
        },
        {
            'name': 'Brain-Computer Interface',
            'device_type': 'Neuromodulation',
            'approval_year': 2024,
            'features': ['wireless', 'implantable', 'high bandwidth']
        }
    ]
    
    print("Predicting hype for new devices:")
    print("-" * 40)
    
    for device in new_devices:
        predicted_hype = analyzer.predict_device_hype({
            'device_type': device['device_type'],
            'approval_year': device['approval_year']
        })
        
        print(f"{device['name']}:")
        print(f"  Type: {device['device_type']}")
        print(f"  Predicted Hype Score: {predicted_hype:.3f}")
        print(f"  Features: {', '.join(device['features'])}")
        print()

def example_4_burst_analysis():
    """Example 4: Detailed burst analysis"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Burst Analysis")
    print("=" * 60)
    
    analyzer = FDADeviceHypeAnalyzer()
    
    # Analyze a device known for citation bursts
    device_name = "Da Vinci Surgical System"
    approval_date = "2000-07-11"
    
    print(f"Detailed burst analysis for {device_name}...")
    results = analyzer.analyze_device_hype(device_name, approval_date)
    
    if results['burst_periods']:
        print(f"\nFound {len(results['burst_periods'])} burst periods:")
        
        for i, burst in enumerate(results['burst_periods'], 1):
            duration = burst['end'] - burst['start']
            print(f"\nBurst {i}:")
            print(f"  Period: {burst['start']} - {burst['end']} ({duration} years)")
            print(f"  Intensity: {burst['intensity']:.2f} publications/year")
            
            # Analyze publications during this burst
            burst_pubs = results['publications_df'][
                (results['publications_df']['publication_year'] >= burst['start']) &
                (results['publications_df']['publication_year'] <= burst['end'])
            ]
            
            if not burst_pubs.empty:
                print(f"  Publications during burst: {len(burst_pubs)}")
                print(f"  Average citations during burst: {burst_pubs['cited_by_count'].mean():.2f}")
                
                # Show top journals during burst
                top_journals = burst_pubs['journal'].value_counts().head(3)
                print(f"  Top journals: {', '.join(top_journals.index.tolist())}")
    else:
        print("No burst periods detected for this device")

def example_5_temporal_analysis():
    """Example 5: Analyze temporal patterns"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Temporal Analysis")
    print("=" * 60)
    
    analyzer = FDADeviceHypeAnalyzer()
    
    # Analyze publications over time for a device
    device_name = "Da Vinci Surgical System"
    approval_date = "2000-07-11"
    
    print(f"Temporal analysis for {device_name}...")
    results = analyzer.analyze_device_hype(device_name, approval_date)
    
    if not results['publications_df'].empty:
        # Group by year and analyze trends
        yearly_data = results['publications_df'].groupby('publication_year').agg({
            'cited_by_count': ['count', 'sum', 'mean']
        }).reset_index()
        
        yearly_data.columns = ['year', 'publications', 'total_citations', 'avg_citations']
        
        print(f"\nYearly publication trends:")
        print("-" * 50)
        print(f"{'Year':<6} {'Pubs':<6} {'Citations':<10} {'Avg Cit':<8}")
        print("-" * 50)
        
        for _, row in yearly_data.iterrows():
            print(f"{row['year']:<6} {row['publications']:<6} {row['total_citations']:<10} {row['avg_citations']:<8.1f}")
        
        # Find peak years
        peak_pubs_year = yearly_data.loc[yearly_data['publications'].idxmax(), 'year']
        peak_citations_year = yearly_data.loc[yearly_data['total_citations'].idxmax(), 'year']
        
        print(f"\nPeak publication year: {peak_pubs_year}")
        print(f"Peak citation year: {peak_citations_year}")
        
        # Calculate lag between approval and peak activity
        approval_year = int(approval_date.split('-')[0])
        lag_to_peak = peak_pubs_year - approval_year
        print(f"Lag from approval to peak: {lag_to_peak} years")

def main():
    """Run all examples"""
    print("FDA Device Hype Analysis - Example Usage")
    print("This script demonstrates various analysis capabilities")
    
    try:
        # Run examples
        example_1_single_device_analysis()
        example_2_comparative_analysis()
        example_3_hype_prediction()
        example_4_burst_analysis()
        example_5_temporal_analysis()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure you have internet connection and the OpenAlex API is accessible.")

if __name__ == "__main__":
    main() 