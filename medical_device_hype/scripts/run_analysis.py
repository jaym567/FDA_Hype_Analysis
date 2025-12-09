#!/usr/bin/env python3
"""
FDA Device Hype Analysis Runner
Dedicated script for running comprehensive analysis and generating figures/statistics

This script provides a complete analysis pipeline with:
- Beautiful terminal output
- Comprehensive visualizations
- Detailed statistics
- Multiple output formats
- Configurable analysis options
- Smart FDA data management
"""

import argparse
import sys
import os
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from scipy.stats import (
    pearsonr, spearmanr, mannwhitneyu, kruskal, 
    f_oneway, chi2_contingency, normaltest, shapiro
)
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import warnings
warnings.filterwarnings('ignore')

# Import our analyzer
import sys

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from fda_device_hype_analysis import FDADeviceHypeAnalyzer

# Initialize Rich console
console = Console()

class AnalysisRunner:
    def __init__(self, output_dir=None, email=None, force_fetch=False, limit=None):
        """
        Initialize the analysis runner
        
        Args:
            output_dir (str): Directory to save results (defaults to output/)
            email (str): OpenAlex email for higher rate limits
            force_fetch (bool): Force fetch FDA data even if exists
            limit (int): Limit number of devices to analyze
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / 'output'
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.email = email
        self.force_fetch = force_fetch
        self.limit = limit
        self.analyzer = None
        self.results = None
        self.summary_df = None
        
    def check_fda_data(self):
        """Check if FDA data exists and is valid"""
        data_dir = Path(__file__).parent.parent / 'data'
        fda_files = [
            data_dir / "fda_pma_comprehensive.json",
            data_dir / "fda_pma_fixed.json",
            data_dir / "fda_pma_by_month.json"
        ]
        
        for file in fda_files:
            if Path(file).exists():
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    if data and len(data) > 0:
                        console.print(f"✅ [green]Found FDA data: {file} ({len(data)} devices)[/green]")
                        return file, len(data)
                except Exception as e:
                    console.print(f"⚠️ [yellow]Error reading {file}: {e}[/yellow]")
        
        return None, 0
    
    def fetch_fda_data_if_needed(self):
        """Fetch FDA data only if it doesn't exist or if forced"""
        existing_file, device_count = self.check_fda_data()
        
        if existing_file and not self.force_fetch:
            console.print(f"📊 [cyan]Using existing FDA data: {existing_file}[/cyan]")
            console.print(f"📈 [cyan]Device count: {device_count}[/cyan]")
            return True
        
        if self.force_fetch:
            console.print("🔄 [yellow]Force fetch requested - will fetch fresh FDA data[/yellow]")
        else:
            console.print("📡 [cyan]No FDA data found - fetching from FDA API...[/cyan]")
        
        # Import and run FDA fetcher
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from fetch_fda_pma_fixed import main as fetch_fda_main
            console.print("🚀 [bold]Starting FDA data fetch...[/bold]")
            fetch_fda_main()
            
            # Check if fetch was successful
            new_file, new_count = self.check_fda_data()
            if new_file and new_count > 0:
                console.print(f"✅ [green]Successfully fetched {new_count} FDA devices[/green]")
                return True
            else:
                console.print("⚠️ [yellow]FDA fetch completed but no data found[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Error fetching FDA data: {e}[/red]")
            console.print("📋 [cyan]Will use fallback sample data for analysis[/cyan]")
            return False
        
    def setup_analysis(self):
        """Initialize the analyzer and display setup information"""
        console.print("\n")
        
        # Welcome panel
        title = Text("🚀 FDA Device Hype Analysis Runner", style="bold blue")
        subtitle = Text("Comprehensive Analysis & Visualization Pipeline", style="italic cyan")
        
        welcome_panel = Panel(
            Align.center(title + "\n" + subtitle),
            border_style="blue",
            box=box.DOUBLE
        )
        console.print(welcome_panel)
        
        # Check and fetch FDA data
        console.print("\n🔍 [bold]Checking FDA Data Availability...[/bold]")
        fda_data_available = self.fetch_fda_data_if_needed()
        
        # Configuration table
        print("I'm here 1")
        config_table = Table(title="Analysis Configuration", box=box.ROUNDED)
        config_table.add_column("Setting", style="cyan", no_wrap=True)
        config_table.add_column("Value", style="white")
        config_table.add_column("Description", style="yellow")
        
        config_table.add_row("Output Directory", str(self.output_dir), "Results will be saved here")
        config_table.add_row("OpenAlex Email", self.email or "Not provided", "Rate limit: 10 req/s" if not self.email else "Rate limit: 100 req/s")
        config_table.add_row("Analysis Mode", "Comprehensive", "Full device analysis with visualizations")
        config_table.add_row("Data Source", "OpenAlex API", "Academic publications database")
        config_table.add_row("FDA Data", "✅ Available" if fda_data_available else "⚠️ Using fallback", "Real FDA data or sample data")
        
        console.print(config_table)
        
        # Initialize analyzer
        console.print("\n🔧 [bold]Initializing Analysis System...[/bold]")
        self.analyzer = FDADeviceHypeAnalyzer(openalex_email=self.email, verbose=False)
        console.print("✅ [green]Analysis system ready![/green]")
        
    def run_comprehensive_analysis(self):
        """Run the complete analysis pipeline"""
        console.print(f"\n{'='*70}")
        console.print(f"🔬 [bold blue]STARTING COMPREHENSIVE ANALYSIS[/bold blue]")
        console.print(f"{'='*70}")

        print("I'm here 333333")
        
        # Run analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Running analysis...", total=100)

            print("I'm here 2")

            
            # Step 1: Run device analysis
            progress.update(task, description="Analyzing FDA devices...", completed=10)
            print("I'm here 2.1")
            self.results = self.analyzer.run_comprehensive_analysis(limit=self.limit)
            print("I'm here 2.2")
            progress.update(task, completed=60)

            print("I'm here 3")
            
            # Step 2: Generate visualizations
            progress.update(task, description="Generating visualizations...", completed=70)
            self.summary_df = self.analyzer.visualize_results(self.results)
            progress.update(task, completed=90)

            print("I'm here 4")
            
            # Step 3: Generate report
            progress.update(task, description="Generating final report...", completed=95)
            report = self.analyzer.generate_report(self.results)
            progress.update(task, completed=100)
        
        console.print("✅ [bold green]Analysis completed successfully![/bold green]")
        return self.results, self.summary_df
    
    def generate_detailed_statistics(self):
        """Generate comprehensive statistics"""
        if self.summary_df is None:
            console.print("❌ [red]No analysis results available. Run analysis first.[/red]")
            return
        
        console.print(f"\n📊 [bold]GENERATING DETAILED STATISTICS[/bold]")
        
        # Basic statistics
        stats_table = Table(title="📈 Summary Statistics", box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan", no_wrap=True)
        stats_table.add_column("Value", style="white")
        stats_table.add_column("Description", style="yellow")
        
        total_devices = len(self.summary_df)
        avg_hype = self.summary_df['hype_score'].mean()
        median_hype = self.summary_df['hype_score'].median()
        max_hype = self.summary_df['hype_score'].max()
        min_hype = self.summary_df['hype_score'].min()
        std_hype = self.summary_df['hype_score'].std()
        
        stats_table.add_row("Total Devices", str(total_devices), "Number of devices analyzed")
        stats_table.add_row("Average Hype Score", f"{avg_hype:.3f}", "Mean hype score across all devices")
        stats_table.add_row("Median Hype Score", f"{median_hype:.3f}", "Middle value of hype scores")
        stats_table.add_row("Highest Hype Score", f"{max_hype:.3f}", "Maximum hype score achieved")
        stats_table.add_row("Lowest Hype Score", f"{min_hype:.3f}", "Minimum hype score achieved")
        stats_table.add_row("Standard Deviation", f"{std_hype:.3f}", "Variability in hype scores")
        
        console.print(stats_table)
        
        # Device type analysis
        device_type_stats = self.summary_df.groupby('device_type').agg({
            'hype_score': ['count', 'mean', 'std'],
            'total_publications': 'mean',
            'total_citations': 'mean',
            'num_bursts': 'mean'
        }).round(3)
        
        device_type_stats.columns = ['Count', 'Avg_Hype', 'Std_Hype', 'Avg_Pubs', 'Avg_Citations', 'Avg_Bursts']
        device_type_stats = device_type_stats.reset_index()
        
        device_table = Table(title="🏥 Device Type Analysis", box=box.ROUNDED)
        device_table.add_column("Device Type", style="cyan", no_wrap=True)
        device_table.add_column("Count", style="green")
        device_table.add_column("Avg Hype", style="yellow")
        device_table.add_column("Avg Pubs", style="magenta")
        device_table.add_column("Avg Citations", style="blue")
        
        for _, row in device_type_stats.iterrows():
            device_table.add_row(
                row['device_type'],
                str(row['Count']),
                f"{row['Avg_Hype']:.3f}",
                f"{row['Avg_Pubs']:.1f}",
                f"{row['Avg_Citations']:.1f}"
            )
        
        console.print(device_table)
        
        # Top performers
        top_devices = self.summary_df.nlargest(5, 'hype_score')
        
        top_table = Table(title="🏆 Top 5 Highest Hype Devices", box=box.ROUNDED)
        top_table.add_column("Rank", style="cyan")
        top_table.add_column("Device Name", style="white", no_wrap=True)
        top_table.add_column("Type", style="yellow")
        top_table.add_column("Hype Score", style="green")
        top_table.add_column("Publications", style="magenta")
        top_table.add_column("Citations", style="blue")
        
        for i, (_, device) in enumerate(top_devices.iterrows(), 1):
            top_table.add_row(
                f"#{i}",
                device['device_name'],
                device['device_type'],
                f"{device['hype_score']:.3f}",
                str(device['total_publications']),
                str(device['total_citations'])
            )
        
        console.print(top_table)
        
        return device_type_stats
    
    def perform_statistical_analysis(self):
        """Perform comprehensive statistical analysis"""
        if self.summary_df is None:
            console.print("❌ [red]No analysis results available. Run analysis first.[/red]")
            return
        
        console.print(f"\n🔬 [bold]PERFORMING STATISTICAL ANALYSIS[/bold]")
        
        # Clean data for statistical analysis
        df = self.summary_df.copy()
        numeric_cols = ['hype_score', 'total_publications', 'total_citations', 'avg_citations', 'num_bursts']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # 1. Correlation Analysis with Significance Tests
        console.print(f"\n📊 [bold cyan]1. CORRELATION ANALYSIS[/bold cyan]")
        self._correlation_analysis(df)
        
        # 2. Device Type Comparisons
        console.print(f"\n🏥 [bold cyan]2. DEVICE TYPE COMPARISONS[/bold cyan]")
        self._device_type_comparisons(df)
        
        # 3. Regression Analysis
        console.print(f"\n📈 [bold cyan]3. REGRESSION ANALYSIS[/bold cyan]")
        self._regression_analysis(df)
        
        # 4. Time Series Analysis (if approval_year available)
        if 'approval_year' in df.columns and df['approval_year'].notna().any():
            console.print(f"\n📅 [bold cyan]4. TEMPORAL TRENDS ANALYSIS[/bold cyan]")
            self._temporal_analysis(df)
        
        # 5. Distribution Tests
        console.print(f"\n📉 [bold cyan]5. DISTRIBUTION ANALYSIS[/bold cyan]")
        self._distribution_tests(df)
        
        # 6. Effect Sizes
        console.print(f"\n📏 [bold cyan]6. EFFECT SIZE ANALYSIS[/bold cyan]")
        self._effect_size_analysis(df)
        
        # Save statistical results
        self._save_statistical_results(df)
        
        console.print(f"\n✅ [bold green]Statistical analysis complete![/bold green]")
    
    def _correlation_analysis(self, df):
        """Perform correlation analysis with significance tests"""
        numeric_cols = ['hype_score', 'total_publications', 'total_citations', 'avg_citations', 'num_bursts']
        available_cols = [col for col in numeric_cols if col in df.columns]
        
        if len(available_cols) < 2:
            console.print("⚠️ [yellow]Insufficient data for correlation analysis[/yellow]")
            return
        
        corr_table = Table(title="Correlation Matrix with Significance", box=box.ROUNDED)
        corr_table.add_column("Variable 1", style="cyan")
        corr_table.add_column("Variable 2", style="cyan")
        corr_table.add_column("Pearson r", style="green")
        corr_table.add_column("p-value", style="yellow")
        corr_table.add_column("Significance", style="magenta")
        corr_table.add_column("Spearman ρ", style="blue")
        
        correlations = []
        for i, col1 in enumerate(available_cols):
            for col2 in available_cols[i+1:]:
                # Remove NaN values for this pair
                valid_data = df[[col1, col2]].dropna()
                if len(valid_data) < 3:
                    continue
                
                x = valid_data[col1].values
                y = valid_data[col2].values
                
                # Pearson correlation
                try:
                    pearson_r, pearson_p = pearsonr(x, y)
                    # Spearman correlation
                    spearman_rho, spearman_p = spearmanr(x, y)
                    
                    # Significance interpretation
                    if pearson_p < 0.001:
                        sig = "***"
                    elif pearson_p < 0.01:
                        sig = "**"
                    elif pearson_p < 0.05:
                        sig = "*"
                    else:
                        sig = "ns"
                    
                    corr_table.add_row(
                        col1.replace('_', ' ').title(),
                        col2.replace('_', ' ').title(),
                        f"{pearson_r:.3f}",
                        f"{pearson_p:.4f}",
                        sig,
                        f"{spearman_rho:.3f}"
                    )
                    
                    correlations.append({
                        'var1': col1,
                        'var2': col2,
                        'pearson_r': pearson_r,
                        'pearson_p': pearson_p,
                        'spearman_rho': spearman_rho,
                        'spearman_p': spearman_p
                    })
                except Exception as e:
                    continue
        
        console.print(corr_table)
        console.print("\n[dim]Significance: *** p<0.001, ** p<0.01, * p<0.05, ns = not significant[/dim]")
        
        return correlations
    
    def _device_type_comparisons(self, df):
        """Compare hype scores across device types"""
        if 'device_type' not in df.columns or 'hype_score' not in df.columns:
            console.print("⚠️ [yellow]Missing required columns for device type comparison[/yellow]")
            return
        
        device_types = df['device_type'].unique()
        if len(device_types) < 2:
            console.print("⚠️ [yellow]Need at least 2 device types for comparison[/yellow]")
            return
        
        # Group data by device type
        groups = [df[df['device_type'] == dt]['hype_score'].dropna().values 
                 for dt in device_types if len(df[df['device_type'] == dt]) > 0]
        group_labels = [dt for dt in device_types if len(df[df['device_type'] == dt]) > 0]
        
        if len(groups) < 2:
            console.print("⚠️ [yellow]Insufficient groups for comparison[/yellow]")
            return
        
        # Kruskal-Wallis test (non-parametric ANOVA)
        try:
            h_stat, p_value = kruskal(*groups)
            
            kw_table = Table(title="Kruskal-Wallis Test (Device Type Comparison)", box=box.ROUNDED)
            kw_table.add_column("Test", style="cyan")
            kw_table.add_column("H-statistic", style="green")
            kw_table.add_column("p-value", style="yellow")
            kw_table.add_column("Interpretation", style="magenta")
            
            interpretation = "Significant difference" if p_value < 0.05 else "No significant difference"
            kw_table.add_row(
                "Kruskal-Wallis",
                f"{h_stat:.3f}",
                f"{p_value:.4f}",
                interpretation
            )
            console.print(kw_table)
            
            # Pairwise comparisons (Mann-Whitney U)
            if len(groups) > 2 and p_value < 0.05:
                console.print("\n[bold]Pairwise Comparisons (Mann-Whitney U):[/bold]")
                pairwise_table = Table(box=box.ROUNDED)
                pairwise_table.add_column("Group 1", style="cyan")
                pairwise_table.add_column("Group 2", style="cyan")
                pairwise_table.add_column("U-statistic", style="green")
                pairwise_table.add_column("p-value", style="yellow")
                pairwise_table.add_column("Significant", style="magenta")
                
                for i in range(len(group_labels)):
                    for j in range(i+1, len(group_labels)):
                        try:
                            u_stat, p_val = mannwhitneyu(groups[i], groups[j], alternative='two-sided')
                            sig = "Yes" if p_val < 0.05 else "No"
                            pairwise_table.add_row(
                                group_labels[i],
                                group_labels[j],
                                f"{u_stat:.2f}",
                                f"{p_val:.4f}",
                                sig
                            )
                        except:
                            continue
                
                console.print(pairwise_table)
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Error in device type comparison: {e}[/yellow]")
    
    def _regression_analysis(self, df):
        """Perform regression analysis to predict hype scores"""
        if 'hype_score' not in df.columns:
            return
        
        # Prepare features
        feature_cols = ['total_publications', 'total_citations', 'avg_citations', 'num_bursts']
        available_features = [col for col in feature_cols if col in df.columns]
        
        if len(available_features) == 0:
            console.print("⚠️ [yellow]No features available for regression[/yellow]")
            return
        
        # Prepare data
        X = df[available_features].fillna(0).values
        y = df['hype_score'].fillna(0).values
        
        if len(X) < len(available_features) + 1:
            console.print("⚠️ [yellow]Insufficient data for regression[/yellow]")
            return
        
        try:
            # Fit linear regression
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)
            
            reg_table = Table(title="Multiple Linear Regression Results", box=box.ROUNDED)
            reg_table.add_column("Feature", style="cyan")
            reg_table.add_column("Coefficient", style="green")
            reg_table.add_column("Importance", style="yellow")
            
            for i, feature in enumerate(available_features):
                coef = model.coef_[i]
                importance = abs(coef) / sum(abs(model.coef_)) * 100
                reg_table.add_row(
                    feature.replace('_', ' ').title(),
                    f"{coef:.4f}",
                    f"{importance:.1f}%"
                )
            
            reg_table.add_row("Intercept", f"{model.intercept_:.4f}", "-")
            reg_table.add_row("R² Score", f"{r2:.4f}", "-")
            
            console.print(reg_table)
            
            # Interpretation
            if r2 > 0.7:
                interpretation = "Strong predictive power"
            elif r2 > 0.5:
                interpretation = "Moderate predictive power"
            elif r2 > 0.3:
                interpretation = "Weak predictive power"
            else:
                interpretation = "Very weak predictive power"
            
            console.print(f"\n[bold]Model Interpretation:[/bold] {interpretation} (R² = {r2:.3f})")
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Error in regression analysis: {e}[/yellow]")
    
    def _temporal_analysis(self, df):
        """Analyze temporal trends in hype scores"""
        if 'approval_year' not in df.columns or 'hype_score' not in df.columns:
            return
        
        # Group by year
        yearly_data = df.groupby('approval_year')['hype_score'].agg(['mean', 'std', 'count']).reset_index()
        yearly_data = yearly_data[yearly_data['count'] > 0].sort_values('approval_year')
        
        if len(yearly_data) < 3:
            console.print("⚠️ [yellow]Insufficient temporal data for analysis[/yellow]")
            return
        
        # Spearman correlation between year and hype score
        try:
            rho, p_value = spearmanr(yearly_data['approval_year'], yearly_data['mean'])
            
            temp_table = Table(title="Temporal Trend Analysis", box=box.ROUNDED)
            temp_table.add_column("Metric", style="cyan")
            temp_table.add_column("Value", style="green")
            temp_table.add_column("Interpretation", style="yellow")
            
            trend = "Increasing" if rho > 0 else "Decreasing" if rho < 0 else "No trend"
            significance = "Significant" if p_value < 0.05 else "Not significant"
            
            temp_table.add_row("Spearman ρ", f"{rho:.3f}", f"{trend} trend")
            temp_table.add_row("p-value", f"{p_value:.4f}", significance)
            temp_table.add_row("Years analyzed", f"{len(yearly_data)}", f"{yearly_data['approval_year'].min()}-{yearly_data['approval_year'].max()}")
            
            console.print(temp_table)
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Error in temporal analysis: {e}[/yellow]")
    
    def _distribution_tests(self, df):
        """Test distribution of hype scores"""
        if 'hype_score' not in df.columns:
            return
        
        hype_scores = df['hype_score'].dropna().values
        
        if len(hype_scores) < 3:
            console.print("⚠️ [yellow]Insufficient data for distribution tests[/yellow]")
            return
        
        dist_table = Table(title="Distribution Tests", box=box.ROUNDED)
        dist_table.add_column("Test", style="cyan")
        dist_table.add_column("Statistic", style="green")
        dist_table.add_column("p-value", style="yellow")
        dist_table.add_column("Interpretation", style="magenta")
        
        # Normality test (D'Agostino-Pearson)
        try:
            if len(hype_scores) >= 8:
                stat, p_val = normaltest(hype_scores)
                is_normal = "Normal" if p_val > 0.05 else "Not normal"
                dist_table.add_row("Normality (D'Agostino)", f"{stat:.3f}", f"{p_val:.4f}", is_normal)
        except:
            pass
        
        # Shapiro-Wilk (for smaller samples)
        try:
            if 3 <= len(hype_scores) <= 5000:
                stat, p_val = shapiro(hype_scores)
                is_normal = "Normal" if p_val > 0.05 else "Not normal"
                dist_table.add_row("Normality (Shapiro-Wilk)", f"{stat:.3f}", f"{p_val:.4f}", is_normal)
        except:
            pass
        
        # Skewness and Kurtosis
        from scipy.stats import skew, kurtosis
        skewness = skew(hype_scores)
        kurt = kurtosis(hype_scores)
        
        skew_interp = "Right-skewed" if skewness > 0.5 else "Left-skewed" if skewness < -0.5 else "Symmetric"
        kurt_interp = "Heavy-tailed" if kurt > 3 else "Light-tailed" if kurt < -1 else "Normal tails"
        
        dist_table.add_row("Skewness", f"{skewness:.3f}", "-", skew_interp)
        dist_table.add_row("Kurtosis", f"{kurt:.3f}", "-", kurt_interp)
        
        console.print(dist_table)
    
    def _effect_size_analysis(self, df):
        """Calculate effect sizes for device type comparisons"""
        if 'device_type' not in df.columns or 'hype_score' not in df.columns:
            return
        
        device_types = df['device_type'].unique()
        if len(device_types) < 2:
            return
        
        effect_table = Table(title="Effect Size Analysis (Cohen's d)", box=box.ROUNDED)
        effect_table.add_column("Group 1", style="cyan")
        effect_table.add_column("Group 2", style="cyan")
        effect_table.add_column("Cohen's d", style="green")
        effect_table.add_column("Effect Size", style="yellow")
        
        def cohens_d(group1, group2):
            """Calculate Cohen's d effect size"""
            n1, n2 = len(group1), len(group2)
            var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
            pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
            if pooled_std == 0:
                return 0
            return (np.mean(group1) - np.mean(group2)) / pooled_std
        
        for i in range(len(device_types)):
            for j in range(i+1, len(device_types)):
                group1 = df[df['device_type'] == device_types[i]]['hype_score'].dropna().values
                group2 = df[df['device_type'] == device_types[j]]['hype_score'].dropna().values
                
                if len(group1) > 0 and len(group2) > 0:
                    d = cohens_d(group1, group2)
                    
                    if abs(d) < 0.2:
                        effect = "Negligible"
                    elif abs(d) < 0.5:
                        effect = "Small"
                    elif abs(d) < 0.8:
                        effect = "Medium"
                    else:
                        effect = "Large"
                    
                    effect_table.add_row(
                        device_types[i],
                        device_types[j],
                        f"{d:.3f}",
                        effect
                    )
        
        if len(effect_table.rows) > 0:
            console.print(effect_table)
    
    def _save_statistical_results(self, df):
        """Save statistical results to file"""
        stats_file = self.output_dir / "statistical_analysis_results.txt"
        
        with open(stats_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("COMPREHENSIVE STATISTICAL ANALYSIS RESULTS\n")
            f.write("="*70 + "\n\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Devices: {len(df)}\n\n")
            
            # Summary statistics
            f.write("SUMMARY STATISTICS\n")
            f.write("-"*70 + "\n")
            numeric_cols = ['hype_score', 'total_publications', 'total_citations', 'avg_citations', 'num_bursts']
            for col in numeric_cols:
                if col in df.columns:
                    f.write(f"{col.replace('_', ' ').title()}:\n")
                    f.write(f"  Mean: {df[col].mean():.3f}\n")
                    f.write(f"  Median: {df[col].median():.3f}\n")
                    f.write(f"  Std Dev: {df[col].std():.3f}\n")
                    f.write(f"  Min: {df[col].min():.3f}\n")
                    f.write(f"  Max: {df[col].max():.3f}\n\n")
        
        console.print(f"📄 [green]Statistical results saved to: {stats_file}[/green]")
    
    def create_advanced_visualizations(self):
        """Create clean, informative advanced visualizations"""
        if self.summary_df is None:
            console.print("❌ [red]No analysis results available. Run analysis first.[/red]")
            return
        
        console.print(f"\n🎨 [bold]CREATING ADVANCED VISUALIZATIONS[/bold]")
        
        # Set clean style
        plt.style.use('default')
        sns.set_style("whitegrid")
        
        # Professional color palette
        colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'accent': '#F18F01',
            'highlight': '#C73E1D',
            'neutral': '#6C757D'
        }
        
        # Create figure with better layout
        fig = plt.figure(figsize=(20, 14))
        gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.35)
        
        # 1. Hype Score Distribution with Statistics - Top Left
        ax1 = fig.add_subplot(gs[0, 0])
        n, bins, patches = ax1.hist(self.summary_df['hype_score'], bins=20, color=colors['primary'], 
                                    alpha=0.7, edgecolor='white', linewidth=1.5)
        # Color bars by value
        for i, (bar, val) in enumerate(zip(patches, bins[:-1])):
            if val >= 0.6:
                bar.set_facecolor(colors['primary'])
            elif val >= 0.3:
                bar.set_facecolor(colors['secondary'])
            else:
                bar.set_facecolor(colors['accent'])
        
        mean_val = self.summary_df['hype_score'].mean()
        median_val = self.summary_df['hype_score'].median()
        ax1.axvline(mean_val, color=colors['highlight'], linestyle='--', linewidth=2.5, 
                   label=f'Mean: {mean_val:.3f}')
        ax1.axvline(median_val, color='black', linestyle='--', linewidth=2.5, 
                   label=f'Median: {median_val:.3f}')
        ax1.set_xlabel('Hype Score', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Number of Devices', fontsize=11, fontweight='bold')
        ax1.set_title('Hype Score Distribution', fontsize=13, fontweight='bold', pad=10)
        ax1.legend(fontsize=9, loc='upper right')
        ax1.grid(alpha=0.3, linestyle='--', axis='y')
        
        # 2. Device Type Comparison (Box Plot) - Top Middle
        ax2 = fig.add_subplot(gs[0, 1])
        device_types = self.summary_df['device_type'].unique()
        device_type_data = [self.summary_df[self.summary_df['device_type'] == dt]['hype_score'].values 
                           for dt in device_types if len(self.summary_df[self.summary_df['device_type'] == dt]) > 0]
        device_type_labels = [dt for dt in device_types if len(self.summary_df[self.summary_df['device_type'] == dt]) > 0]
        
        bp = ax2.boxplot(device_type_data, labels=device_type_labels, patch_artist=True,
                        showmeans=True, meanline=True)
        for patch in bp['boxes']:
            patch.set_facecolor(colors['primary'])
            patch.set_alpha(0.7)
        ax2.set_ylabel('Hype Score', fontsize=11, fontweight='bold')
        ax2.set_title('Hype Score by Device Type', fontsize=13, fontweight='bold', pad=10)
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(alpha=0.3, linestyle='--', axis='y')
        
        # 3. Correlation Heatmap - Top Right
        ax3 = fig.add_subplot(gs[0, 2])
        numeric_cols = ['hype_score', 'total_publications', 'total_citations', 'avg_citations', 'num_bursts']
        available_cols = [col for col in numeric_cols if col in self.summary_df.columns]
        if len(available_cols) > 1:
            correlation_matrix = self.summary_df[available_cols].corr()
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))  # Mask upper triangle
            sns.heatmap(correlation_matrix, mask=mask, annot=True, fmt='.2f', cmap='RdYlBu_r', 
                       center=0, square=True, linewidths=1.5, cbar_kws={"shrink": 0.8},
                       vmin=-1, vmax=1, ax=ax3)
            ax3.set_title('Metric Correlations', fontsize=13, fontweight='bold', pad=10)
        else:
            ax3.text(0.5, 0.5, 'Insufficient data for correlation', ha='center', va='center', 
                    transform=ax3.transAxes)
            ax3.set_title('Metric Correlations', fontsize=13, fontweight='bold')
        
        # 4. Publications vs Citations by Device Type - Middle Left (spans 2 columns)
        ax4 = fig.add_subplot(gs[1, :2])
        device_types = self.summary_df['device_type'].unique()
        type_colors = plt.cm.tab10(np.linspace(0, 1, len(device_types)))
        
        for i, device_type in enumerate(device_types):
            subset = self.summary_df[self.summary_df['device_type'] == device_type]
            if len(subset) > 0:
                ax4.scatter(subset['total_publications'], subset['total_citations'], 
                           c=[type_colors[i]], label=f'{device_type} (n={len(subset)})', 
                           s=150, alpha=0.6, edgecolors='white', linewidths=1.5)
        
        ax4.set_xlabel('Total Publications', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Total Citations', fontsize=12, fontweight='bold')
        ax4.set_title('Research Impact by Device Type', fontsize=13, fontweight='bold', pad=10)
        ax4.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9, framealpha=0.9)
        ax4.grid(alpha=0.3, linestyle='--')
        # Add trend line
        if len(self.summary_df) > 1:
            z = np.polyfit(self.summary_df['total_publications'], 
                          self.summary_df['total_citations'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(self.summary_df['total_publications'].min(), 
                               self.summary_df['total_publications'].max(), 100)
            ax4.plot(x_line, p(x_line), "k--", alpha=0.5, linewidth=2, label='Overall Trend')
        
        # 5. Hype Score Over Time (if approval_year available) - Middle Right
        ax5 = fig.add_subplot(gs[1, 2])
        if 'approval_year' in self.summary_df.columns and self.summary_df['approval_year'].notna().any():
            yearly_stats = self.summary_df.groupby('approval_year').agg({
                'hype_score': ['mean', 'std', 'count']
            }).reset_index()
            yearly_stats.columns = ['year', 'mean_hype', 'std_hype', 'count']
            yearly_stats = yearly_stats[yearly_stats['count'] > 0].sort_values('year')
            
            if len(yearly_stats) > 0:
                ax5.fill_between(yearly_stats['year'], 
                                yearly_stats['mean_hype'] - yearly_stats['std_hype'],
                                yearly_stats['mean_hype'] + yearly_stats['std_hype'],
                                alpha=0.2, color=colors['primary'], label='±1 Std Dev')
                ax5.plot(yearly_stats['year'], yearly_stats['mean_hype'], 
                        'o-', color=colors['primary'], linewidth=2.5, markersize=8, 
                        label='Mean Hype Score', alpha=0.9)
                ax5.set_xlabel('Approval Year', fontsize=11, fontweight='bold')
                ax5.set_ylabel('Average Hype Score', fontsize=11, fontweight='bold')
                ax5.set_title('Hype Trends Over Time', fontsize=13, fontweight='bold', pad=10)
                ax5.legend(fontsize=9)
                ax5.grid(alpha=0.3, linestyle='--')
            else:
                ax5.text(0.5, 0.5, 'No time series data', ha='center', va='center', 
                        transform=ax5.transAxes)
                ax5.set_title('Hype Trends Over Time', fontsize=13, fontweight='bold')
        else:
            ax5.text(0.5, 0.5, 'No approval year data', ha='center', va='center', 
                    transform=ax5.transAxes)
            ax5.set_title('Hype Trends Over Time', fontsize=13, fontweight='bold')
        
        # 6. Sustained Interest Analysis - Bottom Left
        ax6 = fig.add_subplot(gs[2, 0])
        if 'sustained_interest' in self.summary_df.columns:
            sustained_counts = self.summary_df["sustained_interest"].value_counts()
            if len(sustained_counts) > 0:
                labels = ['Sustained Interest' if val else 'No Sustained Interest' 
                         for val in sustained_counts.index]
                colors_pie = [colors['primary'], colors['neutral']]
                wedges, texts, autotexts = ax6.pie(sustained_counts.values, labels=labels, 
                                                   autopct='%1.1f%%', colors=colors_pie[:len(sustained_counts)],
                                                   startangle=90, textprops={'fontsize': 10, 'fontweight': 'bold'})
                ax6.set_title('Sustained Research Interest', fontsize=13, fontweight='bold', pad=10)
            else:
                ax6.text(0.5, 0.5, 'No sustained interest data', ha='center', va='center', 
                        transform=ax6.transAxes)
                ax6.set_title('Sustained Interest', fontsize=13, fontweight='bold')
        else:
            ax6.text(0.5, 0.5, 'No sustained interest data', ha='center', va='center', 
                    transform=ax6.transAxes)
            ax6.set_title('Sustained Interest', fontsize=13, fontweight='bold')
        
        # 7. Top Performers by Multiple Metrics - Bottom Middle (spans 2 columns)
        ax7 = fig.add_subplot(gs[2, 1:])
        # Create composite score for ranking
        df_normalized = self.summary_df.copy()
        
        # Clean data: replace inf and NaN values
        for col in ['hype_score', 'total_publications', 'total_citations', 'avg_citations']:
            if col in df_normalized.columns:
                df_normalized[col] = df_normalized[col].replace([np.inf, -np.inf], np.nan).fillna(0)
        
        for col in ['hype_score', 'total_publications', 'total_citations', 'avg_citations']:
            if col in df_normalized.columns:
                max_val = df_normalized[col].max()
                if max_val > 0 and not np.isnan(max_val) and not np.isinf(max_val):
                    df_normalized[f'{col}_norm'] = df_normalized[col] / max_val
                else:
                    df_normalized[f'{col}_norm'] = 0
        
        # Composite score
        if all(col in df_normalized.columns for col in ['hype_score_norm', 'total_publications_norm', 
                                                         'total_citations_norm', 'avg_citations_norm']):
            df_normalized['composite_score'] = (
                df_normalized['hype_score_norm'].fillna(0) * 0.4 +
                df_normalized['total_publications_norm'].fillna(0) * 0.2 +
                df_normalized['total_citations_norm'].fillna(0) * 0.2 +
                df_normalized['avg_citations_norm'].fillna(0) * 0.2
            )
            # Clean composite score
            df_normalized['composite_score'] = df_normalized['composite_score'].replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # Filter out rows with invalid composite scores
            valid_df = df_normalized[df_normalized['composite_score'].notna() & (df_normalized['composite_score'] >= 0)]
            if len(valid_df) > 0:
                top_performers = valid_df.nlargest(min(12, len(valid_df)), 'composite_score')
                
                y_pos = np.arange(len(top_performers))
                # Ensure hype_score is valid for color selection
                hype_scores = top_performers['hype_score'].fillna(0).replace([np.inf, -np.inf], 0)
                bar_colors = [colors['primary'] if x >= 0.6 else colors['secondary'] 
                             for x in hype_scores]
                bars = ax7.barh(y_pos, top_performers['composite_score'], 
                              color=bar_colors,
                              alpha=0.8, edgecolor='white', linewidth=1.5)
                ax7.set_yticks(y_pos)
                ax7.set_yticklabels([str(name)[:35] + '...' if len(str(name)) > 35 else str(name) 
                                   for name in top_performers['device_name']], fontsize=9)
                ax7.set_xlabel('Composite Performance Score', fontsize=11, fontweight='bold')
                ax7.set_title('Top Performers: Composite Score (Hype + Publications + Citations)', 
                             fontsize=12, fontweight='bold', pad=10)
                ax7.grid(axis='x', alpha=0.3, linestyle='--')
                # Add hype score labels - with error handling
                for i, (idx, row) in enumerate(top_performers.iterrows()):
                    try:
                        comp_score = float(row['composite_score']) if pd.notna(row['composite_score']) else 0.0
                        hype_score = float(row['hype_score']) if pd.notna(row['hype_score']) else 0.0
                        if not (np.isnan(comp_score) or np.isinf(comp_score)):
                            ax7.text(comp_score + 0.01, i, 
                                    f"Hype: {hype_score:.2f}", va='center', fontsize=8)
                    except (ValueError, TypeError, KeyError):
                        continue
            else:
                # Fallback if no valid composite scores
                top_performers = self.summary_df.nlargest(min(12, len(self.summary_df)), 'hype_score')
                y_pos = np.arange(len(top_performers))
                bars = ax7.barh(y_pos, top_performers['hype_score'].fillna(0), 
                              color=colors['primary'], alpha=0.8, edgecolor='white', linewidth=1.5)
                ax7.set_yticks(y_pos)
                ax7.set_yticklabels([str(name)[:35] + '...' if len(str(name)) > 35 else str(name) 
                                   for name in top_performers['device_name']], fontsize=9)
                ax7.set_xlabel('Hype Score', fontsize=11, fontweight='bold')
                ax7.set_title('Top Performers by Hype Score', fontsize=12, fontweight='bold', pad=10)
                ax7.grid(axis='x', alpha=0.3, linestyle='--')
        else:
            # Fallback: just show top by hype score
            top_performers = self.summary_df.nlargest(min(12, len(self.summary_df)), 'hype_score')
            y_pos = np.arange(len(top_performers))
            # Clean hype scores
            clean_hype = top_performers['hype_score'].replace([np.inf, -np.inf], np.nan).fillna(0)
            bars = ax7.barh(y_pos, clean_hype, 
                          color=colors['primary'], alpha=0.8, edgecolor='white', linewidth=1.5)
            ax7.set_yticks(y_pos)
            ax7.set_yticklabels([str(name)[:35] + '...' if len(str(name)) > 35 else str(name) 
                               for name in top_performers['device_name']], fontsize=9)
            ax7.set_xlabel('Hype Score', fontsize=11, fontweight='bold')
            ax7.set_title('Top Performers by Hype Score', fontsize=12, fontweight='bold', pad=10)
            ax7.grid(axis='x', alpha=0.3, linestyle='--')
        
        # Main title
        fig.suptitle('Advanced FDA Device Hype Analysis (2000-2025)', fontsize=16, fontweight='bold', y=0.995)
        
        plt.tight_layout(rect=[0, 0, 1, 0.98])
        
        # Save advanced visualizations
        advanced_viz_file = self.output_dir / "advanced_visualizations.png"
        plt.savefig(advanced_viz_file, dpi=300, bbox_inches='tight', facecolor='white')
        console.print(f"📊 [green]Advanced visualizations saved to: {str(advanced_viz_file)}[/green]")
        
        plt.close()  # Close to avoid showing plot
    
    def save_results(self):
        """Save all results to files"""
        if self.summary_df is None:
            console.print("❌ [red]No analysis results available. Run analysis first.[/red]")
            return
        
        console.print(f"\n💾 [bold]SAVING RESULTS[/bold]")
        
        # Save summary data
        summary_file = self.output_dir / "fda_device_hype_summary.csv"
        self.summary_df.to_csv(summary_file, index=False)
        console.print(f"📄 [green]Summary data saved to: {summary_file}[/green]")
        
        # Save detailed results
        detailed_results = []
        for result in self.results:
            detailed_results.append({
                'device_name': result['device_name'],
                'device_type': result.get('device_type', 'Other'),
                'total_publications': result['total_publications'],
                'total_citations': result.get('total_citations', 0),
                'avg_citations': result.get('avg_citations', 0.0),
                'hype_score': result['hype_score'],
                'peak_year': result.get('peak_year'),
                'sustained_interest': result.get('sustained_interest', False),
                'num_bursts': result.get('num_bursts', len(result.get('burst_periods', []))),
                'burst_periods': str(result.get('burst_periods', []))  # Convert to string for CSV
            })
        
        detailed_file = self.output_dir / "detailed_analysis_results.csv"
        pd.DataFrame(detailed_results).to_csv(detailed_file, index=False)
        console.print(f"📋 [green]Detailed results saved to: {detailed_file}[/green]")
        
        # Save statistics
        stats_file = self.output_dir / "analysis_statistics.txt"
        with open(stats_file, 'w') as f:
            f.write("FDA Device Hype Analysis - Statistics Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Devices Analyzed: {len(self.summary_df)}\n")
            f.write(f"Average Hype Score: {self.summary_df['hype_score'].mean():.3f}\n")
            f.write(f"Median Hype Score: {self.summary_df['hype_score'].median():.3f}\n")
            f.write(f"Highest Hype Score: {self.summary_df['hype_score'].max():.3f}\n")
            f.write(f"Lowest Hype Score: {self.summary_df['hype_score'].min():.3f}\n")
            f.write(f"Standard Deviation: {self.summary_df['hype_score'].std():.3f}\n\n")
            
            f.write("Device Type Analysis:\n")
            f.write("-" * 20 + "\n")
            device_type_stats = self.summary_df.groupby('device_type')['hype_score'].agg(['count', 'mean', 'std'])
            f.write(device_type_stats.to_string())
        
        console.print(f"📊 [green]Statistics saved to: {stats_file}[/green]")
        
        # Move main visualization if it exists
        main_viz_file = Path(__file__).parent.parent / "fda_device_hype_analysis.png"
        if main_viz_file.exists():
            new_main_viz = self.output_dir / "main_visualizations.png"
            main_viz_file.rename(new_main_viz)
            console.print(f"📈 [green]Main visualizations moved to: {new_main_viz}[/green]")
    
    def run_complete_pipeline(self):
        """Run the complete analysis pipeline"""
        try:
            # Setup
            self.setup_analysis()
            
            # Run analysis
            self.run_comprehensive_analysis()
            
            # Generate statistics
            self.generate_detailed_statistics()
            
            # Perform comprehensive statistical analysis
            self.perform_statistical_analysis()
            
            # Create advanced visualizations
            self.create_advanced_visualizations()
            
            # Save results
            self.save_results()
            
            # Final summary
            console.print(f"\n{'='*70}")
            console.print(f"🎉 [bold green]COMPLETE ANALYSIS PIPELINE FINISHED![/bold green]")
            console.print(f"{'='*70}")
            console.print(f"📁 Results saved in: {self.output_dir}")
            console.print(f"📊 Devices analyzed: {len(self.results)}")
            console.print(f"📈 Visualizations created: 2 files")
            console.print(f"📋 Reports generated: 3 files")
            console.print(f"⏱️ Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            import traceback
            error_msg = str(e) if e else "Unknown error"
            console.print(f"❌ [red]Error in analysis pipeline: {error_msg}[/red]")
            if self.verbose:
                console.print(f"[red]Traceback:[/red]")
                console.print(traceback.format_exc())
            raise


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="FDA Device Hype Analysis Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis.py                           # Run with default settings
  python run_analysis.py --output results          # Save to custom directory
  python run_analysis.py --email your@email.com    # Use email for higher rate limits
  python run_analysis.py --force-fetch             # Force refresh FDA data
  python run_analysis.py --quiet                   # Minimal output
        """
    )
    
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output directory for results (default: output/)'
    )
    
    parser.add_argument(
        '--email', '-e',
        help='OpenAlex email for higher rate limits'
    )
    
    parser.add_argument(
        '--force-fetch', '-f',
        action='store_true',
        help='Force fetch fresh FDA data (ignores existing data)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output mode'
    )

    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=20,
        help='Limit number of devices to analyze (default: 20)'
    )
    
    args = parser.parse_args()
    
    # Set console level based on quiet mode
    if args.quiet:
        console.print = lambda *args, **kwargs: None
    
    try:
        # Create and run analysis
        runner = AnalysisRunner(
            output_dir=args.output,
            email=args.email,
            force_fetch=args.force_fetch,
            limit=args.limit
        )
        runner.run_complete_pipeline()
        
    except KeyboardInterrupt:
        console.print("\n⚠️ [yellow]Analysis interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        import traceback
        error_msg = str(e) if e else "Unknown error"
        console.print(f"\n❌ [red]Analysis failed: {error_msg}[/red]")
        console.print(f"[red]Full traceback:[/red]")
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 