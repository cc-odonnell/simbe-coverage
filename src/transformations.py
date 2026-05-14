"""
Data transformations for coverage metrics pipeline.

Handles timestamp parsing, date filtering, data cleaning, and loading into DuckDB.
These transformations prepare raw data for coverage metric calculations.
"""

import duckdb
import pandas as pd

from src import config


# ============================================================================
# DUCKDB SETUP
# ============================================================================

def load_into_duckdb(df: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    """
    Load raw dataframe into DuckDB for SQL-based transformations.

    Args:
        df: Raw traversals dataframe from ingestion

    Returns:
        DuckDB connection with 'traversals' table loaded
    """
    print("\nLoading data into DuckDB...")

    con = duckdb.connect()
    con.execute("CREATE TABLE traversals AS SELECT * FROM df")

    row_count = con.execute("SELECT COUNT(*) FROM traversals").fetchone()[0]
    print(f"Loaded {row_count:,} records into DuckDB")

    return con


# ============================================================================
# TIMESTAMP PARSING
# ============================================================================

def parse_timestamps(con: duckdb.DuckDBPyConnection) -> None:
    """
    Parse traversal timestamps and add derived date/time columns.
    Uses DuckDB for efficient SQL-based transformations.

    Adds columns:
    - traversal_timestamp: Clean timestamp without timezone
    - traversal_date: Date only
    - traversal_time: Time only
    - traversal_hour: Hour (0-23)
    - traversal_day_of_week: Day of week (1=Monday, 7=Sunday)
    - traversal_day_name: Day name (Monday, Tuesday, etc.)

    Also labels null skip_reasons as 'no_reason_given' when scheduled=1 and visited=0.

    Args:
        con: DuckDB connection with 'traversals' table
    """
    print("\nParsing timestamps and cleaning data...")

    con.execute("""
        CREATE OR REPLACE TABLE traversals_clean AS
        SELECT 
            store_name,
            CAST(traversal_start_time AS TIMESTAMP) as traversal_timestamp,
            CAST(CAST(traversal_start_time AS TIMESTAMP) AS DATE) as traversal_date,
            CAST(CAST(traversal_start_time AS TIMESTAMP) AS TIME) as traversal_time,
            HOUR(CAST(traversal_start_time AS TIMESTAMP)) as traversal_hour,
            DAYOFWEEK(CAST(traversal_start_time AS TIMESTAMP)) as traversal_day_of_week,
            DAYNAME(CAST(traversal_start_time AS TIMESTAMP)) as traversal_day_name,
            waypoint_id,
            aisle,
            scene,
            x,
            y,
            scheduled,
            visited,
            CASE 
                WHEN scheduled = 1 AND visited = 0 AND skip_reason IS NULL 
                THEN 'no_reason_given'
                ELSE skip_reason
            END as skip_reason
        FROM traversals
    """)

    row_count = con.execute("SELECT COUNT(*) FROM traversals_clean").fetchone()[0]
    print(f"Parsed timestamps for {row_count:,} records")


# ============================================================================
# DATE FILTERING
# ============================================================================

def filter_date_range(con: duckdb.DuckDBPyConnection) -> None:
    """
    Filter traversals to configured date range.
    Uses config.START_DATE and config.END_DATE.

    Args:
        con: DuckDB connection with 'traversals_clean' table
    """
    print(f"\nFiltering to date range: {config.START_DATE} to {config.END_DATE}")

    con.execute(f"""
        CREATE OR REPLACE TABLE traversals_clean AS
        SELECT *
        FROM traversals_clean
        WHERE traversal_date BETWEEN '{config.START_DATE}' AND '{config.END_DATE}'
    """)

    row_count = con.execute("SELECT COUNT(*) FROM traversals_clean").fetchone()[0]
    print(f"Filtered to {row_count:,} records in date range")


# ============================================================================
# OPTIONAL: SCHEDULED WAYPOINTS ONLY
# ============================================================================

def filter_scheduled_only(con: duckdb.DuckDBPyConnection) -> None:
    """
    Filter to scheduled waypoints only if configured.
    Uses config.SCHEDULED_ONLY flag.

    Args:
        con: DuckDB connection with 'traversals_clean' table
    """
    if config.SCHEDULED_ONLY:
        print("\nFiltering to scheduled waypoints only...")

        con.execute("""
            CREATE OR REPLACE TABLE traversals_clean AS
            SELECT *
            FROM traversals_clean
            WHERE scheduled = 1
        """)

        row_count = con.execute("SELECT COUNT(*) FROM traversals_clean").fetchone()[0]
        print(f"Filtered to {row_count:,} scheduled waypoints")
    else:
        print("\nKeeping all waypoints (scheduled and unscheduled)")


# ============================================================================
# MAIN TRANSFORMATION PIPELINE
# ============================================================================

def transform_data(df: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    """
    Main transformation pipeline: load into DuckDB, parse timestamps, filter.

    Args:
        df: Raw dataframe from ingestion (already validated)

    Returns:
        DuckDB connection with 'traversals_clean' table ready for metrics
    """
    print("=" * 80)
    print("STARTING DATA TRANSFORMATIONS")
    print("=" * 80)

    # Load into DuckDB
    con = load_into_duckdb(df)

    # Parse timestamps and clean data
    parse_timestamps(con)

    # Filter date range
    filter_date_range(con)

    # Filter scheduled only (optional)
    filter_scheduled_only(con)

    # Summary
    print("\n" + "=" * 80)
    print("DATA TRANSFORMATIONS COMPLETE")
    print("=" * 80)

    summary = con.execute("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT store_name) as stores,
            MIN(traversal_date) as start_date,
            MAX(traversal_date) as end_date,
            COUNT(DISTINCT traversal_date) as unique_dates,
            COUNT(DISTINCT scene) as unique_scenes
        FROM traversals_clean
    """).df()

    print("\nTransformed data summary:")
    print(summary.to_string(index=False))

    return con


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    from src.ingestion import ingest_data

    print("Testing transformations independently...")

    # Ingest raw data
    df = ingest_data()

    # Transform
    con = transform_data(df)

    # Show sample
    print("\nSample of transformed data:")
    sample = con.execute("SELECT * FROM traversals_clean LIMIT 5").df()
    print(sample.to_string(index=False))

    # Show date/time columns
    print("\nDate/time columns sample:")
    sample_dates = con.execute("""
        SELECT DISTINCT
            traversal_date,
            traversal_hour,
            traversal_day_of_week,
            traversal_day_name
        FROM traversals_clean
        ORDER BY traversal_date
        LIMIT 5
    """).df()
    print(sample_dates.to_string(index=False))