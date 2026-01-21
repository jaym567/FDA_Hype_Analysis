import pandas as pd
import random

# Load full dataset with surgical flag
df = pd.read_csv('data/processed/devices_surgical.csv')
df['is_surgical'] = True

# Load original to get excluded devices
df_all = pd.read_csv('data/processed/devices.csv')
df_all['is_surgical'] = df_all['pma_number'].isin(df['pma_number'])

surgical = df_all[df_all['is_surgical']]
non_surgical = df_all[~df_all['is_surgical']]

print("=" * 80)
print("SURGICAL FILTER VALIDATION")
print("=" * 80)

print(f"\nTotal devices: {len(df_all)}")
print(f"Classified as SURGICAL: {len(surgical)} ({len(surgical)/len(df_all)*100:.1f}%)")
print(f"Classified as NON-SURGICAL: {len(non_surgical)} ({len(non_surgical)/len(df_all)*100:.1f}%)")

# Sample surgical devices by panel
print("\n" + "=" * 80)
print("SAMPLE SURGICAL DEVICES (Should all be truly surgical)")
print("=" * 80)

for panel in surgical['advisory_panel'].unique():
    panel_devices = surgical[surgical['advisory_panel'] == panel]
    sample_size = min(10, len(panel_devices))
    samples = panel_devices.sample(n=sample_size, random_state=42)
    
    print(f"\n{panel} ({len(panel_devices)} devices):")
    for idx, row in samples.iterrows():
        print(f"  ✓ {row['trade_name']}")

# Sample non-surgical devices by panel
print("\n" + "=" * 80)
print("SAMPLE NON-SURGICAL DEVICES (Should all be correctly excluded)")
print("=" * 80)

for panel in non_surgical['advisory_panel'].unique():
    panel_devices = non_surgical[non_surgical['advisory_panel'] == panel]
    sample_size = min(10, len(panel_devices))
    if len(panel_devices) > 0:
        samples = panel_devices.sample(n=sample_size, random_state=42)
        
        print(f"\n{panel} ({len(panel_devices)} devices):")
        for idx, row in samples.iterrows():
            print(f"  ✗ {row['trade_name']}")

# Edge cases to review
print("\n" + "=" * 80)
print("POTENTIAL EDGE CASES TO REVIEW")
print("=" * 80)

# Check for ambiguous keywords
ambiguous_surgical = surgical[surgical['trade_name'].str.contains('SYSTEM|KIT|SET', na=False, case=False)]
if len(ambiguous_surgical) > 0:
    print(f"\nSurgical devices with 'SYSTEM/KIT/SET' ({len(ambiguous_surgical)}):")
    for name in ambiguous_surgical['trade_name'].head(10):
        print(f"  ? {name}")

ambiguous_nonsurgical = non_surgical[non_surgical['trade_name'].str.contains('IMPLANT|PROSTHESIS|GRAFT', na=False, case=False)]
if len(ambiguous_nonsurgical) > 0:
    print(f"\nNon-surgical devices with 'IMPLANT/PROSTHESIS/GRAFT' ({len(ambiguous_nonsurgical)}):")
    for name in ambiguous_nonsurgical['trade_name'].head(10):
        print(f"  ? {name}")
