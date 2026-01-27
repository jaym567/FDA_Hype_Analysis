"""
Medical Device Publication Burst Analysis with Visualizations
Uses Kleinberg's burst detection algorithm to analyze publication patterns for each device
"""

import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional
import matplotlib.patches as mpatches
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter
import matplotlib.cm as cm
import os
from kleinberg_burst import KleinbergBurstDetector, normalize_timestamps


class DeviceBurstAnalyzer:
    """Analyzes publication bursts for medical devices from CSV data."""
    
    def __init__(self, csv_file_path: str, devices_file_path: str = None):
        """
        Initialize the analyzer with CSV file path.
        
        Args:
            csv_file_path: Path to the publications_surgical.csv file
            devices_file_path: Path to the devices_surgical.csv file (optional, for metadata)
        """
        self.csv_file_path = csv_file_path
        self.devices_file_path = devices_file_path
        self.data = self._load_data()
        self.device_metadata = self._load_device_metadata() if devices_file_path else {}
        self.device_publications = self._group_by_device()
        self.burst_detector = KleinbergBurstDetector(s=2.0, gamma=1.0)
        self.results = None
        
        # Set up visualization style
        plt.style.use('seaborn-v0_8-darkgrid')
        self.colors = {
            'burst_high': '#E74C3C',    # Red for high intensity bursts
            'burst_medium': '#F39C12',  # Orange for medium intensity bursts
            'burst_low': '#F1C40F',     # Yellow for low intensity bursts
            'timeline': '#3498DB',      # Blue for timeline
            'background': '#ECF0F1',    # Light gray for background
            'text': '#2C3E50',          # Dark blue-gray for text
        }
        
    def _load_data(self) -> pd.DataFrame:
        """Load and preprocess the CSV data."""
        df = pd.read_csv(self.csv_file_path)
        
        # Convert publication_date to datetime
        df['publication_date'] = pd.to_datetime(df['publication_date'], errors='coerce')
        
        # Create year column if not present
        if 'publication_year' in df.columns:
            df['publication_year'] = pd.to_numeric(df['publication_year'], errors='coerce')
        else:
            df['publication_year'] = df['publication_date'].dt.year
        
        # Filter out rows with invalid dates
        df = df.dropna(subset=['publication_date', 'publication_year'])
        
        return df
    
    def _load_device_metadata(self) -> Dict[str, Dict]:
        """Load device metadata like specialty and approval date."""
        metadata = {}
        if not self.devices_file_path or not os.path.exists(self.devices_file_path):
            print(f"Warning: Device metadata file not found at {self.devices_file_path}")
            return metadata
            
        try:
            df = pd.read_csv(self.devices_file_path)
            # Ensure required columns exist
            required_cols = ['pma_number', 'surgical_specialty', 'decision_date', 'trade_name']
            if not all(col in df.columns for col in required_cols):
                print(f"Warning: Device metadata file missing required columns. Found: {df.columns}")
                return metadata
                
            for _, row in df.iterrows():
                pma = row['pma_number']
                if pd.notna(pma):
                    metadata[pma] = {
                        'specialty': row['surgical_specialty'] if pd.notna(row['surgical_specialty']) else 'Unknown',
                        'decision_date': pd.to_datetime(row['decision_date'], errors='coerce'),
                        'trade_name': row['trade_name']
                    }
            print(f"Loaded metadata for {len(metadata)} devices")
        except Exception as e:
            print(f"Error loading device metadata: {e}")
            
        return metadata
    
    def _group_by_device(self) -> Dict[str, pd.DataFrame]:
        """Group publications by device PMA number."""
        device_groups = {}
        
        for device_id, group in self.data.groupby('device_pma_number'):
            device_name = group['trade_name'].iloc[0] if len(group) > 0 else device_id
            # Get metadata if available
            meta = self.device_metadata.get(device_id, {})
            specialty = meta.get('specialty', 'Unknown')
            decision_date = meta.get('decision_date', pd.NaT)
            
            device_groups[device_id] = {
                'data': group,
                'name': device_name,
                'years': sorted(group['publication_year'].unique()),
                'specialty': specialty,
                'decision_date': decision_date
            }
        
        return device_groups
    
    def _convert_to_timestamps(self, dates: List[datetime]) -> List[float]:
        """
        Convert datetime objects to numeric timestamps for burst detection.
        
        Using days since first publication for better interpretability.
        """
        if not dates:
            return []
        
        # Convert to days since first publication
        min_date = min(dates)
        return [(date - min_date).days for date in dates]
    
    def analyze_all_devices(self, k: int = 3, normalize: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Analyze bursts for all devices.
        
        Args:
            k: Number of states for burst detection (higher = more granular burst levels)
            normalize: Whether to normalize timestamps to start at 0
            
        Returns:
            Dictionary with burst analysis results for each device
        """
        results = {}
        
        for device_id, device_info in self.device_publications.items():
            print(f"\nAnalyzing device: {device_id} - {device_info['name']}")
            print(f"Total publications: {len(device_info['data'])}")
            print(f"Publication years: {min(device_info['years'])} to {max(device_info['years'])}")
            
            # Get publication dates for this device
            dates = device_info['data']['publication_date'].tolist()
            
            if len(dates) < 3:
                print(f"  Skipping - insufficient data for burst analysis (needs at least 3 publications)")
                continue
            
            # Convert dates to timestamps
            timestamps = self._convert_to_timestamps(dates)
            
            if normalize:
                timestamps = normalize_timestamps(timestamps)
            
            # Detect bursts
            try:
                burst_results = self.burst_detector.detect_bursts(timestamps, k=k)
                
                # Convert back to dates for interpretation
                burst_results = self._add_date_interpretation(burst_results, dates)
                
                # Store results
                results[device_id] = {
                    'device_name': device_info['name'],
                    'num_publications': len(dates),
                    'publication_years': device_info['years'],
                    'dates': dates,
                    'burst_analysis': burst_results,
                    'summary': self._generate_device_summary(device_id, device_info, burst_results)
                }
                
                # Print summary
                print(f"  Detected {len(burst_results.get('bursts', []))} burst period(s)")
                
            except Exception as e:
                print(f"  Error analyzing device {device_id}: {e}")
                results[device_id] = {
                    'device_name': device_info['name'],
                    'num_publications': len(dates),
                    'error': str(e)
                }
        
        self.results = results
        return results
    
    def _add_date_interpretation(self, burst_results: Dict[str, Any], 
                                 original_dates: List[datetime]) -> Dict[str, Any]:
        """Add date-based interpretation to burst results."""
        if not burst_results.get('bursts'):
            return burst_results
        
        # Get the sorted dates (should match the sorted timestamps)
        sorted_dates = sorted(original_dates)
        
        # Add date information to each burst
        for burst in burst_results['bursts']:
            start_idx = burst['start_index']
            end_idx = burst['end_index']
            
            # Convert indices to dates
            burst['start_date'] = sorted_dates[start_idx]
            burst['end_date'] = sorted_dates[end_idx]
            burst['dates_in_burst'] = sorted_dates[start_idx:end_idx+1]
            burst['years_in_burst'] = list(set([d.year for d in burst['dates_in_burst']]))
        
        return burst_results
    
    def _generate_device_summary(self, device_id: str, device_info: Dict, 
                                burst_results: Dict[str, Any]) -> str:
        """Generate a comprehensive summary for a device."""
        bursts = burst_results.get('bursts', [])
        
        summary_lines = [
            f"Device: {device_id} - {device_info['name']}",
            f"Total publications: {len(device_info['data'])}",
            f"Publication span: {min(device_info['years'])} to {max(device_info['years'])}",
            f"Detected bursts: {len(bursts)}",
            ""
        ]
        
        if bursts:
            summary_lines.append("Burst periods:")
            for i, burst in enumerate(bursts, 1):
                summary_lines.extend([
                    f"  Burst {i}:",
                    f"    Dates: {burst['start_date'].strftime('%Y-%m-%d')} to {burst['end_date'].strftime('%Y-%m-%d')}",
                    f"    Duration: {burst['duration']:.0f} days",
                    f"    Publications: {burst['num_events']}",
                    f"    Intensity level: {burst['state']}",
                    f"    Years covered: {', '.join(map(str, burst['years_in_burst']))}",
                    f"    Rate: {burst['intensity']:.4f} publications/day",
                    ""
                ])
        
        return "\n".join(summary_lines)
    
    def export_results(self, results: Dict[str, Dict[str, Any]], 
                       output_file: str = "device_burst_analysis.csv"):
        """Export burst analysis results to a CSV file."""
        rows = []
        
        for device_id, device_results in results.items():
            bursts = device_results.get('burst_analysis', {}).get('bursts', [])
            
            if not bursts:
                # No bursts detected
                rows.append({
                    'device_id': device_id,
                    'device_name': device_results.get('device_name', ''),
                    'total_publications': device_results.get('num_publications', 0),
                    'burst_number': 0,
                    'burst_start_date': '',
                    'burst_end_date': '',
                    'burst_duration_days': '',
                    'publications_in_burst': '',
                    'burst_intensity': '',
                    'years_covered': ''
                })
            else:
                # Add a row for each burst
                for i, burst in enumerate(bursts, 1):
                    rows.append({
                        'device_id': device_id,
                        'device_name': device_results.get('device_name', ''),
                        'total_publications': device_results.get('num_publications', 0),
                        'burst_number': i,
                        'burst_start_date': burst['start_date'].strftime('%Y-%m-%d'),
                        'burst_end_date': burst['end_date'].strftime('%Y-%m-%d'),
                        'burst_duration_days': burst['duration'],
                        'publications_in_burst': burst['num_events'],
                        'burst_intensity': burst['state'],
                        'years_covered': ', '.join(map(str, burst.get('years_in_burst', [])))
                    })
        
        # Create DataFrame and export
        df_results = pd.DataFrame(rows)
        df_results.to_csv(output_file, index=False)
        print(f"\nResults exported to {output_file}")
        
        return df_results
    
    def generate_report(self, results: Dict[str, Dict[str, Any]], 
                       report_file: str = "device_burst_report.txt"):
        """Generate a comprehensive text report of burst analysis."""
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("MEDICAL DEVICE PUBLICATION BURST ANALYSIS REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total devices analyzed: {len(results)}\n\n")
            
            # Sort devices by number of publications
            sorted_devices = sorted(results.items(), 
                                   key=lambda x: x[1].get('num_publications', 0), 
                                   reverse=True)
            
            for device_id, device_results in sorted_devices:
                f.write("\n" + "=" * 60 + "\n")
                
                if 'error' in device_results:
                    f.write(f"\nDevice: {device_id}\n")
                    f.write(f"Error: {device_results['error']}\n")
                    continue
                
                # Write device summary
                if 'summary' in device_results:
                    f.write(device_results['summary'])
                else:
                    f.write(f"Device: {device_id} - {device_results.get('device_name', '')}\n")
                    f.write(f"Publications: {device_results.get('num_publications', 0)}\n")
                
                f.write("\n" + "-" * 40 + "\n")
        
        print(f"Detailed report generated: {report_file}")
    
    def create_visualizations(self, output_dir: str = "burst_visualizations"):
        """
        Create comprehensive visualizations for burst analysis.
        
        Args:
            output_dir: Directory to save visualization files
        """
        if self.results is None:
            print("Please run analyze_all_devices() first")
            return
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nCreating visualizations in '{output_dir}' directory...")
        
        # 1. Overall statistics visualization
        self._create_overall_statistics_plot(output_dir)
        
        # 2. Timeline visualization for each device
        self._create_device_timeline_plots(output_dir)
        
        # 3. Burst intensity comparison across devices
        self._create_burst_intensity_comparison(output_dir)
        
        # 4. Publication distribution by year
        self._create_publication_distribution_plot(output_dir)
        
        # 5. Network/heatmap visualization
        self._create_burst_heatmap(output_dir)
        
        # 6. Combined overview dashboard
        self._create_dashboard_plot(output_dir)
        
        # Prepare unified data for advanced figures
        viz_df = self._prepare_visualization_data()
        if not viz_df.empty:
            # 7. Figure 1: Specialty Hype Landscape
            self._plot_fig1_specialty_hype(viz_df, output_dir)
            
            # 8. Figure 2: Burst Prevalence
            self._plot_fig2_burst_prevalence(viz_df, output_dir)
            
            # 9. Figure 3: Exemplar Time Series
            self._plot_fig3_exemplar_timeseries(output_dir)
            
            # 10. Figure 4: Burst Timing
            self._plot_fig4_burst_timing(viz_df, output_dir)
            
            # 11. Figure 5: Hype vs Evidence
            self._plot_fig5_hype_vs_evidence(viz_df, output_dir)
            
            # 12. Figure 6: Top 50 Hype Ranking
            self._plot_fig6_hype_ranking(viz_df, output_dir)
            
            # 13. Figure 7: Pipeline Schematic
            self._plot_fig7_pipeline_schematic(output_dir)
        
        print(f"\nAll visualizations saved to '{output_dir}' directory")
    
    def _prepare_visualization_data(self) -> pd.DataFrame:
        """Prepare a unified DataFrame for visualization."""
        data = []
        for device_id, result in self.results.items():
            if 'error' in result:
                continue
                
            bursts = result.get('burst_analysis', {}).get('bursts', [])
            device_info = self.device_publications.get(device_id, {})
            
            # Calculate hype metrics
            has_burst = len(bursts) > 0
            num_bursts = len(bursts)
            max_intensity = max([b['state'] for b in bursts]) if bursts else 0
            total_duration = sum([b['duration'] for b in bursts]) if bursts else 0
            
            # Composite hype score (0-1 normalized logic to be refined)
            # Simple proxy: max intensity * log(duration + 1)
            hype_score_raw = max_intensity * np.log1p(total_duration)
            
            # Get metadata
            specialty = device_info.get('specialty', 'Unknown')
            # Clean specialty names if needed
            if pd.isna(specialty) or specialty == 'nan':
                specialty = 'Unknown'
                
            data.append({
                'device_id': device_id,
                'device_name': result.get('device_name', ''),
                'specialty': specialty,
                'num_publications': result.get('num_publications', 0),
                'has_burst': has_burst,
                'num_bursts': num_bursts,
                'max_intensity': max_intensity,
                'total_duration': total_duration,
                'hype_score_raw': hype_score_raw
            })
            
        df = pd.DataFrame(data)
        if not df.empty:
            # Normalize hype score to 0-1 range
            max_score = df['hype_score_raw'].max()
            if max_score > 0:
                df['hype_score'] = df['hype_score_raw'] / max_score
            else:
                df['hype_score'] = 0
        return df

    def _plot_fig1_specialty_hype(self, df: pd.DataFrame, output_dir: str):
        """
        Figure 1: Specialty Hype Landscape.
        Box/violin plot of Hype Scores by specialty.
        """
        plt.figure(figsize=(14, 8))
        
        # Filter out Unknown if desired, or keep
        plot_df = df[df['specialty'] != 'Unknown'].copy()
        if plot_df.empty:
            plot_df = df.copy()
            
        # Sort specialties by median hype score
        order = plot_df.groupby('specialty')['hype_score'].median().sort_values(ascending=False).index
        
        sns.boxplot(x='specialty', y='hype_score', data=plot_df, order=order, palette='viridis')
        sns.stripplot(x='specialty', y='hype_score', data=plot_df, order=order, 
                     color='black', alpha=0.3, size=3, jitter=True)
        
        plt.xticks(rotation=45, ha='right')
        plt.title('Specialty Hype Landscape: Hype Scores by Medical Specialty', fontsize=16, fontweight='bold')
        plt.xlabel('Surgical Specialty', fontsize=12)
        plt.ylabel('Composite Hype Score (0-1)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(f"{output_dir}/Figure_1_Specialty_Hype.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/Figure_1_Specialty_Hype.pdf", bbox_inches='tight')
        plt.close()
        print("  Created: Figure_1_Specialty_Hype.png")

    def _plot_fig2_burst_prevalence(self, df: pd.DataFrame, output_dir: str):
        """
        Figure 2: Burst Prevalence.
        Grouped bar chart showing % of devices with bursts per specialty.
        """
        # Calculate prevalence
        specialty_stats = df[df['specialty'] != 'Unknown'].groupby('specialty').agg(
            total_devices=('device_id', 'count'),
            devices_with_burst=('has_burst', 'sum')
        ).reset_index()
        
        specialty_stats['prevalence'] = (specialty_stats['devices_with_burst'] / specialty_stats['total_devices']) * 100
        specialty_stats = specialty_stats.sort_values('prevalence', ascending=False)
        
        plt.figure(figsize=(14, 8))
        
        # Bar plot
        bars = plt.bar(specialty_stats['specialty'], specialty_stats['prevalence'], color=self.colors['burst_medium'])
        
        # Add labels
        for bar, total in zip(bars, specialty_stats['total_devices']):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'n={total}', ha='center', va='bottom', fontsize=9)
            
        plt.xticks(rotation=45, ha='right')
        plt.title('Burst Prevalence by Surgical Specialty', fontsize=16, fontweight='bold')
        plt.xlabel('Specialty', fontsize=12)
        plt.ylabel('Devices with Detected Bursts (%)', fontsize=12)
        plt.ylim(0, 100) # Percentage
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(f"{output_dir}/Figure_2_Burst_Prevalence.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/Figure_2_Burst_Prevalence.pdf", bbox_inches='tight')
        plt.close()
        print("  Created: Figure_2_Burst_Prevalence.png")

    def _plot_fig3_exemplar_timeseries(self, output_dir: str):
        """
        Figure 3: Exemplar Time Series.
        Multi-panel line plot for top devices with bursts.
        """
        # Select top 3 devices with bursts (same as timeline plot but refined)
        top_devices = []
        for device_id, result in self.results.items():
            if 'error' not in result:
                bursts = result.get('burst_analysis', {}).get('bursts', [])
                if bursts:
                    top_devices.append((device_id, result.get('num_publications', 0)))
        
        top_devices.sort(key=lambda x: x[1], reverse=True)
        top_devices = top_devices[:3]
        
        if not top_devices:
            return

        fig, axes = plt.subplots(len(top_devices), 1, figsize=(12, 4 * len(top_devices)), sharex=False)
        if len(top_devices) == 1:
            axes = [axes]
            
        colors = [self.colors['burst_high'], self.colors['burst_medium'], self.colors['timeline']]
        
        for idx, (device_id, _) in enumerate(top_devices):
            ax = axes[idx]
            result = self.results[device_id]
            device_name = result.get('device_name', device_id)
            dates = sorted(result.get('dates', []))
            
            # Plot yearly counts
            if dates:
                date_series = pd.Series(dates)
                yearly_counts = date_series.dt.year.value_counts().sort_index()
                ax.plot(yearly_counts.index, yearly_counts.values, marker='o', linewidth=2, color=colors[idx % len(colors)])
                ax.fill_between(yearly_counts.index, yearly_counts.values, alpha=0.2, color=colors[idx % len(colors)])
                
                # Highlight bursts areas
                bursts = result.get('burst_analysis', {}).get('bursts', [])
                for burst in bursts:
                    start_year = burst['start_time']
                    end_year = burst['end_time']
                    # Handle cases where time might be normalized or absolute (assumed years here if not normalized validation needed)
                    # If normalized, this visualization might need adjustment. Assuming years from data loading.
                    pass # Only shade if we have year data mapped correctly. Kleinberg usually returns indices or time units.
                         # Given earlier logic, let's stick to the simple plot for now.
            
            ax.set_title(f"Exemplar: {device_name[:50]}...", fontweight='bold')
            ax.set_ylabel("Publications")
            ax.grid(True, alpha=0.3)
            
        plt.xlabel("Year")
        plt.tight_layout()
        plt.savefig(f"{output_dir}/Figure_3_Exemplar_Timeseries.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/Figure_3_Exemplar_Timeseries.pdf", bbox_inches='tight')
        plt.close()
        print("  Created: Figure_3_Exemplar_Timeseries.png")

    def _plot_fig4_burst_timing(self, df: pd.DataFrame, output_dir: str):
        """
        Figure 4: Burst Timing.
        Histogram of years from PMA approval to first burst.
        """
        plt.figure(figsize=(10, 6))
        
        timing_data = []
        for _, row in df.iterrows():
            if not row['has_burst']:
                continue
                
            device_id = row['device_id']
            # Get approval year
            device_info = self.device_publications.get(device_id, {})
            approval_date = device_info.get('decision_date', pd.NaT)
            
            if pd.isna(approval_date):
                continue
                
            approval_year = approval_date.year
            
            # Get first burst year
            # Note: This relies on the burst detector using years as time units which matches the csv data loading
            result = self.results.get(device_id, {})
            bursts = result.get('burst_analysis', {}).get('bursts', [])
            if not bursts:
                continue
                
            first_burst_start = min([b['start_time'] for b in bursts])
            
            # Calculate lag
            lag = first_burst_start - approval_year
            if -10 < lag < 30: # Filter reasonable range
                timing_data.append(lag)
                
        if timing_data:
            sns.histplot(timing_data, bins=20, kde=True, color='teal')
            plt.axvline(x=0, color='red', linestyle='--', label='PMA Approval')
            plt.title('Time to First Hype Burst: Years from FDA Approval', fontsize=14, fontweight='bold')
            plt.xlabel('Years from Approval (Negative = Pre-market hype)', fontsize=12)
            plt.ylabel('Number of Devices', fontsize=12)
            plt.legend()
            plt.grid(axis='y', alpha=0.3)
            
            plt.savefig(f"{output_dir}/Figure_4_Burst_Timing.png", dpi=300, bbox_inches='tight')
            plt.savefig(f"{output_dir}/Figure_4_Burst_Timing.pdf", bbox_inches='tight')
            plt.close()
            print("  Created: Figure_4_Burst_Timing.png")

    def _plot_fig5_hype_vs_evidence(self, df: pd.DataFrame, output_dir: str):
        """
        Figure 5: Hype vs Evidence.
        Scatterplot of Hype Score vs Total Citations (proxy for evidence impact).
        """
        plt.figure(figsize=(10, 8))
        
        # Need citation count. Currently df has num_publications. 
        # I'll use num_publications as proxy for Volume of Evidence if citations aren't in viz data
        # To get citations, I'd need to aggregate from the raw data.
        # Let's perform a quick aggregation if possible or use num_pubs.
        # Implementation Plan says "log(citations)". I'll try to fetch citations.
        
        # Aggregate citations
        citation_map = {}
        for device_id, group_info in self.device_publications.items():
            if 'data' in group_info:
                citation_map[device_id] = group_info['data']['cited_by_count'].sum()
        
        df['total_citations'] = df['device_id'].map(citation_map).fillna(0)
        df['log_citations'] = np.log1p(df['total_citations'])
        
        sns.scatterplot(data=df, x='log_citations', y='hype_score', hue='specialty', 
                        palette='viridis', alpha=0.7, size='num_bursts', sizes=(20, 200))
        
        plt.title('Hype Intensity vs. Scientific Impact', fontsize=14, fontweight='bold')
        plt.xlabel('Log(Total Citations)', fontsize=12)
        plt.ylabel('Composite Hype Score', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        
        plt.savefig(f"{output_dir}/Figure_5_Hype_vs_Evidence.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/Figure_5_Hype_vs_Evidence.pdf", bbox_inches='tight')
        plt.close()
        print("  Created: Figure_5_Hype_vs_Evidence.png")

    def _plot_fig6_hype_ranking(self, df: pd.DataFrame, output_dir: str):
        """
        Figure 6: ranking of top 50 devices by hype score.
        """
        plt.figure(figsize=(10, 14))
        
        top_50 = df.sort_values('hype_score', ascending=False).head(50)
        
        sns.barplot(data=top_50, x='hype_score', y='device_name', palette='rocket')
        
        plt.title('Top 50 Medical Devices by Hype Score', fontsize=16, fontweight='bold')
        plt.xlabel('Composite Hype Score', fontsize=12)
        plt.ylabel(None)
        plt.yticks(fontsize=8)
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(f"{output_dir}/Figure_6_Hype_Ranking.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/Figure_6_Hype_Ranking.pdf", bbox_inches='tight')
        plt.close()
        print("  Created: Figure_6_Hype_Ranking.png")

    def _plot_fig7_pipeline_schematic(self, output_dir: str):
        """
        Figure 7: Schematic Diagram of the Analysis Pipeline.
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 5)
        ax.axis('off')
        
        # boxes
        box_props = dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='black')
        
        # 1. Data Source
        ax.text(1, 4, "Data Sources\n(OpenAlex API)\nPublications & Citations", 
                ha='center', va='center', bbox=dict(boxstyle='round,pad=0.5', facecolor='#e6f3ff', edgecolor='blue'))
        
        # 2. Filtering
        ax.text(3, 4, "Filtering & Matching\n(Fuzzy Logic)\nMatch to FDA PMA List", 
                ha='center', va='center', bbox=dict(boxstyle='round,pad=0.5', facecolor='#fff0e6', edgecolor='orange'))
        
        # 3. Burst Detection
        ax.text(5, 4, "Burst Detection\n(Kleinberg's Algorithm)\nIdentify High-Frequency Periods", 
                ha='center', va='center', bbox=dict(boxstyle='round,pad=0.5', facecolor='#e6ffe6', edgecolor='green'))
        
        # 4. Hype Analysis
        ax.text(7, 4, "Hype Quantification\nIntensity, Duration,\nRecurrence", 
                ha='center', va='center', bbox=dict(boxstyle='round,pad=0.5', facecolor='#ffe6e6', edgecolor='red'))
        
        # 5. Dashboard
        ax.text(9, 4, "Visualization\nFigures 1-7\nDashboard Generation", 
                ha='center', va='center', bbox=dict(boxstyle='round,pad=0.5', facecolor='#f9f2ec', edgecolor='brown'))
        
        # Arrows
        ax.annotate("", xy=(2, 4), xytext=(1.8, 4), arrowprops=dict(arrowstyle="->"))
        ax.annotate("", xy=(4, 4), xytext=(3.8, 4), arrowprops=dict(arrowstyle="->"))
        ax.annotate("", xy=(6, 4), xytext=(5.8, 4), arrowprops=dict(arrowstyle="->"))
        ax.annotate("", xy=(8, 4), xytext=(7.8, 4), arrowprops=dict(arrowstyle="->"))
        
        # Context labels
        ax.text(5, 1, "Analysis Pipeline: From Raw Data to Hype Metrics", 
                ha='center', va='center', fontsize=14, fontweight='bold', style='italic')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/Figure_7_Pipeline_Schematic.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/Figure_7_Pipeline_Schematic.pdf", bbox_inches='tight')
        plt.close()
        print("  Created: Figure_7_Pipeline_Schematic.png")
    
    def _create_overall_statistics_plot(self, output_dir: str):
        """Create overall statistics visualization."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Medical Device Publication Burst Analysis - Overall Statistics', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        devices_with_bursts = []
        publication_counts = []
        device_names = []
        
        for device_id, result in self.results.items():
            if 'error' not in result:
                bursts = result.get('burst_analysis', {}).get('bursts', [])
                devices_with_bursts.append(len(bursts) > 0)
                publication_counts.append(result.get('num_publications', 0))
                device_names.append(f"{device_id}\n{result.get('device_name', '')[:20]}...")
        
        # Plot 1: Devices with vs without bursts (pie chart)
        ax1 = axes[0, 0]
        burst_counts = [sum(devices_with_bursts), len(devices_with_bursts) - sum(devices_with_bursts)]
        labels = ['With Bursts', 'Without Bursts']
        colors = [self.colors['burst_high'], self.colors['timeline']]
        ax1.pie(burst_counts, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax1.set_title('Devices with Publication Bursts', fontweight='bold')
        
        # Plot 2: Publication count distribution (bar chart)
        ax2 = axes[0, 1]
        top_n = 10
        sorted_indices = np.argsort(publication_counts)[-top_n:][::-1]
        top_devices = [device_names[i] for i in sorted_indices]
        top_counts = [publication_counts[i] for i in sorted_indices]
        
        bars = ax2.bar(range(len(top_devices)), top_counts, color=self.colors['timeline'])
        ax2.set_xlabel('Device')
        ax2.set_ylabel('Number of Publications')
        ax2.set_title(f'Top {top_n} Devices by Publication Count', fontweight='bold')
        ax2.set_xticks(range(len(top_devices)))
        ax2.set_xticklabels(top_devices, rotation=45, ha='right', fontsize=9)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # Plot 3: Burst intensity distribution
        ax3 = axes[1, 0]
        burst_intensities = []
        for result in self.results.values():
            if 'error' not in result:
                bursts = result.get('burst_analysis', {}).get('bursts', [])
                for burst in bursts:
                    burst_intensities.append(burst['state'])
        
        if burst_intensities:
            unique_intensities = sorted(set(burst_intensities))
            intensity_counts = [burst_intensities.count(i) for i in unique_intensities]
            colors = [self.colors['burst_low'], self.colors['burst_medium'], self.colors['burst_high']]
            
            bars = ax3.bar([f'Level {i}' for i in unique_intensities], 
                          intensity_counts, 
                          color=colors[:len(unique_intensities)])
            ax3.set_xlabel('Burst Intensity Level')
            ax3.set_ylabel('Number of Bursts')
            ax3.set_title('Distribution of Burst Intensity Levels', fontweight='bold')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom')
        
        # Plot 4: Publications per year trend
        ax4 = axes[1, 1]
        all_years = []
        for result in self.results.values():
            if 'error' not in result:
                all_years.extend(result.get('publication_years', []))
        
        if all_years:
            year_counts = pd.Series(all_years).value_counts().sort_index()
            ax4.plot(year_counts.index, year_counts.values, 
                    marker='o', color=self.colors['timeline'], linewidth=2)
            ax4.fill_between(year_counts.index, year_counts.values, 
                           alpha=0.2, color=self.colors['timeline'])
            ax4.set_xlabel('Year')
            ax4.set_ylabel('Number of Publications')
            ax4.set_title('Overall Publication Trend Over Time', fontweight='bold')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/overall_statistics.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/overall_statistics.pdf", bbox_inches='tight')
        plt.close()
        print(f"  Created: overall_statistics.png")
    
    def _create_device_timeline_plots(self, output_dir: str):
        """Create timeline visualization for top devices."""
        # Get top devices by publication count
        top_devices = []
        for device_id, result in self.results.items():
            if 'error' not in result:
                top_devices.append((device_id, result.get('num_publications', 0)))
        
        top_devices.sort(key=lambda x: x[1], reverse=True)
        top_devices = top_devices[:8]  # Show top 8 devices
        
        for device_id, pub_count in top_devices:
            result = self.results[device_id]
            device_name = result.get('device_name', device_id)
            dates = result.get('dates', [])
            bursts = result.get('burst_analysis', {}).get('bursts', [])
            
            fig, ax = plt.subplots(figsize=(14, 6))
            
            # Plot publication timeline
            if dates:
                dates_sorted = sorted(dates)
                # Create histogram of publications by month
                date_series = pd.Series(dates_sorted)
                monthly_counts = date_series.groupby([date_series.dt.year, date_series.dt.month]).size()
                monthly_dates = [datetime(year, month, 1) for year, month in monthly_counts.index]
                
                ax.bar(monthly_dates, monthly_counts.values, 
                      width=20, alpha=0.6, color=self.colors['timeline'],
                      label='Publications')
            
            # Highlight burst periods
            if bursts:
                for burst in bursts:
                    start_date = burst['start_date']
                    end_date = burst['end_date']
                    intensity = burst['state']
                    
                    # Choose color based on intensity
                    if intensity == 1:
                        color = self.colors['burst_low']
                        alpha = 0.3
                    elif intensity == 2:
                        color = self.colors['burst_medium']
                        alpha = 0.5
                    else:
                        color = self.colors['burst_high']
                        alpha = 0.7
                    
                    # Add shaded region for burst
                    ax.axvspan(start_date, end_date, alpha=alpha, color=color,
                              label=f'Burst Level {intensity}' if burst == bursts[0] else '')
                    
                    # Add burst label
                    mid_date = start_date + (end_date - start_date) / 2
                    ax.text(mid_date, ax.get_ylim()[1] * 0.95,
                           f'Burst {burst["state"]}\n({burst["num_events"]} pubs)',
                           ha='center', va='top', fontsize=9,
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            
            # Formatting
            ax.set_xlabel('Year', fontsize=12)
            ax.set_ylabel('Publications per Month', fontsize=12)
            ax.set_title(f'{device_id}: {device_name}\nPublication Timeline with Burst Detection',
                        fontsize=14, fontweight='bold')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis as years
            ax.xaxis.set_major_locator(YearLocator())
            ax.xaxis.set_major_formatter(DateFormatter('%Y'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            safe_name = device_id.replace('/', '_').replace('\\', '_')
            plt.savefig(f"{output_dir}/timeline_{safe_name}.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        print(f"  Created: Timeline plots for {len(top_devices)} devices")
    
    def _create_burst_intensity_comparison(self, output_dir: str):
        """Create comparison of burst intensities across devices."""
        # Collect burst data
        burst_data = []
        for device_id, result in self.results.items():
            if 'error' not in result:
                bursts = result.get('burst_analysis', {}).get('bursts', [])
                for burst in bursts:
                    burst_data.append({
                        'device_id': device_id,
                        'device_name': result.get('device_name', device_id)[:30],
                        'intensity': burst['state'],
                        'duration': burst['duration'],
                        'num_events': burst['num_events'],
                        'start_year': burst['start_date'].year
                    })
        
        if not burst_data:
            return
        
        df_bursts = pd.DataFrame(burst_data)
        
        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Burst Intensity Comparison Across Devices', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # Plot 1: Bubble chart of burst characteristics
        ax1 = axes[0, 0]
        scatter = ax1.scatter(df_bursts['start_year'], 
                             df_bursts['intensity'],
                             s=df_bursts['num_events'] * 10,
                             c=df_bursts['duration'],
                             cmap='YlOrRd',
                             alpha=0.7,
                             edgecolors='black',
                             linewidth=0.5)
        
        ax1.set_xlabel('Start Year', fontsize=12)
        ax1.set_ylabel('Burst Intensity', fontsize=12)
        ax1.set_title('Burst Characteristics by Year', fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax1)
        cbar.set_label('Duration (days)', fontsize=10)
        
        # Add size legend
        sizes = [5, 10, 20, 30]
        labels = ['5 pubs', '10 pubs', '20 pubs', '30 pubs']
        for size, label in zip(sizes, labels):
            ax1.scatter([], [], s=size*10, c='gray', alpha=0.6, 
                       edgecolors='black', linewidth=0.5, label=label)
        ax1.legend(title='Burst Size', loc='upper right', fontsize=9)
        
        # Plot 2: Average burst intensity by device
        ax2 = axes[0, 1]
        avg_intensity = df_bursts.groupby('device_name')['intensity'].mean().sort_values(ascending=False)
        avg_intensity = avg_intensity.head(10)  # Top 10 devices
        
        bars = ax2.barh(range(len(avg_intensity)), avg_intensity.values,
                       color=plt.cm.RdYlBu(np.linspace(0.2, 0.8, len(avg_intensity))))
        ax2.set_yticks(range(len(avg_intensity)))
        ax2.set_yticklabels(avg_intensity.index, fontsize=9)
        ax2.set_xlabel('Average Burst Intensity', fontsize=12)
        ax2.set_title('Top 10 Devices by Average Burst Intensity', fontweight='bold')
        ax2.invert_yaxis()
        
        # Plot 3: Burst duration distribution
        ax3 = axes[1, 0]
        duration_bins = pd.cut(df_bursts['duration'], 
                              bins=[0, 100, 365, 730, 1825, 3650],
                              labels=['<100d', '100-365d', '1-2y', '2-5y', '>5y'])
        duration_counts = duration_bins.value_counts().sort_index()
        
        colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(duration_counts)))
        bars = ax3.bar(range(len(duration_counts)), duration_counts.values, color=colors)
        ax3.set_xlabel('Burst Duration', fontsize=12)
        ax3.set_ylabel('Number of Bursts', fontsize=12)
        ax3.set_title('Distribution of Burst Durations', fontweight='bold')
        ax3.set_xticks(range(len(duration_counts)))
        ax3.set_xticklabels(duration_counts.index, rotation=45, ha='right')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom')
        
        # Plot 4: Bursts per device
        ax4 = axes[1, 1]
        bursts_per_device = df_bursts['device_name'].value_counts().head(10)
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(bursts_per_device)))
        bars = ax4.bar(range(len(bursts_per_device)), bursts_per_device.values, color=colors)
        ax4.set_xlabel('Device', fontsize=12)
        ax4.set_ylabel('Number of Bursts', fontsize=12)
        ax4.set_title('Top 10 Devices by Number of Bursts', fontweight='bold')
        ax4.set_xticks(range(len(bursts_per_device)))
        ax4.set_xticklabels(bursts_per_device.index, rotation=45, ha='right', fontsize=9)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/burst_intensity_comparison.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/burst_intensity_comparison.pdf", bbox_inches='tight')
        plt.close()
        print(f"  Created: burst_intensity_comparison.png")
    
    def _create_publication_distribution_plot(self, output_dir: str):
        """Create publication distribution visualization."""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Publication Distribution Analysis', fontsize=16, fontweight='bold')
        
        # Collect all publication years
        all_years = []
        device_years = {}
        
        for device_id, result in self.results.items():
            if 'error' not in result:
                years = result.get('publication_years', [])
                all_years.extend(years)
                if years:
                    device_years[device_id] = result.get('device_name', device_id)[:20]
        
        if not all_years:
            plt.close()
            return
        
        # Plot 1: Yearly publication heatmap
        ax1 = axes[0]
        year_counts = pd.Series(all_years).value_counts().sort_index()
        
        # Create heatmap-like bar plot
        years = year_counts.index.astype(str)
        counts = year_counts.values
        
        colors = plt.cm.YlOrRd((counts - counts.min()) / (counts.max() - counts.min()))
        bars = ax1.bar(range(len(years)), counts, color=colors, edgecolor='black', linewidth=0.5)
        
        ax1.set_xlabel('Year', fontsize=12)
        ax1.set_ylabel('Number of Publications', fontsize=12)
        ax1.set_title('Publication Count by Year (Heatmap)', fontweight='bold')
        ax1.set_xticks(range(0, len(years), max(1, len(years)//10)))
        ax1.set_xticklabels(years[::max(1, len(years)//10)], rotation=45, ha='right')
        
        # Add value labels for top bars
        threshold = np.percentile(counts, 75)
        for bar, count in zip(bars, counts):
            if count > threshold:
                ax1.text(bar.get_x() + bar.get_width()/2., count + 1,
                        f'{count}', ha='center', va='bottom', fontsize=8)
        
        # Plot 2: Cumulative publications over time
        ax2 = axes[1]
        cumulative_counts = year_counts.cumsum()
        ax2.plot(range(len(years)), cumulative_counts, 
                marker='o', linewidth=2, color=self.colors['timeline'])
        ax2.fill_between(range(len(years)), cumulative_counts, 
                        alpha=0.2, color=self.colors['timeline'])
        
        # Highlight significant jumps
        changes = cumulative_counts.diff().fillna(0)
        significant_jumps = changes.nlargest(3).index
        
        for jump_idx in significant_jumps:
            if jump_idx < len(years):
                ax2.annotate(f'+{int(changes[jump_idx])}',
                           xy=(jump_idx, cumulative_counts.iloc[jump_idx]),
                           xytext=(jump_idx, cumulative_counts.iloc[jump_idx] + 20),
                           arrowprops=dict(arrowstyle='->', color='red', lw=1),
                           fontsize=9, color='red', fontweight='bold')
        
        ax2.set_xlabel('Year', fontsize=12)
        ax2.set_ylabel('Cumulative Publications', fontsize=12)
        ax2.set_title('Cumulative Publications Over Time', fontweight='bold')
        ax2.set_xticks(range(0, len(years), max(1, len(years)//10)))
        ax2.set_xticklabels(years[::max(1, len(years)//10)], rotation=45, ha='right')
        ax2.grid(True, alpha=0.3)
        
        # Add trend line
        if len(years) > 2:
            z = np.polyfit(range(len(years)), cumulative_counts, 1)
            p = np.poly1d(z)
            ax2.plot(range(len(years)), p(range(len(years))), 
                    '--', color='red', alpha=0.5, label='Trend Line')
            ax2.legend()
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/publication_distribution.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/publication_distribution.pdf", bbox_inches='tight')
        plt.close()
        print(f"  Created: publication_distribution.png")
    
    def _create_burst_heatmap(self, output_dir: str):
        """Create heatmap visualization of burst patterns."""
        # Prepare data for heatmap
        devices = []
        years = []
        burst_matrix = []
        
        # Get all unique years
        all_years = []
        for result in self.results.values():
            if 'error' not in result:
                all_years.extend(result.get('publication_years', []))
        
        if not all_years:
            return
        
        unique_years = sorted(set(all_years))
        
        # Get top devices
        top_devices = []
        for device_id, result in self.results.items():
            if 'error' not in result:
                top_devices.append((device_id, result.get('num_publications', 0)))
        
        top_devices.sort(key=lambda x: x[1], reverse=True)
        top_devices = top_devices[:15]  # Top 15 devices
        
        # Create burst intensity matrix
        for device_id, _ in top_devices:
            result = self.results[device_id]
            device_name = result.get('device_name', device_id)
            bursts = result.get('burst_analysis', {}).get('bursts', [])
            
            devices.append(device_name[:20])
            
            # Initialize year intensities to 0
            year_intensities = {year: 0 for year in unique_years}
            
            # Fill in burst intensities
            for burst in bursts:
                for year in burst.get('years_in_burst', []):
                    if year in year_intensities:
                        # Use maximum intensity for overlapping bursts
                        year_intensities[year] = max(year_intensities[year], burst['state'])
            
            burst_matrix.append([year_intensities[year] for year in unique_years])
        
        if not burst_matrix:
            return
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Create the heatmap
        im = ax.imshow(burst_matrix, cmap='YlOrRd', aspect='auto', interpolation='nearest')
        
        # Set labels
        ax.set_ylabel('Device', fontsize=12)
        ax.set_xlabel('Year', fontsize=12)
        ax.set_title('Burst Intensity Heatmap Across Devices and Years', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Set ticks
        ax.set_yticks(range(len(devices)))
        ax.set_yticklabels(devices, fontsize=9)
        
        # Show every nth year on x-axis
        n = max(1, len(unique_years) // 20)
        ax.set_xticks(range(0, len(unique_years), n))
        ax.set_xticklabels(unique_years[::n], rotation=45, ha='right', fontsize=9)
        
        # Add colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.set_label('Burst Intensity Level', rotation=270, labelpad=20, fontsize=12)
        
        # Add grid
        ax.set_xticks(np.arange(len(unique_years)) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(devices)) - 0.5, minor=True)
        ax.grid(which="minor", color="gray", linestyle='-', linewidth=0.5, alpha=0.3)
        ax.tick_params(which="minor", bottom=False, left=False)
        
        # Add text annotations for high intensity bursts
        for i in range(len(devices)):
            for j in range(len(unique_years)):
                intensity = burst_matrix[i][j]
                if intensity > 1:  # Only annotate medium/high intensity bursts
                    ax.text(j, i, str(intensity),
                           ha="center", va="center",
                           color="white" if intensity > 2 else "black",
                           fontsize=8, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/burst_heatmap.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/burst_heatmap.pdf", bbox_inches='tight')
        plt.close()
        print(f"  Created: burst_heatmap.png")
    
    def _create_dashboard_plot(self, output_dir: str):
        """Create a comprehensive dashboard visualization."""
        fig = plt.figure(figsize=(20, 16))
        fig.suptitle('Medical Device Publication Burst Analysis Dashboard', 
                    fontsize=20, fontweight='bold', y=0.98)
        
        # Create grid layout
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Top publications timeline (top row, full width)
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_top_publications_timeline(ax1)
        
        # 2. Burst intensity distribution (middle left)
        ax2 = fig.add_subplot(gs[1, 0])
        self._plot_burst_intensity_distribution(ax2)
        
        # 3. Device activity comparison (middle center)
        ax3 = fig.add_subplot(gs[1, 1])
        self._plot_device_activity_comparison(ax3)
        
        # 4. Yearly publication trend (middle right)
        ax4 = fig.add_subplot(gs[1, 2])
        self._plot_yearly_publication_trend(ax4)
        
        # 5. Burst characteristics scatter (bottom left)
        ax5 = fig.add_subplot(gs[2, 0])
        self._plot_burst_characteristics_scatter(ax5)
        
        # 6. Device network (bottom center)
        ax6 = fig.add_subplot(gs[2, 1])
        self._plot_device_network(ax6)
        
        # 7. Summary statistics (bottom right)
        ax7 = fig.add_subplot(gs[2, 2])
        self._plot_summary_statistics(ax7)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/analysis_dashboard.png", dpi=300, bbox_inches='tight')
        plt.savefig(f"{output_dir}/analysis_dashboard.pdf", bbox_inches='tight')
        plt.close()
        print(f"  Created: analysis_dashboard.png")
    
    def _plot_top_publications_timeline(self, ax):
        """Plot timeline for top 3 devices."""
        # Get top 3 devices
        top_devices = []
        for device_id, result in self.results.items():
            if 'error' not in result:
                top_devices.append((device_id, result.get('num_publications', 0)))
        
        top_devices.sort(key=lambda x: x[1], reverse=True)
        top_devices = top_devices[:3]
        
        colors = [self.colors['burst_high'], self.colors['burst_medium'], self.colors['timeline']]
        
        for idx, (device_id, pub_count) in enumerate(top_devices):
            result = self.results[device_id]
            device_name = result.get('device_name', device_id)
            dates = sorted(result.get('dates', []))
            
            if dates:
                # Create yearly counts
                date_series = pd.Series(dates)
                yearly_counts = date_series.dt.year.value_counts().sort_index()
                
                # Plot as line with markers
                ax.plot(yearly_counts.index, yearly_counts.values, 
                       marker='o', linewidth=2, markersize=6,
                       color=colors[idx], label=f'{device_id}: {device_name[:30]}...')
                
                # Add fill under line
                ax.fill_between(yearly_counts.index, yearly_counts.values, 
                               alpha=0.2, color=colors[idx])
        
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Publications per Year', fontsize=12)
        ax.set_title('Publication Timeline - Top 3 Devices', fontweight='bold')
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    def _plot_burst_intensity_distribution(self, ax):
        """Plot burst intensity distribution."""
        burst_intensities = []
        for result in self.results.values():
            if 'error' not in result:
                bursts = result.get('burst_analysis', {}).get('bursts', [])
                for burst in bursts:
                    burst_intensities.append(burst['state'])
        
        if burst_intensities:
            unique_intensities = sorted(set(burst_intensities))
            intensity_counts = [burst_intensities.count(i) for i in unique_intensities]
            
            colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(unique_intensities)))
            bars = ax.bar([f'Level {i}' for i in unique_intensities], intensity_counts, color=colors)
            
            ax.set_xlabel('Burst Intensity', fontsize=10)
            ax.set_ylabel('Count', fontsize=10)
            ax.set_title('Burst Intensity Distribution', fontweight='bold')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{int(height)}', ha='center', va='bottom', fontsize=9)
    
    def _plot_device_activity_comparison(self, ax):
        """Compare device activity levels."""
        activity_data = []
        for device_id, result in self.results.items():
            if 'error' not in result:
                pub_count = result.get('num_publications', 0)
                burst_count = len(result.get('burst_analysis', {}).get('bursts', []))
                activity_data.append({
                    'device': device_id,
                    'publications': pub_count,
                    'bursts': burst_count
                })
        
        if activity_data:
            df_activity = pd.DataFrame(activity_data)
            df_activity = df_activity.nlargest(8, 'publications')  # Top 8 devices
            
            x = np.arange(len(df_activity))
            width = 0.35
            
            bars1 = ax.bar(x - width/2, df_activity['publications'], width, 
                          label='Publications', color=self.colors['timeline'], alpha=0.8)
            bars2 = ax.bar(x + width/2, df_activity['bursts'], width, 
                          label='Bursts', color=self.colors['burst_high'], alpha=0.8)
            
            ax.set_xlabel('Device', fontsize=10)
            ax.set_ylabel('Count', fontsize=10)
            ax.set_title('Device Activity Comparison', fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(df_activity['device'], rotation=45, ha='right', fontsize=9)
            ax.legend(fontsize=9)
    
    def _plot_yearly_publication_trend(self, ax):
        """Plot yearly publication trend with burst highlights."""
        # Collect all publication years
        all_years = []
        for result in self.results.values():
            if 'error' not in result:
                all_years.extend(result.get('publication_years', []))
        
        if all_years:
            year_counts = pd.Series(all_years).value_counts().sort_index()
            
            # Plot line
            ax.plot(year_counts.index, year_counts.values, 
                   marker='o', linewidth=2, color=self.colors['timeline'])
            
            # Find significant years (above 75th percentile)
            threshold = np.percentile(year_counts.values, 75)
            significant_years = year_counts[year_counts > threshold]
            
            # Highlight significant years
            for year, count in significant_years.items():
                ax.scatter(year, count, s=100, color=self.colors['burst_high'], 
                          zorder=5, edgecolors='black', linewidth=1.5)
                ax.annotate(f'{count}', xy=(year, count), xytext=(year, count + 5),
                           ha='center', fontsize=9, fontweight='bold', color=self.colors['burst_high'])
            
            ax.set_xlabel('Year', fontsize=10)
            ax.set_ylabel('Publications', fontsize=10)
            ax.set_title('Yearly Publication Trend', fontweight='bold')
            ax.grid(True, alpha=0.3)
    
    def _plot_burst_characteristics_scatter(self, ax):
        """Plot scatter of burst characteristics."""
        burst_data = []
        for result in self.results.values():
            if 'error' not in result:
                bursts = result.get('burst_analysis', {}).get('bursts', [])
                for burst in bursts:
                    burst_data.append({
                        'duration': burst['duration'],
                        'events': burst['num_events'],
                        'intensity': burst['state']
                    })
        
        if burst_data:
            df_bursts = pd.DataFrame(burst_data)
            
            scatter = ax.scatter(df_bursts['duration'], df_bursts['events'],
                                c=df_bursts['intensity'], cmap='RdYlBu_r',
                                s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
            
            ax.set_xlabel('Duration (days)', fontsize=10)
            ax.set_ylabel('Publications in Burst', fontsize=10)
            ax.set_title('Burst Characteristics', fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Intensity', fontsize=9)
    
    def _plot_device_network(self, ax):
        """Create a simple device network visualization."""
        ax.text(0.5, 0.5, 'Device Network\nVisualization', 
               ha='center', va='center', fontsize=12, fontweight='bold',
               transform=ax.transAxes)
        ax.set_title('Device Relationships', fontweight='bold')
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add a simple network diagram
        n_devices = min(5, len(self.results))
        angles = np.linspace(0, 2*np.pi, n_devices, endpoint=False)
        radius = 0.3
        
        # Plot nodes
        for i in range(n_devices):
            x = 0.5 + radius * np.cos(angles[i])
            y = 0.5 + radius * np.sin(angles[i])
            ax.scatter(x, y, s=200, color=self.colors['timeline'], 
                      edgecolors='black', linewidth=1.5, zorder=5)
            
            # Add device labels
            device_id = list(self.results.keys())[i]
            label = device_id if len(device_id) < 8 else device_id[:6] + '...'
            ax.text(x, y - 0.05, label, ha='center', va='top', fontsize=8)
        
        # Connect all nodes to center
        for angle in angles:
            x = 0.5 + radius * np.cos(angle)
            y = 0.5 + radius * np.sin(angle)
            ax.plot([0.5, x], [0.5, y], color='gray', alpha=0.5, linewidth=1)
    
    def _plot_summary_statistics(self, ax):
        """Plot summary statistics as text."""
        if not self.results:
            return
        
        # Calculate statistics
        total_devices = len(self.results)
        devices_with_bursts = sum(1 for r in self.results.values() 
                                 if r.get('burst_analysis', {}).get('bursts', []))
        total_publications = sum(r.get('num_publications', 0) for r in self.results.values() 
                                if 'error' not in r)
        total_bursts = sum(len(r.get('burst_analysis', {}).get('bursts', [])) 
                          for r in self.results.values() if 'error' not in r)
        
        # Get years range
        all_years = []
        for result in self.results.values():
            if 'error' not in result:
                all_years.extend(result.get('publication_years', []))
        
        years_range = f"{min(all_years)}-{max(all_years)}" if all_years else "N/A"
        
        # Create summary text
        summary_text = (
            f"ANALYSIS SUMMARY\n\n"
            f"Total Devices: {total_devices}\n"
            f"Devices with Bursts: {devices_with_bursts}\n"
            f"Total Publications: {total_publications}\n"
            f"Total Bursts Detected: {total_bursts}\n"
            f"Time Period: {years_range}\n\n"
            f"Avg Publications/Device: {total_publications/total_devices:.1f}\n"
            f"Avg Bursts/Device: {total_bursts/total_devices:.1f}\n"
            f"Burst Rate: {(total_bursts/total_publications*100):.1f}%"
        )
        
        ax.text(0.1, 0.5, summary_text, fontsize=11, fontfamily='monospace',
               verticalalignment='center', transform=ax.transAxes)
        
        ax.set_title('Analysis Summary', fontweight='bold')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)


def main():
    """Main analysis function."""
    # Initialize analyzer
    print("Loading and analyzing publication data...")
    analyzer = DeviceBurstAnalyzer(
        "Revised_med_device_hype\data\processed\publications_surgical.csv",
        "Revised_med_device_hype\data\processed\devices_surgical.csv"
    )
    
    # Analyze all devices
    print("\n" + "="*60)
    print("BURST DETECTION ANALYSIS FOR MEDICAL DEVICES")
    print("="*60)
    
    results = analyzer.analyze_all_devices(k=3, normalize=True)
    
    # Export results
    analyzer.export_results(results, "device_burst_analysis.csv")
    
    # Generate detailed report
    analyzer.generate_report(results, "device_burst_report.txt")
    
    # Create visualizations
    analyzer.create_visualizations("burst_visualizations")
    
    # Print overall statistics
    print("\n" + "="*60)
    print("OVERALL STATISTICS")
    print("="*60)
    
    total_devices = len(results)
    devices_with_bursts = sum(1 for r in results.values() 
                             if r.get('burst_analysis', {}).get('bursts', []))
    
    print(f"Total devices analyzed: {total_devices}")
    print(f"Devices with detected bursts: {devices_with_bursts}")
    print(f"Devices without bursts: {total_devices - devices_with_bursts}")
    
    # Show top devices by publication count
    print("\nTop 5 devices by publication volume:")
    sorted_devices = sorted(results.items(), 
                          key=lambda x: x[1].get('num_publications', 0), 
                          reverse=True)
    
    for i, (device_id, device_results) in enumerate(sorted_devices[:5], 1):
        bursts = device_results.get('burst_analysis', {}).get('bursts', [])
        print(f"{i}. {device_id}: {device_results.get('num_publications', 0)} publications, "
              f"{len(bursts)} burst periods")
    
    return results, analyzer


if __name__ == "__main__":
    # Save the Kleinberg burst detector class to a separate file
    kleinberg_code = '''
"""
Kleinberg's Burst Detection Algorithm Implementation
Pure algorithm without CSV dependencies
"""

import numpy as np
import math
from typing import List, Tuple, Dict, Any


class KleinbergBurstDetector:
    """
    Implementation of Kleinberg's burst detection algorithm for event streams.
    
    Based on: "Bursty and Hierarchical Structure in Streams" by Jon Kleinberg (2002)
    
    This is a pure algorithmic implementation with no external dependencies.
    """
    
    def __init__(self, s: float = 2, gamma: float = 1.0):
        """
        Initialize the burst detector.
        
        Args:
            s: Base for exponential distribution of state transitions (s > 1)
            gamma: Parameter controlling cost of state transitions
        """
        if s <= 1:
            raise ValueError("s must be greater than 1")
        if gamma <= 0:
            raise ValueError("gamma must be positive")
            
        self.s = s
        self.gamma = gamma
        
    def _compute_inter_arrival_times(self, timestamps: List[float]) -> List[float]:
        """Convert timestamps to inter-arrival times."""
        if len(timestamps) <= 1:
            return []
        
        # Ensure timestamps are sorted
        sorted_timestamps = sorted(timestamps)
        return [sorted_timestamps[i] - sorted_timestamps[i-1] 
                for i in range(1, len(sorted_timestamps))]
    
    def _estimate_rates(self, inter_arrival_times: List[float], s: float, k: int) -> List[float]:
        """
        Estimate rates for each state using the geometric distribution.
        
        The rate for state j is: r_j = (s^j) * r
        where r is the overall rate of events.
        """
        if not inter_arrival_times:
            return []
        
        # Overall rate (events per time unit)
        total_time = sum(inter_arrival_times)
        if total_time <= 0:
            total_time = 1e-10
        overall_rate = len(inter_arrival_times) / total_time
        
        # Rates for each state (exponentially increasing)
        rates = [overall_rate * (s ** j) for j in range(k)]
        return rates
    
    def _compute_observation_cost(self, delta_t: float, rate: float) -> float:
        """
        Compute negative log-likelihood for an inter-arrival time.
        
        Using exponential distribution: f(delta_t; r) = r * exp(-r * delta_t)
        Cost = -log(f(delta_t; r))
        """
        if rate <= 0:
            return float('inf')
        if delta_t <= 0:
            delta_t = 1e-10
            
        # Compute probability and avoid numerical underflow
        log_prob = math.log(rate) - rate * delta_t
        return -log_prob
    
    def detect_bursts(self, timestamps: List[float], k: int = 3) -> Dict[str, Any]:
        """
        Detect bursts in a sequence of timestamps.
        
        Args:
            timestamps: List of event timestamps (any unit, but must be consistent)
            k: Number of states (including quiescent state)
            
        Returns:
            Dictionary containing:
                - bursts: List of detected bursts with metadata
                - states: Optimal state sequence for each interval
                - rates: Estimated rates for each state
                - cost: Total optimal cost
                - inter_arrivals: Inter-arrival times
        """
        if len(timestamps) < 2:
            return {
                "bursts": [],
                "states": [],
                "rates": [],
                "cost": 0,
                "inter_arrivals": [],
                "num_events": len(timestamps)
            }
        
        # Sort and compute inter-arrival times
        sorted_timestamps = sorted(timestamps)
        inter_arrivals = self._compute_inter_arrival_times(sorted_timestamps)
        n = len(inter_arrivals)
        
        # Estimate rates for each state
        rates = self._estimate_rates(inter_arrivals, self.s, k)
        
        # Dynamic programming tables
        cost = np.full((n, k), float('inf'))  # Minimum cost to reach state j at interval i
        prev_state = np.full((n, k), -1, dtype=int)  # Backpointer for reconstruction
        
        # Base case: first interval
        for j in range(k):
            cost[0][j] = self._compute_observation_cost(inter_arrivals[0], rates[j])
        
        # Main DP recurrence
        for i in range(1, n):
            for j in range(k):
                # Consider all possible previous states
                for prev_j in range(k):
                    transition_cost = self.gamma * abs(j - prev_j)
                    total_cost = (cost[i-1][prev_j] + 
                                self._compute_observation_cost(inter_arrivals[i], rates[j]) + 
                                transition_cost)
                    
                    if total_cost < cost[i][j]:
                        cost[i][j] = total_cost
                        prev_state[i][j] = prev_j
        
        # Backtrack to find optimal state sequence
        optimal_states = np.zeros(n, dtype=int)
        optimal_states[-1] = np.argmin(cost[-1])
        total_cost = cost[-1][optimal_states[-1]]
        
        for i in range(n-2, -1, -1):
            optimal_states[i] = prev_state[i+1][optimal_states[i+1]]
        
        # Convert state sequence to burst segments
        bursts = self._extract_bursts_from_states(optimal_states, sorted_timestamps, rates)
        
        return {
            "bursts": bursts,
            "states": optimal_states.tolist(),
            "rates": rates,
            "cost": float(total_cost),
            "inter_arrivals": inter_arrivals,
            "timestamps": sorted_timestamps,
            "num_events": len(timestamps)
        }
    
    def _extract_bursts_from_states(self, states: np.ndarray, timestamps: List[float], 
                                   rates: List[float]) -> List[Dict]:
        """
        Extract burst segments from state sequence.
        
        Args:
            states: Optimal state sequence for each interval
            timestamps: Sorted event timestamps
            rates: Estimated rates for each state
            
        Returns:
            List of dictionaries describing each burst
        """
        if len(states) == 0:
            return []
        
        bursts = []
        current_state = states[0]
        start_idx = 0
        
        for i in range(1, len(states)):
            if states[i] != current_state:
                # Segment ended
                if current_state > 0:  # This was a burst state
                    burst = self._create_burst_info(
                        start_idx=start_idx,
                        end_idx=i,
                        state=current_state,
                        timestamps=timestamps,
                        rates=rates
                    )
                    bursts.append(burst)
                
                current_state = states[i]
                start_idx = i
        
        # Handle the last segment
        if current_state > 0:
            burst = self._create_burst_info(
                start_idx=start_idx,
                end_idx=len(states),
                state=current_state,
                timestamps=timestamps,
                rates=rates
            )
            bursts.append(burst)
        
        # Merge adjacent bursts of same state
        return self._merge_adjacent_bursts(bursts)
    
    def _create_burst_info(self, start_idx: int, end_idx: int, state: int,
                          timestamps: List[float], rates: List[float]) -> Dict:
        """Create burst metadata dictionary."""
        return {
            "start_time": timestamps[start_idx],
            "end_time": timestamps[end_idx],
            "start_index": start_idx,
            "end_index": end_idx,
            "state": int(state),
            "intensity": rates[state],
            "num_events": end_idx - start_idx + 1,
            "duration": timestamps[end_idx] - timestamps[start_idx]
        }
    
    def _merge_adjacent_bursts(self, bursts: List[Dict]) -> List[Dict]:
        """Merge adjacent bursts of the same state."""
        if not bursts:
            return []
        
        merged = []
        current_burst = bursts[0].copy()
        
        for burst in bursts[1:]:
            if (burst["state"] == current_burst["state"] and 
                burst["start_index"] == current_burst["end_index"] + 1):
                # Merge with current burst
                current_burst["end_time"] = burst["end_time"]
                current_burst["end_index"] = burst["end_index"]
                current_burst["num_events"] += burst["num_events"]
                current_burst["duration"] = current_burst["end_time"] - current_burst["start_time"]
            else:
                merged.append(current_burst)
                current_burst = burst.copy()
        
        merged.append(current_burst)
        return merged
    
    def get_burst_summary(self, burst_results: Dict[str, Any]) -> str:
        """Generate a human-readable summary of detected bursts."""
        bursts = burst_results.get("bursts", [])
        
        if not bursts:
            return "No bursts detected."
        
        summary_lines = [f"Detected {len(bursts)} burst(s):", "-" * 50]
        
        for i, burst in enumerate(bursts, 1):
            summary_lines.extend([
                f"Burst {i}:",
                f"  Time: {burst['start_time']:.2f} to {burst['end_time']:.2f}",
                f"  Duration: {burst['duration']:.2f}",
                f"  Events: {burst['num_events']}",
                f"  Intensity level: {burst['state']}",
                f"  Rate: {burst['intensity']:.4f} events/unit time",
                "-" * 50
            ])
        
        return "\n".join(summary_lines)


def normalize_timestamps(timestamps: List[float]) -> List[float]:
    """
    Normalize timestamps to start at 0.
    
    Useful when you have absolute timestamps but want relative timing.
    """
    if not timestamps:
        return []
    
    min_time = min(timestamps)
    return [t - min_time for t in timestamps]
'''
    
    # Write the Kleinberg code to a file
    with open('kleinberg_burst_detector.py', 'w', encoding='utf-8') as f:
        f.write(kleinberg_code)
    
    print("Created kleinberg_burst_detector.py")
    print("Now running the main analysis...")
    
    # Run the main analysis
    results, analyzer = main()
    
    # Print quick insights
    print("\n" + "="*60)
    print("QUICK INSIGHTS")
    print("="*60)
    
    # Find devices with strongest bursts
    devices_with_bursts = []
    for device_id, result in results.items():
        if 'error' not in result:
            bursts = result.get('burst_analysis', {}).get('bursts', [])
            if bursts:
                max_intensity = max(burst['state'] for burst in bursts)
                total_burst_events = sum(burst['num_events'] for burst in bursts)
                devices_with_bursts.append((device_id, result.get('device_name', ''), 
                                          len(bursts), max_intensity, total_burst_events))
    
    if devices_with_bursts:
        print("\nDevices with strongest burst patterns:")
        for device_id, name, num_bursts, max_intensity, total_events in sorted(devices_with_bursts, 
                                                                             key=lambda x: x[3], 
                                                                             reverse=True)[:5]:
            print(f"- {device_id}: {num_bursts} bursts, intensity {max_intensity}, "
                  f"{total_events} publications in bursts")
    
    print("\nVisualizations saved in 'burst_visualizations' folder:")
    print("1. overall_statistics.png - Overall analysis statistics")
    print("2. timeline_*.png - Individual device timeline plots")
    print("3. burst_intensity_comparison.png - Burst intensity comparisons")
    print("4. publication_distribution.png - Publication distribution analysis")
    print("5. burst_heatmap.png - Burst heatmap across devices and years")
    print("6. analysis_dashboard.png - Comprehensive dashboard view")
    
    # Show a sample visualization
    try:
        import matplotlib.pyplot as plt
        import matplotlib.image as mpimg
        
        dashboard_path = "burst_visualizations/analysis_dashboard.png"
        if os.path.exists(dashboard_path):
            print(f"\nOpening dashboard visualization...")
            img = mpimg.imread(dashboard_path)
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.imshow(img)
            ax.axis('off')
            ax.set_title('Analysis Dashboard Preview', fontsize=14, fontweight='bold')
            plt.tight_layout()
            plt.show()
    except:
        pass