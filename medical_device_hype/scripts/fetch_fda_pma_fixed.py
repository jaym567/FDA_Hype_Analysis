#!/usr/bin/env python3
"""
Fetch FDA PMA Data - Fixed Approach
Addresses server-side issues with proper pagination and rate limiting
"""

import requests
import time
import json
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

console = Console()

from pathlib import Path

BASE_URL = "https://api.fda.gov/device/pma.json"
LIMIT = 100  # Reduced limit - FDA API may have restrictions
MAX_SKIP = 5000  # Maximum skip value to prevent 400 errors
DATA_DIR = Path(__file__).parent.parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
OUT_FILE = DATA_DIR / "fda_pma_fixed.json"

def fetch_fda_pma_fixed():
    """Fetch FDA PMA data with proper pagination and rate limiting"""
    
    console.print("🔍 [bold]Fetching FDA PMA Data (Fixed Approach)[/bold]")
    console.print(f"📡 [cyan]API Endpoint:[/cyan] {BASE_URL}")
    console.print(f"📊 [cyan]Limit per request:[/cyan] {LIMIT}")
    console.print(f"⏱️ [cyan]Rate limiting:[/cyan] 0.5s between requests")
    
    all_results = []
    skip = 0
    total_requests = 0
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Fetching recent FDA data...", total=None)
        
        while True:
            # Stop if skip exceeds maximum (FDA API may have limits)
            if skip > MAX_SKIP:
                console.print(f"⚠️ [yellow]Reached maximum skip value ({MAX_SKIP}), stopping[/yellow]")
                console.print(f"📋 [cyan]Retrieved {len(all_results)} records total.[/cyan]")
                break
            
            # Build params - use simplest approach (no sort to avoid 400 errors)
            params = {
                "limit": LIMIT
            }
            
            # Only add skip if > 0 (FDA API may not support skip=0)
            if skip > 0:
                params["skip"] = skip
            
            try:
                progress.update(task, description=f"Request {total_requests + 1}: skip={skip}")
                
                r = requests.get(BASE_URL, params=params, timeout=30)
                
                if r.status_code != 200:
                    error_msg = f"Error {r.status_code}"
                    if r.status_code == 400:
                        error_msg += " (Bad Request - API may not support this query)"
                        # For 400 errors, try with smaller limit or stop if already tried
                        if LIMIT > 100:
                            console.print(f"⚠️ [yellow]{error_msg} for skip {skip}, trying with smaller limit[/yellow]")
                            # Try with smaller limit on next iteration
                            params["limit"] = 100
                            time.sleep(1.0)
                            continue
                        else:
                            console.print(f"⚠️ [yellow]{error_msg} for skip {skip}, stopping pagination[/yellow]")
                            break
                    else:
                        error_msg += f" for skip {skip}"
                    
                    console.print(f"⚠️ [yellow]{error_msg}[/yellow]")
                    consecutive_errors += 1
                    
                    if consecutive_errors >= max_consecutive_errors:
                        console.print(f"❌ [red]Too many consecutive errors ({consecutive_errors}), stopping[/red]")
                        break
                    
                    # Wait longer on errors
                    time.sleep(2.0)
                    continue

                data = r.json()
                consecutive_errors = 0  # Reset error counter on success

                if "results" not in data:
                    console.print("⚠️ [yellow]No 'results' in response[/yellow]")
                    break

                results = data["results"]
                
                if not results:
                    console.print("✅ [green]No more results[/green]")
                    break
                
                all_results.extend(results)
                total_requests += 1
                
                progress.update(task, description=f"Retrieved {len(results)} records (total: {len(all_results)})")

                if len(results) < LIMIT:
                    console.print("✅ [green]Retrieved all available data[/green]")
                    break

                skip += len(results)  # Use actual number of results, not LIMIT
                
                # Rate limiting - be very polite to the FDA API
                time.sleep(1.0)  # Increased delay to avoid rate limits
                
                # Stop if we've made too many requests (safety check)
                if total_requests > 50:  # Reduced limit to avoid hitting API restrictions
                    console.print("⚠️ [yellow]Reached maximum request limit (50), stopping[/yellow]")
                    console.print(f"📋 [cyan]Retrieved {len(all_results)} records total.[/cyan]")
                    break
                
                # Stop if we got fewer results than limit (likely end of data)
                if len(results) < LIMIT:
                    console.print("✅ [green]Retrieved all available data (fewer results than limit)[/green]")
                    break
                
            except Exception as e:
                console.print(f"❌ [red]Error fetching skip {skip}: {e}[/red]")
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    console.print(f"❌ [red]Too many consecutive errors ({consecutive_errors}), stopping[/red]")
                    break
                
                time.sleep(2.0)
                continue
    
    # Save recent results to JSON file
    console.print(f"\n💾 [green]Saving {len(all_results)} recent PMA records to {str(OUT_FILE)}...[/green]")
    
    with open(OUT_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    console.print(f"✅ [green]Saved {len(all_results)} recent PMA records[/green]")
    
    # Display summary
    display_summary(all_results)
    
    return all_results

def fetch_historical_fda_data():
    """Fetch historical FDA PMA data from 1990-2014"""
    
    console.print("🔍 [bold]Fetching Historical FDA PMA Data (1990-2014)[/bold]")
    
    all_historical_results = []
    
    # Try different approaches for historical data (simplified to avoid 400 errors)
    approaches = [
        ("no_sort_small", {"limit": 100}),  # Simplest approach first
        ("ascending_sort", {"sort": "decision_date:asc", "limit": 100}),
        ("no_sort_medium", {"limit": 50}),
    ]
    
    for approach_name, params in approaches:
        console.print(f"\n📡 [cyan]Trying {approach_name} approach...[/cyan]")
        
        skip = 0
        approach_results = []
        consecutive_errors = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task(f"Fetching {approach_name}...", total=None)
            
            while True:
                # Stop if skip exceeds maximum
                if skip > MAX_SKIP:
                    console.print(f"⚠️ [yellow]Reached maximum skip value ({MAX_SKIP}) for {approach_name}[/yellow]")
                    break
                
                request_params = params.copy()
                # Only add skip if > 0
                if skip > 0:
                    request_params["skip"] = skip
                
                try:
                    progress.update(task, description=f"{approach_name}: skip={skip}")
                    
                    r = requests.get(BASE_URL, params=request_params, timeout=30)
                    
                    if r.status_code != 200:
                        error_msg = f"Error {r.status_code}"
                        if r.status_code == 400:
                            error_msg += " (Bad Request - API may not support this query)"
                            # For 400 errors, skip this approach entirely
                            console.print(f"⚠️ [yellow]{error_msg} for {approach_name}, trying next approach[/yellow]")
                            break
                        elif r.status_code == 404:
                            error_msg += " (Not Found - endpoint may not exist)"
                            console.print(f"⚠️ [yellow]{error_msg} for {approach_name}, trying next approach[/yellow]")
                            break
                        else:
                            error_msg += f" for {approach_name} skip {skip}"
                            console.print(f"⚠️ [yellow]{error_msg}[/yellow]")
                            consecutive_errors += 1
                            
                            if consecutive_errors >= 3:
                                console.print(f"❌ [red]Too many errors for {approach_name}, trying next approach[/red]")
                                break
                            
                            time.sleep(2.0)
                            continue

                    data = r.json()
                    consecutive_errors = 0

                    if "results" not in data:
                        break

                    results = data["results"]
                    
                    if not results:
                        console.print(f"✅ [green]No more results for {approach_name}[/green]")
                        break
                    
                    # Filter for historical dates (1990-2014)
                    historical_results = []
                    for result in results:
                        decision_date = result.get('decision_date', '')
                        if decision_date and decision_date.startswith(('199', '200', '2010', '2011', '2012', '2013', '2014')):
                            historical_results.append(result)
                    
                    if historical_results:
                        approach_results.extend(historical_results)
                        all_historical_results.extend(historical_results)
                    
                    progress.update(task, description=f"{approach_name}: {len(approach_results)} historical records")
                    
                    # Stop if we got fewer results than limit
                    if len(results) < params.get("limit", LIMIT):
                        console.print(f"✅ [green]Retrieved all available data for {approach_name}[/green]")
                        break
                    
                    skip += len(results)  # Use actual number of results
                    
                    # Rate limiting - be more conservative
                    time.sleep(1.0)
                    
                    # Safety check - reduced limit
                    if skip > MAX_SKIP or len(approach_results) > 5000:
                        console.print(f"⚠️ [yellow]Reached limit for {approach_name} (skip={skip}, records={len(approach_results)})[/yellow]")
                        break
                
                except Exception as e:
                    console.print(f"❌ [red]Error in {approach_name}: {e}[/red]")
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        break
                    time.sleep(2.0)
                    continue
            
            console.print(f"✅ [green]{approach_name}: Found {len(approach_results)} historical records[/green]")
    
    # Save historical results
    historical_file = DATA_DIR / "fda_pma_historical.json"
    console.print(f"\n💾 [green]Saving {len(all_historical_results)} historical PMA records to {str(historical_file)}...[/green]")
    
    with open(historical_file, "w") as f:
        json.dump(all_historical_results, f, indent=2)

    console.print(f"✅ [green]Saved {len(all_historical_results)} historical PMA records[/green]")
    
    # Display historical summary
    display_summary(all_historical_results, "Historical FDA PMA Data")
    
    return all_historical_results

def fetch_fda_pma_by_month():
    """Fetch FDA PMA data month by month with smaller ranges"""
    
    console.print("🔍 [bold]Fetching FDA PMA Data Month by Month[/bold]")
    
    all_results = []
    
    # Generate month ranges from 2025 to 1990 (full range)
    # Start with recent months first (more likely to have data)
    start_date = datetime(2025, 12, 1)  # End of 2025
    end_date = datetime(1990, 1, 1)     # Start of 1990
    
    current_date = start_date
    month_ranges = []
    
    while current_date >= end_date:
        # Get the first day of the month
        month_start = current_date.replace(day=1)
        # Get the last day of the month
        if current_date.month == 12:
            month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
        
        month_ranges.append({
            'year': current_date.year,
            'month': current_date.month,
            'start': month_start.strftime('%Y%m%d'),
            'end': month_end.strftime('%Y%m%d')
        })
        
        # Move to previous month
        if current_date.month == 1:
            current_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            current_date = current_date.replace(month=current_date.month - 1)
    
    console.print(f"📅 [cyan]Date Range:[/cyan] 1990-01-01 to 2025-12-31")
    console.print(f"📊 [cyan]Total Months:[/cyan] {len(month_ranges)}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for i, month_range in enumerate(month_ranges):
            task = progress.add_task(f"Fetching {month_range['year']}-{month_range['month']:02d}...", total=None)
            
            skip = 0
            month_results = []
            
            while True:
                # Use exact Lucene syntax for date range
                params = {
                    "search": f"decision_date:[{month_range['start']}+TO+{month_range['end']}]",
                    "limit": 500,  # Reasonable limit for month queries
                    "skip": skip
                }
                
                try:
                    progress.update(task, description=f"{month_range['year']}-{month_range['month']:02d}: skip={skip}")
                    
                    r = requests.get(BASE_URL, params=params, timeout=30)
                    
                    if r.status_code != 200:
                        error_msg = f"Error {r.status_code}"
                        if r.status_code == 400:
                            error_msg += " (Bad Request - skipping this month)"
                            console.print(f"⚠️ [yellow]{error_msg} for {month_range['year']}-{month_range['month']:02d}[/yellow]")
                        else:
                            error_msg += f" for {month_range['year']}-{month_range['month']:02d} skip {skip}"
                            console.print(f"⚠️ [yellow]{error_msg}[/yellow]")
                        break

                    data = r.json()

                    if "results" not in data:
                        break

                    results = data["results"]
                    
                    if not results:
                        break
                    
                    month_results.extend(results)
                    all_results.extend(results)
                    
                    progress.update(task, description=f"{month_range['year']}-{month_range['month']:02d}: {len(month_results)} records")

                    if len(results) < 500:
                        break

                    skip += 500
                    time.sleep(0.8)  # Slightly longer delay for month queries
                    
                except Exception as e:
                    console.print(f"❌ [red]Error fetching {month_range['year']}-{month_range['month']:02d} skip {skip}: {e}[/red]")
                    break
            
            progress.update(task, description=f"✅ {month_range['year']}-{month_range['month']:02d}: {len(month_results)} records")
            time.sleep(0.5)  # Delay between months
            
            # Show progress every 10 months
            if (i + 1) % 10 == 0:
                console.print(f"📊 [cyan]Progress: {i + 1}/{len(month_ranges)} months processed[/cyan]")
    
    # Save results
    out_file = DATA_DIR / "fda_pma_by_month.json"
    console.print(f"\n💾 [green]Saving {len(all_results)} PMA records to {str(out_file)}...[/green]")
    
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)

    console.print(f"✅ [green]Saved {len(all_results)} PMA records[/green]")
    
    # Display summary
    display_summary(all_results)
    
    return all_results

def display_summary(results, title="FDA PMA Data Summary"):
    """Display a summary of the fetched data"""
    
    if not results:
        console.print("⚠️ [yellow]No results found[/yellow]")
        return
    
    # Extract key information
    devices = []
    date_range = {"min": None, "max": None}
    
    for result in results:
        try:
            device_name = result.get('trade_name', result.get('device_name', 'Unknown'))
            decision_date = result.get('decision_date', 'Unknown')
            decision_code = result.get('decision_code', 'Unknown')
            applicant = result.get('applicant', 'Unknown')
            pma_number = result.get('pma_number', 'Unknown')
            
            # Track date range
            if decision_date and decision_date != 'Unknown':
                if date_range["min"] is None or decision_date < date_range["min"]:
                    date_range["min"] = decision_date
                if date_range["max"] is None or decision_date > date_range["max"]:
                    date_range["max"] = decision_date
            
            if device_name and decision_date and decision_code == 'APPR':
                devices.append({
                    'device_name': device_name,
                    'approval_date': decision_date,
                    'applicant': applicant,
                    'pma_number': pma_number
                })
        except Exception:
            continue
    
    # Create summary table
    summary_table = Table(title=title, box=box.ROUNDED)
    summary_table.add_column("Metric", style="cyan", no_wrap=True)
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total API Results", str(len(results)))
    summary_table.add_row("Approved Devices", str(len(devices)))
    summary_table.add_row("Date Range", f"{date_range['min']} to {date_range['max']}" if date_range['min'] else "Unknown")
    summary_table.add_row("Output File", str(OUT_FILE))
    
    console.print(summary_table)
    
    # Show sample devices
    if devices:
        sample_table = Table(title="📋 Sample Approved Devices", box=box.ROUNDED)
        sample_table.add_column("Device Name", style="cyan", no_wrap=True)
        sample_table.add_column("Approval Date", style="green")
        sample_table.add_column("Applicant", style="blue")
        sample_table.add_column("PMA Number", style="yellow")
        
        for device in devices[:10]:  # Show first 10
            sample_table.add_row(
                device['device_name'][:40] + "..." if len(device['device_name']) > 40 else device['device_name'],
                device['approval_date'],
                device['applicant'][:30] + "..." if len(device['applicant']) > 30 else device['applicant'],
                device['pma_number']
            )
        
        console.print(sample_table)

def main():
    """Main function"""
    console.print("🚀 [bold blue]FDA PMA Data Fetcher (Fixed)[/bold blue]")
    console.print("Addressing server-side issues with proper pagination and rate limiting")
    
    try:
        # Fetch recent data (2014-2025)
        console.print("\n📡 [cyan]Step 1: Fetching recent FDA data (2014-2025)...[/cyan]")
        recent_results = fetch_fda_pma_fixed()
        
        # Fetch historical data (1990-2014)
        console.print("\n📡 [cyan]Step 2: Fetching historical FDA data (1990-2014)...[/cyan]")
        historical_results = fetch_historical_fda_data()
        
        # Combine all data
        console.print("\n🔗 [cyan]Step 3: Combining recent and historical data...[/cyan]")
        all_results = recent_results + historical_results
        
        # Improved deduplication logic
        console.print("🧹 [cyan]Removing duplicates with improved logic...[/cyan]")
        
        # Group by PMA number and keep the most relevant record for each device
        pma_groups = {}
        for result in all_results:
            pma_number = result.get('pma_number', '')
            if not pma_number:
                continue
                
            if pma_number not in pma_groups:
                pma_groups[pma_number] = []
            pma_groups[pma_number].append(result)
        
        # For each PMA number, select the best record based on priority
        unique_results = []
        for pma_number, records in pma_groups.items():
            if len(records) == 1:
                # Only one record, keep it
                unique_results.append(records[0])
            else:
                # Multiple records, select the best one
                best_record = _select_best_record(records)
                unique_results.append(best_record)
        
        console.print(f"📊 [cyan]Original records: {len(all_results)}[/cyan]")
        console.print(f"📊 [cyan]After deduplication: {len(unique_results)}[/cyan]")
        console.print(f"📊 [cyan]Removed duplicates: {len(all_results) - len(unique_results)}[/cyan]")
        
        # Save comprehensive dataset
        comprehensive_file = DATA_DIR / "fda_pma_comprehensive.json"
        console.print(f"\n💾 [green]Saving comprehensive dataset: {len(unique_results)} unique devices to {str(comprehensive_file)}...[/green]")
        
        with open(comprehensive_file, "w") as f:
            json.dump(unique_results, f, indent=2)
        
        console.print(f"✅ [green]Comprehensive FDA dataset saved![/green]")
        console.print(f"📊 [cyan]Total unique devices: {len(unique_results)}[/cyan]")
        
        # Display final comprehensive summary
        display_summary(unique_results, "Comprehensive FDA PMA Data (1990-2025)")
        
        return unique_results
        
    except KeyboardInterrupt:
        console.print("\n⚠️ [yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n❌ [red]Error: {e}[/red]")
    
def _select_best_record(records):
        """Select the best record from multiple records for the same PMA number"""
        
        # Priority order for decision codes
        decision_priority = {
            'APPR': 1,    # Approved - highest priority
            'OK30': 2,    # 30-day approval
            'APRL': 3,    # Released
            'APCB': 4,    # Conditional approval
            'APCV': 5,    # Conditional approval
            'APWD': 6,    # Withdrawn - lowest priority
        }
        
        # Sort records by priority
        def get_priority(record):
            decision_code = record.get('decision_code', '')
            return decision_priority.get(decision_code, 999)  # Unknown codes get lowest priority
        
        sorted_records = sorted(records, key=get_priority)
        
        # Return the record with highest priority (lowest number)
        return sorted_records[0]

if __name__ == "__main__":
    main() 