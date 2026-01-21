import pandas as pd
from pathlib import Path

csv_path = Path(r'c:\Users\jaymo\OneDrive\Desktop\ARGOS\medical_device_hype\FDA_Hype_Analysis\Revised_med_device_hype\data\processed\publications_surgical.csv')

if not csv_path.exists():
    print(f"File not found: {csv_path}")
else:
    df = pd.read_csv(csv_path)
    print(f"Total Publications: {len(df)}")
    print(f"Unique PMAs with papers: {df['device_pma_number'].nunique()}")
    print("\n--- Match Quality Audit ---")
    summary = df[['device_pma_number', 'trade_name']].drop_duplicates()
    print(summary.head(20))
