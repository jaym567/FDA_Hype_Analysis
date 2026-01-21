import requests
import json
import time
import csv
from datetime import datetime
import config

def fetch_recalls_for_surgical_devices_exact():
    """
    Fetch recall data for EXACTLY the devices in devices_surgical.csv
    No more, no less - precise matching only
    """
    
    # Read ALL devices from surgical CSV
    devices_path = config.PROCESSED_DIR / "devices_surgical.csv"
    if not devices_path.exists():
        print("❌ devices_surgical.csv not found")
        return
    
    devices = []
    with open(devices_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            devices.append({
                'pma_number': row['pma_number'],
                'supplement_number': row.get('supplement_number', ''),
                'trade_name': row.get('trade_name', ''),
                'product_code': row.get('product_code', ''),
                'applicant': row.get('applicant', '')
            })
    
    print(f"📊 Processing recall data for {len(devices)} surgical devices")
    
    # Get unique PMA numbers from our surgical devices
    pma_numbers = list(set([d['pma_number'] for d in devices if d['pma_number']]))
    print(f"🔍 Searching {len(pma_numbers)} unique PMA numbers")
    
    all_recalls = []
    
    # Fetch recalls for each PMA
    for i, pma in enumerate(pma_numbers):
        if i % 25 == 0:
            print(f"  Processing PMA {i+1}/{len(pma_numbers)}: {pma}")
        
        recalls = fetch_recalls_for_pma(pma)
        
        # Tag recalls with the PMA they came from
        for recall in recalls:
            recall['source_pma'] = pma
            all_recalls.append(recall)
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"📚 Total recall records found: {len(all_recalls)}")
    
    # Process recalls to match our exact format
    processed_recalls = process_recall_events(all_recalls, devices)
    
    # Save results
    save_recall_events(processed_recalls)
    
    return processed_recalls

def fetch_recalls_for_pma(pma_number):
    """Fetch recall events for a single PMA number"""
    url = config.OPENFDA_RECALL_URL
    all_results = []
    
    # Try multiple search strategies for recalls
    search_queries = [
        f'openfda.pma_number:"{pma_number}"',  # Primary field
        f'product_description:"{pma_number}"',  # Sometimes PMA is in description
        f'res_event_number:"{pma_number}"'      # Alternative field
    ]
    
    for query in search_queries:
        params = {
            'search': query,
            'limit': 100
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 404:
                continue
            
            if response.status_code == 429:
                print(f"    ⏳ Rate limited for {pma_number} - waiting...")
                time.sleep(2)
                continue
            
            if response.status_code != 200:
                continue
            
            data = response.json()
            results = data.get('results', [])
            all_results.extend(results)
            
        except Exception as e:
            continue
    
    # Remove duplicates based on recall number
    seen_recalls = set()
    unique_recalls = []
    for recall in all_results:
        recall_id = recall.get('recall_number') or recall.get('product_res_number') or recall.get('cfres_id')
        if recall_id and recall_id not in seen_recalls:
            seen_recalls.add(recall_id)
            unique_recalls.append(recall)
    
    return unique_recalls

def process_recall_events(raw_recalls, devices):
    """Process recall events to match our surgical devices exactly"""
    processed = []
    seen_recalls = set()
    
    # Create lookup for our surgical devices
    device_lookup = {}
    for device in devices:
        pma = device['pma_number']
        if pma not in device_lookup:
            device_lookup[pma] = []
        device_lookup[pma].append(device)
    
    for recall in raw_recalls:
        # Get recall identifier
        recall_number = (recall.get('recall_number') or 
                        recall.get('product_res_number') or 
                        recall.get('cfres_id') or '')
        
        if not recall_number or recall_number in seen_recalls:
            continue
        seen_recalls.add(recall_number)
        
        # Check if this recall is linked to our surgical devices
        openfda = recall.get('openfda', {})
        linked_pmas = openfda.get('pma_number', [])
        
        # Find which of our PMAs this recall affects
        matching_pmas = []
        for pma in linked_pmas:
            if pma in device_lookup:
                matching_pmas.append(pma)
        
        # Also check if source PMA is in our list
        source_pma = recall.get('source_pma', '')
        if source_pma and source_pma in device_lookup:
            if source_pma not in matching_pmas:
                matching_pmas.append(source_pma)
        
        # Only include if this recall affects our surgical devices
        if not matching_pmas:
            continue
        
        # Create recall record
        processed_recall = {
            'recall_number': recall_number,
            'pma_numbers': ';'.join(matching_pmas),  # List all affected PMAs
            'product_code': recall.get('product_code', ''),
            'classification': clean_classification(recall.get('classification', '')),
            'reason_for_recall': recall.get('reason_for_recall', ''),
            'root_cause_description': recall.get('root_cause_description', ''),
            'recall_initiation_date': clean_date(recall.get('recall_initiation_date') or recall.get('event_date_initiated')),
            'report_date': clean_date(recall.get('report_date') or recall.get('event_date_posted')),
            'termination_date': clean_date(recall.get('termination_date') or recall.get('event_date_terminated')),
            'status': recall.get('status') or recall.get('recall_status', ''),
            'product_description': recall.get('product_description', ''),
            'recalling_firm': recall.get('recalling_firm', ''),
            'distribution_pattern': recall.get('distribution_pattern', ''),
            'recall_quantity': recall.get('code_info', '')
        }
        
        processed.append(processed_recall)
    
    return processed

def clean_classification(classification):
    """Clean recall classification"""
    if not classification:
        return ''
    
    # Normalize "Class I" to "I", etc.
    classification = str(classification).replace('Class ', '').strip()
    return classification

def clean_date(date_str):
    """Convert various date formats to YYYY-MM-DD"""
    if not date_str:
        return ''
    
    date_str = str(date_str)
    
    # Handle YYYYMMDD format
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    # Handle YYYY-MM-DD format (already clean)
    if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str
    
    return date_str

def save_recall_events(recalls):
    """Save recall events to CSV"""
    if not recalls:
        print("❌ No recall events to save")
        return
    
    output_path = config.PROCESSED_DIR / "recalls_events_surgical_exact.csv"
    
    fieldnames = [
        'recall_number', 'pma_numbers', 'product_code', 'classification',
        'reason_for_recall', 'root_cause_description', 'recall_initiation_date',
        'report_date', 'termination_date', 'status', 'product_description',
        'recalling_firm', 'distribution_pattern', 'recall_quantity'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(recalls)
    
    print(f"✅ Saved {len(recalls)} recall events to recalls_events_surgical_exact.csv")
    
    # Show summary
    classifications = {}
    for recall in recalls:
        classification = recall['classification'] or 'Unknown'
        classifications[classification] = classifications.get(classification, 0) + 1
    
    print("📊 Recall classification breakdown:")
    for classification, count in classifications.items():
        print(f"  Class {classification}: {count}")
    
    # Show status breakdown
    statuses = {}
    for recall in recalls:
        status = recall['status'] or 'Unknown'
        statuses[status] = statuses.get(status, 0) + 1
    
    print("📊 Recall status breakdown:")
    for status, count in statuses.items():
        print(f"  {status}: {count}")

if __name__ == "__main__":
    print("🚀 Fetching recall data for surgical devices (exact match)...")
    fetch_recalls_for_surgical_devices_exact()
    print("🎉 Recall data collection complete!")