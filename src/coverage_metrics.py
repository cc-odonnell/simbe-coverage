"""
Coverage metrics calculation - business logic.

Calculates scene-level physical coverage metric:
- Numerator: Scenes with at least one visited waypoint
- Denominator: Total unique scenes (with scheduled waypoints)
- Output: Daily coverage percentage by store

Also generates skip attribution analysis showing why waypoints were not visited.
"""

import duckdb
import pandas as pd

from src import config


# ============================================================================
# SCENE-LEVEL COVERAGE CALCULATION
# ============================================================================

def calculate_scene_coverage(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Calculate scene-level physical coverage by store and date.

    Coverage Definition:
    - Numerator: Count of scenes with at least one visited waypoint
    - Denominator: Count of total unique scenes
    - Calculated per store per date

    Args:
        con: DuckDB connection with 'traversals_clean' table

    Returns:
        DataFrame with columns: store_name, traversal_date, total_scenes,
                                scenes_covered, coverage_pct
    """
    print("\nCalculating scene-level coverage...")

    query = """
        CREATE OR REPLACE TABLE scene_coverage AS
        SELECT 
            store_name,
            traversal_date,

            -- Total unique scenes
            COUNT(DISTINCT scene) as total_scenes,

            -- Scenes with at least one visited waypoint
            COUNT(DISTINCT CASE WHEN visited = 1 THEN scene END) as scenes_covered,

            -- Coverage percentage
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN visited = 1 THEN scene END) / 
                  NULLIF(COUNT(DISTINCT scene), 0), 2) as coverage_pct

        FROM traversals_clean
        GROUP BY store_name, traversal_date
        ORDER BY store_name, traversal_date
    """

    con.execute(query)

    # Return as DataFrame
    df = con.execute("SELECT * FROM scene_coverage").df()

    print(f"Calculated coverage for {len(df):,} store-days")

    return df


# ============================================================================
# SKIP ATTRIBUTION ANALYSIS
# ============================================================================

def calculate_skip_attribution(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Calculate skip reason attribution by store and date.

    Shows breakdown of why waypoints were not visited:
    - Count and percentage of each skip reason
    - Helps identify operational issues

    Args:
        con: DuckDB connection with 'traversals_clean' table

    Returns:
        DataFrame with columns: store_name, traversal_date, skip_reason,
                                skip_count, total_skips, skip_pct
    """
    print("\nCalculating skip attribution...")

    query = """
        CREATE OR REPLACE TABLE skip_attribution AS
        WITH skipped_waypoints AS (
            SELECT 
                store_name,
                traversal_date,
                skip_reason,
                COUNT(*) as skip_count
            FROM traversals_clean
            WHERE visited = 0
            GROUP BY store_name, traversal_date, skip_reason
        ),
        daily_totals AS (
            SELECT 
                store_name,
                traversal_date,
                SUM(skip_count) as total_skips
            FROM skipped_waypoints
            GROUP BY store_name, traversal_date
        )
        SELECT 
            s.store_name,
            s.traversal_date,
            s.skip_reason,
            s.skip_count,
            d.total_skips,
            ROUND(100.0 * s.skip_count / NULLIF(d.total_skips, 0), 2) as skip_pct
        FROM skipped_waypoints s
        INNER JOIN daily_totals d
            ON s.store_name = d.store_name
            AND s.traversal_date = d.traversal_date
        ORDER BY s.store_name, s.traversal_date, s.skip_count DESC
    """

    con.execute(query)

    # Return as DataFrame
    df = con.execute("SELECT * FROM skip_attribution").df()

    print(f"Calculated skip attribution for {len(df):,} store-day-reason combinations")

    return df


# ============================================================================
# MAIN METRICS CALCULATION
# ============================================================================

def calculate_all_metrics(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Calculate all coverage metrics.

    Args:
        con: DuckDB connection with 'traversals_clean' table

    Returns:
        Dictionary with DataFrames: 'scene_coverage' and 'skip_attribution'
    """
    print("=" * 80)
    print("CALCULATING COVERAGE METRICS")
    print("=" * 80)

    # Calculate scene coverage
    scene_coverage_df = calculate_scene_coverage(con)

    # Calculate skip attribution
    skip_attribution_df = calculate_skip_attribution(con)

    # Summary
    print("\n" + "=" * 80)
    print("METRICS CALCULATION COMPLETE")
    print("=" * 80)

    print(f"\nScene coverage:")
    print(f"  Records: {len(scene_coverage_df):,}")
    print(f"  Date range: {scene_coverage_df['traversal_date'].min()} to {scene_coverage_df['traversal_date'].max()}")
    print(f"  Avg coverage: {scene_coverage_df['coverage_pct'].mean():.2f}%")

    print(f"\nSkip attribution:")
    print(f"  Records: {len(skip_attribution_df):,}")
    print(f"  Unique skip reasons: {skip_attribution_df['skip_reason'].nunique()}")

    return {
        'scene_coverage': scene_coverage_df,
        'skip_attribution': skip_attribution_df
    }


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    from src.ingestion import ingest_data
    from src.transformations import transform_data

    print("Testing coverage metrics calculation...")

    # Ingest and transform
    df = ingest_data()
    con = transform_data(df)

    # Calculate metrics
    metrics = calculate_all_metrics(con)

    # Show samples
    print("\nScene coverage sample:")
    print(metrics['scene_coverage'].head(10).to_string(index=False))

    print("\nSkip attribution sample:")
    print(metrics['skip_attribution'].head(10).to_string(index=False))

