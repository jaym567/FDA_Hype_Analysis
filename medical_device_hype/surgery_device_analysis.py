#!/usr/bin/env python3
"""
Surgery-Specific FDA Device Analysis with Publication Burst Detection
Analyzes FDA PMA data specifically for surgical devices and procedures

This script:
1. Filters FDA PMA data for surgery-related devices
2. Categorizes devices by surgical specialty
3. Collects publication data from OpenAlex API
4. Implements Kleinberg burst detection algorithm
5. Analyzes publication trends and citation patterns
6. Identifies high-impact surgical devices
7. Generates surgery-specific insights and visualizations
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import re
import requests
import time
from collections import defaultdict, Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

warnings.filterwarnings('ignore')

console = Console()

class SurgeryDeviceAnalyzer:
    def __init__(self, fda_data_file="data/fda_pma_comprehensive.json", openalex_email=None, verbose=True):
        """
        Initialize the Surgery Device Analyzer
        
        Args:
            fda_data_file (str): Path to the FDA PMA data file
            openalex_email (str): Email for OpenAlex API (optional, for higher rate limits)
            verbose (bool): Enable verbose output with rich formatting
        """
        self.fda_data_file = fda_data_file
        self.verbose = verbose
        self.base_url = "https://api.openalex.org"
        self.headers = {}
        if openalex_email:
            self.headers['User-Agent'] = f'mailto:{openalex_email}'
        
        self.surgery_devices = None
        self.surgical_specialties = {
            'cardiac_surgery': [
                'cardiac', 'heart', 'cardiovascular', 'coronary', 'valve', 'pacemaker',
                'defibrillator', 'stent', 'catheter', 'angioplasty', 'bypass'
            ],
            'orthopedic_surgery': [
                'orthopedic', 'orthopaedic', 'joint', 'knee', 'hip', 'shoulder', 'spine',
                'prosthesis', 'implant', 'fixation', 'plate', 'screw', 'rod'
            ],
            'neurosurgery': [
                'neurological', 'brain', 'spinal', 'neurostimulator', 'deep brain',
                'neuromodulation', 'stereotactic', 'neurovascular'
            ],
            'general_surgery': [
                'surgical', 'laparoscopic', 'endoscopic', 'robotic', 'surgical robot',
                'minimally invasive', 'surgical instrument', 'surgical tool'
            ],
            'plastic_surgery': [
                'cosmetic', 'plastic', 'reconstructive', 'breast', 'facial', 'aesthetic'
            ],
            'ophthalmology': [
                'ophthalmic', 'eye', 'retinal', 'cataract', 'glaucoma', 'corneal',
                'intraocular', 'ophthalmology'
            ],
            'urology': [
                'urological', 'urology', 'prostate', 'bladder', 'kidney', 'urinary',
                'nephrology', 'dialysis'
            ],
            'gynecology': [
                'gynecological', 'gynecology', 'obstetric', 'uterine', 'ovarian',
                'hysterectomy', 'endometrial'
            ],
            'dental_surgery': [
                'dental', 'oral', 'maxillofacial', 'dental implant', 'orthodontic',
                'periodontal', 'endodontic'
            ],
            'vascular_surgery': [
                'vascular', 'arterial', 'venous', 'peripheral', 'vascular graft',
                'aneurysm', 'thrombectomy'
            ]
        }
        
        self.load_fda_data()
        self.filter_surgery_devices()
        
        if self.verbose:
            self._print_initialization_info()
    
    def _print_initialization_info(self):
        """Print beautiful initialization information"""
        console.print("\n")
        
        # Title panel
        title = Text("🔪 Surgery Device Analysis System", style="bold blue")
        subtitle = Text("Powered by OpenAlex API & Kleinberg Burst Detection", style="italic cyan")
        
        title_panel = Panel(
            Align.center(title + "\n" + subtitle),
            border_style="blue",
            box=box.DOUBLE
        )
        console.print(title_panel)
        
    def load_fda_data(self):
        """Load FDA PMA data from JSON file"""
        try:
            with open(self.fda_data_file, 'r') as f:
                data = json.load(f)
            
            # Convert to DataFrame for easier manipulation
            if isinstance(data, list):
                self.fda_data = pd.DataFrame(data)
            else:
                # Handle different data structures
                self.fda_data = pd.DataFrame(data.get('results', []))
            
            console.print(f"✅ [green]Loaded {len(self.fda_data)} FDA PMA records[/green]")
            
        except FileNotFoundError:
            console.print(f"❌ [red]FDA data file not found: {self.fda_data_file}[/red]")
            console.print("Please ensure the FDA data file exists in the current directory")
            self.fda_data = pd.DataFrame()
        except Exception as e:
            console.print(f"❌ [red]Error loading FDA data: {e}[/red]")
            self.fda_data = pd.DataFrame()
    
    def filter_surgery_devices(self):
        """Filter FDA data for surgery-related devices with strict criteria"""
        if self.fda_data.empty:
            console.print("⚠️ [yellow]No FDA data available for filtering[/yellow]")
            self.surgery_devices = pd.DataFrame()
            return
        
        # Create surgery-related keywords (specific terms only, no generic terms)
        surgery_keywords = []
        for specialty, keywords in self.surgical_specialties.items():
            surgery_keywords.extend(keywords)
        
        # Add specific surgical terms (removed generic terms like 'device', 'system', 'tool')
        specific_surgical_terms = [
            'surgery', 'surgical', 'surgical robot', 'surgical instrument', 'surgical tool',
            'operation', 'operative', 'procedure', 'implant', 'prosthesis', 'prosthetic',
            'robotic surgery', 'laparoscopic', 'endoscopic', 'minimally invasive',
            'surgical system', 'surgical platform', 'surgical device'
        ]
        surgery_keywords.extend(specific_surgical_terms)
        
        # Exclusion patterns for non-surgical devices
        exclusion_patterns = [
            'diagnostic', 'diagnosis', 'test', 'assay', 'analyzer', 'monitor', 'detector',
            'imaging', 'scanner', 'x-ray', 'mri', 'ct scan', 'ultrasound', 'fluoroscopy',
            'laboratory', 'lab', 'in vitro', 'ivd', 'reagent', 'calibrator', 'control',
            'software', 'app', 'application', 'database', 'system software',
            'bandage', 'dressing', 'gauze', 'tape', 'adhesive', 'wound care',
            'supplement', 'vitamin', 'nutrition', 'dietary',
            'drug', 'pharmaceutical', 'medication', 'therapy drug',
            'disposable', 'single use', 'sterile', 'packaging'
        ]
        
        def is_surgical_device(row):
            """Check if device is surgical with strict criteria"""
            # Get all text fields to search
            device_name = str(row.get('openfda', {}).get('device_name', '')).lower()
            generic_name = str(row.get('generic_name', '')).lower()
            trade_name = str(row.get('trade_name', '')).lower()
            product_code = str(row.get('product_code', '')).lower()
            all_text = f"{device_name} {generic_name} {trade_name} {product_code}"
            
            # First check exclusions - if it matches exclusion patterns, it's not surgical
            for exclusion in exclusion_patterns:
                if exclusion in all_text:
                    # Exception: if it's explicitly surgical AND matches exclusion, check more carefully
                    if 'surgical' in all_text or 'surgery' in all_text:
                        # Allow if it's clearly surgical (e.g., "surgical diagnostic" might be OK)
                        if 'surgical' in all_text and exclusion in ['diagnostic', 'monitor']:
                            continue  # Might be surgical diagnostic tool
                    else:
                        return False  # Non-surgical device
            
            # Must match at least one specific surgical keyword
            for keyword in surgery_keywords:
                if keyword.lower() in all_text:
                    return True
            
            return False
        
        # Filter devices
        surgery_mask = self.fda_data.apply(is_surgical_device, axis=1)
        self.surgery_devices = self.fda_data[surgery_mask].copy()
        
        # Additional validation: require at least one specific surgical specialty keyword
        # (not just generic terms)
        if len(self.surgery_devices) > 0:
            specialty_keywords = []
            for specialty, keywords in self.surgical_specialties.items():
                specialty_keywords.extend(keywords)
            
            def has_specific_surgical_term(row):
                device_name = str(row.get('openfda', {}).get('device_name', '')).lower()
                generic_name = str(row.get('generic_name', '')).lower()
                trade_name = str(row.get('trade_name', '')).lower()
                all_text = f"{device_name} {generic_name} {trade_name}"
                
                # Check for specific surgical terms (not just 'surgery' or 'surgical')
                for keyword in specialty_keywords:
                    if keyword.lower() in all_text:
                        return True
                
                # Also allow if it has surgical robot terms
                if any(term in all_text for term in ['surgical robot', 'robotic surgery', 'da vinci', 'mako', 'rosa']):
                    return True
                
                return False
            
            # Further filter to require specific surgical terms
            specific_mask = self.surgery_devices.apply(has_specific_surgical_term, axis=1)
            self.surgery_devices = self.surgery_devices[specific_mask].copy()
        
        # Categorize by surgical specialty
        if len(self.surgery_devices) > 0:
            self.surgery_devices['surgical_specialty'] = self.surgery_devices.apply(
                self._categorize_surgical_specialty, axis=1
            )
        
        console.print(f"✅ [green]Identified {len(self.surgery_devices)} surgery-related devices (strict filtering applied)[/green]")
    
    def _categorize_surgical_specialty(self, row):
        """Categorize device by surgical specialty"""
        device_name = str(row.get('openfda', {}).get('device_name', '')).lower()
        generic_name = str(row.get('generic_name', '')).lower()
        trade_name = str(row.get('trade_name', '')).lower()
        
        # Score each specialty based on keyword matches
        specialty_scores = {}
        
        for specialty, keywords in self.surgical_specialties.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in device_name or keyword.lower() in generic_name or keyword.lower() in trade_name:
                    score += 1
            specialty_scores[specialty] = score
        
        # Return the specialty with the highest score, or 'other_surgery' if no clear match
        if specialty_scores:
            max_score = max(specialty_scores.values())
            if max_score > 0:
                for specialty, score in specialty_scores.items():
                    if score == max_score:
                        return specialty
        
        return 'other_surgery'
    
    def analyze_surgery_devices(self):
        """Perform comprehensive analysis of surgery devices"""
        if self.surgery_devices.empty:
            console.print("⚠️ [yellow]No surgery devices found for analysis[/yellow]")
            return {}
        
        analysis_results = {
            'total_devices': len(self.surgery_devices),
            'specialty_breakdown': self.surgery_devices['surgical_specialty'].value_counts().to_dict(),
            'approval_trends': self._analyze_approval_trends(),
            'product_codes': self.surgery_devices['product_code'].value_counts().to_dict(),
            'manufacturers': self._analyze_manufacturers(),
            'recent_devices': self._get_recent_devices(),
            'high_impact_devices': self._identify_high_impact_devices()
        }
        
        return analysis_results
    
    def _analyze_approval_trends(self):
        """Analyze approval trends over time"""
        if 'decision_date' in self.surgery_devices.columns:
            # Convert dates and group by year
            self.surgery_devices['decision_date'] = pd.to_datetime(
                self.surgery_devices['decision_date'], errors='coerce'
            )
            self.surgery_devices['approval_year'] = self.surgery_devices['decision_date'].dt.year
            
            yearly_approvals = self.surgery_devices.groupby('approval_year').size()
            return yearly_approvals.to_dict()
        
        return {}
    
    def _analyze_manufacturers(self):
        """Analyze device manufacturers"""
        if 'applicant' in self.surgery_devices.columns:
            manufacturer_counts = self.surgery_devices['applicant'].value_counts()
            return manufacturer_counts.head(20).to_dict()
        
        return {}
    
    def _get_recent_devices(self, years=5):
        """Get devices approved in the last N years"""
        if 'decision_date' in self.surgery_devices.columns:
            cutoff_date = datetime.now() - timedelta(days=years*365)
            recent_mask = self.surgery_devices['decision_date'] >= cutoff_date
            recent_devices = self.surgery_devices[recent_mask]
            return recent_devices[['trade_name', 'surgical_specialty', 'decision_date']].to_dict('records')
        
        return []
    
    def _identify_high_impact_devices(self):
        """Identify potentially high-impact surgical devices"""
        # Look for devices with keywords suggesting innovation
        innovation_keywords = [
            'robot', 'robotic', 'artificial intelligence', 'ai', 'machine learning',
            'minimally invasive', 'endoscopic', 'laparoscopic', '3d', 'virtual reality',
            'augmented reality', 'smart', 'intelligent', 'automated', 'precision'
        ]
        
        high_impact_devices = []
        
        for _, device in self.surgery_devices.iterrows():
            device_name = str(device.get('openfda', {}).get('device_name', '')).lower()
            generic_name = str(device.get('generic_name', '')).lower()
            trade_name = str(device.get('trade_name', '')).lower()
            impact_score = 0
            
            for keyword in innovation_keywords:
                if keyword in device_name or keyword in generic_name or keyword in trade_name:
                    impact_score += 1
            
            if impact_score >= 1:  # At least one innovation keyword
                high_impact_devices.append({
                    'device_name': device.get('openfda', {}).get('device_name', ''),
                    'generic_name': device.get('generic_name', ''),
                    'trade_name': device.get('trade_name', ''),
                    'surgical_specialty': device.get('surgical_specialty', ''),
                    'impact_score': impact_score,
                    'decision_date': device.get('decision_date', ''),
                    'applicant': device.get('applicant', '')
                })
        
        # Sort by impact score
        high_impact_devices.sort(key=lambda x: x['impact_score'], reverse=True)
        return high_impact_devices[:20]  # Top 20
    
    def search_openalex_works(self, query, start_year=1990, end_year=2025, per_page=200):
        """
        Search OpenAlex for works related to surgical devices
        
        Args:
            query (str): Search query
            start_year (int): Start year for publication date filter
            end_year (int): End year for publication date filter
            per_page (int): Number of results per page
            
        Returns:
            list: List of work objects from OpenAlex
        """
        works = []
        cursor = "*"
        
        if self.verbose:
            console.print(f"\n🔍 [bold cyan]Searching OpenAlex[/bold cyan] for: [yellow]{query}[/yellow]")
            console.print(f"📅 Time range: {start_year} - {end_year}")
        
        # Use simple console output instead of Rich progress to avoid conflicts
        if self.verbose:
            console.print("📚 Fetching publications...")
        
        while cursor:
            payload = {
                "filter": (
                    f"default.search:{query},"
                    f"from_publication_date:{start_year}-01-01,"
                    f"to_publication_date:{end_year}-12-31,"
                    "has_doi:true"
                ),
                "per_page": per_page,
                "cursor": cursor
            }
            
            try:
                response = requests.get(
                    f"{self.base_url}/works", 
                    params=payload, 
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                works.extend(data["results"])
                cursor = data["meta"]["next_cursor"]
                
                # Optional: limit for testing
                if len(works) > 10000:
                    if self.verbose:
                        console.print("⚠️ [yellow]Reached limit of 10,000 publications, stopping search[/yellow]")
                    break
                    
            except requests.exceptions.RequestException as e:
                if self.verbose:
                    console.print(f"❌ [red]Error fetching data: {e}[/red]")
                    if "403" in str(e):
                        console.print("⚠️ [yellow]Rate limited by OpenAlex API, waiting 2 seconds...[/yellow]")
                        time.sleep(2)
                break
                
        if self.verbose:
            console.print(f"✅ [green]Found {len(works)} publications[/green]")
                    
        return works
    
    def get_device_publications(self, device_name, approval_date, years_before=3, years_after=3):
        """
        Get publications related to a specific surgical device around its approval date
        
        Args:
            device_name (str): Name of the surgical device
            approval_date (str): FDA approval date (YYYY-MM-DD)
            years_before (int): Years before approval to search
            years_after (int): Years after approval to search
            
        Returns:
            pd.DataFrame: Publications with citation data
        """
        approval_dt = datetime.strptime(approval_date, "%Y-%m-%d")
        start_year = approval_dt.year - years_before
        end_year = approval_dt.year + years_after
        
        # Ensure we capture a reasonable range for analysis
        # For older devices, extend the search window to get more historical context
        if approval_dt.year < 2020:
            # For devices approved before 2020, extend the search window
            start_year = max(1990, start_year - 2)  # Go back 2 more years for older devices
            end_year = min(2025, end_year + 2)      # Extend forward but cap at 2025
        elif approval_dt.year >= 2025:
            # For future/2025 devices, ensure we can search up to 2025
            end_year = max(end_year, 2025)
        
        if self.verbose:
            console.print(f"\n📊 [bold]Analyzing Surgical Device:[/bold] [cyan]{device_name}[/cyan]")
            console.print(f"📅 [bold]Approval Date:[/bold] {approval_date}")
            console.print(f"🔍 [bold]Search Window:[/bold] {start_year} - {end_year}")
            if approval_dt.year < 2020:
                console.print(f"📈 [yellow]Extended search window for older device (approved {approval_dt.year})[/yellow]")
            elif approval_dt.year >= 2025:
                console.print(f"🔮 [cyan]Future device - searching up to 2025[/cyan]")
        
        # Search for device-related publications
        works = self.search_openalex_works(device_name, start_year, end_year)
        
        publications = []
        for work in works:
            try:
                pub_data = {
                    'title': work.get('title', ''),
                    'doi': work.get('doi', ''),
                    'publication_year': work.get('publication_year'),
                    'publication_date': work.get('publication_date', ''),
                    'cited_by_count': work.get('cited_by_count', 0),
                    'concepts': [c.get('display_name', '') for c in work.get('concepts', []) if c],
                    'authors': [a.get('author', {}).get('display_name', '') for a in work.get('authorships', []) if a],
                    'journal': work.get('primary_location', {}).get('source', {}).get('display_name', ''),
                    'abstract': work.get('abstract_inverted_index', {}),
                    'device_name': device_name,
                    'approval_date': approval_date
                }
                publications.append(pub_data)
            except Exception as e:
                if self.verbose:
                    console.print(f"⚠️ [yellow]Error processing publication: {e}[/yellow]")
                continue
        
        if self.verbose:
            console.print(f"📚 [green]Processed {len(publications)} publications[/green]")
        
        return pd.DataFrame(publications)
    
    def kleinberg_burst_detection(self, time_series, gamma=0.5, s=2):
        """
        Implement Kleinberg's burst detection algorithm
        
        Args:
            time_series (list): List of (time, count) tuples
            gamma (float): Cost parameter for state transitions
            s (int): Number of states (0=normal, 1=burst)
            
        Returns:
            list: Burst periods with start, end, and intensity
        """
        if len(time_series) < 2:
            return []
        
        if self.verbose:
            console.print(f"🔍 [bold]Running Kleinberg Burst Detection[/bold]")
            console.print(f"⚙️ Parameters: γ={gamma}, states={s}")
        
        # Sort by time
        time_series = sorted(time_series, key=lambda x: x[0])
        times, counts = zip(*time_series)
        
        # Initialize state machine
        n = len(times)
        states = np.zeros((n, s), dtype=float)
        transitions = np.zeros((n, s, s), dtype=float)
        
        # Forward pass
        for i in range(n):
            for j in range(s):
                if i == 0:
                    states[i, j] = 0
                else:
                    # Transition costs
                    for k in range(s):
                        cost = gamma if j > k else 0
                        states[i, j] = max(states[i, j], 
                                         states[i-1, k] + self._emission_prob(counts[i], j) - cost)
        
        # Backward pass to find optimal path
        path = []
        current_state = np.argmax(states[-1])
        
        for i in range(n-1, -1, -1):
            path.append((times[i], current_state))
            if i > 0:
                # Find previous state
                best_prev = 0
                best_score = float('-inf')
                for j in range(s):
                    cost = gamma if current_state > j else 0
                    score = states[i-1, j] + self._emission_prob(counts[i], current_state) - cost
                    if score > best_score:
                        best_score = score
                        best_prev = j
                current_state = best_prev
        
        path.reverse()
        
        # Extract burst periods
        bursts = []
        in_burst = False
        burst_start = None
        
        for time, state in path:
            if state == 1 and not in_burst:  # Start of burst
                in_burst = True
                burst_start = time
            elif state == 0 and in_burst:  # End of burst
                in_burst = False
                bursts.append({
                    'start': burst_start,
                    'end': time,
                    'intensity': self._calculate_burst_intensity(time_series, burst_start, time)
                })
        
        # Handle ongoing burst
        if in_burst:
            bursts.append({
                'start': burst_start,
                'end': path[-1][0],
                'intensity': self._calculate_burst_intensity(time_series, burst_start, path[-1][0])
            })
        
        if self.verbose:
            console.print(f"✅ [green]Detected {len(bursts)} burst periods[/green]")
        
        return bursts
    
    def _emission_prob(self, count, state):
        """Calculate emission probability for burst detection"""
        if state == 0:  # Normal state
            return np.log(max(count, 1))
        else:  # Burst state
            return np.log(max(count, 1)) * 2  # Higher weight for burst state
    
    def _calculate_burst_intensity(self, time_series, start_time, end_time):
        """Calculate intensity of a burst period"""
        burst_counts = [count for time, count in time_series if start_time <= time <= end_time]
        if not burst_counts:
            return 0
        return sum(burst_counts) / len(burst_counts)
    
    def analyze_surgical_device_hype(self, device_name, approval_date):
        """
        Analyze hype around a specific surgical device
        
        Args:
            device_name (str): Name of the surgical device
            approval_date (str): FDA approval date
            
        Returns:
            dict: Hype analysis results
        """
        if self.verbose:
            console.print(f"\n{'='*60}")
            console.print(f"🔬 [bold blue]ANALYZING SURGICAL DEVICE HYPE[/bold blue]")
            console.print(f"{'='*60}")
        
        # Get publications
        publications = self.get_device_publications(device_name, approval_date)
        
        if publications.empty:
            if self.verbose:
                console.print(f"⚠️ [yellow]No publications found for {device_name}[/yellow]")
            return {
                'device_name': device_name,
                'total_publications': 0,
                'total_citations': 0,
                'avg_citations': 0,
                'burst_periods': [],
                'hype_score': 0,
                'peak_year': None,
                'sustained_interest': False
            }
        
        # Create time series for burst detection
        yearly_counts = publications.groupby('publication_year').size().reset_index()
        yearly_counts.columns = ['year', 'count']
        time_series = list(zip(yearly_counts['year'], yearly_counts['count']))
        
        # Detect bursts
        try:
            bursts = self.kleinberg_burst_detection(time_series)
        except Exception as e:
            if self.verbose:
                console.print(f"⚠️ [yellow]Error in burst detection: {e}[/yellow]")
            bursts = []
        
        # Calculate hype metrics
        total_pubs = len(publications)
        total_citations = publications['cited_by_count'].sum()
        avg_citations = publications['cited_by_count'].mean()
        
        # Find peak year
        peak_year = yearly_counts.loc[yearly_counts['count'].idxmax(), 'year']
        
        # Calculate hype score (normalized combination of metrics)
        hype_score = self._calculate_hype_score(total_pubs, total_citations, avg_citations, len(bursts))
        
        # Check for sustained interest (publications continue after initial burst)
        approval_year = datetime.strptime(approval_date, "%Y-%m-%d").year
        post_approval_pubs = publications[publications['publication_year'] > approval_year + 2]
        sustained_interest = len(post_approval_pubs) > total_pubs * 0.3
        
        if self.verbose:
            self._display_surgical_device_results(device_name, total_pubs, total_citations, 
                                               avg_citations, hype_score, peak_year, bursts, sustained_interest)
        
        return {
            'device_name': device_name,
            'total_publications': total_pubs,
            'total_citations': total_citations,
            'avg_citations': avg_citations,
            'burst_periods': bursts,
            'hype_score': hype_score,
            'peak_year': peak_year,
            'sustained_interest': sustained_interest
        }
    
    def _display_surgical_device_results(self, device_name, total_pubs, total_citations, 
                                       avg_citations, hype_score, peak_year, bursts, sustained_interest):
        """Display results for a surgical device"""
        console.print(f"\n📊 [bold cyan]Surgical Device Analysis Results[/bold cyan]")
        console.print(f"🔪 Device: [yellow]{device_name}[/yellow]")
        
        # Create results table
        results_table = Table(title="Publication Analysis", box=box.ROUNDED)
        results_table.add_column("Metric", style="cyan", no_wrap=True)
        results_table.add_column("Value", justify="right", style="green")
        
        results_table.add_row("Total Publications", str(total_pubs))
        results_table.add_row("Total Citations", str(total_citations))
        results_table.add_row("Average Citations", f"{avg_citations:.2f}")
        results_table.add_row("Hype Score", f"{hype_score:.4f}")
        results_table.add_row("Peak Year", str(peak_year) if peak_year else "N/A")
        results_table.add_row("Burst Periods", str(len(bursts)))
        results_table.add_row("Sustained Interest", "✅ Yes" if sustained_interest else "❌ No")
        
        console.print(results_table)
        
        # Display burst periods if any
        if bursts:
            burst_table = Table(title="Burst Periods", box=box.ROUNDED)
            burst_table.add_column("Start", style="cyan")
            burst_table.add_column("End", style="cyan")
            burst_table.add_column("Intensity", justify="right", style="green")
            
            for burst in bursts:
                burst_table.add_row(
                    str(burst['start']),
                    str(burst['end']),
                    f"{burst['intensity']:.2f}"
                )
            
            console.print(burst_table)
    
    def _calculate_hype_score(self, total_pubs, total_citations, avg_citations, num_bursts):
        """Calculate normalized hype score"""
        # Normalize each component
        pub_score = min(total_pubs / 100, 1.0)  # Cap at 100 publications
        citation_score = min(total_citations / 1000, 1.0)  # Cap at 1000 citations
        avg_citation_score = min(avg_citations / 50, 1.0)  # Cap at 50 avg citations
        burst_score = min(num_bursts / 3, 1.0)  # Cap at 3 bursts
        
        # Weighted combination
        hype_score = (0.3 * pub_score + 0.3 * citation_score + 
                     0.2 * avg_citation_score + 0.2 * burst_score)
        
        return hype_score
    
    def run_surgical_device_hype_analysis(self, max_devices=None):
        """
        Run comprehensive hype analysis on ALL surgical devices
        
        Args:
            max_devices (int): Maximum number of devices to analyze (None for all devices)
            
        Returns:
            list: List of hype analysis results
        """
        if self.surgery_devices.empty:
            console.print("⚠️ [yellow]No surgery devices available for analysis[/yellow]")
            return []
        
        console.print(f"\n🔬 [bold blue]RUNNING COMPREHENSIVE SURGICAL DEVICE HYPE ANALYSIS[/bold blue]")
        console.print(f"📊 Analyzing {len(self.surgery_devices)} surgical devices...")
        
        # Use all surgical devices, but prioritize historical ones for better publication data
        # Filter for devices approved before 2025 to have historical publication data
        historical_devices = self.surgery_devices[
            self.surgery_devices['decision_date'].dt.year < 2025
        ]
        
        if historical_devices.empty:
            console.print("⚠️ [yellow]No historical devices found, using all devices[/yellow]")
            devices_to_analyze = self.surgery_devices
        else:
            devices_to_analyze = historical_devices
            
        # Limit if specified
        if max_devices:
            devices_to_analyze = devices_to_analyze.head(max_devices)
            console.print(f"📊 Analyzing up to {max_devices} surgical devices...")
        else:
            console.print(f"📊 Analyzing ALL {len(devices_to_analyze)} surgical devices...")
        
        results = []
        
        # Use simple iteration instead of Rich progress to avoid conflicts
        total_devices = len(devices_to_analyze)
        successful_analyses = 0
        failed_analyses = 0
        
        for idx, device in devices_to_analyze.iterrows():
            device_name = device.get('openfda', {}).get('device_name', '')
            trade_name = device.get('trade_name', '')
            approval_date = device.get('decision_date', '')
            
            # Convert pandas Timestamp to string if needed
            if hasattr(approval_date, 'strftime'):
                approval_date = approval_date.strftime('%Y-%m-%d')
            
            # Use trade name if available, otherwise device name
            search_name = trade_name if trade_name else device_name
            
            if not search_name or not approval_date:
                failed_analyses += 1
                continue
            
            if self.verbose:
                progress = f"[{idx+1}/{total_devices}]"
                console.print(f"\n📊 {progress} Analyzing {search_name[:50]}...")
            
            try:
                # Analyze device hype
                analysis_result = self.analyze_surgical_device_hype(search_name, approval_date)
                
                # Add device metadata
                analysis_result.update({
                    'surgical_specialty': device.get('surgical_specialty', ''),
                    'applicant': device.get('applicant', ''),
                    'product_code': device.get('product_code', ''),
                    'trade_name': trade_name,
                    'device_name': device_name
                })
                
                results.append(analysis_result)
                successful_analyses += 1
                
                if self.verbose:
                    console.print(f"✅ [green]{search_name[:30]}: Hype Score = {analysis_result['hype_score']:.3f}[/green]")
                
                # Rate limiting for API calls - be more conservative
                time.sleep(2)  # Reduced for large-scale analysis
                
            except Exception as e:
                failed_analyses += 1
                if self.verbose:
                    console.print(f"❌ [red]Error analyzing {search_name}: {e}[/red]")
                continue
        
        if self.verbose:
            console.print(f"\n🎉 [bold green]Analysis Complete![/bold green]")
            console.print(f"✅ [green]Successfully analyzed: {successful_analyses} devices[/green]")
            console.print(f"❌ [red]Failed analyses: {failed_analyses} devices[/red]")
            console.print(f"📊 [cyan]Total processed: {successful_analyses + failed_analyses} devices[/cyan]")
        
        return results
    
    def analyze_single_device(self, device_data):
        """Analyze a single device (for parallel processing)"""
        try:
            device_name = device_data.get('device_name', '')
            trade_name = device_data.get('trade_name', '')
            approval_date = device_data.get('approval_date', '')
            surgical_specialty = device_data.get('surgical_specialty', '')
            applicant = device_data.get('applicant', '')
            product_code = device_data.get('product_code', '')
            
            # Use trade name if available, otherwise device name
            search_name = trade_name if trade_name else device_name
            
            if not search_name or not approval_date:
                return None
            
            # Analyze device hype
            analysis_result = self.analyze_surgical_device_hype(search_name, approval_date)
            
            # Add device metadata
            analysis_result.update({
                'surgical_specialty': surgical_specialty,
                'applicant': applicant,
                'product_code': product_code,
                'trade_name': trade_name,
                'device_name': device_name
            })
            
            return analysis_result
            
        except Exception as e:
            if self.verbose:
                console.print(f"❌ [red]Error analyzing {device_data.get('device_name', 'Unknown')}: {e}[/red]")
            return None

    def run_surgical_device_hype_analysis_parallel(self, max_devices=None, max_workers=4):
        """
        Run comprehensive hype analysis on ALL surgical devices with parallelization
        
        Args:
            max_devices (int): Maximum number of devices to analyze (None for all devices)
            max_workers (int): Number of parallel workers
            
        Returns:
            list: List of hype analysis results
        """
        if self.surgery_devices.empty:
            console.print("⚠️ [yellow]No surgery devices available for analysis[/yellow]")
            return []
        
        console.print(f"\n🔬 [bold blue]RUNNING PARALLEL SURGICAL DEVICE HYPE ANALYSIS[/bold blue]")
        console.print(f"📊 Total surgical devices available: {len(self.surgery_devices)}")
        
        # Use ALL surgical devices (no filtering for historical ones)
        devices_to_analyze = self.surgery_devices.copy()
            
        # Limit if specified
        if max_devices:
            devices_to_analyze = devices_to_analyze.head(max_devices)
            console.print(f"📊 Analyzing up to {max_devices} surgical devices...")
        else:
            console.print(f"📊 Analyzing ALL {len(devices_to_analyze)} surgical devices...")
        
        console.print(f"🚀 [green]Using parallel processing with {max_workers} workers[/green]")
        
        results = []
        successful_analyses = 0
        failed_analyses = 0
        
        # Prepare device data for parallel processing
        device_list = []
        for idx, device in devices_to_analyze.iterrows():
            device_name = device.get('openfda', {}).get('device_name', '')
            trade_name = device.get('trade_name', '')
            approval_date = device.get('decision_date', '')
            
            # Convert pandas Timestamp to string if needed
            if hasattr(approval_date, 'strftime'):
                approval_date = approval_date.strftime('%Y-%m-%d')
            
            device_data = {
                'device_name': device_name,
                'trade_name': trade_name,
                'approval_date': approval_date,
                'surgical_specialty': device.get('surgical_specialty', ''),
                'applicant': device.get('applicant', ''),
                'product_code': device.get('product_code', '')
            }
            device_list.append(device_data)
        
        total_devices = len(device_list)
        console.print(f"📊 Starting parallel analysis of {total_devices} devices...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_device = {
                executor.submit(self.analyze_single_device, device_data): device_data 
                for device_data in device_list
            }
            
            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_device), 1):
                device_data = future_to_device[future]
                search_name = device_data.get('trade_name') or device_data.get('device_name', 'Unknown')
                
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        successful_analyses += 1
                        if self.verbose:
                            console.print(f"✅ [{i}/{total_devices}] {search_name[:30]}: Hype Score = {result['hype_score']:.3f}")
                    else:
                        failed_analyses += 1
                        if self.verbose:
                            console.print(f"❌ [{i}/{total_devices}] {search_name[:30]}: Failed")
                except Exception as e:
                    failed_analyses += 1
                    if self.verbose:
                        console.print(f"❌ [{i}/{total_devices}] {search_name[:30]}: Error - {e}")
                
                # Progress update every 10 devices
                if i % 10 == 0:
                    console.print(f"📊 Progress: {i}/{total_devices} ({i/total_devices*100:.1f}%)")
        
        console.print(f"\n🎉 [bold green]Parallel Analysis Complete![/bold green]")
        console.print(f"✅ [green]Successfully analyzed: {successful_analyses} devices[/green]")
        console.print(f"❌ [red]Failed analyses: {failed_analyses} devices[/red]")
        console.print(f"📊 [cyan]Total processed: {successful_analyses + failed_analyses} devices[/cyan]")
        
        return results
    
    def generate_surgery_report(self):
        """Generate a comprehensive surgery device report"""
        analysis = self.analyze_surgery_devices()
        
        if not analysis:
            console.print("❌ [red]No analysis data available[/red]")
            return
        
        # Create report
        report = {
            'summary': {
                'total_surgery_devices': analysis['total_devices'],
                'specialties_covered': len(analysis['specialty_breakdown']),
                'years_covered': len(analysis['approval_trends']),
                'top_manufacturers': len(analysis['manufacturers'])
            },
            'specialty_breakdown': analysis['specialty_breakdown'],
            'approval_trends': analysis['approval_trends'],
            'top_manufacturers': analysis['manufacturers'],
            'recent_devices': analysis['recent_devices'],
            'high_impact_devices': analysis['high_impact_devices']
        }
        
        return report
    
    def display_surgery_summary(self):
        """Display a beautiful summary of surgery device analysis"""
        report = self.generate_surgery_report()
        
        if not report:
            return
        
        console.print("\n")
        
        # Title
        title = Text("🔪 Surgery Device Analysis Report", style="bold blue")
        subtitle = Text(f"Analysis of {report['summary']['total_surgery_devices']} FDA-Approved Surgical Devices", style="italic cyan")
        
        title_panel = Panel(
            Align.center(title + "\n" + subtitle),
            border_style="blue",
            box=box.DOUBLE
        )
        console.print(title_panel)
        
        # Specialty breakdown table
        specialty_table = Table(title="Surgical Specialty Breakdown", box=box.ROUNDED)
        specialty_table.add_column("Specialty", style="cyan", no_wrap=True)
        specialty_table.add_column("Device Count", justify="right", style="green")
        specialty_table.add_column("Percentage", justify="right", style="yellow")
        
        total_devices = report['summary']['total_surgery_devices']
        for specialty, count in report['specialty_breakdown'].items():
            percentage = (count / total_devices) * 100
            specialty_table.add_row(
                specialty.replace('_', ' ').title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(specialty_table)
        
        # Top manufacturers
        if report['top_manufacturers']:
            manufacturer_table = Table(title="Top Surgical Device Manufacturers", box=box.ROUNDED)
            manufacturer_table.add_column("Manufacturer", style="cyan", no_wrap=True)
            manufacturer_table.add_column("Device Count", justify="right", style="green")
            
            for manufacturer, count in list(report['top_manufacturers'].items())[:10]:
                manufacturer_table.add_row(manufacturer, str(count))
            
            console.print(manufacturer_table)
        
        # High impact devices
        if report['high_impact_devices']:
            impact_table = Table(title="High-Impact Surgical Devices", box=box.ROUNDED)
            impact_table.add_column("Device Name", style="cyan", no_wrap=True)
            impact_table.add_column("Specialty", style="yellow")
            impact_table.add_column("Impact Score", justify="right", style="green")
            impact_table.add_column("Manufacturer", style="magenta")
            
            for device in report['high_impact_devices'][:10]:
                device_name = device.get('trade_name', device.get('device_name', 'Unknown Device'))
                impact_table.add_row(
                    device_name[:50] + "..." if len(device_name) > 50 else device_name,
                    device['surgical_specialty'].replace('_', ' ').title(),
                    str(device['impact_score']),
                    device['applicant'][:20] + "..." if len(device['applicant']) > 20 else device['applicant']
                )
            
            console.print(impact_table)
    
    def save_surgery_analysis(self, output_file="surgery_device_analysis.json"):
        """Save the surgery analysis results to a JSON file"""
        report = self.generate_surgery_report()
        
        if report:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            console.print(f"✅ [green]Surgery analysis saved to {output_file}[/green]")
        else:
            console.print("❌ [red]No analysis data to save[/red]")
    
    def create_surgery_visualizations(self):
        """Create visualizations for surgery device analysis"""
        report = self.generate_surgery_report()
        
        if not report:
            console.print("❌ [red]No analysis data available for visualization[/red]")
            return
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Surgery Device Analysis Visualizations', fontsize=16, fontweight='bold')
        
        # 1. Specialty breakdown pie chart
        if report['specialty_breakdown']:
            specialties = list(report['specialty_breakdown'].keys())
            counts = list(report['specialty_breakdown'].values())
            
            axes[0, 0].pie(counts, labels=[s.replace('_', ' ').title() for s in specialties], 
                          autopct='%1.1f%%', startangle=90)
            axes[0, 0].set_title('Surgical Specialty Distribution')
        
        # 2. Approval trends over time
        if report['approval_trends']:
            years = sorted(report['approval_trends'].keys())
            approvals = [report['approval_trends'][year] for year in years]
            
            axes[0, 1].plot(years, approvals, marker='o', linewidth=2, markersize=6)
            axes[0, 1].set_title('Surgical Device Approvals Over Time')
            axes[0, 1].set_xlabel('Year')
            axes[0, 1].set_ylabel('Number of Approvals')
            axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Top manufacturers bar chart
        if report['top_manufacturers']:
            manufacturers = list(report['top_manufacturers'].keys())[:10]
            counts = list(report['top_manufacturers'].values())[:10]
            
            axes[1, 0].barh(range(len(manufacturers)), counts)
            axes[1, 0].set_yticks(range(len(manufacturers)))
            axes[1, 0].set_yticklabels([m[:20] + "..." if len(m) > 20 else m for m in manufacturers])
            axes[1, 0].set_title('Top Surgical Device Manufacturers')
            axes[1, 0].set_xlabel('Number of Devices')
        
        # 4. High impact devices by specialty
        if report['high_impact_devices']:
            impact_by_specialty = defaultdict(int)
            for device in report['high_impact_devices']:
                impact_by_specialty[device['surgical_specialty']] += device['impact_score']
            
            specialties = list(impact_by_specialty.keys())
            scores = list(impact_by_specialty.values())
            
            axes[1, 1].bar(range(len(specialties)), scores)
            axes[1, 1].set_xticks(range(len(specialties)))
            axes[1, 1].set_xticklabels([s.replace('_', ' ').title() for s in specialties], rotation=45)
            axes[1, 1].set_title('Innovation Impact by Surgical Specialty')
            axes[1, 1].set_ylabel('Total Impact Score')
        
        plt.tight_layout()
        plt.savefig('surgery_device_analysis.png', dpi=300, bbox_inches='tight')
        console.print("✅ [green]Surgery device visualizations saved to surgery_device_analysis.png[/green]")
        plt.show()

def main():
    """Main function to run the surgery device analysis"""
    console.print("🔪 [bold]Starting Surgery Device Analysis with Publication Burst Detection[/bold]")
    
    # Initialize analyzer
    analyzer = SurgeryDeviceAnalyzer(verbose=True)
    
    # Display summary
    analyzer.display_surgery_summary()
    
    # Run publication analysis on surgical devices
    console.print("\n" + "="*80)
    console.print("🔬 [bold blue]PUBLICATION ANALYSIS PHASE[/bold blue]")
    console.print("="*80)
    
    # Run comprehensive hype analysis on ALL surgical devices
    console.print("\n" + "="*80)
    console.print("🔬 [bold blue]COMPREHENSIVE PUBLICATION ANALYSIS PHASE[/bold blue]")
    console.print("="*80)
    
    # Run hype analysis on surgical devices - analyze ALL devices with parallelization
    # Now run the full comprehensive analysis on all surgical devices with parallel processing
    console.print("🚀 [green]Using parallel processing for faster analysis[/green]")
    hype_results = analyzer.run_surgical_device_hype_analysis_parallel(max_devices=None, max_workers=4)  # All devices, 4 workers
    
    if hype_results:
        # Create enhanced report with publication data
        enhanced_report = analyzer.generate_surgery_report()
        enhanced_report['publication_analysis'] = {
            'devices_analyzed': len(hype_results),
            'total_publications': sum(r.get('total_publications', 0) for r in hype_results),
            'total_citations': sum(r.get('total_citations', 0) for r in hype_results),
            'avg_hype_score': np.mean([r.get('hype_score', 0) for r in hype_results]),
            'devices_with_bursts': len([r for r in hype_results if r.get('burst_periods')]),
            'sustained_interest_devices': len([r for r in hype_results if r.get('sustained_interest', False)]),
            'detailed_results': hype_results
        }
        
        # Save enhanced analysis with timestamp for fresh run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'surgery_device_enhanced_analysis_fresh_{timestamp}.json'
        
        with open(output_file, 'w') as f:
            json.dump(enhanced_report, f, indent=2, default=str)
        
        console.print(f"✅ [green]Fresh enhanced analysis saved to {output_file}[/green]")
        
        # Display top performing devices
        console.print("\n🏆 [bold cyan]TOP PERFORMING SURGICAL DEVICES[/bold cyan]")
        top_devices = sorted(hype_results, key=lambda x: x.get('hype_score', 0), reverse=True)[:5]
        
        top_table = Table(title="Top Surgical Devices by Hype Score", box=box.ROUNDED)
        top_table.add_column("Rank", style="cyan", justify="right")
        top_table.add_column("Device Name", style="yellow")
        top_table.add_column("Specialty", style="green")
        top_table.add_column("Hype Score", justify="right", style="magenta")
        top_table.add_column("Publications", justify="right", style="blue")
        top_table.add_column("Citations", justify="right", style="red")
        
        for i, device in enumerate(top_devices, 1):
            top_table.add_row(
                str(i),
                device.get('device_name', '')[:40] + "..." if len(device.get('device_name', '')) > 40 else device.get('device_name', ''),
                device.get('surgical_specialty', '').replace('_', ' ').title(),
                f"{device.get('hype_score', 0):.4f}",
                str(device.get('total_publications', 0)),
                str(device.get('total_citations', 0))
            )
        
        console.print(top_table)
    
    # Save basic analysis
    analyzer.save_surgery_analysis()
    
    # Create visualizations
    analyzer.create_surgery_visualizations()
    
    console.print("✅ [green]Surgery device analysis with publication burst detection completed![/green]")

if __name__ == "__main__":
    main() 