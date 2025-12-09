# Quick Start Guide

## Prerequisites

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Ensure you have FDA data:**
   - The system will automatically check for data files in the `data/` directory
   - If no data is found, it will attempt to fetch from the FDA API

## Running the Analysis

### Option 1: Main Analysis Pipeline (Recommended)

Run the complete analysis pipeline with visualizations and statistics:

```bash
# From the project root directory
python scripts/run_analysis.py
```

**With options:**
```bash
# Custom output directory
python scripts/run_analysis.py --output my_results

# With email for higher API rate limits (recommended)
python scripts/run_analysis.py --email your@email.com

# Force refresh FDA data
python scripts/run_analysis.py --force-fetch

# Quiet mode (minimal output)
python scripts/run_analysis.py --quiet
```

### Option 2: Surgery-Specific Device Analysis

Analyze only surgical devices:

```python
from src.surgery_device_analysis import SurgeryDeviceAnalyzer

# Initialize analyzer
analyzer = SurgeryDeviceAnalyzer(
    openalex_email="your@email.com",  # Optional, for higher rate limits
    verbose=True
)

# Run comprehensive analysis
results = analyzer.run_surgical_device_hype_analysis()

# Save results
analyzer.save_surgery_analysis("output/surgery_analysis.json")
```

### Option 3: General FDA Device Hype Analysis

Analyze all FDA devices (not just surgical):

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from fda_device_hype_analysis import FDADeviceHypeAnalyzer

# Initialize analyzer
analyzer = FDADeviceHypeAnalyzer(
    openalex_email="your@email.com",  # Optional
    verbose=True
)

# Run comprehensive analysis
results = analyzer.run_comprehensive_analysis()

# Generate visualizations
summary_df = analyzer.visualize_results(results)

# Generate report
report = analyzer.generate_report(results)
```

### Option 4: Demo/Test Scripts

```bash
# See beautiful terminal output demo (no API calls)
python scripts/demo_output.py

# Run example usage scenarios
python scripts/example_usage.py

# Test basic functionality
python scripts/test_script.py
```

## Output Files

After running the analysis, results will be saved to:

- **Default location:** `output/` directory
- **Files generated:**
  - `fda_device_hype_summary.csv` - Summary of all devices
  - `detailed_analysis_results.csv` - Detailed analysis results
  - `analysis_statistics.txt` - Statistical summary
  - `main_visualizations.png` - Main charts (4 plots)
  - `advanced_visualizations.png` - Advanced charts (9 plots)

## Configuration

### Adjusting Surgical Device Filtering

Edit the configuration file to modify keywords:

```bash
# Open the config file
nano data/surgical_device_filter_config.json
# or
code data/surgical_device_filter_config.json
```

See `docs/CONFIGURATION.md` for detailed instructions.

### Using Custom Config

```python
analyzer = SurgeryDeviceAnalyzer(
    config_file="path/to/custom_config.json"
)
```

## Common Issues

### No FDA Data Found

If you see a warning about missing FDA data:

```bash
# Force fetch fresh data
python scripts/run_analysis.py --force-fetch
```

Or manually fetch:

```bash
python scripts/fetch_fda_pma_fixed.py
```

### API Rate Limiting

If you encounter rate limit errors:

1. Add your email for higher limits:
```bash
python scripts/run_analysis.py --email your@email.com
```

2. The system includes automatic rate limiting, but large datasets may take time

### Import Errors

Make sure you're running from the project root:

```bash
# Check you're in the right directory
pwd
# Should show: .../medical_device_hype

# Run from project root
python scripts/run_analysis.py
```

## Example Workflow

1. **First time setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Fetch FDA data (if needed)
python scripts/run_analysis.py --force-fetch --email your@email.com
```

2. **Run analysis:**
```bash
# Run complete analysis
python scripts/run_analysis.py --email your@email.com
```

3. **Check results:**
```bash
# View output files
ls -lh output/
cat output/analysis_statistics.txt
```

4. **Adjust filtering (optional):**
```bash
# Edit config file
nano data/surgical_device_filter_config.json

# Re-run analysis
python scripts/run_analysis.py
```

## Need Help?

- See `docs/README.md` for detailed documentation
- See `docs/CONFIGURATION.md` for keyword configuration
- See `docs/METHODS.md` for methodology details

