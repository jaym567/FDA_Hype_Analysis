import pandas as pd
import sys
from pathlib import Path

# Add current directory and subdirectory to path for imports to work
sys.path.append(str(Path.cwd()))
sys.path.append(str(Path.cwd() / "Revised_med_device_hype"))

import config
from collect_surgical_publications_and_analysis import SurgicalPublicationAnalyzer

def main():
    devices_path = config.PROCESSED_DIR / "devices_surgical.csv"
    pubs_path = config.PROCESSED_DIR / "publications_surgical.csv"
    
    if not pubs_path.exists():
        print(f"Error: {pubs_path} not found.")
        return

    print(f"Finalizing analysis for {pubs_path}...")
    analyzer = SurgicalPublicationAnalyzer(devices_path)
    pubs_df = pd.read_csv(pubs_path)
    
    analysis_df = analyzer.analyze_hype(pubs_df, devices_path)
    print(f"Successfully generated analysis for {len(analysis_df)} devices.")

if __name__ == "__main__":
    main()
