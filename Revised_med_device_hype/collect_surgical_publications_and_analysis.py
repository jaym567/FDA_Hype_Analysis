#!/usr/bin/env python3
"""
Surgical Device Publication Collection & Hype Analysis
This script collects publication data for surgical devices from OpenAlex
and performs a comprehensive hype analysis without burst detection.
"""

import os
import requests
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import config

# Initialize Rich console
console = Console()
logger = config.setup_logger(__name__, config.PROCESSED_DIR / "surgical_hype_analysis.log")

class SurgicalPublicationAnalyzer:
    def __init__(self, devices_csv_path, openalex_email=None):
        self.devices_csv_path = Path(devices_csv_path)
        self.openalex_email = openalex_email or config.OPENALEX_EMAIL
        self.base_url = "https://api.openalex.org"
        self.headers = {
            'User-Agent': f'mailto:{self.openalex_email}',
            'Accept-Encoding': 'gzip, deflate' # Avoid brotli if it causes issues
        }
        self.output_dir = config.PROCESSED_DIR
        self.raw_output_dir = config.RAW_OPENALEX_DIR
        
        # Performance/Politeness settings (Safety Limits)
        self.per_page = 50
        self.max_results_per_device = config.MAX_RESULTS_PER_DEVICE
        self.request_delay = config.SLEEP_BETWEEN_REQUESTS
        
    def _clean_device_name(self, name):
        """Clean trade name for API queries."""
        if pd.isna(name): return ""
        
        # 1. Handle slash-separated names (common in FDA data)
        # Take the first part as it's usually the primary trade name
        name = str(name).split('/')[0].strip()
        
        # 2. Remove trademarks and common noisy characters
        clean = name.replace('"', '').replace('™', '').replace('®', '').replace(',', '').strip()
        
        # 3. If the name is still very long, it might be a description. 
        # OpenAlex works best with 2-4 word phrases.
        words = clean.split()
        if len(words) > 6:
            clean = " ".join(words[:4])
            
        return clean

    def _reconstruct_abstract(self, inverted_index):
        """Reconstruct text from OpenAlex inverted index."""
        if not inverted_index:
            return ""
        
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))
        
        words.sort(key=lambda x: x[0])
        return " ".join([w[1] for w in words])

    def fetch_publications(self, limit_devices=None):
        """Fetch publications for the surgical device cohort."""
        if not self.devices_csv_path.exists():
            console.print(f"[red]Error: {self.devices_csv_path} not found[/red]")
            return pd.DataFrame()

        devices_df = pd.read_csv(self.devices_csv_path)
        
        # Collapse supplements: group by pma_number and take the first entry
        # Sorting by decision_date ensures we likely get the original approval or most relevant first
        unique_devices = devices_df.sort_values('decision_date').groupby('pma_number').first().reset_index()
        
        if limit_devices:
            unique_devices = unique_devices.head(limit_devices)

        all_publications = []
        processed_pmas = set()
        output_file = self.output_dir / "publications_surgical.csv"
        
        # Resume Logic: Load existing publications if they exist
        if output_file.exists():
            try:
                existing_df = pd.read_csv(output_file)
                if not existing_df.empty:
                    all_publications = existing_df.to_dict('records')
                    processed_pmas = set(existing_df['device_pma_number'].unique())
                    console.print(f"[yellow]Resuming: {len(processed_pmas)} devices already processed. Skipping...[/yellow]")
            except Exception as e:
                logger.warning(f"Could not load existing publications for resume: {e}")

        # Filter out already processed devices
        devices_to_process = unique_devices[~unique_devices['pma_number'].isin(processed_pmas)]
        
        if limit_devices:
            devices_to_process = devices_to_process.head(limit_devices)

        console.print(Panel(
            f"[bold blue]Surgical Device Publication Collection[/bold blue]\n"
            f"Total entries in cohort: [yellow]{len(devices_df)}[/yellow]\n"
            f"Unique devices total: [green]{len(unique_devices)}[/green]\n"
            f"Devices remaining to search: [cyan]{len(devices_to_process)}[/cyan]"
        ))

        # Track devices processed in this session for the session limit
        devices_seen_this_run = 0

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            device_task = progress.add_task("[cyan]Processing unique devices...", total=len(unique_devices))
            # Mark already processed items as completed in progress bar
            progress.update(device_task, completed=len(processed_pmas))

            for _, row in devices_to_process.iterrows():
                pma_num = row.get('pma_number')
                trade_name = row.get('trade_name')
                applicant = row.get('applicant', '')
                
                # Calculate Dynamic Window: -5 to +10 years
                decision_date_str = row.get('decision_date')
                try:
                    decision_year = datetime.strptime(decision_date_str, '%Y-%m-%d').year
                    window_start = decision_year - 5
                    window_end = decision_year + 10
                    # Cap window_end at current year
                    current_year = datetime.now().year
                    window_end = min(window_end, current_year)
                except Exception as e:
                    logger.warning(f"Could not parse decision date for {pma_num}: {e}. Using global config.")
                    window_start = config.START_YEAR
                    window_end = config.END_YEAR

                clean_name = self._clean_device_name(trade_name)
                if not clean_name:
                    progress.advance(device_task)
                    continue

                # High-Specificity Querying: Always anchor with manufacturer simplified name
                query = f'"{clean_name}"'
                if pd.notna(applicant) and str(applicant).strip():
                    # Take the first two words of the applicant (e.g., "GENERAL ELECTRIC" or "ETHICON")
                    # Usually enough to distinguish from competitors while staying flexible
                    mfr_parts = str(applicant).replace(',', '').replace('.', '').split()
                    mfr_anchor = " ".join(mfr_parts[:1]) # Start with just one word for better recall, or two for precision
                    if mfr_anchor:
                        query = f'"{clean_name}" AND "{mfr_anchor}"'

                # Search Logic: Try with manufacturer anchor first, fallback to name only
                name_only_query = f'"{clean_name}"'
                
                # We'll try the full query with manufacturer if available
                current_query = query 
                
                # Cursor Pagination
                cursor = "*"
                device_pubs = []
                
                while cursor and len(device_pubs) < self.max_results_per_device:
                    params = {
                        'filter': f"from_publication_date:{window_start}-01-01,to_publication_date:{window_end}-12-31",
                        'search': current_query,
                        'per_page': self.per_page,
                        'sort': 'cited_by_count:desc',
                        'cursor': cursor
                    }

                    # Local retry for 429 (Too Many Requests)
                    max_retries = 3
                    retry_count = 0
                    backoff = 2
                    data = {}
                    
                    while retry_count <= max_retries:
                        try:
                            response = requests.get(
                                f"{self.base_url}/works",
                                params=params,
                                headers=self.headers,
                                timeout=30
                            )
                            
                            if response.status_code == 429:
                                retry_count += 1
                                if retry_count > max_retries:
                                    logger.error(f"Max retries exceeded for {pma_num} (429)")
                                    break
                                wait_time = backoff ** retry_count
                                logger.warning(f"Rate limited (429) for {pma_num}. Retrying in {wait_time}s...")
                                time.sleep(wait_time)
                                continue
                                
                            response.raise_for_status()
                            data = response.json()
                            break # Success
                            
                        except Exception as e:
                            if retry_count >= max_retries:
                                # Sanitize the name for the logger to avoid UnicodeErrors
                                safe_name = clean_name.encode('ascii', 'ignore').decode('ascii')
                                logger.error(f"Error fetching for {safe_name}: {e}")
                                break
                            retry_count += 1
                            time.sleep(2)
                    
                    if not data:
                        break # Stop pagination for this device

                    results = data.get('results', [])
                    
                    # Fallback: If no results with Manufacturer Anchor, try Name Only
                    if not results and current_query != name_only_query:
                        logger.info(f"No results with manufacturer anchor for {pma_num}. Retrying with name only: {name_only_query}")
                        current_query = name_only_query
                        cursor = "*" # Reset cursor for fallback search
                        continue # Restart the loop with simplified query
                    
                    if not results:
                        break # Stop if still no results or already using name_only
                    
                    logger.info(f"Fetching publications for PMA: {pma_num} | Query: {current_query} | Results: {len(results)}")

                    results = data.get('results', [])
                    for work in results:
                        # Safety check: work itself should be a dict
                        if not isinstance(work, dict): continue
                        
                        # Reconstruct Abstract
                        abstract = self._reconstruct_abstract(work.get('abstract_inverted_index'))
                        
                        # Deep get for nested fields
                        primary_loc = work.get('primary_location') or {}
                        source = primary_loc.get('source') or {}
                        oa = work.get('open_access') or {}
                        
                        pub_data = {
                            'device_pma_number': pma_num,
                            'trade_name': trade_name,
                            'openalex_id': work.get('id'),
                            'doi': work.get('doi'),
                            'title': work.get('title'),
                            'publication_date': work.get('publication_date'),
                            'publication_year': work.get('publication_year'),
                            'abstract': abstract,
                            'venue': source.get('display_name'),
                            'cited_by_count': work.get('cited_by_count', 0),
                            'is_oa': oa.get('is_oa', False),
                            'type': work.get('type'),
                            'concepts': [c.get('display_name') for c in (work.get('concepts') or [])[:5]]
                        }
                        device_pubs.append(pub_data)
                    
                    cursor = data.get('meta', {}).get('next_cursor')
                    if not results: break
                    
                    # Rate limit politeness: safety delay to preserve credits
                    time.sleep(self.request_delay)
                
                all_publications.extend(device_pubs[:self.max_results_per_device])
                progress.advance(device_task)

                # Session Limit: Break if we've processed enough devices for this session
                # We use a relative counter instead of the DataFrame index
                devices_seen_this_run += 1
                if hasattr(config, 'DEVICES_PER_SESSION') and devices_seen_this_run >= config.DEVICES_PER_SESSION:
                    logger.info(f"Session limit reached ({config.DEVICES_PER_SESSION} devices). Stopping to preserve credits.")
                    break

                # Incremental Save: every 10 devices
                if (_ + 1) % 10 == 0:
                    temp_df = pd.DataFrame(all_publications)
                    output_file = self.output_dir / "publications_surgical.csv"
                    temp_df.to_csv(output_file, index=False)
                    logger.info(f"Incremental save: {len(temp_df)} publications collected so far.")

        pubs_df = pd.DataFrame(all_publications)
        if not pubs_df.empty:
            # Deduplicate (a paper might match multiple devices, but we keep those associations)
            # However, we'll save the raw publication list
            output_file = self.output_dir / "publications_surgical.csv"
            pubs_df.to_csv(output_file, index=False)
            console.print(f"[green]Saved {len(pubs_df)} publications to {output_file}[/green]")
        
        return pubs_df

    def analyze_hype(self, pubs_df, devices_df_path):
        """Analyze publication metrics per device."""
        if pubs_df.empty:
            return pd.DataFrame()

        devices_df = pd.read_csv(devices_df_path)
        analysis_results = []
        
        unique_devices = devices_df.sort_values('decision_date').groupby('pma_number').first().reset_index()
        
        for _, device_info in unique_devices.iterrows():
            pma_num = device_info['pma_number']
            device_pubs = pubs_df[pubs_df['device_pma_number'] == pma_num] if not pubs_df.empty else pd.DataFrame()
            
            # 1. Hype Volume (Papers per year)
            vol_per_year = device_pubs.groupby('publication_year').size() if not device_pubs.empty else pd.Series()
            peak_year = vol_per_year.idxmax() if not vol_per_year.empty else None
            peak_count = vol_per_year.max() if not vol_per_year.empty else 0
            
            # 2. Hype Impact (Citations)
            total_citations = device_pubs['cited_by_count'].sum() if not device_pubs.empty else 0
            avg_citations = device_pubs['cited_by_count'].mean() if not device_pubs.empty else 0

            # 3. Trial Types
            num_rcts = device_pubs['is_rct'].sum() if 'is_rct' in device_pubs.columns else 0
            num_obs = device_pubs['is_observational'].sum() if 'is_observational' in device_pubs.columns else 0
            
            # 4. Concept Mapping (Aggregate)
            top_concepts = []
            if not device_pubs.empty:
                all_concepts = []
                for concepts in device_pubs['concepts'].dropna():
                    # Handle stringified list or list
                    if isinstance(concepts, str):
                        try:
                            # If it looks like a list string, parse it
                            c_list = eval(concepts) if concepts.startswith('[') else concepts.split(';')
                            all_concepts.extend(c_list)
                        except:
                            all_concepts.append(concepts)
                    else:
                        all_concepts.extend(concepts)
                top_concepts = pd.Series(all_concepts).value_counts().head(5).index.tolist()
            
            analysis_results.append({
                'pma_number': pma_num,
                'trade_name': device_info.get('trade_name'),
                'total_publications': len(device_pubs),
                'total_citations': total_citations,
                'avg_citations_per_pub': round(avg_citations, 2),
                'num_rcts': num_rcts,
                'num_observational': num_obs,
                'peak_publication_year': peak_year,
                'peak_publication_count': peak_count,
                'top_concepts': "; ".join(top_concepts),
                'is_surgical': device_info.get('is_surgical', True)
            })
            
        analysis_df = pd.DataFrame(analysis_results)
        output_file = self.output_dir / "publication_analysis_surgical.csv"
        analysis_df.to_csv(output_file, index=False)
        console.print(f"[green]Saved analysis for {len(analysis_df)} devices to {output_file}[/green]")
        
        return analysis_df

def main():
    devices_path = config.PROCESSED_DIR / "devices_surgical.csv"
    
    analyzer = SurgicalPublicationAnalyzer(devices_path)
    
    # Run fetch for the entire cohort
    pubs_df = analyzer.fetch_publications()
    
    if not pubs_df.empty:
        analyzer.analyze_hype(pubs_df, devices_path)
        
        # Display sample results
        table = Table(title="Surgical Publication Analysis Sample")
        table.add_column("Trade Name", style="cyan")
        table.add_column("Pubs", justify="right")
        table.add_column("Citations", justify="right")
        table.add_column("Peak Year", justify="center")
        
        # We need to reload analysis_df or use it from return
        analysis_df = pd.read_csv(config.PROCESSED_DIR / "publication_analysis_surgical.csv")
        for _, row in analysis_df.head(10).iterrows():
            table.add_row(
                str(row['trade_name']),
                str(row['total_publications']),
                str(row['total_citations']),
                str(row['peak_publication_year'])
            )
        console.print(table)

if __name__ == "__main__":
    main()
