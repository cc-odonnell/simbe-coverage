"""
Main pipeline orchestration for coverage metrics calculation.

Coordinates the full data pipeline from ingestion through visualization:
1. Ingest raw data
2. Validate raw data (Pydantic + assertions)
3. Transform data (timestamp parsing, filtering)
4. Validate transformed data (Pydantic + assertions)
5. Calculate coverage metrics
6. Save dataset outputs (saved as parquet files in output folder)
7. Generate visualizations (saved as png in output folder)

This is the entry point for running the complete pipeline.
"""

import sys
from pathlib import Path

from src import config
from src.ingestion import ingest_data
from src.transformations import transform_data
from src.coverage_metrics import calculate_all_metrics

from tests.data_type_checks import validate_traversals_schema
from tests.assertions_raw import run_all_raw_data_tests
from tests.assertions_transformed import run_all_transformed_tests


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

def run_pipeline() -> dict:
    """
    Execute the complete coverage metrics pipeline.

    Returns:
        Dictionary with pipeline outputs and status
    """
    print("=" * 80)
    print("STARTING COVERAGE METRICS PIPELINE")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Date range: {config.START_DATE} to {config.END_DATE}")
    print(f"  Scheduled only: {config.SCHEDULED_ONLY}")
    print(f"  Output directory: {config.OUTPUT_DIR}")

    # ========================================================================
    # STAGE 1: INGESTION
    # ========================================================================

    print("\n" + "=" * 80)
    print("STAGE 1: DATA INGESTION")
    print("=" * 80)

    try:
        df_raw = ingest_data()
    except Exception as e:
        print(f"\nERROR in ingestion: {e}")
        sys.exit(1)

    # ========================================================================
    # STAGE 2: RAW DATA VALIDATION
    # ========================================================================

    print("\n" + "=" * 80)
    print("STAGE 2: RAW DATA VALIDATION")
    print("=" * 80)

    # Pydantic validation
    pydantic_results = validate_traversals_schema(df_raw, sample_size=1000)

    if pydantic_results['invalid'] > 0:
        print(f"\nWARNING: {pydantic_results['invalid']} Pydantic validation errors")
        print("Review errors above. Proceeding with pipeline...")

    # Assertion tests
    assertion_results = run_all_raw_data_tests(df_raw)

    if not assertion_results['all_passed']:
        print("\nERROR: Raw data assertion tests failed")
        print("Pipeline cannot proceed with data quality issues")
        sys.exit(1)

    # ========================================================================
    # STAGE 3: TRANSFORMATION
    # ========================================================================

    print("\n" + "=" * 80)
    print("STAGE 3: DATA TRANSFORMATION")
    print("=" * 80)

    try:
        con = transform_data(df_raw)
    except Exception as e:
        print(f"\nERROR in transformation: {e}")
        sys.exit(1)

    # ========================================================================
    # STAGE 4: TRANSFORMED DATA VALIDATION
    # ========================================================================

    print("\n" + "=" * 80)
    print("STAGE 4: TRANSFORMED DATA VALIDATION")
    print("=" * 80)

    transformed_results = run_all_transformed_tests(con)

    if not transformed_results['all_passed']:
        print("\nERROR: Transformed data validation failed")
        print("Pipeline cannot proceed with transformation issues")
        sys.exit(1)

    # ========================================================================
    # STAGE 5: COVERAGE METRICS CALCULATION
    # ========================================================================

    print("\n" + "=" * 80)
    print("STAGE 5: COVERAGE METRICS CALCULATION")
    print("=" * 80)

    try:
        metrics = calculate_all_metrics(con)
    except Exception as e:
        print(f"\nERROR in metrics calculation: {e}")
        sys.exit(1)

    # ========================================================================
    # STAGE 6: SAVE OUTPUTS
    # ========================================================================

    print("\n" + "=" * 80)
    print("STAGE 6: SAVING OUTPUTS")
    print("=" * 80)

    try:
        # Ensure output directory exists
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Save scene coverage
        print(f"\nSaving scene coverage to: {config.SCENE_COVERAGE_OUTPUT}")
        metrics['scene_coverage'].to_csv(config.SCENE_COVERAGE_OUTPUT, index=False)
        print(f"Saved {len(metrics['scene_coverage']):,} records")

        # Save skip attribution
        print(f"\nSaving skip attribution to: {config.SKIP_ATTRIBUTION_OUTPUT}")
        metrics['skip_attribution'].to_csv(config.SKIP_ATTRIBUTION_OUTPUT, index=False)
        print(f"Saved {len(metrics['skip_attribution']):,} records")

    except Exception as e:
        print(f"\nERROR saving outputs: {e}")
        sys.exit(1)

    # ========================================================================
    # STAGE 7: GENERATE VISUALIZATIONS
    # ========================================================================

    print("\n" + "=" * 80)
    print("STAGE 7: GENERATING VISUALIZATIONS")
    print("=" * 80)

    try:
        # Import here to avoid loading matplotlib unless needed
        sys.path.append(str(config.PROJECT_ROOT / "output"))
        from visualizations import generate_all_visualizations

        # Get traversals data for heatmap
        traversals_df = con.execute("SELECT * FROM traversals_clean").df()

        # Generate visualizations
        generate_all_visualizations(
            coverage_df=metrics['scene_coverage'],
            skip_df=metrics['skip_attribution'],
            traversals_df=traversals_df
        )

    except Exception as e:
        print(f"\nWARNING: Visualization generation failed: {e}")
        print("Pipeline outputs are still valid, but visualizations were not created")

    # ========================================================================
    # PIPELINE COMPLETE
    # ========================================================================

    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION COMPLETE")
    print("=" * 80)

    print("\nPipeline Summary:")
    print(f"  Raw records ingested: {len(df_raw):,}")
    print(f"  Transformed records: {con.execute('SELECT COUNT(*) FROM traversals_clean').fetchone()[0]:,}")
    print(f"  Scene coverage records: {len(metrics['scene_coverage']):,}")
    print(f"  Skip attribution records: {len(metrics['skip_attribution']):,}")

    print("\nOutputs saved to:")
    print(f"  {config.SCENE_COVERAGE_OUTPUT}")
    print(f"  {config.SKIP_ATTRIBUTION_OUTPUT}")
    print(f"  Visualizations: {config.OUTPUT_DIR}/*.png")

    print("\nPipeline executed successfully")

    return {
        'status': 'success',
        'metrics': metrics,
        'record_counts': {
            'raw': len(df_raw),
            'transformed': con.execute('SELECT COUNT(*) FROM traversals_clean').fetchone()[0],
            'scene_coverage': len(metrics['scene_coverage']),
            'skip_attribution': len(metrics['skip_attribution'])
        }
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        result = run_pipeline()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nPipeline failed with unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)