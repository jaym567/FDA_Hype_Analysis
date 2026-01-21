import json
import os
from pathlib import Path

def check_json_for_date():
    json_dir = Path("Revised_med_device_hype/data/raw/openalex")
    files = list(json_dir.glob("*.json"))
    if not files:
        print("No JSON files found.")
        return
    
    with open(files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Check first result if it exists
        if data and isinstance(data, list):
            item = data[0]
            print(f"Sample Result from {files[0].name}:")
            print(f"publication_date: {item.get('publication_date')}")
            print(f"available keys: {list(item.keys())}")
        elif data and isinstance(data, dict):
            results = data.get('results', [])
            if results:
                item = results[0]
                print(f"Sample Result from {files[0].name}:")
                print(f"publication_date: {item.get('publication_date')}")
                print(f"available keys: {list(item.keys())}")
        else:
            print(f"No results or unexpected format in {files[0].name}")

if __name__ == "__main__":
    check_json_for_date()
