import requests
import json

url = "https://api.fda.gov/device/event.json"
pmas = ["P150012", "P000009"]
q_terms = " OR ".join([f'"{p}"' for p in pmas])
query = f'pma_pmn_number:({q_terms})'
print(f"Testing Batch Query: {query}")
params = {'search': query, 'limit': 1}
resp = requests.get(url, params=params)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Total results: {data.get('meta', {}).get('results', {}).get('total', 0)}")
