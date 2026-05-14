"""
Data ingestion module - handles loading raw data from CSV files.
Performs minimal validation (file existence, basic structure).
Returns raw DataFrames for downstream validation and processing.
"""

import pandas as pd
from pathlib import Path

from src import config


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_traversals() -> pd.DataFrame:
    """
    Load traversals data from CSV file.
    Performs basic structural checks only - detailed validation happens in tests/.

    Returns:
        Raw traversals dataframe

    Raises:
        FileNotFoundError: If traversals file doesn't exist
        ValueError: If file is empty or missing required columns
    """
    print(f"\nLoading traversals from: {config.TRAVERSALS_FILE}")

    # Check file exists
    if not config.TRAVERSALS_FILE.exists():
        raise FileNotFoundError(f"Traversals file not found: {config.TRAVERSALS_FILE}")

    # Load CSV
    df = pd.read_csv(config.TRAVERSALS_FILE)

    # Basic checks
    if len(df) == 0:
        raise ValueError("Traversals file is empty (0 rows)")

    # Check required columns exist
    required_columns = [
        'store_name', 'traversal_start_time', 'waypoint_id',
        'aisle', 'scene', 'x', 'y', 'scheduled', 'visited', 'skip_reason'
    ]

    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    print(f"✓ Loaded {len(df):,} traversal records")
    print(f"✓ Columns: {list(df.columns)}")
    print(f"✓ Date range: {df['traversal_start_time'].min()} to {df['traversal_start_time'].max()}")

    return df


# ============================================================================
# MAIN INGESTION FUNCTION
# ============================================================================

def ingest_data() -> pd.DataFrame:
    """
    Main ingestion function: load raw data and return for validation/processing.

    Returns:
        Raw traversals dataframe
    """
    print("=" * 80)
    print("STARTING DATA INGESTION")
    print("=" * 80)

    df = load_traversals()

    print("\n" + "=" * 80)
    print("DATA INGESTION COMPLETE")
    print("=" * 80)
    print(f"→ Loaded {len(df):,} records")
    print("→ Ready for validation (see tests/)")

    return df


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Test ingestion independently
    df = ingest_data()

    # Show sample
    print("\nSample of raw data:")
    print(df.head().to_string(index=False))

    print("\nData types:")
    print(df.dtypes)