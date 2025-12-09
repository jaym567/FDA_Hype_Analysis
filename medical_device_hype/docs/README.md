# FDA Device Hype Analysis

This script analyzes the hype around new medical devices by cross-referencing FDA PMA database dates with PubMed publications and implementing Kleinberg burst detection to quantify and predict device hype.

## ✨ Features

- **🎨 Beautiful Terminal Output**: Rich, colorful, and informative terminal interface
- **🔍 OpenAlex API Integration**: Uses OpenAlex API to search for device-related publications
- **📅 FDA PMA Cross-referencing**: Analyzes publications within ±3 years of FDA approval dates
- **🚀 Kleinberg Burst Detection**: Implements the Kleinberg algorithm to detect citation bursts
- **📊 Hype Quantification**: Calculates comprehensive hype scores based on multiple metrics
- **🔮 Hype Prediction**: Predicts hype potential for new devices based on device characteristics
- **📈 Advanced Visualizations**: Generates comprehensive charts and graphs of analysis results
- **📋 Detailed Reporting**: Creates detailed analysis reports with key insights
- **⚡ Complete Analysis Pipeline**: Dedicated runner script for end-to-end analysis

## 🚀 Quick Start

### Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Set up OpenAlex API access:
   - Register at https://openalex.org/
   - Add your email to the script for higher rate limits

### Basic Usage

#### Option 1: Run the Complete Analysis Pipeline (Recommended)
```bash
# Run with default settings
python scripts/run_analysis.py

# Run with custom output directory
python scripts/run_analysis.py --output my_results

# Run with email for higher rate limits
python scripts/run_analysis.py --email your@email.com

# Run with minimal output
python scripts/run_analysis.py --quiet
```

#### Option 2: Run the Main Analysis Script
```bash
python src/fda_device_hype_analysis.py
```

#### Option 3: See the Beautiful Terminal Output Demo
```bash
python demo_output.py
```

## 📁 Scripts Overview

### 1. `run_analysis.py` - Complete Analysis Pipeline ⭐
**Recommended for most users**

- **Beautiful terminal interface** with progress bars and status indicators
- **Comprehensive analysis** of all FDA devices
- **Advanced visualizations** (9 different chart types)
- **Detailed statistics** with tables and summaries
- **Multiple output formats** (CSV, PNG, TXT)
- **Organized results** in dedicated output directory
- **Command-line options** for customization

**Features:**
- Progress tracking with time estimates
- Real-time status updates
- Color-coded results and statistics
- Professional-looking tables and panels
- Comprehensive error handling

### 2. `fda_device_hype_analysis.py` - Core Analysis Engine
**For developers and custom analysis**

- Core analysis functionality
- OpenAlex API integration
- Kleinberg burst detection algorithm
- Hype prediction model
- Basic visualizations

### 3. `demo_output.py` - Terminal Output Demo
**See the beautiful interface without API calls**

- Demonstrates the enhanced terminal output
- Shows all tables, progress bars, and formatting
- No internet connection required
- Perfect for understanding the interface

### 4. `example_usage.py` - Usage Examples
**Learn how to use the analyzer programmatically**

- 5 different use case examples
- Code snippets for custom analysis
- Demonstrates API usage patterns

### 5. `test_script.py` - Functionality Testing
**Validate the system works correctly**

- Tests core functionality
- Validates algorithms
- No API calls required

## 🎨 Terminal Output Features

The enhanced scripts provide a beautiful, professional terminal interface:

### Visual Elements
- **🎨 Color-coded output** with emojis and status indicators
- **📊 Professional tables** with borders and alignment
- **📈 Progress bars** with time estimates and descriptions
- **🔄 Spinning indicators** for long-running operations
- **📋 Status panels** with system information

### Information Display
- **System Status**: Shows API connectivity and data loading
- **Device Information**: Lists all FDA devices being analyzed
- **Progress Tracking**: Real-time updates on analysis progress
- **Results Tables**: Beautiful formatted results with status indicators
- **Statistics**: Comprehensive statistical summaries
- **Error Handling**: Clear error messages with suggestions

### Example Output
```
╔═══════════════════════════════════════════════════════════════════╗
║                    🔬 FDA Device Hype Analysis System             ║
║              Powered by OpenAlex API & Kleinberg Burst Detection  ║
╚═══════════════════════════════════════════════════════════════════╝

                         System Information                         
╭─────────────────┬───────────┬────────────────────────────────────╮
│ Component       │ Status    │ Details                            │
├─────────────────┼───────────┼────────────────────────────────────┤
│ OpenAlex API    │ ✅ Ready  │ Base URL: https://api.openalex.org │
│ FDA PMA Data    │ ✅ Loaded │ 10 sample devices                  │
│ Burst Detection │ ✅ Ready  │ Kleinberg algorithm implemented    │
│ Hype Prediction │ ✅ Ready  │ ML-based prediction model          │
╰─────────────────┴───────────┴────────────────────────────────────╯
```

## 📊 Output Files

The analysis generates several output files:

### From `run_analysis.py`:
- `analysis_results/` directory containing:
  - `fda_device_hype_summary.csv` - Summary data
  - `detailed_analysis_results.csv` - Detailed results
  - `analysis_statistics.txt` - Statistical report
  - `main_visualizations.png` - Main charts (4 plots)
  - `advanced_visualizations.png` - Advanced charts (9 plots)

### From `fda_device_hype_analysis.py`:
- `fda_device_hype_analysis.png` - Visualization charts
- `fda_device_hype_summary.csv` - Summary data in CSV format
- Console output with detailed analysis report

## 🔧 Custom Analysis

### Using the Core Analyzer
```python
from fda_device_hype_analysis import FDADeviceHypeAnalyzer

# Initialize analyzer
analyzer = FDADeviceHypeAnalyzer(openalex_email="your_email@example.com")

# Analyze a specific device
results = analyzer.analyze_device_hype("Da Vinci Surgical System", "2000-07-11")

# Run comprehensive analysis
all_results = analyzer.run_comprehensive_analysis()

# Generate visualizations
summary_df = analyzer.visualize_results(all_results)

# Generate report
report = analyzer.generate_report(all_results)

# Predict hype for a new device
new_device = {
    'device_type': 'Surgical Robot',
    'approval_year': 2024
}
predicted_hype = analyzer.predict_device_hype(new_device)
```

### Using the Analysis Runner
```python
from run_analysis import AnalysisRunner

# Create runner with custom settings
runner = AnalysisRunner(output_dir="my_results", email="your@email.com")

# Run complete pipeline
runner.run_complete_pipeline()

# Or run individual components
runner.setup_analysis()
results, summary_df = runner.run_comprehensive_analysis()
runner.generate_detailed_statistics()
runner.create_advanced_visualizations()
runner.save_results()
```

## 📈 Visualization Types

### Main Visualizations (4 plots):
1. **Hype Scores by Device** - Horizontal bar chart
2. **Publications vs Citations** - Scatter plot with hype coloring
3. **Device Type Analysis** - Average hype by device type
4. **Burst Distribution** - Pie chart of burst periods

### Advanced Visualizations (9 plots):
1. **Hype Score Distribution** - Histogram
2. **Publications vs Citations by Type** - Scatter plot with device types
3. **Hype Score by Device Type** - Box plot
4. **Burst Analysis** - Bar chart of burst counts
5. **Sustained Interest Analysis** - Pie chart
6. **Correlation Matrix** - Heatmap of correlations
7. **Hype Scores Over Time** - Scatter plot
8. **Citations per Publication** - Horizontal bar chart
9. **Performance Radar Chart** - Polar plot of average metrics

## 🏥 Sample FDA Devices

The system includes 10 major FDA-approved devices:

| Device | Type | Approval Date | Expected Hype |
|--------|------|---------------|---------------|
| Da Vinci Surgical System | Surgical Robot | 2000-07-11 | High |
| HeartMate II LVAD | Ventricular Assist | 2008-04-21 | Medium |
| CyberKnife System | Radiosurgery | 2001-08-22 | Medium |
| Intuitive Surgical System | Surgical Robot | 2000-07-11 | High |
| Medtronic Deep Brain Stimulation | Neuromodulation | 2003-01-14 | Medium |
| Boston Scientific Drug-Eluting Stent | Cardiovascular | 2003-04-24 | High |
| Edwards SAPIEN Transcatheter Valve | Cardiovascular | 2011-11-02 | High |
| Stryker Mako Robotic System | Surgical Robot | 2008-06-20 | High |
| Zimmer Biomet ROSA Knee System | Orthopedic | 2019-12-19 | Medium |
| Medtronic Guardian Sensor 3 | Diabetes Management | 2018-06-21 | Low |

## 📊 Methodology

### Hype Score Calculation

The hype score combines four weighted metrics:

1. **Total Publications** (30%): Number of publications related to the device
2. **Total Citations** (30%): Total citations received by device-related publications
3. **Average Citations** (20%): Average citations per publication
4. **Burst Periods** (20%): Number of citation burst periods detected

### Kleinberg Burst Detection

The script implements Kleinberg's burst detection algorithm to identify periods of unusually high citation activity. The algorithm:

- Uses a two-state hidden Markov model (normal vs. burst)
- Calculates optimal state transitions with cost parameter γ
- Identifies burst periods with start, end, and intensity metrics

### FDA Cross-referencing

The analysis focuses on publications within ±3 years of FDA approval dates to capture:

- Pre-approval research and development activity
- Post-approval clinical adoption and research
- Citation patterns that indicate device impact

## ⚙️ Configuration Options

### Command Line Arguments (`run_analysis.py`)
```bash
--output, -o    Output directory for results (default: analysis_results)
--email, -e     OpenAlex email for higher rate limits
--quiet, -q     Minimal output mode
```

### Analyzer Parameters
```python
# Initialize with custom settings
analyzer = FDADeviceHypeAnalyzer(
    openalex_email="your@email.com",  # Higher rate limits
    verbose=True                      # Beautiful output
)

# Custom search parameters
publications = analyzer.get_device_publications(
    device_name, 
    approval_date, 
    years_before=5,  # 5 years before
    years_after=5    # 5 years after
)
```

## 🔄 API Rate Limits

OpenAlex has rate limits:
- **Without email**: ~10 requests per second
- **With email**: ~100 requests per second

The script includes built-in rate limiting and error handling.

## 🛠️ Troubleshooting

### Common Issues

1. **API Connection Errors**: Check internet connection and API status
2. **Rate Limiting**: Add your email to the analyzer for higher limits
3. **No Results**: Verify device names match OpenAlex search terms
4. **Memory Issues**: Reduce the `per_page` parameter or add early stopping

### Debug Mode

Enable debug output by modifying the script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Quiet Mode

For minimal output, use the `--quiet` flag:
```bash
python scripts/run_analysis.py --quiet
```

## 🎯 Use Cases

### 1. Research Analysis
- Analyze historical device hype patterns
- Identify factors contributing to device success
- Study citation burst patterns in medical literature

### 2. Investment Decisions
- Predict hype potential for new devices
- Compare device categories for investment opportunities
- Identify emerging trends in medical technology

### 3. Regulatory Insights
- Understand post-approval research activity
- Analyze device adoption patterns
- Study the relationship between approval and research interest

### 4. Academic Research
- Study bibliometric patterns in medical device literature
- Analyze temporal trends in device research
- Investigate citation dynamics in medical technology

## 🔮 Future Enhancements

### Potential Improvements
1. **Real FDA Database Integration**: Replace sample data with actual FDA PMA database
2. **Advanced ML Models**: Train more sophisticated hype prediction models
3. **Additional Data Sources**: Integrate with PubMed, ClinicalTrials.gov, etc.
4. **Real-time Analysis**: Monitor ongoing device approvals
5. **Comparative Analysis**: Compare with non-FDA approved devices

### Scalability
- **Batch Processing**: Process multiple devices efficiently
- **Database Storage**: Store results in database for historical analysis
- **API Optimization**: Implement caching and rate limiting
- **Parallel Processing**: Multi-threaded API calls

## 📄 License

This script is provided as-is for research and educational purposes.

## 🤝 Contributing

To extend the functionality:

1. Add new device types to the prediction model
2. Implement additional burst detection algorithms
3. Add more visualization options
4. Integrate with other FDA databases
5. Enhance the terminal output with new features

## 📞 Support

For questions or issues:
1. Check the troubleshooting section
2. Review the example scripts
3. Test with the demo script first
4. Ensure all dependencies are installed 