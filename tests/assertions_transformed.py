"""
Data type checks and assertion tests for transformed data.

This file combines Pydantic-style type validation with SQL-based assertion tests.

Note: In a production pipeline, these would be separated:
- Pydantic models would live in separate YAML files (e.g., data_type_check_transformed.yml)
- Assertion tests would migrate to dbt tests with .yml schema definitions
For this case study, they are combined here to keep the file structure simple.
"""

import duckdb
import pandas as pd
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime, date, time
from jinja2 import Template

from src import config


# ============================================================================
# PYDANTIC DATA TYPE CHECKS
# ============================================================================


class TransformedColumnsRecord(BaseModel):
    """
    Schema validation for columns created or modified by transformations.
    Only validates new/transformed fields, not original fields already validated.
    """
    traversal_timestamp: datetime = Field(
        ...,
        description="Clean timestamp (parsed from string)"
    )
    traversal_date: date = Field(
        ...,
        description="Date only"
    )
    traversal_time: time = Field(
        ...,
        description="Time only"
    )
    traversal_hour: int = Field(
        ...,
        ge=0,
        le=23,
        description="Hour (0-23)"
    )
    traversal_day_of_week: int = Field(
        ...,
        ge=1,
        le=7,
        description="Day of week (1-7)"
    )
    traversal_day_name: str = Field(
        ...,
        min_length=1,
        description="Day name"
    )



def validate_transformed_schema(con: duckdb.DuckDBPyConnection, sample_size: int = 1000) -> dict:
    """
    Validate transformed data against Pydantic schema.
    Only validates new/modified columns created by transformation.

    Args:
        con: DuckDB connection with 'traversals_clean' table
        sample_size: Number of rows to validate

    Returns:
        Dictionary with validation results
    """
    print("\n" + "=" * 80)
    print("PYDANTIC DATA TYPE VALIDATION (TRANSFORMED DATA)")
    print("=" * 80)

    # Extract sample to DataFrame
    df = con.execute(f"SELECT * FROM traversals_clean LIMIT {sample_size}").df()

    print(f"\nValidating schema (sample size: {len(df):,})...")

    valid_count = 0
    error_count = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            # Only validate transformed columns
            TransformedColumnsRecord(**{
                'traversal_timestamp': row['traversal_timestamp'],
                'traversal_date': row['traversal_date'],
                'traversal_time': row['traversal_time'],
                'traversal_hour': row['traversal_hour'],
                'traversal_day_of_week': row['traversal_day_of_week'],
                'traversal_day_name': row['traversal_day_name']
            })
            valid_count += 1
        except Exception as e:
            error_count += 1
            if len(errors) < 10:
                errors.append({
                    'row_index': idx,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                })

    print(f"\nValid records: {valid_count:,}/{len(df):,} "
          f"({100 * valid_count / len(df):.1f}%)")

    if error_count > 0:
        print(f"Invalid records: {error_count:,}/{len(df):,} "
              f"({100 * error_count / len(df):.1f}%)")
        print("\nSample errors (first 10):")
        for err in errors:
            print(f"  Row {err['row_index']}: [{err['error_type']}] {err['error_message']}")
    else:
        print("No validation errors found")

    return {
        'valid': valid_count,
        'invalid': error_count,
        'sample_size': len(df),
        'errors': errors
    }

# ============================================================================
# JINJA TEMPLATES FOR ASSERTION TESTS
# ============================================================================

# Template: Check null percentage for a column
NULL_CHECK_TEMPLATE = Template("""
    SELECT 
        '{{ column_name }}' as column_name,
        COUNT(*) as total_rows,
        SUM(CASE WHEN {{ column_name }} IS NULL THEN 1 ELSE 0 END) as null_count,
        ROUND(100.0 * SUM(CASE WHEN {{ column_name }} IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as null_pct
    FROM traversals_clean
""")


# ============================================================================
# ASSERTION TEST FUNCTIONS
# ============================================================================

def test_timestamp_columns_not_null(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Test that timestamp parsing created all derived columns without nulls.
    Validates transformation correctness.
    """
    print("\n1. Testing timestamp-derived columns for nulls...")
    print("-" * 60)

    timestamp_columns = [
        'traversal_timestamp',
        'traversal_date',
        'traversal_time',
        'traversal_hour',
        'traversal_day_of_week',
        'traversal_day_name'
    ]

    results = []
    all_passed = True

    for column in timestamp_columns:
        query = NULL_CHECK_TEMPLATE.render(column_name=column)
        result = con.execute(query).df().iloc[0]
        passed = result['null_count'] == 0

        results.append({
            'column': column,
            'null_count': result['null_count'],
            'passed': passed
        })

        status = "PASSED" if passed else "FAILED"
        print(f"  {status}: {column} - {result['null_count']:,} nulls")

        if not passed:
            all_passed = False

    return {
        'test_name': 'timestamp_columns_not_null',
        'passed': all_passed,
        'results': results
    }


def test_date_range_filter_applied(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Test that date filtering worked correctly.
    All dates should be between config.START_DATE and config.END_DATE.
    """
    print("\n2. Testing date range filter...")
    print("-" * 60)

    result = con.execute(f"""
        SELECT 
            MIN(traversal_date) as min_date,
            MAX(traversal_date) as max_date,
            '{config.START_DATE}' as expected_min,
            '{config.END_DATE}' as expected_max,
            SUM(CASE WHEN traversal_date < '{config.START_DATE}' THEN 1 ELSE 0 END) as before_start,
            SUM(CASE WHEN traversal_date > '{config.END_DATE}' THEN 1 ELSE 0 END) as after_end
        FROM traversals_clean
    """).df().iloc[0]

    passed = (result['before_start'] == 0 and result['after_end'] == 0)

    status = "PASSED" if passed else "FAILED"
    print(f"  {status}: Date range")
    print(f"    Actual range: {result['min_date']} to {result['max_date']}")
    print(f"    Expected range: {config.START_DATE} to {config.END_DATE}")
    print(f"    Records before start: {result['before_start']:,}")
    print(f"    Records after end: {result['after_end']:,}")

    return {
        'test_name': 'date_range_filter_applied',
        'passed': passed,
        'min_date': str(result['min_date']),
        'max_date': str(result['max_date']),
        'before_start': int(result['before_start']),
        'after_end': int(result['after_end'])
    }


def test_scheduled_filter_applied(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Test that scheduled filter was applied if configured.
    If config.SCHEDULED_ONLY=True, all rows should have scheduled=1.
    """
    print("\n4. Testing scheduled filter...")
    print("-" * 60)

    result = con.execute("""
        SELECT 
            SUM(CASE WHEN scheduled = 0 THEN 1 ELSE 0 END) as unscheduled_count,
            COUNT(*) as total_rows
        FROM traversals_clean
    """).df().iloc[0]

    if config.SCHEDULED_ONLY:
        passed = result['unscheduled_count'] == 0
        status = "PASSED" if passed else "FAILED"
        print(f"  {status}: Scheduled filter (SCHEDULED_ONLY=True)")
        print(f"    Unscheduled waypoints: {result['unscheduled_count']:,}")
        print(f"    Total rows: {result['total_rows']:,}")
    else:
        passed = True  # No filter expected
        print(f"  SKIPPED: Scheduled filter (SCHEDULED_ONLY=False)")
        print(f"    All waypoints kept (scheduled and unscheduled)")

    return {
        'test_name': 'scheduled_filter_applied',
        'passed': passed,
        'unscheduled_count': int(result['unscheduled_count']),
        'total_rows': int(result['total_rows']),
        'filter_expected': config.SCHEDULED_ONLY
    }


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def run_all_transformed_tests(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Run Pydantic validation and assertion tests on transformed data.

    Args:
        con: DuckDB connection with 'traversals_clean' table

    Returns:
        Dictionary with all test results
    """
    print("=" * 80)
    print("TRANSFORMED DATA VALIDATION")
    print("=" * 80)

    # Pydantic validation
    pydantic_results = validate_transformed_schema(con, sample_size=1000)

    # Assertion tests
    print("\n" + "=" * 80)
    print("ASSERTION TESTS")
    print("=" * 80)

    test_results = []
    test_results.append(test_timestamp_columns_not_null(con))
    test_results.append(test_date_range_filter_applied(con))
    test_results.append(test_scheduled_filter_applied(con))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    pydantic_passed = pydantic_results['invalid'] == 0
    assertion_total = len(test_results)
    assertion_passed = sum(1 for t in test_results if t['passed'])

    print(f"\nPydantic validation: {'PASSED' if pydantic_passed else 'FAILED'}")
    print(f"  Valid: {pydantic_results['valid']:,}")
    print(f"  Invalid: {pydantic_results['invalid']:,}")

    print(f"\nAssertion tests:")
    print(f"  Total: {assertion_total}")
    print(f"  Passed: {assertion_passed}")
    print(f"  Failed: {assertion_total - assertion_passed}")

    all_passed = pydantic_passed and (assertion_passed == assertion_total)

    if all_passed:
        print("\nAll validation and tests passed")
    else:
        print(f"\nValidation or tests failed - review above")

    return {
        'pydantic': pydantic_results,
        'assertions': {
            'total_tests': assertion_total,
            'passed': assertion_passed,
            'failed': assertion_total - assertion_passed,
            'test_results': test_results
        },
        'all_passed': all_passed
    }


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    from src.ingestion import ingest_data
    from src.transformations import transform_data

    print("Running transformed data validation...")

    # Ingest and transform
    df = ingest_data()
    con = transform_data(df)

    # Run tests
    results = run_all_transformed_tests(con)

    if not results['all_passed']:
        print("\nValidation or tests failed. Pipeline should not proceed.")
        exit(1)
    else:
        print("\nAll validation and tests passed. Safe to proceed with coverage calculation.")