
import pandas as pd
from pathlib import Path
import config

def validate_datasets():
    print("\n--- Data Validation & Date Audit ---\n")
    
    files = [
        {
            "name": "devices.csv",
            "path": config.PROCESSED_DIR / "devices.csv",
            "date_col": "decision_date"
        },
        {
            "name": "devices_surgical.csv",
            "path": config.PROCESSED_DIR / "devices_surgical.csv",
            "date_col": "decision_date"
        },
        {
            "name": "recalls_events.csv",
            "path": config.PROCESSED_DIR / "recalls_events.csv",
            "date_col": "recall_initiation_date"
        },
        {
            "name": "publications.csv",
            "path": config.PROCESSED_DIR / "publications.csv",
            "date_col": "publication_date"
        },
        {
            "name": "publications_surgical.csv",
            "path": config.PROCESSED_DIR / "publications_surgical.csv",
            "date_col": "publication_date"
        },
        {
            "name": "maude_events.csv",
            "path": config.PROCESSED_DIR / "maude_events.csv",
            "date_col": "event_date"
        }
    ]
    
    for f in files:
        p = f['path']
        name = f['name']
        date_col = f['date_col']
        
        if not p.exists():
            print(f"❌ {name}: File not found.")
            continue
            
        try:
            df = pd.read_csv(p)
            count = len(df)
            
            if date_col not in df.columns:
                print(f"❌ {name}: Missing required date column '{date_col}'")
                continue
                
            # Date stats
            dates = pd.to_datetime(df[date_col], errors='coerce')
            valid_dates = dates.dropna()
            
            if len(valid_dates) == 0:
                print(f"⚠️ {name}: {count} rows, BUT 0 valid dates in '{date_col}'")
            else:
                min_date = valid_dates.min().strftime('%Y-%m-%d')
                max_date = valid_dates.max().strftime('%Y-%m-%d')
                print(f"✅ {name}: {count} rows, {date_col} {min_date} to {max_date}")
                
        except Exception as e:
            print(f"❌ {name}: Error reading file - {e}")

if __name__ == "__main__":
    validate_datasets()
