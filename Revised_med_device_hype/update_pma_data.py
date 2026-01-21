import requests
import json
import time
import csv
from datetime import datetime
import config

logger = config.setup_logger(__name__, config.RAW_DIR / "pma_updater.log")

def get_all_pma_numbers():
    """Get all unique PMA numbers from devices_surgical.csv"""
    devices_path = config.PROCESSED_DIR / "devices_surgical.csv"
    
    if not devices_path.exists():
        print("❌ devices_surgical.csv not found")
        return []
    
    pma_numbers = set()
    with open(devices_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pma = row.get('pma_number', '').strip()
            if pma:
                pma_numbers.add(pma)
    
    return sorted(list(pma_numbers))

def fetch_pma_data(pma_number):
    """Fetch detailed PMA data from FDA API"""
    url = config.OPENFDA_PMA_URL
    
    params = {
        'search': f'pma_number:"{pma_number}"',
        'limit': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            logger.warning(f"API error {response.status_code} for PMA {pma_number}")
            return None
        
        data = response.json()
        results = data.get('results', [])
        
        if results:
            return results[0]  # Return first match
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching PMA data for {pma_number}: {e}")
        return None

def fetch_updated_maude_data(pma_numbers):
    """Fetch updated MAUDE data for all PMA numbers"""
    print("🔍 Fetching updated MAUDE data...")
    
    all_events = []
    
    for i, pma in enumerate(pma_numbers):
        if i % 25 == 0:
            print(f"  Processing PMA {i+1}/{len(pma_numbers)}: {pma}")
        
        # Fetch MAUDE events for this PMA
        events = fetch_maude_for_pma(pma)
        all_events.extend(events)
        
        time.sleep(0.5)  # Rate limiting
    
    # Process and save
    processed_events = []
    for event in all_events:
        processed_event = {
            'pma_number': event.get('pma_pmn_number', ''),
            'report_number': event.get('report_number', ''),
            'event_date': clean_date(event.get('date_of_event', '')),
            'report_date': clean_date(event.get('date_received', '')),
            'event_type': event.get('event_type', ''),
            'product_code': get_device_product_code(event),
            'brand_name': get_device_brand_name(event),
            'manufacturer_name': get_device_manufacturer(event),
            'serious_injury': 1 if event.get('event_type') == 'Injury' else 0,
            'death': 1 if event.get('event_type') == 'Death' else 0,
            'malfunction': 1 if event.get('event_type') == 'Malfunction' else 0,
            'narrative': get_narrative(event)
        }
        processed_events.append(processed_event)
    
    # Remove duplicates and save
    unique_events = remove_duplicate_events(processed_events)
    save_maude_csv(unique_events)
    
    return unique_events

def fetch_maude_for_pma(pma_number):
    """Fetch MAUDE events for a single PMA"""
    url = "https://api.fda.gov/device/event.json"
    
    params = {
        'search': f'pma_pmn_number:"{pma_number}"',
        'limit': 100
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 404:
            return []
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        return data.get('results', [])
        
    except Exception as e:
        logger.error(f"Error fetching MAUDE for PMA {pma_number}: {e}")
        return []

def fetch_updated_recall_data(pma_numbers):
    """Fetch updated recall data for all PMA numbers"""
    print("🔍 Fetching updated recall data...")
    
    all_recalls = []
    
    for i, pma in enumerate(pma_numbers):
        if i % 25 == 0:
            print(f"  Processing PMA {i+1}/{len(pma_numbers)}: {pma}")
        
        # Fetch recalls for this PMA
        recalls = fetch_recalls_for_pma(pma)
        all_recalls.extend(recalls)
        
        time.sleep(0.5)  # Rate limiting
    
    # Process and save
    processed_recalls = []
    for recall in all_recalls:
        processed_recall = {
            'recall_number': recall.get('recall_number', ''),
            'pma_numbers': pma,  # The PMA we searched for
            'product_code': recall.get('product_code', ''),
            'classification': recall.get('classification', ''),
            'reason_for_recall': recall.get('reason_for_recall', ''),
            'root_cause_description': recall.get('root_cause_description', ''),
            'recall_initiation_date': clean_date(recall.get('recall_initiation_date', '')),
            'report_date': clean_date(recall.get('report_date', '')),
            'termination_date': clean_date(recall.get('termination_date', '')),
            'status': recall.get('status', ''),
            'product_description': recall.get('product_description', ''),
            'recalling_firm': recall.get('recalling_firm', '')
        }
        processed_recalls.append(processed_recall)
    
    # Remove duplicates and save
    unique_recalls = remove_duplicate_recalls(processed_recalls)
    save_recalls_csv(unique_recalls)
    
    return unique_recalls

def fetch_recalls_for_pma(pma_number):
    """Fetch recalls for a single PMA"""
    url = config.OPENFDA_RECALL_URL
    
    # Try different search strategies
    search_queries = [
        f'openfda.pma_number:"{pma_number}"',
        f'product_description:"{pma_number}"'
    ]
    
    all_results = []
    
    for query in search_queries:
        params = {
            'search': query,
            'limit': 50
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                all_results.extend(results)
            
        except Exception as e:
            continue
    
    return all_results

def get_device_product_code(event):
    """Extract product code from MAUDE event"""
    devices = event.get('device', [])
    if devices:
        return devices[0].get('device_report_product_code', '')
    return ''

def get_device_brand_name(event):
    """Extract brand name from MAUDE event"""
    devices = event.get('device', [])
    if devices:
        return devices[0].get('brand_name', '')
    return ''

def get_device_manufacturer(event):
    """Extract manufacturer from MAUDE event"""
    devices = event.get('device', [])
    if devices:
        return devices[0].get('manufacturer_d_name', '')
    return ''

def get_narrative(event):
    """Extract narrative from MAUDE event"""
    mdr_text = event.get('mdr_text', [])
    if mdr_text:
        texts = [item.get('text', '') for item in mdr_text]
        return ' '.join(texts)[:2000]  # Limit length
    return ''

def clean_date(date_str):
    """Clean date format from YYYYMMDD to YYYY-MM-DD"""
    if not date_str:
        return ''
    
    date_str = str(date_str)
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    return date_str

def remove_duplicate_events(events):
    """Remove duplicate MAUDE events"""
    seen = set()
    unique = []
    
    for event in events:
        key = (event['report_number'], event['pma_number'])
        if key not in seen:
            seen.add(key)
            unique.append(event)
    
    return unique

def remove_duplicate_recalls(recalls):
    """Remove duplicate recalls"""
    seen = set()
    unique = []
    
    for recall in recalls:
        key = recall['recall_number']
        if key and key not in seen:
            seen.add(key)
            unique.append(recall)
    
    return unique

def save_maude_csv(events):
    """Save MAUDE events to CSV"""
    output_path = config.PROCESSED_DIR / "maude_events_updated.csv"
    
    fieldnames = [
        'pma_number', 'report_number', 'event_date', 'report_date',
        'event_type', 'product_code', 'brand_name', 'manufacturer_name',
        'serious_injury', 'death', 'malfunction', 'narrative'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)
    
    print(f"✅ Saved {len(events)} MAUDE events to maude_events_updated.csv")

def save_recalls_csv(recalls):
    """Save recalls to CSV"""
    output_path = config.PROCESSED_DIR / "recalls_events_updated.csv"
    
    fieldnames = [
        'recall_number', 'pma_numbers', 'product_code', 'classification',
        'reason_for_recall', 'root_cause_description', 'recall_initiation_date',
        'report_date', 'termination_date', 'status', 'product_description',
        'recalling_firm'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(recalls)
    
    print(f"✅ Saved {len(recalls)} recalls to recalls_events_updated.csv")

def main():
    """Main function to update all PMA-related data"""
    print("🚀 Starting PMA data update for surgical devices...")
    
    # Get all PMA numbers
    pma_numbers = get_all_pma_numbers()
    print(f"📊 Found {len(pma_numbers)} unique PMA numbers")
    
    if not pma_numbers:
        print("❌ No PMA numbers found")
        return
    
    # Fetch updated MAUDE data
    maude_events = fetch_updated_maude_data(pma_numbers)
    print(f"📚 Collected {len(maude_events)} MAUDE events")
    
    # Fetch updated recall data
    recall_events = fetch_updated_recall_data(pma_numbers)
    print(f"📚 Collected {len(recall_events)} recall events")
    
    print("🎉 PMA data update complete!")

if __name__ == "__main__":
    main()