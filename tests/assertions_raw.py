"""
Assertion tests for raw ingested data (pre-transformation).

Tests validate data quality on the raw DataFrame returned from ingestion.py
before any transformations are applied. These tests check aggregate statistics
and cross-row constraints that cannot be validated by Pydantic's row-level checks.

Note: In a production dbt-based pipeline, these would migrate to dbt tests
(tests/ folder with .yml schema definitions), enabling version control,
lineage tracking, and integration with orchestration tools.
"""

import duckdb
import pandas as pd
from jinja2 import Template

from src import config

# ============================================================================
# JINJA TEMPLATES FOR REUSABLE SQL TESTS
# ============================================================================

# Template: Check null percentage for a column
NULL_CHECK_TEMPLATE = Template("""
    SELECT 
        '{{ column_name }}' as column_name,
        COUNT(*) as total_rows,
        SUM(CASE WHEN {{ column_name }} IS NULL THEN 1 ELSE 0 END) as null_count,
        ROUND(100.0 * SUM(CASE WHEN {{ column_name }} IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as null_pct,
        {{ max_null_pct }} as max_allowed_pct
    FROM traversals
""")

# Template: Check for duplicates on a key
DUPLICATE_CHECK_TEMPLATE = Template("""
    SELECT 
        COUNT(*) as duplicate_count
    FROM (
        SELECT 
            {{ key_columns }},
            COUNT(*) as occurrence_count
        FROM traversals
        GROUP BY {{ key_columns }}
        HAVING COUNT(*) > 1
    )
""")


# ============================================================================
# ASSERTION TEST FUNCTIONS
# ============================================================================

def test_critical_fields_not_null(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Test that critical fields have no null values.
    Critical fields: store_name, traversal_start_time, waypoint_id, aisle, scene, scheduled, visited

    Note: Data types are validated by Pydantic. This test validates aggregate null rates.
    """
    print("\n Testing critical fields for nulls...")
    print("-" * 60)

    critical_fields = [
        'store_name', 'traversal_start_time', 'waypoint_id',
        'aisle', 'scene', 'scheduled', 'visited'
    ]

    results = []
    all_passed = True

    for field in critical_fields:
        query = NULL_CHECK_TEMPLATE.render(
            column_name=field,
            max_null_pct=config.MAX_NULL_PCT_CRITICAL_FIELDS
        )

        result = con.execute(query).df().iloc[0]
        passed = result['null_pct'] <= config.MAX_NULL_PCT_CRITICAL_FIELDS

        results.append({
            'field': field,
            'null_count': result['null_count'],
            'null_pct': result['null_pct'],
            'passed': passed
        })

        status = "passed" if passed else "not passed"
        print(f"  {status} {field}: {result['null_count']:,} nulls ({result['null_pct']:.2f}%)")

        if not passed:
            all_passed = False

    return {
        'test_name': 'critical_fields_not_null',
        'passed': all_passed,
        'results': results
    }


def test_skip_reason_null_allowed(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Test that skip_reason can be null (nullable field).
    This is informational - we expect nulls when visited=1.

    Note: Skip reason values are validated by Pydantic against config.VALID_SKIP_REASONS.
    """
    print("\n Testing skip_reason null rate (nullable field)...")
    print("-" * 60)

    query = NULL_CHECK_TEMPLATE.render(
        column_name='skip_reason',
        max_null_pct=config.MAX_NULL_PCT_SKIP_REASON
    )

    result = con.execute(query).df().iloc[0]
    passed = result['null_pct'] <= config.MAX_NULL_PCT_SKIP_REASON

    status = "passed" if passed else "not passed"
    print(f"  {status} skip_reason: {result['null_count']:,} nulls ({result['null_pct']:.2f}%)")
    print(f"     (Allowed: nulls are expected when visited=1)")

    return {
        'test_name': 'skip_reason_null_allowed',
        'passed': passed,
        'null_count': int(result['null_count']),
        'null_pct': float(result['null_pct'])
    }


def test_no_duplicate_waypoints_per_traversal(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Test that each (store, traversal, waypoint) combination is unique.
    This validates a cross-row uniqueness constraint.
    """
    print("\n Testing for duplicate waypoints per traversal...")
    print("-" * 60)

    query = DUPLICATE_CHECK_TEMPLATE.render(
        key_columns='store_name, traversal_start_time, waypoint_id'
    )

    result = con.execute(query).df().iloc[0]
    passed = result['duplicate_count'] == 0

    status = "passed" if passed else "not passed"
    print(f"  {status} Duplicate (store, traversal, waypoint): {result['duplicate_count']:,}")

    return {
        'test_name': 'no_duplicate_waypoints_per_traversal',
        'passed': passed,
        'duplicate_count': int(result['duplicate_count'])
    }


def test_row_count_reasonable(con: duckdb.DuckDBPyConnection) -> dict:
    """
    Test that dataset has a reasonable number of rows.
    Threshold defined in config.MIN_ROW_COUNT.
    """
    print("\n4. Testing row count is reasonable...")
    print("-" * 60)

    result = con.execute("SELECT COUNT(*) as row_count FROM traversals").df().iloc[0]
    passed = result['row_count'] >= config.MIN_ROW_COUNT

    status = "✓" if passed else "✗"
    print(f"  {status} Row count: {result['row_count']:,} (minimum: {config.MIN_ROW_COUNT:,})")

    return {
        'test_name': 'row_count_reasonable',
        'passed': passed,
        'row_count': int(result['row_count']),
        'min_required': config.MIN_ROW_COUNT
    }


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def run_all_raw_data_tests(df: pd.DataFrame) -> dict:
    """
    Run all assertion tests on raw ingested data.

    These tests validate:
    - Aggregate null rates (not checked by Pydantic's row-level validation)
    - Cross-row constraints like uniqueness (not checked by Pydantic)
    - Dataset-level thresholds like row count

    Args:
        df: Raw dataframe from ingestion.py

    Returns:
        Dictionary with all test results
    """
    print("=" * 80)
    print("RAW DATA ASSERTION TESTS")
    print("=" * 80)
    print("\n Note: Data types and value constraints are validated by Pydantic.")
    print("These tests check aggregate statistics and cross-row constraints.\n")

    # Load data into DuckDB for SQL-based tests
    con = duckdb.connect()
    con.execute("CREATE TABLE traversals AS SELECT * FROM df")

    # Run all tests
    test_results = []
    test_results.append(test_critical_fields_not_null(con))
    test_results.append(test_skip_reason_null_allowed(con))
    test_results.append(test_no_duplicate_waypoints_per_traversal(con))
    test_results.append(test_row_count_reasonable(con))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t['passed'])

    print(f"\n Tests run: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

    if passed_tests == total_tests:
        print("\n All raw data tests passed")
    else:
        print(f"\n {total_tests - passed_tests} test(s) failed - review above")

    return {
        'total_tests': total_tests,
        'passed': passed_tests,
        'failed': total_tests - passed_tests,
        'all_passed': passed_tests == total_tests,
        'test_results': test_results
    }


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    from src.ingestion import ingest_data

    print("Running raw data assertion tests...")
    df = ingest_data()

    results = run_all_raw_data_tests(df)

    if not results['all_passed']:
        print("\n  Some tests failed. Pipeline should not proceed.")
        exit(1)
    else:
        print("\n All tests passed. Safe to proceed with transformations.")