# ---- Surgery Citation Bias Analysis - Fixed Pipeline ----
import requests
import pandas as pd
import gender_guesser.detector as gd
import numpy as np
import datetime as dt
import time
import re
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

# Configuration
MAX_PAPERS = 1000  # Target: 1,000 papers for focused analysis
BATCH_SIZE = 200
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
SURGERY_CONCEPT_ID = "C141071460"
MAX_WORKERS = 5

console = Console()

class RateLimiter:
    def __init__(self, delay=5.0):  # Much more conservative delay for OpenAlex API
        self.delay = delay
        self.last_request = 0
    
    def wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request = time.time()

rate_limiter = RateLimiter()

def get_gender_from_name(name):
    """Extract gender from author name using gender_guesser"""
    if not name:
        return "unknown"
    
    # Clean the name
    name = re.sub(r'[^\w\s]', '', name).strip()
    if not name:
        return "unknown"
    
    # Split and get first name
    name_parts = name.split()
    if not name_parts:
        return "unknown"
    
    first_name = name_parts[0]
    
    # Use gender_guesser
    d = gd.Detector()
    gender = d.get_gender(first_name)
    
    # Map to our categories
    if gender in ['M', 'male']:
        return "male"
    elif gender in ['F', 'female']:
        return "female"
    else:
        return "unknown"

def make_rate_limited_request(url, timeout=REQUEST_TIMEOUT, max_retries=MAX_RETRIES):
    """Make a rate-limited request with timeout and retry logic"""
    rate_limiter.wait()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            return response
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                console.print(f"[red]Timeout after {max_retries} attempts for {url}[/red]")
                return None
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                console.print(f"[red]Request failed after {max_retries} attempts: {e}[/red]")
                return None
            time.sleep(2 ** attempt)
    
    return None

def get_paper_author_info(doi):
    """Get author information for a paper using OpenAlex API"""
    if not doi:
        return None
    
    # Clean DOI
    clean_doi = doi.replace('https://doi.org/', '') if doi.startswith('https://doi.org/') else doi
    
    url = f"https://api.openalex.org/works/https://doi.org/{clean_doi}"
    response = make_rate_limited_request(url)
    
    if response is None or response.status_code != 200:
        return None
    
    try:
        data = response.json()
        authorships = data.get('authorships', [])
        
        if not authorships:
            return None
        
        # Get first author
        first_author = authorships[0]
        first_author_name = first_author["author"]["display_name"]
        first_gender = get_gender_from_name(first_author_name)
        
        # Get country from first author's affiliation
        first_author_country = None
        if first_author.get("institutions"):
            first_institution = first_author["institutions"][0]
            if first_institution.get("countries"):
                first_author_country = first_institution["countries"][0]
        
        return {
            'doi': doi,
            'first_author_name': first_author_name,
            'first_author_gender': first_gender,
            'first_author_country': first_author_country,
            'title': data.get('title', ''),
            'publication_year': data.get('publication_year')
        }
    except Exception as e:
        console.print(f"[red]Error processing {doi}: {e}[/red]")
        return None

def fetch_surgery_papers():
    """Fetch surgery papers using OpenAlex"""
    console.print(Panel.fit(
        "🔪 Surgery Citation Bias Analysis - Fixed Pipeline\n"
        "OpenAlex → Crossref → Analysis",
        style="bold blue"
    ))
    
    all_papers = []
    cursor = "*"
    batch_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        paper_task = progress.add_task("🔍 Fetching surgery papers...", total=MAX_PAPERS)
        
        while len(all_papers) < MAX_PAPERS and cursor:
            # Fetch batch of papers
            payload = {
                "filter": f"concept.id:{SURGERY_CONCEPT_ID}",
                "per_page": BATCH_SIZE,
                "cursor": cursor
            }
            
            try:
                console.print(f"\n[bold blue]🔄 Batch {batch_count}: Fetching surgery papers at {time.strftime('%H:%M:%S')}...[/bold blue]")
                
                rate_limiter.wait()
                response = requests.get("https://api.openalex.org/works", params=payload, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 429:
                    console.print(f"[yellow]Rate limited (HTTP 429). Waiting 30 seconds before retry...[/yellow]")
                    time.sleep(30)
                    continue
                elif response.status_code != 200:
                    console.print(f"[red]HTTP {response.status_code} when fetching papers[/red]")
                    break
                
                data = response.json()
                papers = data.get('results', [])
                cursor = data.get('meta', {}).get('next_cursor')
                
                if not papers:
                    console.print("[yellow]No more papers found[/yellow]")
                    break
                
                batch_papers = 0
                
                # Process papers in current batch
                for work in papers:
                    if len(all_papers) >= MAX_PAPERS:
                        break
                    
                    year = work["publication_year"]
                    if year is None or year not in [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]:
                        continue
                    
                    authorships = work["authorships"]
                    if not authorships:
                        continue
                    
                    # Get FIRST author
                    first_author = authorships[0]
                    first_author_name = first_author["author"]["display_name"]
                    
                    # Get LAST author (PI/senior author)
                    last_author = authorships[-1]
                    last_author_name = last_author["author"]["display_name"]
                    
                    if not first_author_name or not last_author_name:
                        continue
                    
                    # Get gender for both authors
                    first_gender = get_gender_from_name(first_author_name)
                    last_gender = get_gender_from_name(last_author_name)
                    
                    # Extract country from first author's affiliation
                    first_author_country = None
                    if first_author.get("institutions"):
                        first_institution = first_author["institutions"][0]
                        if first_institution.get("countries"):
                            first_author_country = first_institution["countries"][0]
                    
                    # Extract country from last author's affiliation
                    last_author_country = None
                    if last_author.get("institutions"):
                        last_institution = last_author["institutions"][0]
                        if last_institution.get("countries"):
                            last_author_country = last_institution["countries"][0]
                    
                    paper_info = {
                        'doi': work.get('doi', ''),
                        'title': work.get('title', ''),
                        'publication_year': year,
                        'first_author_name': first_author_name,
                        'first_author_gender': first_gender,
                        'first_author_country': first_author_country,
                        'last_author_name': last_author_name,
                        'last_author_gender': last_gender,
                        'last_author_country': last_author_country,
                        'cited_by_count': work.get('cited_by_count', 0)
                    }
                    
                    all_papers.append(paper_info)
                    batch_papers += 1
                
                progress.update(paper_task, advance=batch_papers)
                progress.update(paper_task, description=f"📚 Fetched {len(all_papers):,} surgery papers so far...")
                
                console.print(f"[green]✅ Retrieved {batch_papers} surgery papers (Total: {len(all_papers):,})[/green]")
                
                batch_count += 1
                
            except Exception as e:
                console.print(f"[red]Error fetching batch: {e}[/red]")
                time.sleep(5)
                continue
        
        # Final summary
        console.print(f"\n[bold green]✅ Successfully collected {len(all_papers)} surgery papers[/bold green]")
        
        if len(all_papers) == 0:
            console.print("[red]No papers found. Exiting.[/red]")
            return []
        
        return all_papers

def get_paper_references(paper_info, progress, reference_task):
    """Get references (papers that this paper cites) using Crossref API"""
    doi = paper_info.get('doi', '')
    if not doi:
        progress.update(reference_task, advance=1)
        return []
    
    # Clean DOI for Crossref
    clean_doi = doi.replace('https://doi.org/', '') if doi.startswith('https://doi.org/') else doi
    
    url = f"https://api.crossref.org/works/{clean_doi}"
    response = make_rate_limited_request(url)
    
    if response is None:
        progress.update(reference_task, advance=1)
        return []
    
    # Skip 404 errors
    if response.status_code == 404:
        progress.update(reference_task, advance=1)
        return []
    
    if response.status_code == 200:
        try:
            data = response.json()
            message = data.get('message', {})
            
            # Get references (papers that this paper cites)
            references = message.get('reference', [])
            
            # Process each reference
            processed_references = []
            for reference in references:
                if reference.get('DOI'):
                    reference_info = {
                        'citing_paper_doi': doi,  # Our surgery paper
                        'citing_paper_title': paper_info.get('title', ''),
                        'citing_paper_gender': paper_info.get('first_author_gender'),
                        'citing_paper_country': paper_info.get('first_author_country'),
                        'cited_paper_doi': f"https://doi.org/{reference['DOI']}",  # Paper being cited
                        'cited_paper_title': reference.get('article-title', ''),
                        'cited_paper_year': reference.get('year')
                    }
                    processed_references.append(reference_info)
            
            progress.update(reference_task, advance=1)
            return processed_references
            
        except Exception as e:
            console.print(f"[red]Error processing references for {doi}: {e}[/red]")
            progress.update(reference_task, advance=1)
            return []
    else:
        console.print(f"[red]HTTP {response.status_code} for {url}[/red]")
        progress.update(reference_task, advance=1)
        return []

def process_all_references(all_papers):
    """Process references for all papers using Crossref"""
    console.print("[bold blue]🔍 Getting references (papers our surgery papers cite) using Crossref...[/bold blue]")
    
    all_references = []
    total_papers = len(all_papers)
    
    console.print(f"[cyan]Total papers: {total_papers}[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        reference_task = progress.add_task("🔍 Processing references...", total=total_papers)
        
        # Process in batches with parallelization
        for i in range(0, len(all_papers), BATCH_SIZE):
            batch = all_papers[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(all_papers) + BATCH_SIZE - 1) // BATCH_SIZE
            
            console.print(f"[blue]Processing batch {batch_num}/{total_batches} ({len(batch)} papers) with parallelization...[/blue]")
            
            batch_references = []
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit all papers in batch to executor
                future_to_paper = {
                    executor.submit(get_paper_references, paper, progress, reference_task): paper 
                    for paper in batch
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_paper):
                    paper = future_to_paper[future]
                    try:
                        references = future.result()
                        batch_references.extend(references)
                    except Exception as e:
                        console.print(f"[red]Error processing paper {paper.get('doi', 'unknown')}: {e}[/red]")
            
            all_references.extend(batch_references)
            console.print(f"[green]Batch {batch_num} complete: {len(batch_references)} references found[/green]")
    
    console.print(f"[bold green]✅ Reference processing complete: {len(all_references)} references found[/bold green]")
    return all_references

def get_referenced_papers_author_info(references_data):
    """Get author information for all referenced papers using OpenAlex"""
    console.print("[bold blue]🔍 Getting author info for referenced papers using OpenAlex...[/bold blue]")
    
    # Get unique referenced papers
    referenced_dois = set()
    for reference in references_data:
        referenced_doi = reference.get('cited_paper_doi', '')
        if referenced_doi:
            referenced_dois.add(referenced_doi)
    
    console.print(f"[cyan]Unique referenced papers: {len(referenced_dois)}[/cyan]")
    
    referenced_papers_info = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        info_task = progress.add_task("🔍 Getting author info...", total=len(referenced_dois))
        
        # Process in batches
        referenced_dois_list = list(referenced_dois)
        for i in range(0, len(referenced_dois_list), BATCH_SIZE):
            batch_dois = referenced_dois_list[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(referenced_dois_list) + BATCH_SIZE - 1) // BATCH_SIZE
            
            console.print(f"[blue]Processing batch {batch_num}/{total_batches} ({len(batch_dois)} papers)...[/blue]")
            
            batch_info = []
            
            # Use ThreadPoolExecutor for parallel processing
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit all DOIs to executor
                future_to_doi = {
                    executor.submit(get_paper_author_info, doi): doi 
                    for doi in batch_dois
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_doi):
                    doi = future_to_doi[future]
                    try:
                        paper_info = future.result()
                        if paper_info:
                            batch_info.append(paper_info)
                        progress.update(info_task, advance=1)
                    except Exception as e:
                        console.print(f"[red]Error processing {doi}: {e}[/red]")
                        progress.update(info_task, advance=1)
            
            referenced_papers_info.extend(batch_info)
            console.print(f"[green]Batch {batch_num} complete: {len(batch_info)} papers processed[/green]")
    
    console.print(f"[bold green]✅ Author info processing complete: {len(referenced_papers_info)} papers processed[/bold green]")
    return referenced_papers_info

def analyze_citation_bias(surgery_papers, references_data, referenced_papers_info):
    """Analyze citation bias patterns"""
    console.print("[bold blue]📊 Analyzing citation bias patterns...[/bold blue]")
    
    # Create mapping of referenced papers to their author info
    referenced_papers_map = {}
    for paper_info in referenced_papers_info:
        doi = paper_info.get('doi', '')
        if doi:
            referenced_papers_map[doi] = paper_info
    
    # Add referenced paper author info to references
    enhanced_references = []
    for reference in references_data:
        referenced_doi = reference.get('cited_paper_doi', '')
        referenced_info = referenced_papers_map.get(referenced_doi)
        
        if referenced_info:
            enhanced_reference = {
                **reference,
                'cited_paper_gender': referenced_info.get('first_author_gender'),
                'cited_paper_country': referenced_info.get('first_author_country')
            }
            enhanced_references.append(enhanced_reference)
    
    console.print(f"[cyan]Enhanced references with author info: {len(enhanced_references)}[/cyan]")
    
    # Filter for references with complete gender info
    gender_references = [r for r in enhanced_references 
                        if r.get('citing_paper_gender') and r.get('cited_paper_gender') 
                        and r.get('citing_paper_gender') != 'unknown' 
                        and r.get('cited_paper_gender') != 'unknown']
    
    console.print(f"[cyan]References with complete gender info: {len(gender_references)}[/cyan]")
    
    # Analyze gender citation patterns
    if gender_references:
        df = pd.DataFrame(gender_references)
        
        # Create citation matrix
        gender_matrix = pd.crosstab(df['citing_paper_gender'], df['cited_paper_gender'])
        gender_percentages = pd.crosstab(df['citing_paper_gender'], df['cited_paper_gender'], normalize='index') * 100
        
        console.print("\n[bold cyan]Gender Citation Matrix (Citing → Cited):[/bold cyan]")
        console.print(gender_matrix)
        
        console.print("\n[bold cyan]Gender Citation Percentages:[/bold cyan]")
        console.print(gender_percentages.round(2))
        
        # Calculate citation bias metrics
        total_references = len(gender_references)
        female_citing = len(df[df['citing_paper_gender'] == 'female'])
        female_cited = len(df[df['cited_paper_gender'] == 'female'])
        
        expected_female_to_female = (female_citing / total_references) * (female_cited / total_references) * total_references
        observed_female_to_female = len(df[
            (df['citing_paper_gender'] == 'female') & 
            (df['cited_paper_gender'] == 'female')
        ])
        
        console.print(f"\n[bold cyan]Citation Bias Metrics:[/bold cyan]")
        console.print(f"Expected female→female citations: {expected_female_to_female:.1f}")
        console.print(f"Observed female→female citations: {observed_female_to_female}")
        console.print(f"Citation bias ratio: {observed_female_to_female/expected_female_to_female:.2f}")
        
        if observed_female_to_female > expected_female_to_female:
            console.print("→ Female authors cite other female authors MORE than expected (positive bias)")
        else:
            console.print("→ Female authors cite other female authors LESS than expected (negative bias)")
    
    # Analyze geographic patterns
    country_references = [r for r in enhanced_references 
                         if r.get('citing_paper_country') and r.get('cited_paper_country')]
    
    if country_references:
        console.print(f"\n[cyan]References with country info: {len(country_references)}[/cyan]")
        
        df_country = pd.DataFrame(country_references)
        country_matrix = pd.crosstab(df_country['citing_paper_country'], df_country['cited_paper_country'])
        
        console.print("\n[bold cyan]Top Country Citation Patterns:[/bold cyan]")
        console.print(country_matrix.head(10))
    
    return {
        'surgery_papers': surgery_papers,
        'references_data': references_data,
        'referenced_papers_info': referenced_papers_info,
        'enhanced_references': enhanced_references,
        'gender_references': gender_references,
        'country_references': country_references
    }

def save_results(results, filename_prefix="surgery_citation_bias_analysis_fixed"):
    """Save results to files"""
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed results
    results_filename = f"{filename_prefix}_{timestamp}.json"
    with open(results_filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save surgery papers CSV
    surgery_df = pd.DataFrame(results['surgery_papers'])
    surgery_csv_filename = f"{filename_prefix}_surgery_papers_{timestamp}.csv"
    surgery_df.to_csv(surgery_csv_filename, index=False)
    
    # Save references CSV
    references_df = pd.DataFrame(results['references_data'])
    references_csv_filename = f"{filename_prefix}_references_{timestamp}.csv"
    references_df.to_csv(references_csv_filename, index=False)
    
    # Save enhanced references CSV
    if results['enhanced_references']:
        enhanced_df = pd.DataFrame(results['enhanced_references'])
        enhanced_csv_filename = f"{filename_prefix}_enhanced_references_{timestamp}.csv"
        enhanced_df.to_csv(enhanced_csv_filename, index=False)
    
    console.print(f"[bold green]✅ Results saved to:[/bold green]")
    console.print(f"  📄 {results_filename}")
    console.print(f"  📊 {surgery_csv_filename}")
    console.print(f"  📚 {references_csv_filename}")
    if results['enhanced_references']:
        console.print(f"  🔍 {enhanced_csv_filename}")
    
    return results_filename

def main():
    """Main execution function"""
    try:
        # Step 1: Fetch surgery papers using OpenAlex
        surgery_papers = fetch_surgery_papers()
        
        if not surgery_papers:
            console.print("[red]No papers found. Exiting.[/red]")
            return
        
        # Step 2: Get references using Crossref
        references_data = process_all_references(surgery_papers)
        
        if not references_data:
            console.print("[red]No references found. Exiting.[/red]")
            return
        
        # Step 3: Get author info for referenced papers using OpenAlex
        referenced_papers_info = get_referenced_papers_author_info(references_data)
        
        # Step 4: Analyze citation bias
        results = analyze_citation_bias(surgery_papers, references_data, referenced_papers_info)
        
        # Step 5: Save results
        save_results(results)
        
        console.print("\n[bold green]🎉 Citation bias analysis complete![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error during analysis: {e}[/red]")

if __name__ == "__main__":
    main() 