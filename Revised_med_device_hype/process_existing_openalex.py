import json
import csv
from pathlib import Path
import config

def process_existing_openalex_data():
    """
    Process existing OpenAlex batch files to create publications.csv
    """
    
    # Find all existing batch files
    openalex_dir = config.RAW_OPENALEX_DIR
    batch_files = list(openalex_dir.glob("pubs_batch_*.json"))
    
    if not batch_files:
        print("❌ No existing OpenAlex batch files found")
        return
    
    print(f"📁 Found {len(batch_files)} batch files to process")
    
    all_publications = []
    
    # Process each batch file
    for batch_file in batch_files:
        print(f"📖 Processing {batch_file.name}...")
        
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            if isinstance(batch_data, list):
                for pub in batch_data:
                    processed_pub = process_publication(pub)
                    if processed_pub:
                        all_publications.append(processed_pub)
            
            print(f"  ✓ Processed {len(batch_data) if isinstance(batch_data, list) else 0} publications")
            
        except Exception as e:
            print(f"  ❌ Error processing {batch_file.name}: {e}")
            continue
    
    print(f"📚 Total publications collected: {len(all_publications)}")
    
    # Remove duplicates
    unique_pubs = remove_duplicates(all_publications)
    print(f"📚 Unique publications: {len(unique_pubs)}")
    
    # Save to CSV
    if unique_pubs:
        save_publications_csv(unique_pubs)
    else:
        print("❌ No publications to save")

def process_publication(raw_pub):
    """Process a single publication from raw OpenAlex data"""
    try:
        # Extract required fields
        openalex_id = raw_pub.get('id', '')
        doi = raw_pub.get('doi', '')
        title = raw_pub.get('title', '')
        
        # Publication dates
        pub_date = raw_pub.get('publication_date', '')
        pub_year = raw_pub.get('publication_year', '')
        
        # Abstract reconstruction
        abstract = reconstruct_abstract(raw_pub.get('abstract_inverted_index', {}))
        
        # Venue information
        venue = ''
        primary_location = raw_pub.get('primary_location', {})
        if primary_location and primary_location.get('source'):
            venue = primary_location['source'].get('display_name', '')
        
        # Citation count
        cited_by_count = raw_pub.get('cited_by_count', 0)
        
        # Open access
        is_oa = raw_pub.get('open_access', {}).get('is_oa', False)
        
        # Publication type
        pub_type = raw_pub.get('type', '')
        
        # Device info (from our search)
        pma_number = raw_pub.get('device_pma_number', '')
        search_query = raw_pub.get('search_term_used', '')
        
        # Only include if we have essential fields
        if not title or not pub_year:
            return None
        
        return {
            'pma_number': pma_number,
            'openalex_id': openalex_id,
            'doi': doi,
            'title': title,
            'publication_date': pub_date,
            'publication_year': pub_year,
            'abstract': abstract[:3000] if abstract else '',  # Limit length
            'venue': venue,
            'cited_by_count': cited_by_count,
            'is_oa': is_oa,
            'type': pub_type,
            'search_query': search_query
        }
        
    except Exception as e:
        print(f"❌ Error processing publication: {e}")
        return None

def reconstruct_abstract(inverted_index):
    """Reconstruct abstract from OpenAlex inverted index"""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    
    try:
        # Create list of (position, word) pairs
        word_positions = []
        for word, positions in inverted_index.items():
            if isinstance(positions, list):
                for pos in positions:
                    word_positions.append((pos, word))
        
        # Sort by position and reconstruct text
        word_positions.sort(key=lambda x: x[0])
        return " ".join([word for pos, word in word_positions])
        
    except Exception as e:
        print(f"❌ Error reconstructing abstract: {e}")
        return ""

def remove_duplicates(publications):
    """Remove duplicate publications based on OpenAlex ID"""
    seen_ids = set()
    unique_pubs = []
    
    for pub in publications:
        pub_id = pub.get('openalex_id', '')
        if pub_id and pub_id not in seen_ids:
            seen_ids.add(pub_id)
            unique_pubs.append(pub)
        elif not pub_id:
            # If no OpenAlex ID, use title as fallback
            title = pub.get('title', '')
            if title and title not in seen_ids:
                seen_ids.add(title)
                unique_pubs.append(pub)
    
    return unique_pubs

def save_publications_csv(publications):
    """Save publications to CSV with exact required fields"""
    output_path = config.PROCESSED_DIR / "publications.csv"
    
    # Exact field order as requested
    fieldnames = [
        'pma_number',
        'openalex_id',
        'doi', 
        'title',
        'publication_date',
        'publication_year',
        'abstract',
        'venue',
        'cited_by_count',
        'is_oa',
        'type',
        'search_query'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(publications)
    
    print(f"✅ Saved {len(publications)} publications to publications.csv")

if __name__ == "__main__":
    print("🔄 Processing existing OpenAlex data...")
    process_existing_openalex_data()
    print("🎉 Processing complete!")