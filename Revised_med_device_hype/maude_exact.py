import requests
import json
import time
import csv
from datetime import datetime
import config

def fetch_maude_for_surgical_devices_exact():
    """
    Fetch MAUDE data for EXACTLY the devices in devices_surgical.csv
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
    
    print(f"📊 Processing MAUDE data for {len(devices)} surgical devices")
    
    # Get unique PMA numbers from our surgical devices
    pma_numbers = list(set([d['pma_number'] for d in devices if d['pma_number']]))
    print(f"🔍 Searching {len(pma_numbers)} unique PMA numbers")
    
    all_events = []
    
    # Fetch MAUDE events for each PMA
    for i, pma in enumerate(pma_numbers):
        if i % 25 == 0:
            print(f"  Processing PMA {i+1}/{len(pma_numbers)}: {pma}")
        
        events = fetch_maude_for_pma(pma)
        
        # Tag events with the PMA they came from
        for event in events:
            event['source_pma'] = pma
            all_events.append(event)
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"📚 Total MAUDE events found: {len(all_events)}")
    
    # Process events to match our exact format
    processed_events = process_maude_events(all_events, devices)
    
    # Save results
    save_maude_events(processed_events)
    
    return processed_events

def fetch_maude_for_pma(pma_number):
    """Fetch MAUDE events for a single PMA number"""
    url = "https://api.fda.gov/device/event.json"
    
    params = {
        'search': f'pma_pmn_number:"{pma_number}"',
        'limit': 100  # Reasonable limit per PMA
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 404:
            return []
        
        if response.status_code == 429:
            print(f"    ⏳ Rate limited for {pma_number} - waiting...")
            time.sleep(2)
            return []
        
        if response.status_code != 200:
            print(f"    ❌ API error for {pma_number}: {response.status_code}")
            return []
        
        data = response.json()
        return data.get('results', [])
        
    except Exception as e:
        print(f"    ❌ Error fetching {pma_number}: {e}")
        return []

def process_maude_events(raw_events, devices):
    """Process MAUDE events to match our surgical devices exactly"""
    processed = []
    seen_reports = set()
    
    # Create lookup for our surgical devices
    device_lookup = {}
    for device in devices:
        pma = device['pma_number']
        if pma not in device_lookup:
            device_lookup[pma] = []
        device_lookup[pma].append(device)
    
    for event in raw_events:
        report_number = event.get('report_number')
        if report_number in seen_reports:
            continue
        seen_reports.add(report_number)
        
        # Get event details
        pma_number = event.get('pma_pmn_number', '')
        event_date = event.get('date_of_event', '')
        event_type = event.get('event_type', '')
        
        # Only include if this PMA is in our surgical devices
        if pma_number not in device_lookup:
            continue
        
        # Clean date format
        if event_date and len(str(event_date)) == 8:
            date_str = str(event_date)
            event_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # Get device information from the event
        devices_in_event = event.get('device', [])
        device_info = devices_in_event[0] if devices_in_event else {}
        
        # Create event record
        processed_event = {
            'pma_number': pma_number,
            'report_number': report_number,
            'event_date': event_date,
            'report_date': clean_date(event.get('date_received', '')),
            'event_type': event_type,
            'device_product_code': device_info.get('device_report_product_code', ''),
            'brand_name': device_info.get('brand_name', ''),
            'manufacturer_name': device_info.get('manufacturer_d_name', ''),
            'serious_injury': 1 if event_type == 'Injury' else 0,
            'death': 1 if event_type == 'Death' else 0,
            'malfunction': 1 if event_type == 'Malfunction' else 0,
            'narrative': extract_narrative(event)
        }
        
        # Only include events with required fields
        if event_date and event_type:
            processed.append(processed_event)
    
    return processed

def extract_narrative(event):
    """Extract narrative text from MAUDE event"""
    mdr_text = event.get('mdr_text', [])
    if not mdr_text:
        return ''
    
    narratives = []
    for text_item in mdr_text:
        text = text_item.get('text', '')
        if text:
            narratives.append(text)
    
    full_narrative = ' '.join(narratives)
    return full_narrative[:2000] if full_narrative else ''  # Limit length

def clean_date(date_str):
    """Convert YYYYMMDD to YYYY-MM-DD"""
    if not date_str:
        return ''
    
    date_str = str(date_str)
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    return date_str

def save_maude_events(events):
    """Save MAUDE events to CSV"""
    if not events:
        print("❌ No MAUDE events to save")
        return
    
    output_path = config.PROCESSED_DIR / "maude_events_surgical_exact.csv"
    
    fieldnames = [
        'pma_number', 'report_number', 'event_date', 'report_date',
        'event_type', 'device_product_code', 'brand_name', 'manufacturer_name',
        'serious_injury', 'death', 'malfunction', 'narrative'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)
    
    print(f"✅ Saved {len(events)} MAUDE events to maude_events_surgical_exact.csv")
    
    # Show summary
    event_types = {}
    for event in events:
        event_type = event['event_type']
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print("📊 Event type breakdown:")
    for event_type, count in event_types.items():
        print(f"  {event_type}: {count}")

if __name__ == "__main__":
    print("🚀 Fetching MAUDE data for surgical devices (exact match)...")
    fetch_maude_for_surgical_devices_exact()
    print("🎉 MAUDE data collection complete!")