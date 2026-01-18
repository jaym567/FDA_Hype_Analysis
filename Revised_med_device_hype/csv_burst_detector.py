"""
CSV Interface for Kleinberg Burst Detection
Handles CSV reading, preprocessing, and data extraction
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
import warnings

# Import the core algorithm
try:
    from kleinberg_burst import KleinbergBurstDetector, normalize_timestamps
except ImportError:
    # Fallback for when files are in same directory
    class KleinbergBurstDetector:
        def __init__(self, s=2, gamma=1.0):
            pass
    normalize_timestamps = lambda x: x


class CSVBurstDetector:
    """
    Interface for loading CSV data and running burst detection.
    
    This class handles:
    1. Reading CSV files with various timestamp formats
    2. Preprocessing and cleaning temporal data
    3. Extracting timestamps for burst detection
    4. Running Kleinberg algorithm
    5. Exporting results
    """
    
    def __init__(self, csv_path: Optional[str] = None, dataframe: Optional[pd.DataFrame] = None):
        """
        Initialize CSV burst detector.
        
        Args:
            csv_path: Path to CSV file (optional if dataframe provided)
            dataframe: Pandas DataFrame (optional if csv_path provided)
        """
        if csv_path is None and dataframe is None:
            raise ValueError("Either csv_path or dataframe must be provided")
        
        self.csv_path = csv_path
        self.dataframe = dataframe
        self.loaded_data = None
        
        # Default configuration
        self.config = {
            'timestamp_column': 'timestamp',
            'datetime_format': None,  # Auto-detect
            'timezone': 'UTC',
            'drop_duplicates': True,
            'sort_by_time': True,
            'normalize_time': False,  # Shift timestamps to start at 0
            'filter_expression': None,  # e.g., "status == 'active'"
            'min_time': None,
            'max_time': None,
            'event_weight_column': None,
            'aggregation_method': 'direct'  # 'direct', 'uniform', 'middle'
        }
    
    def configure(self, **kwargs) -> 'CSVBurstDetector':
        """
        Configure the detector parameters.
        
        Returns:
            self for method chaining
        """
        self.config.update(kwargs)
        return self
    
    def load_data(self) -> pd.DataFrame:
        """
        Load and preprocess the CSV data.
        
        Returns:
            Cleaned pandas DataFrame
        """
        # Load data if not already loaded
        if self.loaded_data is not None:
            return self.loaded_data
        
        if self.dataframe is not None:
            df = self.dataframe.copy()
        else:
            df = pd.read_csv(self.csv_path)
        
        # Store original for reference
        self.original_data = df.copy()
        
        # Parse timestamps
        df = self._parse_timestamps(df)
        
        # Apply filters
        df = self._apply_filters(df)
        
        # Sort and deduplicate
        if self.config['drop_duplicates']:
            df = df.drop_duplicates(subset=[self.config['timestamp_column'] + '_parsed'])
        
        if self.config['sort_by_time']:
            df = df.sort_values(self.config['timestamp_column'] + '_parsed')
        
        # Store cleaned data
        self.loaded_data = df
        return df
    
    def _parse_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse timestamp column to datetime."""
        timestamp_col = self.config['timestamp_column']
        
        if timestamp_col not in df.columns:
            raise ValueError(f"Timestamp column '{timestamp_col}' not found in data. "
                           f"Available columns: {list(df.columns)}")
        
        parsed_col = timestamp_col + '_parsed'
        
        try:
            # Try to parse with given format or auto-detect
            df[parsed_col] = pd.to_datetime(
                df[timestamp_col], 
                format=self.config['datetime_format'],
                errors='coerce'
            )
            
            # Check for parsing failures
            failed_count = df[parsed_col].isna().sum()
            if failed_count > 0:
                warnings.warn(f"Failed to parse {failed_count} timestamps. They will be dropped.")
                df = df.dropna(subset=[parsed_col])
            
            # Handle timezone
            if self.config['timezone']:
                if df[parsed_col].dt.tz is None:
                    df[parsed_col] = df[parsed_col].dt.tz_localize(self.config['timezone'])
                else:
                    df[parsed_col] = df[parsed_col].dt.tz_convert(self.config['timezone'])
            
        except Exception as e:
            raise ValueError(f"Failed to parse timestamps: {str(e)}")
        
        return df
    
    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply time and expression filters."""
        parsed_col = self.config['timestamp_column'] + '_parsed'
        
        # Time range filters
        if self.config['min_time']:
            min_time = pd.to_datetime(self.config['min_time'])
            df = df[df[parsed_col] >= min_time]
        
        if self.config['max_time']:
            max_time = pd.to_datetime(self.config['max_time'])
            df = df[df[parsed_col] <= max_time]
        
        # Expression filter
        if self.config['filter_expression']:
            try:
                df = df.query(self.config['filter_expression'])
            except Exception as e:
                warnings.warn(f"Failed to apply filter expression: {str(e)}")
        
        return df
    
    def extract_timestamps(self, method: Optional[str] = None) -> List[float]:
        """
        Extract timestamps for burst detection.
        
        Args:
            method: Extraction method ('direct', 'uniform', 'middle')
                - 'direct': Use event timestamps directly
                - 'uniform': For aggregated data, distribute events uniformly
                - 'middle': For aggregated data, place events at middle of period
        
        Returns:
            List of timestamps as float (Unix time)
        """
        df = self.load_data()
        parsed_col = self.config['timestamp_column'] + '_parsed'
        method = method or self.config['aggregation_method']
        
        # Convert to Unix timestamps (seconds since epoch)
        base_timestamps = df[parsed_col].astype('int64') // 10**9
        base_timestamps = base_timestamps.astype(float).tolist()
        
        # Handle weighted events
        weight_col = self.config.get('event_weight_column')
        if weight_col and weight_col in df.columns:
            return self._apply_weights(df, weight_col, base_timestamps, method)
        
        # Normalize if requested
        if self.config['normalize_time']:
            base_timestamps = normalize_timestamps(base_timestamps)
        
        return base_timestamps
    
    def _apply_weights(self, df: pd.DataFrame, weight_col: str, 
                      base_timestamps: List[float], method: str) -> List[float]:
        """Apply event weights to timestamps."""
        weighted_timestamps = []
        
        for idx, (timestamp, weight) in enumerate(zip(base_timestamps, df[weight_col])):
            try:
                weight_val = float(weight)
                if weight_val <= 0:
                    continue
                    
                if method == 'direct':
                    # Repeat timestamp weight times
                    for _ in range(int(weight_val)):
                        weighted_timestamps.append(timestamp)
                        
                elif method == 'uniform' and idx < len(base_timestamps) - 1:
                    # Distribute weighted events uniformly to next timestamp
                    next_ts = base_timestamps[idx + 1]
                    interval = next_ts - timestamp
                    
                    for i in range(int(weight_val)):
                        event_time = timestamp + (i / weight_val) * interval
                        weighted_timestamps.append(event_time)
                        
                elif method == 'middle':
                    # Place all weighted events at middle of period
                    # (requires knowing period length, which we don't have)
                    # For now, use direct method with warning
                    warnings.warn("'middle' method not implemented for weighted events. Using 'direct'.")
                    for _ in range(int(weight_val)):
                        weighted_timestamps.append(timestamp)
                        
            except (ValueError, TypeError):
                continue
        
        return weighted_timestamps
    
    def detect_bursts(self, s: float = 2, gamma: float = 1.0, k: int = 3, 
                     **detector_kwargs) -> Dict[str, Any]:
        """
        Run Kleinberg burst detection on the CSV data.
        
        Args:
            s: State multiplier (s > 1)
            gamma: Transition cost parameter
            k: Number of states
            **detector_kwargs: Additional arguments for KleinbergBurstDetector
        
        Returns:
            Dictionary with burst results and metadata
        """
        # Extract timestamps
        timestamps = self.extract_timestamps()
        
        if len(timestamps) < 2:
            warnings.warn(f"Only {len(timestamps)} timestamps extracted. Need at least 2 for burst detection.")
            return {"bursts": [], "num_events": len(timestamps), "error": "insufficient_data"}
        
        # Create detector and run algorithm
        detector = KleinbergBurstDetector(s=s, gamma=gamma, **detector_kwargs)
        results = detector.detect_bursts(timestamps, k=k)
        
        # Add CSV metadata
        results['csv_metadata'] = {
            'source_file': self.csv_path,
            'num_rows_original': len(self.original_data) if hasattr(self, 'original_data') else None,
            'num_rows_processed': len(self.loaded_data) if self.loaded_data is not None else None,
            'config': self.config.copy(),
            'extraction_method': self.config['aggregation_method']
        }
        
        return results
    
    def bursts_to_dataframe(self, burst_results: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert burst results to pandas DataFrame for analysis.
        
        Args:
            burst_results: Results from detect_bursts()
            
        Returns:
            DataFrame with burst information
        """
        bursts = burst_results.get('bursts', [])
        
        if not bursts:
            return pd.DataFrame(columns=['start_time', 'end_time', 'state', 
                                        'num_events', 'duration', 'intensity'])
        
        # Create DataFrame
        burst_df = pd.DataFrame(bursts)
        
        # Convert Unix timestamps to datetime
        if 'start_time' in burst_df.columns:
            burst_df['start_datetime'] = pd.to_datetime(burst_df['start_time'], unit='s')
            burst_df['end_datetime'] = pd.to_datetime(burst_df['end_time'], unit='s')
            
            # Ensure timezone if original data had it
            if self.loaded_data is not None:
                parsed_col = self.config['timestamp_column'] + '_parsed'
                if self.loaded_data[parsed_col].dt.tz is not None:
                    tz = self.loaded_data[parsed_col].dt.tz
                    burst_df['start_datetime'] = burst_df['start_datetime'].dt.tz_localize('UTC').dt.tz_convert(tz)
                    burst_df['end_datetime'] = burst_df['end_datetime'].dt.tz_localize('UTC').dt.tz_convert(tz)
        
        # Reorder columns for readability
        preferred_order = ['start_datetime', 'end_datetime', 'start_time', 'end_time',
                          'duration', 'state', 'intensity', 'num_events',
                          'start_index', 'end_index']
        
        # Keep only columns that exist
        columns = [col for col in preferred_order if col in burst_df.columns]
        columns += [col for col in burst_df.columns if col not in preferred_order]
        
        return burst_df[columns]
    
    def export_results(self, burst_results: Dict[str, Any], 
                       output_path: str = 'burst_results.csv') -> None:
        """
        Export burst results to CSV file.
        
        Args:
            burst_results: Results from detect_bursts()
            output_path: Path for output CSV
        """
        burst_df = self.bursts_to_dataframe(burst_results)
        
        if not burst_df.empty:
            burst_df.to_csv(output_path, index=False)
            print(f"Burst results exported to {output_path}")
        else:
            print("No bursts to export")
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of the loaded data.
        
        Returns:
            Dictionary with data statistics
        """
        df = self.load_data()
        parsed_col = self.config['timestamp_column'] + '_parsed'
        
        if df.empty:
            return {"message": "No data loaded"}
        
        # Convert to Unix timestamps for calculations
        timestamps = df[parsed_col].astype('int64') // 10**9
        
        summary = {
            "total_events": len(df),
            "time_range": {
                "start": df[parsed_col].min(),
                "end": df[parsed_col].max()
            },
            "duration_seconds": float(timestamps.max() - timestamps.min()),
            "avg_event_rate": len(df) / max(1, (timestamps.max() - timestamps.min())),
            "columns": list(df.columns),
            "sample_timestamps": timestamps.head(5).tolist()
        }
        
        return summary


# Utility functions for CSV processing
def create_sample_csv(output_path: str = 'sample_events.csv') -> None:
    """
    Create a sample CSV file for testing.
    
    Args:
        output_path: Path to save the sample CSV
    """
    import numpy as np
    from datetime import datetime, timedelta
    
    # Generate sample data
    np.random.seed(42)
    base_time = datetime(2024, 1, 1)
    
    data = []
    current_time = base_time
    
    # Quiet period
    for _ in range(20):
        current_time += timedelta(seconds=np.random.exponential(300))  # ~5 minutes average
        data.append({
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': np.random.choice(['user1', 'user2', 'user3']),
            'event_type': np.random.choice(['click', 'view', 'hover']),
            'duration': np.random.exponential(2)
        })
    
    # Burst period
    for _ in range(15):
        current_time += timedelta(seconds=np.random.exponential(30))  # 30 seconds average
        data.append({
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': 'user2',  # Specific user during burst
            'event_type': 'click',
            'duration': np.random.exponential(5)
        })
    
    # Another quiet period
    for _ in range(25):
        current_time += timedelta(seconds=np.random.exponential(600))  # ~10 minutes average
        data.append({
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': np.random.choice(['user1', 'user3', 'user4']),
            'event_type': np.random.choice(['click', 'view']),
            'duration': np.random.exponential(1)
        })
    
    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Sample CSV created at {output_path}")


def validate_csv_structure(file_path: str) -> Dict[str, Any]:
    """
    Validate CSV structure for burst detection.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Dictionary with validation results
    """
    try:
        df = pd.read_csv(file_path, nrows=1000)  # Read first 1000 rows
        
        validation = {
            "file_exists": True,
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "columns": list(df.columns),
            "has_timestamp": False,
            "timestamp_candidates": [],
            "sample_data": df.head(3).to_dict('records')
        }
        
        # Look for timestamp-like columns
        timestamp_patterns = ['time', 'date', 'timestamp', 'datetime', 'created', 'ts']
        for col in df.columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in timestamp_patterns):
                validation['timestamp_candidates'].append(col)
                validation['has_timestamp'] = True
        
        return validation
        
    except Exception as e:
        return {"file_exists": False, "error": str(e)}