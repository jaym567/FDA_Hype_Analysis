import pandas as pd
from datetime import datetime

def test_window_calc():
    df = pd.read_csv('Revised_med_device_hype/data/processed/devices_surgical.csv')
    sample = df[['pma_number', 'trade_name', 'decision_date']].drop_duplicates('pma_number').head(10)
    
    for _, row in sample.iterrows():
        pma = row['pma_number']
        date_str = row['decision_date']
        
        try:
            decision_date = datetime.strptime(date_str, '%Y-%m-%d')
            decision_year = decision_date.year
            start_year = decision_year - 5
            end_year = decision_year + 10
            
            print(f"PMA: {pma} | Approved: {date_str} | Window: {start_year} to {end_year}")
        except Exception as e:
            print(f"Error for {pma}: {e}")

if __name__ == "__main__":
    test_window_calc()
