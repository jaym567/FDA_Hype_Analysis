import pandas as pd

df = pd.read_csv('data/processed/devices.csv')

print('=== Advisory Panel Breakdown ===')
print(df['advisory_panel'].value_counts())

print('\n=== Sample Device Names by Panel ===')
for panel in df['advisory_panel'].unique()[:5]:
    print(f'\n{panel}:')
    samples = df[df['advisory_panel']==panel]['trade_name'].head(10).tolist()
    for s in samples:
        print(f'  - {s}')
