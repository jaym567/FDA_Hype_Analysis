import pandas as pd
from pathlib import Path

def audit_final():
    analysis_file = Path('Revised_med_device_hype/data/processed/publication_analysis_surgical.csv')
    pubs_file = Path('Revised_med_device_hype/data/processed/publications_surgical.csv')
    
    if not analysis_file.exists() or not pubs_file.exists():
        print("Required files not found.")
        return
        
    df_analysis = pd.read_csv(analysis_file)
    df_pubs = pd.read_csv(pubs_file)
    
    print(f"--- Final Production Audit ---")
    print(f"Total Unique Devices: {len(df_analysis)}")
    print(f"Devices with Publications: {len(df_analysis[df_analysis.total_publications > 0])}")
    print(f"Total Combined Publications: {len(df_pubs)}")
    print(f"Total Identified RCTs: {df_analysis.num_rcts.sum()}")
    print(f"Total Identified Observational: {df_analysis.num_observational.sum()}")
    
    print("\n--- Top 15 Devices by Publication Volume ---")
    top_15 = df_analysis.nlargest(15, 'total_publications')
    print(top_15[['pma_number', 'trade_name', 'total_publications', 'num_rcts', 'num_observational']].to_string(index=False))

if __name__ == "__main__":
    audit_final()
