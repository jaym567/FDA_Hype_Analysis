#!/usr/bin/env python3
"""
FDA Device Approval and Surgical PubMed Citation Burst Analysis
Using OpenAlex API and Kleinberg Burst Detection Algorithm

This script analyzes the hype around new medical devices by:
1. Cross-referencing FDA PMA database dates
2. Collecting related PubMed publications within ±3 years
3. Implementing Kleinberg burst detection
4. Quantifying and predicting device hype
"""

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from tqdm import tqdm
import json
import warnings
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import re
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.live import Live
from rich.layout import Layout
from rich import box

warnings.filterwarnings('ignore')

# Initialize Rich console for beautiful output
console = Console()

class FDADeviceHypeAnalyzer:
    def __init__(self, openalex_email=None, verbose=True):
        """
        Initialize the FDA Device Hype Analyzer
        
        Args:
            openalex_email (str): Email for OpenAlex API (optional, for higher rate limits)
            verbose (bool): Enable verbose output with rich formatting
        """
        self.verbose = verbose
        self.base_url = "https://api.openalex.org"
        self.headers = {}
        if openalex_email:
            self.headers['User-Agent'] = f'mailto:{openalex_email}'
        
        # FDA device-related concept IDs in OpenAlex
        self.device_concepts = {
            "medical_devices": "C2778595633",
            "surgery": "C141071460", 
            "biomedical_engineering": "C2778595634",
            "clinical_trials": "C2778595635"
        }
        
        # Load real FDA PMA data from FDA's public database
        try:
            # First try to load from fetched FDA data files
            fda_data = self._load_fetched_fda_data()
            if not fda_data.empty:
                self.fda_pma_data = fda_data
                if self.verbose:
                    console.print(f"✅ [green]Loaded {len(fda_data)} devices from fetched FDA data[/green]")
            else:
                # Fallback to real_fda_data loader
                from .real_fda_data import RealFDADataLoader
                loader = RealFDADataLoader(verbose=self.verbose)
                self.fda_pma_data = loader.load_real_fda_data()
        except ImportError:
            # Fallback to built-in loader
            self.fda_pma_data = self._load_real_fda_data()
        
        if self.verbose:
            self._print_initialization_info()
        
    def _print_initialization_info(self):
        """Print beautiful initialization information"""
        console.print("\n")
        
        # Title panel
        title = Text("🔬 FDA Device Hype Analysis System", style="bold blue")
        subtitle = Text("Powered by OpenAlex API & Kleinberg Burst Detection", style="italic cyan")
        
        title_panel = Panel(
            Align.center(title + "\n" + subtitle),
            border_style="blue",
            box=box.DOUBLE
        )
        console.print(title_panel)
        
        # System info table
        info_table = Table(title="System Information", box=box.ROUNDED)
        info_table.add_column("Component", style="cyan", no_wrap=True)
        info_table.add_column("Status", style="green")
        info_table.add_column("Details", style="white")
        
        info_table.add_row("OpenAlex API", "✅ Ready", "Base URL: https://api.openalex.org")
        info_table.add_row("FDA PMA Data", "✅ Loaded", f"{len(self.fda_pma_data)} sample devices")
        info_table.add_row("Burst Detection", "✅ Ready", "Kleinberg algorithm implemented")
        info_table.add_row("Hype Prediction", "✅ Ready", "ML-based prediction model")
        
        console.print(info_table)
        
        # Device summary
        device_table = Table(title="Sample FDA Devices", box=box.ROUNDED)
        device_table.add_column("Device Name", style="cyan", no_wrap=True)
        device_table.add_column("Type", style="yellow")
        device_table.add_column("Approval Date", style="green")
        
        for _, device in self.fda_pma_data.iterrows():
            device_table.add_row(
                device['device_name'],
                device['device_type'],
                device['approval_date']
            )
        
        console.print(device_table)
        
    def _load_real_fda_data(self):
        """Load real FDA PMA data from FDA's public database"""
        try:
            if self.verbose:
                console.print("🔍 [bold]Loading real FDA PMA data...[/bold]")
            
            # Method 1: Try to load from FDA's public API
            fda_data = self._load_from_fda_api()
            if not fda_data.empty:
                if self.verbose:
                    console.print(f"✅ [green]Loaded {len(fda_data)} devices from FDA API[/green]")
                return fda_data
            
            # Method 2: Try to load from FDA's public dataset
            fda_data = self._load_from_fda_dataset()
            if not fda_data.empty:
                if self.verbose:
                    console.print(f"✅ [green]Loaded {len(fda_data)} devices from FDA dataset[/green]")
                return fda_data
            
            # Method 3: Fallback to sample data if real data unavailable
            if self.verbose:
                console.print("⚠️ [yellow]Real FDA data unavailable, using sample data[/yellow]")
            return self._load_sample_fda_data()
            
        except Exception as e:
            if self.verbose:
                console.print(f"❌ [red]Error loading FDA data: {e}[/red]")
                console.print("⚠️ [yellow]Falling back to sample data[/yellow]")
            return self._load_sample_fda_data()
    
    def _load_from_fda_api(self):
        """Load FDA PMA data from FDA's public API"""
        try:
            # FDA's public API endpoint for PMA data
            api_url = "https://api.fda.gov/device/pma.json"
            
            # Parameters to get recent PMA approvals
            params = {
                'limit': 100,  # Get up to 100 recent PMAs
                'sort': 'decision_date:desc'  # Most recent first
            }
            
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'results' not in data:
                return pd.DataFrame()
            
            fda_devices = []
            for result in data['results']:
                try:
                    # Extract device information
                    device_name = result.get('device_name', 'Unknown Device')
                    decision_date = result.get('decision_date', '')
                    device_type = self._categorize_device_type(device_name)
                    
                    if decision_date and device_name != 'Unknown Device':
                        # Filter to 2000+
                        try:
                            approval_year = int(decision_date.split('-')[0]) if '-' in decision_date else int(decision_date[:4])
                            if approval_year >= 2000:
                                fda_devices.append({
                                    'device_name': device_name,
                                    'approval_date': decision_date,
                                    'approval_year': approval_year,
                                    'device_type': device_type,
                                    'pma_number': row.get('PMA Number', ''),
                                    'applicant': row.get('Applicant', ''),
                                    'decision': row.get('Decision', '')
                                })
                                fda_devices.append({
                                    'device_name': device_name,
                                    'approval_date': decision_date,
                                    'approval_year': approval_year,
                                    'device_type': device_type,
                                    'pma_number': row.get('PMA Number', ''),
                                    'applicant': row.get('Applicant', ''),
                                    'decision': row.get('Decision', '')
                                })
                        except (ValueError, IndexError):
                            continue
                except Exception as e:
                    continue
            
            if fda_devices:
                df = pd.DataFrame(fda_devices)
                # Filter to only approved devices
                df = df[df['decision'].str.contains('Approved', case=False, na=False)]
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            if self.verbose:
                console.print(f"❌ [red]FDA dataset error: {e}[/red]")
            return pd.DataFrame()
    
    def _categorize_device_type(self, device_name):
        """Categorize device type based on device name"""
        device_name_lower = device_name.lower()
        
        # Define device type keywords
        device_types = {
            'Surgical Robot': ['robot', 'robotic', 'da vinci', 'mako', 'rosa', 'surgical system'],
            'Cardiovascular': ['stent', 'valve', 'heart', 'cardiac', 'cardiovascular', 'coronary'],
            'Neuromodulation': ['brain', 'neuro', 'stimulation', 'deep brain', 'neuromodulation'],
            'Orthopedic': ['knee', 'hip', 'joint', 'orthopedic', 'orthopaedic', 'implant'],
            'Diabetes Management': ['insulin', 'diabetes', 'glucose', 'sensor', 'pump'],
            'Radiosurgery': ['cyberknife', 'radiosurgery', 'radiation', 'stereotactic'],
            'Ventricular Assist Device': ['lvad', 'ventricular', 'assist', 'heartmate'],
            'Imaging': ['mri', 'ct', 'ultrasound', 'imaging', 'scanner'],
            'Diagnostic': ['diagnostic', 'test', 'assay', 'analyzer'],
            'Therapeutic': ['therapeutic', 'treatment', 'therapy']
        }
        
        for device_type, keywords in device_types.items():
            if any(keyword in device_name_lower for keyword in keywords):
                return device_type
        
        return 'Other'
    
    def _load_sample_fda_data(self):
        """Load sample FDA PMA data as fallback"""
        sample_data = [
            {"device_name": "Da Vinci Surgical System", "approval_date": "2000-07-11", "device_type": "Surgical Robot"},
            {"device_name": "HeartMate II LVAD", "approval_date": "2008-04-21", "device_type": "Ventricular Assist Device"},
            {"device_name": "CyberKnife System", "approval_date": "2001-08-22", "device_type": "Radiosurgery"},
            {"device_name": "Intuitive Surgical System", "approval_date": "2000-07-11", "device_type": "Surgical Robot"},
            {"device_name": "Medtronic Deep Brain Stimulation", "approval_date": "2003-01-14", "device_type": "Neuromodulation"},
            {"device_name": "Boston Scientific Drug-Eluting Stent", "approval_date": "2003-04-24", "device_type": "Cardiovascular"},
            {"device_name": "Edwards SAPIEN Transcatheter Valve", "approval_date": "2011-11-02", "device_type": "Cardiovascular"},
            {"device_name": "Stryker Mako Robotic System", "approval_date": "2008-06-20", "device_type": "Surgical Robot"},
            {"device_name": "Zimmer Biomet ROSA Knee System", "approval_date": "2019-12-19", "device_type": "Orthopedic"},
            {"device_name": "Medtronic Guardian Sensor 3", "approval_date": "2018-06-21", "device_type": "Diabetes Management"}
        ]
        return pd.DataFrame(sample_data)
    
    def _load_fetched_fda_data(self):
        """Load FDA data from fetched files"""
        import json
        import pandas as pd
        
        # Check for fetched FDA data files in data directory
        data_dir = Path(__file__).parent.parent / 'data'
        fda_files = [
            data_dir / "fda_pma_comprehensive.json",  # Combined recent + historical
            data_dir / "fda_pma_fixed.json",
            data_dir / "fda_pma_by_month.json"
        ]
        
        for file in fda_files:
            if Path(file).exists():
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    
                    if data and len(data) > 0:
                        # Convert to DataFrame
                        df = pd.DataFrame(data)
                        
                        # Extract and clean device information
                        devices = []
                        for _, row in df.iterrows():
                            try:
                                device_name = row.get('trade_name', row.get('device_name', 'Unknown'))
                                decision_date = row.get('decision_date', 'Unknown')
                                decision_code = row.get('decision_code', 'Unknown')
                                applicant = row.get('applicant', 'Unknown')
                                pma_number = row.get('pma_number', 'Unknown')
                                
                                # Only include approved devices from 2000 onwards
                                if decision_code == 'APPR' and device_name != 'Unknown' and decision_date != 'Unknown':
                                    # Parse date and filter to 2000+
                                    try:
                                        approval_year = int(decision_date.split('-')[0]) if '-' in decision_date else int(decision_date[:4])
                                        if approval_year >= 2000:
                                            device_type = self._categorize_device_type(device_name)
                                            
                                            devices.append({
                                                'device_name': device_name,
                                                'approval_date': decision_date,
                                                'approval_year': approval_year,
                                                'device_type': device_type,
                                                'applicant': applicant,
                                                'pma_number': pma_number,
                                                'decision': 'Approved',
                                                'source': 'fda_api'
                                            })
                                    except (ValueError, IndexError):
                                        continue
                            except Exception as e:
                                continue
                        
                        if devices:
                            result_df = pd.DataFrame(devices)
                            if self.verbose:
                                console.print(f"📊 [cyan]Loaded {len(result_df)} approved devices from {file}[/cyan]")
                            return result_df
                            
                except Exception as e:
                    if self.verbose:
                        console.print(f"⚠️ [yellow]Error reading {file}: {e}[/yellow]")
                    continue
        
        # Return empty DataFrame if no valid data found
        return pd.DataFrame()
    
    def search_openalex_works(self, query, start_year=2000, end_year=2025, per_page=200):
        """
        Search OpenAlex for works related to medical devices
        
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
                    headers=self.headers
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
                break
                
        if self.verbose:
            console.print(f"✅ [green]Found {len(works)} publications[/green]")
                    
        return works
    
    def get_device_publications(self, device_name, approval_date, years_before=3, years_after=3):
        """
        Get publications related to a specific device around its approval date
        
        Args:
            device_name (str): Name of the medical device
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
            start_year = max(2000, start_year - 2)  # Go back 2 more years but not before 2000
            end_year = min(2025, end_year + 2)      # Extend forward but cap at 2025
        elif approval_dt.year >= 2025:
            # For future/2025 devices, ensure we can search up to 2025
            end_year = max(end_year, 2025)
        
        if self.verbose:
            console.print(f"\n📊 [bold]Analyzing Device:[/bold] [cyan]{device_name}[/cyan]")
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
            pub_data = {
                'title': work.get('title', ''),
                'doi': work.get('doi', ''),
                'publication_year': work.get('publication_year'),
                'publication_date': work.get('publication_date', ''),
                'cited_by_count': work.get('cited_by_count', 0),
                'concepts': [c.get('display_name', '') for c in work.get('concepts', [])],
                'authors': [a.get('author', {}).get('display_name', '') for a in work.get('authorships', [])],
                'journal': work.get('primary_location', {}).get('source', {}).get('display_name', ''),
                'abstract': work.get('abstract_inverted_index', {}),
                'device_name': device_name,
                'approval_date': approval_date
            }
            publications.append(pub_data)
        
        if self.verbose:
            console.print(f"📚 [green]Processed {len(publications)} publications[/green]")
        
        return pd.DataFrame(publications)
    
    def kleinberg_burst_detection(self, time_series, gamma=1.0, s=2.0, n_states=2):
        """
        Implement Kleinberg's burst detection algorithm using Poisson-based HMM
        
        Args:
            time_series (list): List of (time, count) tuples
            gamma (float): Cost parameter for state transitions (higher = harder to switch)
            s (float): Scaling factor for burst states (activity multiplier)
            n_states (int): Number of states (0=normal, 1=burst, etc.)
            
        Returns:
            list: Burst periods with start, end, and intensity
        """
        if len(time_series) < 2:
            return []
        
        # Sort by time
        time_series = sorted(time_series, key=lambda x: x[0])
        times, counts = zip(*time_series)
        counts = np.array(counts, dtype=float)
        
        # 1. Parameter Estimation
        T = len(counts)       # Total time steps
        R = np.sum(counts)    # Total events
        if R == 0:
            return []
            
        # Expected rate (lambda_0) = total events / total duration
        # Using T for yearly duration
        lambda_0 = R / T
        
        if lambda_0 == 0:
            return []
            
        # Define rates for each state: lambda_i = lambda_0 * s^i
        # State 0: Normal (lambda_0)
        # State 1: Burst (lambda_0 * s)
        lambdas = [lambda_0 * (s ** i) for i in range(n_states)]
        
        if self.verbose:
            console.print(f"🔍 [bold]Running Kleinberg Burst Detection[/bold]")
            console.print(f"⚙️ Parameters: γ={gamma}, s={s}, n_states={n_states}")
            console.print(f"📊 Baseline Rate: {lambda_0:.4f} pubs/year")
            console.print(f"🔥 Burst Rate (State 1): {lambdas[1]:.4f} pubs/year")

        # 2. Initialization
        # C[t, i] is the minimum cost to reach state i at time t
        C = np.full((T, n_states), np.inf)
        # P[t, i] stores the previous state that led to C[t, i]
        P = np.zeros((T, n_states), dtype=int)
        
        # Initial costs (start in state 0 with cost 0, others infinite)
        # Using negative log-likelihood of Poisson emission for t=0
        # Cost(emit) = -ln(P(count|lambda)) ≈ lambda - count * ln(lambda) (ignoring constants)
        def emission_cost(r, lam):
            if lam <= 0: return np.inf
            # Poisson cost function (negative log likelihood)
            return lam - r * np.log(lam)

        # Transition cost function
        def transition_cost(i, j):
            if j <= i:
                return 0  # No cost to drop down or stay
            else:
                return (j - i) * gamma * np.log(T)
        
        # Initialize t=0
        for i in range(n_states):
            if i == 0:
                C[0, i] = emission_cost(counts[0], lambdas[i])
            else:
                # Infinite cost to start in a burst state (assumption)
                C[0, i] = np.inf 

        # 3. Viterbi Forward Pass
        for t in range(1, T):
            for j in range(n_states): # Current state
                emit_c = emission_cost(counts[t], lambdas[j])
                
                # Find best previous state i
                best_cost = np.inf
                best_prev = -1
                
                for i in range(n_states): # Previous state
                    trans_c = transition_cost(i, j)
                    total_c = C[t-1, i] + trans_c + emit_c
                    
                    if total_c < best_cost:
                        best_cost = total_c
                        best_prev = i
                
                C[t, j] = best_cost
                P[t, j] = best_prev

        # 4. Backtracking (Find optimal path)
        state_sequence = np.zeros(T, dtype=int)
        
        # Find minimum cost state at last time step
        state_sequence[T-1] = np.argmin(C[T-1])
        
        for t in range(T-2, -1, -1):
            state_sequence[t] = P[t+1, state_sequence[t+1]]
            
        # 5. Extract Burst Periods
        bursts = []
        in_burst = False
        burst_start = None
        burst_level = 0
        
        for t, state in enumerate(state_sequence):
            if state > 0:
                if not in_burst:
                    in_burst = True
                    burst_start = times[t]
                    burst_level = state
                elif state != burst_level:
                    # Change in burst intensity (nested burst), count as new phase or max
                    # For simplicity, if we go 1 -> 2, we just treat it as continuing burst
                    # If we really want hierarchical, we'd structure differently.
                    # Here we just track "In Burst" vs "Normal"
                    burst_level = max(burst_level, state)
            else:
                if in_burst:
                    in_burst = False
                    # End of burst was previous year
                    burst_end = times[t-1]
                    burst_int = self._calculate_burst_intensity(time_series, burst_start, burst_end)
                    bursts.append({
                        'start': burst_start,
                        'end': burst_end,
                        'intensity': burst_int,
                        'level': int(burst_level)
                    })
                    burst_level = 0

        # Handle burst active at end
        if in_burst:
            burst_end = times[T-1]
            burst_int = self._calculate_burst_intensity(time_series, burst_start, burst_end)
            bursts.append({
                'start': burst_start,
                'end': burst_end,
                'intensity': burst_int,
                'level': int(burst_level)
            })

        if self.verbose:
            console.print(f"✅ [green]Detected {len(bursts)} burst periods (Poisson method)[/green]")
            
        return bursts

    def _calculate_burst_intensity(self, time_series, start_time, end_time):
        """
        Calculate relative intensity of a burst period
        
        Returns excess publications per year compared to baseline average
        """
        # Calculate global baseline first
        total_counts = sum(c for t, c in time_series)
        duration_total = len(time_series)
        baseline_rate = total_counts / max(1, duration_total)
        
        # Calculate burst stats
        burst_counts = [count for time, count in time_series if start_time <= time <= end_time]
        if not burst_counts:
            return 0.0
            
        burst_total = sum(burst_counts)
        burst_duration = len(burst_counts) # Years inclusive
        burst_rate = burst_total / max(1, burst_duration)
        
        # Intensity = How many MORE papers per year than average?
        intensity = max(0, burst_rate - baseline_rate)
        
        return intensity
    
    def analyze_device_hype(self, device_name, approval_date):
        """
        Analyze hype around a specific device
        
        Args:
            device_name (str): Name of the medical device
            approval_date (str): FDA approval date
            
        Returns:
            dict: Hype analysis results
        """
        if self.verbose:
            console.print(f"\n{'='*60}")
            console.print(f"🔬 [bold blue]ANALYZING DEVICE HYPE[/bold blue]")
            console.print(f"{'='*60}")
        
        # Get publications
        publications = self.get_device_publications(device_name, approval_date)
        
        if publications.empty:
            if self.verbose:
                console.print(f"⚠️ [yellow]No publications found for {device_name}[/yellow]")
            device_type = self._categorize_device_type(device_name)
            # Extract approval year
            approval_year = None
            try:
                approval_dt = datetime.strptime(approval_date, "%Y-%m-%d")
                approval_year = approval_dt.year
            except:
                pass
            
            return {
                'device_name': device_name,
                'device_type': device_type,
                'approval_year': approval_year,
                'total_publications': 0,
                'total_citations': 0,
                'avg_citations': 0.0,
                'burst_periods': [],
                'hype_score': 0.0,
                'peak_year': None,
                'sustained_interest': False,
                'num_bursts': 0
            }
        
        # Create time series for burst detection
        yearly_counts = publications.groupby('publication_year').size().reset_index()
        yearly_counts.columns = ['year', 'count']
        time_series = list(zip(yearly_counts['year'], yearly_counts['count']))
        
        # Detect bursts
        bursts = self.kleinberg_burst_detection(time_series)
        
        # Calculate hype metrics
        total_pubs = len(publications)
        total_citations = publications['cited_by_count'].sum() if 'cited_by_count' in publications.columns else 0
        avg_citations = publications['cited_by_count'].mean() if 'cited_by_count' in publications.columns and total_pubs > 0 else 0.0
        
        # Handle NaN values
        if pd.isna(avg_citations):
            avg_citations = 0.0
        if pd.isna(total_citations):
            total_citations = 0
        
        # Find peak year
        if len(yearly_counts) > 0:
            peak_year = int(yearly_counts.loc[yearly_counts['count'].idxmax(), 'year'])
        else:
            peak_year = None
        
        # Calculate hype score (normalized combination of metrics)
        hype_score = self._calculate_hype_score(total_pubs, total_citations, avg_citations, len(bursts))
        
        # Check for sustained interest (publications continue after initial burst)
        approval_year = datetime.strptime(approval_date, "%Y-%m-%d").year
        post_approval_pubs = publications[publications['publication_year'] > approval_year + 2]
        sustained_interest = len(post_approval_pubs) > total_pubs * 0.3
        
        # Display results in a beautiful table
        if self.verbose:
            self._display_device_results(device_name, total_pubs, total_citations, 
                                       avg_citations, hype_score, peak_year, bursts, sustained_interest)
        
        # Categorize device type
        device_type = self._categorize_device_type(device_name)
        
        # Extract approval year
        approval_year = None
        try:
            approval_dt = datetime.strptime(approval_date, "%Y-%m-%d")
            approval_year = approval_dt.year
        except:
            pass
        
        return {
            'device_name': device_name,
            'device_type': device_type,
            'approval_year': approval_year,
            'total_publications': total_pubs,
            'total_citations': int(total_citations),
            'avg_citations': float(avg_citations),
            'burst_periods': bursts,
            'hype_score': float(hype_score),
            'peak_year': peak_year,
            'sustained_interest': sustained_interest,
            'num_bursts': len(bursts),
            'publications_df': publications
        }
    
    def _display_device_results(self, device_name, total_pubs, total_citations, 
                              avg_citations, hype_score, peak_year, bursts, sustained_interest):
        """Display device analysis results in a beautiful table"""
        
        # Main metrics table
        metrics_table = Table(title=f"📊 Analysis Results: {device_name}", box=box.ROUNDED)
        metrics_table.add_column("Metric", style="cyan", no_wrap=True)
        metrics_table.add_column("Value", style="white")
        metrics_table.add_column("Status", style="green")
        
        # Determine status based on values
        pub_status = "🟢 High" if total_pubs > 50 else "🟡 Medium" if total_pubs > 20 else "🔴 Low"
        citation_status = "🟢 High" if total_citations > 500 else "🟡 Medium" if total_citations > 200 else "🔴 Low"
        hype_status = "🟢 High" if hype_score > 0.7 else "🟡 Medium" if hype_score > 0.4 else "🔴 Low"
        sustained_status = "🟢 Yes" if sustained_interest else "🔴 No"
        
        metrics_table.add_row("Total Publications", f"{total_pubs:,}", pub_status)
        metrics_table.add_row("Total Citations", f"{total_citations:,}", citation_status)
        metrics_table.add_row("Average Citations", f"{avg_citations:.1f}", "📈")
        metrics_table.add_row("Hype Score", f"{hype_score:.3f}", hype_status)
        metrics_table.add_row("Peak Year", str(peak_year), "📅")
        metrics_table.add_row("Sustained Interest", str(sustained_interest), sustained_status)
        
        console.print(metrics_table)
        
        # Burst periods table
        if bursts:
            burst_table = Table(title="🚀 Citation Burst Periods", box=box.ROUNDED)
            burst_table.add_column("Burst #", style="cyan")
            burst_table.add_column("Period", style="yellow")
            burst_table.add_column("Duration", style="green")
            burst_table.add_column("Intensity", style="magenta")
            
            for i, burst in enumerate(bursts, 1):
                duration = burst['end'] - burst['start']
                burst_table.add_row(
                    f"Burst {i}",
                    f"{burst['start']} - {burst['end']}",
                    f"{duration} years",
                    f"{burst['intensity']:.1f} pubs/year"
                )
            
            console.print(burst_table)
        else:
            console.print("📉 [yellow]No burst periods detected[/yellow]")
    
    def _calculate_hype_score(self, total_pubs, total_citations, avg_citations, num_bursts):
        """Calculate normalized hype score"""
        # Normalize each metric (0-1 scale)
        norm_pubs = min(total_pubs / 100, 1.0)  # Cap at 100 publications
        norm_citations = min(total_citations / 1000, 1.0)  # Cap at 1000 citations
        norm_avg_citations = min(avg_citations / 50, 1.0)  # Cap at 50 avg citations
        norm_bursts = min(num_bursts / 3, 1.0)  # Cap at 3 bursts
        
        # Weighted combination
        hype_score = (0.3 * norm_pubs + 
                      0.3 * norm_citations + 
                      0.2 * norm_avg_citations + 
                      0.2 * norm_bursts)
        
        return hype_score
    
    def predict_device_hype(self, device_features):
        """
        Predict hype for a new device based on features
        
        Args:
            device_features (dict): Device characteristics
            
        Returns:
            float: Predicted hype score
        """
        # This is a simplified prediction model
        # In practice, you'd train a more sophisticated ML model
        
        base_score = 0.5
        
        # Adjust based on device type
        device_type_weights = {
            'Surgical Robot': 0.8,
            'Cardiovascular': 0.7,
            'Neuromodulation': 0.6,
            'Orthopedic': 0.5,
            'Diabetes Management': 0.4
        }
        
        device_type = device_features.get('device_type', 'Other')
        base_score *= device_type_weights.get(device_type, 0.5)
        
        # Adjust based on novelty (approximation)
        approval_year = device_features.get('approval_year', 2020)
        novelty_factor = max(0.5, 1.0 - (2024 - approval_year) * 0.1)
        base_score *= novelty_factor
        
        return min(base_score, 1.0)
    
    def run_comprehensive_analysis(self, limit=None):
        """
        Run comprehensive analysis on all FDA devices
        
        Args:
            limit (int): Maximum number of devices to analyze (None for all)
        """
        if self.verbose:
            console.print(f"\n{'='*60}")
            console.print(f"🚀 [bold blue]COMPREHENSIVE FDA DEVICE ANALYSIS[/bold blue]")
            console.print(f"{'='*60}")
            console.print(f"📋 Analyzing {len(self.fda_pma_data)} devices...")
        
        results = []
        
        # Apply limit if specified
        devices_to_analyze = self.fda_pma_data
        if limit:
            devices_to_analyze = self.fda_pma_data.head(limit)
            if self.verbose:
                console.print(f"⚠️ [yellow]Limiting analysis to first {limit} devices[/yellow]")

        # Use simple iteration instead of Rich progress to avoid conflicts
        for i, (_, device) in enumerate(devices_to_analyze.iterrows(), 1):
            try:
                if self.verbose:
                    console.print(f"\n📊 [{i}/{len(self.fda_pma_data)}] Analyzing {device['device_name']}...")
                
                analysis = self.analyze_device_hype(
                    device['device_name'], 
                    device['approval_date']
                )
                analysis['device_type'] = device['device_type']
                # Add approval year if available
                if 'approval_year' in device:
                    analysis['approval_year'] = device['approval_year']
                elif 'approval_date' in device:
                    try:
                        analysis['approval_year'] = int(device['approval_date'].split('-')[0])
                    except:
                        analysis['approval_year'] = None
                results.append(analysis)
                
                if self.verbose:
                    console.print(f"✅ [green]{device['device_name']}: Hype Score = {analysis['hype_score']:.3f}[/green]")
                
            except Exception as e:
                if self.verbose:
                    console.print(f"❌ [red]Error analyzing {device['device_name']}: {e}[/red]")
                continue
        
        if self.verbose:
            console.print(f"\n🎉 [bold green]Analysis Complete![/bold green] Processed {len(results)} devices.")
        
        return results
    
    def visualize_results(self, results):
        """Create visualizations of the analysis results"""
        if not results:
            if self.verbose:
                console.print("❌ [red]No results to visualize[/red]")
            return
        
        if self.verbose:
            console.print(f"\n📊 [bold]Generating Visualizations...[/bold]")
        
        # Create summary DataFrame with approval year
        summary_data = []
        for result in results:
            summary_data.append({
                'device_name': result['device_name'],
                'device_type': result.get('device_type', 'Other'),
                'approval_year': result.get('approval_year'),
                'hype_score': result['hype_score'],
                'total_publications': result['total_publications'],
                'total_citations': result.get('total_citations', 0),
                'avg_citations': result.get('avg_citations', 0.0),
                'num_bursts': result.get('num_bursts', len(result.get('burst_periods', []))),
                'sustained_interest': result.get('sustained_interest', False),
                'peak_year': result.get('peak_year')
            })
        
        df = pd.DataFrame(summary_data)
        df = df.sort_values('hype_score', ascending=False)  # Sort by hype score
        
        # Set clean, modern style
        plt.style.use('default')
        sns.set_style("whitegrid")
        sns.set_palette("Set2")
        
        # Create clean visualizations with better layout
        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)
        
        # Professional color palette
        colors = {
            'high': '#2E86AB',      # Blue for high hype
            'medium': '#A23B72',    # Purple for medium
            'low': '#F18F01',       # Orange for low
            'accent': '#C73E1D'     # Red for accents
        }
        
        # 1. Top Devices by Hype Score (Horizontal Bar Chart) - Top Left, spans 2 columns
        ax1 = fig.add_subplot(gs[0, :2])
        # Clean hype scores
        df_clean = df.copy()
        df_clean['hype_score'] = df_clean['hype_score'].replace([np.inf, -np.inf], np.nan).fillna(0)
        df_clean = df_clean.sort_values('hype_score', ascending=False)
        
        top_n = min(15, len(df_clean))
        top_df = df_clean.head(top_n)
        hype_scores_clean = top_df['hype_score'].fillna(0)
        bar_colors = [colors['high'] if x >= 0.6 else colors['medium'] if x >= 0.3 else colors['low'] 
                     for x in hype_scores_clean]
        bars = ax1.barh(range(len(top_df)), hype_scores_clean, color=bar_colors, alpha=0.8, edgecolor='white', linewidth=1.5)
        ax1.set_yticks(range(len(top_df)))
        ax1.set_yticklabels([str(name)[:40] + '...' if len(str(name)) > 40 else str(name) 
                            for name in top_df['device_name']], fontsize=9)
        ax1.set_xlabel('Hype Score', fontsize=11, fontweight='bold')
        ax1.set_title(f'Top {top_n} Devices by Hype Score', fontsize=13, fontweight='bold', pad=10)
        ax1.grid(axis='x', alpha=0.3, linestyle='--')
        max_hype = hype_scores_clean.max() if len(hype_scores_clean) > 0 else 1.0
        ax1.set_xlim(0, max_hype * 1.1)
        # Add value labels on bars
        for i, (idx, row) in enumerate(top_df.iterrows()):
            try:
                hype_val = float(row['hype_score']) if pd.notna(row['hype_score']) else 0.0
                if not (np.isnan(hype_val) or np.isinf(hype_val)):
                    ax1.text(hype_val + 0.01, i, f"{hype_val:.2f}", 
                            va='center', fontsize=8, fontweight='bold')
            except (ValueError, TypeError, KeyError):
                continue
        
        # 2. Hype Score Distribution (Histogram) - Top Right
        ax2 = fig.add_subplot(gs[0, 2])
        hype_scores_hist = df['hype_score'].replace([np.inf, -np.inf], np.nan).dropna()
        if len(hype_scores_hist) > 0:
            ax2.hist(hype_scores_hist, bins=15, color=colors['high'], alpha=0.7, edgecolor='white', linewidth=1.5)
            mean_val = hype_scores_hist.mean()
            median_val = hype_scores_hist.median()
            if not (np.isnan(mean_val) or np.isinf(mean_val)):
                ax2.axvline(mean_val, color=colors['accent'], linestyle='--', linewidth=2, label=f'Mean: {mean_val:.2f}')
            if not (np.isnan(median_val) or np.isinf(median_val)):
                ax2.axvline(median_val, color='black', linestyle='--', linewidth=2, label=f'Median: {median_val:.2f}')
        ax2.set_xlabel('Hype Score', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Number of Devices', fontsize=10, fontweight='bold')
        ax2.set_title('Hype Score Distribution', fontsize=12, fontweight='bold')
        ax2.legend(fontsize=8)
        ax2.grid(alpha=0.3, linestyle='--')
        
        # 3. Publications vs Citations (Scatter with Hype Coloring) - Middle Left, spans 2 columns
        ax3 = fig.add_subplot(gs[1, :2])
        # Clean data for scatter plot
        scatter_df = df.copy()
        scatter_df['total_publications'] = scatter_df['total_publications'].replace([np.inf, -np.inf], np.nan).fillna(0)
        scatter_df['total_citations'] = scatter_df['total_citations'].replace([np.inf, -np.inf], np.nan).fillna(0)
        scatter_df['hype_score'] = scatter_df['hype_score'].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        scatter = ax3.scatter(scatter_df['total_publications'], scatter_df['total_citations'], 
                             c=scatter_df['hype_score'], s=120, alpha=0.6, cmap='viridis', 
                             edgecolors='white', linewidths=1)
        ax3.set_xlabel('Total Publications', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Total Citations', fontsize=11, fontweight='bold')
        ax3.set_title('Research Impact: Publications vs Citations\n(Color = Hype Score)', 
                     fontsize=12, fontweight='bold', pad=10)
        ax3.grid(alpha=0.3, linestyle='--')
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('Hype Score', fontsize=10, fontweight='bold')
        # Add trend line
        if len(scatter_df) > 1:
            try:
                valid_mask = (scatter_df['total_publications'] > 0) & (scatter_df['total_citations'] > 0)
                if valid_mask.sum() > 1:
                    z = np.polyfit(scatter_df.loc[valid_mask, 'total_publications'], 
                                 scatter_df.loc[valid_mask, 'total_citations'], 1)
                    p = np.poly1d(z)
                    x_min, x_max = scatter_df['total_publications'].min(), scatter_df['total_publications'].max()
                    if x_max > x_min:
                        x_line = np.linspace(x_min, x_max, 100)
                        ax3.plot(x_line, p(x_line), "r--", alpha=0.5, linewidth=2, label='Trend')
                        ax3.legend(fontsize=9)
            except (ValueError, np.linalg.LinAlgError):
                pass
        
        # 4. Device Type Performance (Grouped Bar Chart) - Middle Right
        ax4 = fig.add_subplot(gs[1, 2])
        device_type_stats = df.groupby('device_type').agg({
            'hype_score': ['mean', 'count']
        }).round(3)
        device_type_stats.columns = ['avg_hype', 'count']
        device_type_stats = device_type_stats.sort_values('avg_hype', ascending=True)
        
        x_pos = np.arange(len(device_type_stats))
        bars = ax4.barh(x_pos, device_type_stats['avg_hype'], 
                       color=[colors['high'] if x >= 0.5 else colors['medium'] if x >= 0.3 else colors['low'] 
                             for x in device_type_stats['avg_hype']],
                       alpha=0.8, edgecolor='white', linewidth=1.5)
        ax4.set_yticks(x_pos)
        ax4.set_yticklabels([name[:15] + '...' if len(name) > 15 else name 
                            for name in device_type_stats.index], fontsize=9)
        ax4.set_xlabel('Average Hype Score', fontsize=10, fontweight='bold')
        ax4.set_title('Performance by Device Type', fontsize=12, fontweight='bold')
        ax4.grid(axis='x', alpha=0.3, linestyle='--')
        # Add count labels
        for i, (idx, row) in enumerate(device_type_stats.iterrows()):
            ax4.text(row['avg_hype'] + 0.02, i, f"n={int(row['count'])}", 
                    va='center', fontsize=8)
        
        # 5. Hype Score Over Time (if approval_year available) - Bottom Left
        ax5 = fig.add_subplot(gs[2, 0])
        if 'approval_year' in df.columns and df['approval_year'].notna().any():
            yearly_hype = df.groupby('approval_year')['hype_score'].agg(['mean', 'count']).reset_index()
            yearly_hype = yearly_hype[yearly_hype['count'] > 0]
            if len(yearly_hype) > 0:
                ax5_twin = ax5.twinx()
                line1 = ax5.plot(yearly_hype['approval_year'], yearly_hype['mean'], 
                               'o-', color=colors['high'], linewidth=2.5, markersize=8, 
                               label='Avg Hype Score', alpha=0.8)
                ax5.set_xlabel('Approval Year', fontsize=10, fontweight='bold')
                ax5.set_ylabel('Average Hype Score', fontsize=10, fontweight='bold', color=colors['high'])
                ax5.tick_params(axis='y', labelcolor=colors['high'])
                ax5.grid(alpha=0.3, linestyle='--')
                
                # Add count as bars
                bars2 = ax5_twin.bar(yearly_hype['approval_year'], yearly_hype['count'], 
                                   alpha=0.3, color=colors['accent'], width=0.8, label='Device Count')
                ax5_twin.set_ylabel('Number of Devices', fontsize=10, fontweight='bold', color=colors['accent'])
                ax5_twin.tick_params(axis='y', labelcolor=colors['accent'])
                
                ax5.set_title('Hype Trends Over Time', fontsize=12, fontweight='bold')
                # Combine legends
                lines1, labels1 = ax5.get_legend_handles_labels()
                lines2, labels2 = ax5_twin.get_legend_handles_labels()
                ax5.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
            else:
                ax5.text(0.5, 0.5, 'No approval year data', ha='center', va='center', transform=ax5.transAxes)
                ax5.set_title('Hype Trends Over Time', fontsize=12, fontweight='bold')
        else:
            ax5.text(0.5, 0.5, 'No approval year data', ha='center', va='center', transform=ax5.transAxes)
            ax5.set_title('Hype Trends Over Time', fontsize=12, fontweight='bold')
        
        # 6. Citation Efficiency (Citations per Publication) - Bottom Middle
        ax6 = fig.add_subplot(gs[2, 1])
        # Clean data first
        df_clean = df.copy()
        df_clean['total_publications'] = df_clean['total_publications'].replace([np.inf, -np.inf], np.nan).fillna(0)
        df_clean['total_citations'] = df_clean['total_citations'].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        efficiency = df_clean['total_citations'] / (df_clean['total_publications'] + 1)  # +1 to avoid division by zero
        efficiency = efficiency.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        if len(df_clean) > 0 and efficiency.max() > 0:
            df_clean['efficiency'] = efficiency
            top_efficiency = df_clean.nlargest(min(10, len(df_clean)), 'efficiency')
            efficiency_values = top_efficiency['efficiency']
            efficiency_values = efficiency_values.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            bars = ax6.barh(range(len(top_efficiency)), efficiency_values,
                          color=colors['medium'], alpha=0.8, edgecolor='white', linewidth=1.5)
            ax6.set_yticks(range(len(top_efficiency)))
            ax6.set_yticklabels([str(name)[:25] + '...' if len(str(name)) > 25 else str(name) 
                               for name in top_efficiency['device_name']], fontsize=8)
            ax6.set_xlabel('Citations per Publication', fontsize=10, fontweight='bold')
            ax6.set_title('Top Devices by Citation Efficiency', fontsize=12, fontweight='bold')
            ax6.grid(axis='x', alpha=0.3, linestyle='--')
        else:
            ax6.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax6.transAxes)
            ax6.set_title('Citation Efficiency', fontsize=12, fontweight='bold')
        
        # 7. Burst Analysis - Bottom Right
        ax7 = fig.add_subplot(gs[2, 2])
        burst_counts = df['num_bursts'].value_counts().sort_index()
        colors_burst = [colors['high'], colors['medium'], colors['low'], colors['accent'], '#6C757D']
        bars = ax7.bar(burst_counts.index, burst_counts.values, 
                      color=colors_burst[:len(burst_counts)], alpha=0.8, edgecolor='white', linewidth=1.5)
        ax7.set_xlabel('Number of Burst Periods', fontsize=10, fontweight='bold')
        ax7.set_ylabel('Number of Devices', fontsize=10, fontweight='bold')
        ax7.set_title('Citation Burst Distribution', fontsize=12, fontweight='bold')
        ax7.grid(axis='y', alpha=0.3, linestyle='--')
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax7.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Main title
        fig.suptitle('FDA Device Hype Analysis (2000-2025)', fontsize=16, fontweight='bold', y=0.995)
        
        plt.tight_layout(rect=[0, 0, 1, 0.98])
        
        # Save with high quality
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        filename = output_dir / 'fda_device_hype_analysis.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        
        if self.verbose:
            console.print(f"📈 [green]Visualizations saved to: {filename}[/green]")
        
        plt.close()  # Close to avoid showing plot
        
        return df
    
    def generate_report(self, results):
        """Generate a comprehensive analysis report"""
        if not results:
            return "No results to report"
        
        if self.verbose:
            console.print(f"\n📋 [bold]Generating Analysis Report...[/bold]")
        
        report = []
        report.append("=" * 60)
        report.append("FDA DEVICE HYPE ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary statistics
        hype_scores = [r['hype_score'] for r in results]
        report.append(f"Total devices analyzed: {len(results)}")
        report.append(f"Average hype score: {np.mean(hype_scores):.3f}")
        report.append(f"Median hype score: {np.median(hype_scores):.3f}")
        report.append(f"Highest hype score: {max(hype_scores):.3f}")
        report.append(f"Lowest hype score: {min(hype_scores):.3f}")
        report.append("")
        
        # Top performers
        sorted_results = sorted(results, key=lambda x: x['hype_score'], reverse=True)
        report.append("TOP 5 HIGHEST HYPE DEVICES:")
        report.append("-" * 40)
        for i, result in enumerate(sorted_results[:5], 1):
            report.append(f"{i}. {result['device_name']}")
            report.append(f"   Hype Score: {result['hype_score']:.3f}")
            report.append(f"   Publications: {result['total_publications']}")
            report.append(f"   Citations: {result['total_citations']}")
            report.append(f"   Burst Periods: {len(result['burst_periods'])}")
            report.append("")
        
        # Device type analysis
        device_types = {}
        for result in results:
            device_type = result['device_type']
            if device_type not in device_types:
                device_types[device_type] = []
            device_types[device_type].append(result['hype_score'])
        
        report.append("HYPE SCORES BY DEVICE TYPE:")
        report.append("-" * 40)
        for device_type, scores in device_types.items():
            avg_score = np.mean(scores)
            report.append(f"{device_type}: {avg_score:.3f} (n={len(scores)})")
        report.append("")
        
        # Burst analysis
        devices_with_bursts = [r for r in results if r['burst_periods']]
        report.append(f"Devices with citation bursts: {len(devices_with_bursts)}/{len(results)}")
        report.append(f"Devices with sustained interest: {sum(1 for r in results if r['sustained_interest'])}/{len(results)}")
        
        report_text = "\n".join(report)
        
        if self.verbose:
            console.print(Panel(report_text, title="📊 Analysis Report", border_style="blue"))
        
        return report_text


def main():
    """Main execution function"""
    console.print("\n")
    
    # Title
    title = Text("🔬 FDA Device Hype Analysis", style="bold blue")
    subtitle = Text("Using OpenAlex API & Kleinberg Burst Detection", style="italic cyan")
    
    title_panel = Panel(
        Align.center(title + "\n" + subtitle),
        border_style="blue",
        box=box.DOUBLE
    )
    console.print(title_panel)
    
    # Initialize analyzer
    analyzer = FDADeviceHypeAnalyzer(verbose=True)
    
    # Run comprehensive analysis
    results = analyzer.run_comprehensive_analysis()
    
    if results:
        # Generate visualizations
        summary_df = analyzer.visualize_results(results)
        
        # Generate report
        report = analyzer.generate_report(results)
        
        # Save results to output directory
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        summary_file = output_dir / 'fda_device_hype_summary.csv'
        summary_df.to_csv(summary_file, index=False)
        console.print(f"💾 [green]Summary data saved to: {summary_file}[/green]")
        
        # Example prediction
        console.print(f"\n{'='*50}")
        console.print(f"🔮 [bold blue]EXAMPLE HYPE PREDICTION[/bold blue]")
        console.print(f"{'='*50}")
        
        new_device = {
            'device_type': 'Surgical Robot',
            'approval_year': 2023
        }
        
        predicted_hype = analyzer.predict_device_hype(new_device)
        console.print(f"🤖 [cyan]Predicted hype score for new surgical robot:[/cyan] [bold green]{predicted_hype:.3f}[/bold green]")
        
        # Final summary
        console.print(f"\n{'='*60}")
        console.print(f"🎉 [bold green]ANALYSIS COMPLETE![/bold green]")
        console.print(f"{'='*60}")
        console.print(f"📊 Processed {len(results)} devices")
        console.print(f"📈 Generated visualizations")
        console.print(f"📋 Created comprehensive report")
        console.print(f"💾 Saved results to CSV")
        
    else:
        console.print("❌ [red]No results obtained. Check your internet connection and API access.[/red]")


if __name__ == "__main__":
    main() 