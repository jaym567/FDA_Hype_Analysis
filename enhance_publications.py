import pandas as pd
import json
import os
import re
from pathlib import Path
from tqdm import tqdm
from rich.console import Console

console = Console()

def identify_trial_type(title, abstract):
    """Heuristic to identify trial types."""
    text = f"{str(title)} {str(abstract)}".lower()
    
    # RCT Heuristics
    is_rct = False
    if any(kw in text for kw in ["randomized", "randomised", "controlled trial", "rct"]):
        is_rct = True
        
    # Observational Heuristics
    is_observational = False
    if any(kw in text for kw in ["observational", "cohort study", "prospective", "retrospective", "case series"]):
        is_observational = True
        
    return is_rct, is_observational

def enhance_publications():
    # Paths
    base_dir = Path("Revised_med_device_hype/data")
    pubs_file = base_dir / "processed" / "publications_surgical.csv"
    raw_dir = base_dir / "raw" / "openalex"
    
    if not pubs_file.exists():
        console.print(f"[red]Error: {pubs_file} not found[/red]")
        return

    console.print("[cyan]Loading existing publications...[/cyan]")
    pubs_df = pd.read_csv(pubs_file)
    
    # Check if we already have the columns
    if 'publication_date' not in pubs_df.columns:
        pubs_df['publication_date'] = ""
    if 'is_rct' not in pubs_df.columns:
        pubs_df['is_rct'] = False
    if 'is_observational' not in pubs_df.columns:
        pubs_df['is_observational'] = False

    # 1. Backfill Publication Dates from Raw JSONs
    console.print("[cyan]Backfilling publication dates from raw JSON batches...[/cyan]")
    id_to_date = {}
    json_files = list(raw_dir.glob("*.json"))
    
    for f_path in tqdm(json_files, desc="Parsing JSON batches"):
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Raw data can be a list or a dict with 'results'
                results = data if isinstance(data, list) else data.get('results', [])
                for item in results:
                    o_id = item.get('id')
                    p_date = item.get('publication_date')
                    if o_id and p_date:
                        id_to_date[o_id] = p_date
        except Exception as e:
            console.print(f"[yellow]Warning: Could not parse {f_path.name}: {e}[/yellow]")

    # 2. Apply Dates and Trial Heuristics
    console.print("[cyan]Applying updates to dataset...[/cyan]")
    updated_count = 0
    for idx, row in tqdm(pubs_df.iterrows(), total=len(pubs_df), desc="Enhancing rows"):
        openalex_id = row.get('openalex_id')
        
        # Date Backfill
        if openalex_id in id_to_date:
            pubs_df.at[idx, 'publication_date'] = id_to_date[openalex_id]
            updated_count += 1
            
        # Trial Identification
        title = row.get('title', '')
        # Abstracts might be in the CSV already
        abstract = row.get('abstract', '')
        
        is_rct, is_obs = identify_trial_type(title, abstract)
        pubs_df.at[idx, 'is_rct'] = is_rct
        pubs_df.at[idx, 'is_observational'] = is_obs

    # Save Results
    pubs_df.to_csv(pubs_file, index=False)
    console.print(f"[green]Successfully enhanced {len(pubs_df)} publications.[/green]")
    console.print(f"[green]Backfilled {updated_count} granular dates.[/green]")
    console.print(f"[green]Identified {pubs_df['is_rct'].sum()} RCTs and {pubs_df['is_observational'].sum()} observational studies.[/green]")

if __name__ == "__main__":
    enhance_publications()
