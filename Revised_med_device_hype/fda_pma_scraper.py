
import requests
import pandas as pd
import json
import time
from datetime import datetime
from tqdm import tqdm
import config

logger = config.setup_logger(__name__, config.RAW_DIR / "fda_scraper.log")

def fetch_surgical_pma_data(start_year=2000, end_year=2020, advisory_committees=None, include_supplements=False):
    """
    Fetch PMA data from openFDA for specified advisory committees and year range.
    
    Args:
        start_year (int): Start year (inclusive)
        end_year (int): End year (inclusive)
        advisory_committees (list[str]): List of FDA advisory committee descriptions to filter by.
        include_supplements (bool): If True, fetch all supplements. If False, try to limit to original PMAs (approx).
    
    Returns:
        pd.DataFrame: Processed dataframe of unique devices.
    """
    
    if advisory_committees is None:
        advisory_committees = config.ADVISORY_COMMITTEES
        
    all_records = []
    
    # OpenFDA limited to 25000 records per query, but also 1000 limit deep paging without search_after (which is complex).
    # Best strategy: Iterate by year and committee to keep result sets small.
    
    logger.info(f"Starting PMA fetch for years {start_year}-{end_year} across {len(advisory_committees)} panels.")
    
    for committee in advisory_committees:
        logger.info(f"Fetching data for committee: {committee}")
        
        # Clean specific committee string for URL if needed, but requests handles params well.
        # Generally searching "advisory_committee_description" requires exact phrase matching.
        
        for year in range(start_year, end_year + 1):
            date_query = f"decision_date:[{year}-01-01 TO {year}-12-31]"
            committee_query = f'advisory_committee_description:"{committee}"'
            
            # Combine queries
            # Syntax: date AND committee
            query = f"{date_query} AND {committee_query}"
            
            records = _fetch_with_pagination(query)
            
            logger.info(f"  Year {year}: Found {len(records)} records")
            
            # Save raw batch
            if records:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                short_comm = committee.split()[0].replace('/', '_')
                raw_filename = config.RAW_PMA_DIR / f"pma_{short_comm}_{year}_{timestamp}.json"
                with open(raw_filename, 'w') as f:
                    json.dump(records, f, indent=2)
                
            all_records.extend(records)
            
    logger.info(f"Total records fetched: {len(all_records)}")
    
    if not all_records:
        logger.warning("No records found. Returning empty DataFrame.")
        return pd.DataFrame()

    # --- Processing ---
    df = pd.DataFrame(all_records)
    
    # 1. Standardize Columns
    # Inspect likely columns: pma_number, supplement_number, trade_name, generic_name, product_code, applicant, decision_date
    desired_cols = [
        'pma_number', 'supplement_number', 'trade_name', 'generic_name', 
        'product_code', 'advisory_committee_description', 'decision_date', 
        'applicant', 'docket_number', 'device_class',
        'received_date', 'decision_type'
    ]
    
    # Keep only columns that exist
    cols_to_keep = [c for c in desired_cols if c in df.columns]
    df = df[cols_to_keep].copy()
    
    # Rename advisory committee
    df.rename(columns={'advisory_committee_description': 'advisory_panel'}, inplace=True)
    
    # 2. Filter Supplements if requested
    # Supplements usually have supplement_number > 0. Original PMAs often have supplement_number '0' or null?
    # Actually in openFDA, pma_number is like P000001. Supplement number is a separate field.
    # Often we only want the original approval (Supplement 0 or null).
    
    if not include_supplements:
        # Check if supplement_number exists first
        if 'supplement_number' in df.columns:
            # Convert to numeric, errors='coerce' turns non-numeric to NaN
            df['supp_num_int'] = pd.to_numeric(df['supplement_number'], errors='coerce').fillna(0)
            initial_count = len(df)
            df = df[df['supp_num_int'] == 0]
            logger.info(f"Filtered supplements: {initial_count} -> {len(df)} (kept only supplement 0)")
            df.drop(columns=['supp_num_int'], inplace=True)
    
    # 3. Add Surgical Specialty derived field
    df['surgical_specialty'] = df['advisory_panel'].map(config.SPECIALTY_MAP).fillna('Other')
    
    # 4. Data Cleaning
    text_cols = ['trade_name', 'generic_name', 'applicant']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()
            
    # Normalize dates
    if 'decision_date' in df.columns:
        df['decision_date'] = pd.to_datetime(df['decision_date']).dt.strftime('%Y-%m-%d')
    if 'received_date' in df.columns:
        df['received_date'] = pd.to_datetime(df['received_date']).dt.strftime('%Y-%m-%d')

    # Deduplicate (just in case)
    df.drop_duplicates(subset=['pma_number', 'supplement_number'], inplace=True)
    
    # 5. Save Processed
    out_path = config.PROCESSED_DIR / "devices.csv"
    df.to_csv(out_path, index=False)
    logger.info(f"Saved processed devices table to {out_path} ({len(df)} rows)")
    
    return df

def _fetch_with_pagination(query, limit=1000):
    """Helper to handle openFDA pagination (cursor-based if available/needed, or skip-limit)"""
    # OpenFDA generic skip/limit is usually limited to 26000 total.
    # Since we break down by year/committee, we likely won't hit 26000 per query.
    # Just simple looping with 'skip' is fine for < 25000 records.
    
    results = []
    skip = 0
    url = config.OPENFDA_PMA_URL
    
    while True:
        params = {
            'search': query,
            'limit': limit,
            'skip': skip
        }
        
        try:
            resp = requests.get(url, params=params)
            
            if resp.status_code == 404:
                # No matches typically returns 404 in openFDA
                break
                
            resp.raise_for_status()
            data = resp.json()
            
            meta = data.get('meta', {}).get('results', {})
            total = meta.get('total', 0)
            batch = data.get('results', [])
            
            results.extend(batch)
            
            skip += limit
            if skip >= total:
                break
                
            # Respect rate limits (standard is generous but good practice)
            time.sleep(0.2)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data: {e}")
            break
            
    return results

if __name__ == "__main__":
    # Example usage: Run for full period
    df = fetch_surgical_pma_data(
        start_year=config.START_YEAR,
        end_year=config.END_YEAR,
        include_supplements=False # Focus on original approvals
    )
    print(df.head())
    print(df['advisory_panel'].value_counts())
