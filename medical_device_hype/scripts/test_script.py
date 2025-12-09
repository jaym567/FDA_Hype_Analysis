#!/usr/bin/env python3
"""
Simple test script for the FDA Device Hype Analyzer
"""

from fda_device_hype_analysis import FDADeviceHypeAnalyzer

def test_basic_functionality():
    """Test basic functionality without making API calls"""
    print("Testing FDA Device Hype Analyzer...")
    
    # Initialize analyzer
    analyzer = FDADeviceHypeAnalyzer()
    
    # Test FDA data loading
    print(f"✓ Loaded {len(analyzer.fda_pma_data)} sample FDA devices")
    
    # Test hype prediction
    test_device = {
        'device_type': 'Surgical Robot',
        'approval_year': 2023
    }
    predicted_hype = analyzer.predict_device_hype(test_device)
    print(f"✓ Hype prediction works: {predicted_hype:.3f}")
    
    # Test burst detection with sample data
    sample_time_series = [(2018, 5), (2019, 8), (2020, 15), (2021, 12), (2022, 6)]
    bursts = analyzer.kleinberg_burst_detection(sample_time_series)
    print(f"✓ Burst detection works: found {len(bursts)} bursts")
    
    # Test hype score calculation
    hype_score = analyzer._calculate_hype_score(50, 500, 25, 2)
    print(f"✓ Hype score calculation works: {hype_score:.3f}")
    
    print("\nAll basic functionality tests passed!")
    return True

def test_sample_data():
    """Test with sample FDA data"""
    print("\nTesting with sample FDA data...")
    
    analyzer = FDADeviceHypeAnalyzer()
    
    # Show sample devices
    print("Sample FDA devices:")
    for i, (_, device) in enumerate(analyzer.fda_pma_data.iterrows(), 1):
        print(f"  {i}. {device['device_name']} ({device['device_type']}) - {device['approval_date']}")
    
    # Test prediction for each device type
    device_types = analyzer.fda_pma_data['device_type'].unique()
    print(f"\nDevice types found: {len(device_types)}")
    
    for device_type in device_types:
        predicted_hype = analyzer.predict_device_hype({
            'device_type': device_type,
            'approval_year': 2023
        })
        print(f"  {device_type}: {predicted_hype:.3f}")

if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_sample_data()
        print("\n✓ All tests completed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}") 