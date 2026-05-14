"""
Data type and schema validation using Pydantic models.

Note: In a dbt-based pipeline, these validation rules would be converted to
YAML schema definitions (schema.yml) alongside dbt models, consolidating
validation logic in a single declarative format.
"""

import pandas as pd
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

from src import config


# ============================================================================
# PYDANTIC VALIDATION MODELS
# ============================================================================

class TraversalRecord(BaseModel):
    """
    Schema validation for traversal records.
    Validates data types, value constraints, and business rules.
    """
    store_name: Literal['Store A', 'Store B'] = Field(
        ...,
        description="Store identifier - must be 'Store A' or 'Store B'"
    )
    traversal_start_time: str = Field(
        ...,
        description="Traversal start timestamp as string (will be parsed later)"
    )
    waypoint_id: int = Field(
        ...,
        ge=0,
        description="Waypoint identifier (non-negative integer)"
    )
    aisle: str = Field(
        ...,
        min_length=1,
        description="Aisle identifier (non-empty string)"
    )
    scene: str = Field(
        ...,
        min_length=1,
        description="Scene identifier (non-empty string)"
    )
    x: float = Field(
        ...,
        description="X coordinate (float)"
    )
    y: float = Field(
        ...,
        description="Y coordinate (float)"
    )
    scheduled: Literal[0, 1] = Field(
        ...,
        description="Scheduled flag - must be 0 or 1"
    )
    visited: Literal[0, 1] = Field(
        ...,
        description="Visited flag - must be 0 or 1"
    )
    skip_reason: Optional[str] = Field(
        None,
        description="Skip reason (nullable) - required when scheduled=1 and visited=0"
    )

    @field_validator('skip_reason')
    @classmethod
    def validate_skip_reason(cls, v):
        """
        Validate skip_reason is in allowed list if not null.
        Valid values defined in config.VALID_SKIP_REASONS.
        """
        if v is not None and v not in config.VALID_SKIP_REASONS:
            raise ValueError(
                f'skip_reason must be one of {config.VALID_SKIP_REASONS} or null, '
                f'got: {v}'
            )
        return v

    class Config:
        str_strip_whitespace = True


# ============================================================================
# VALIDATION EXECUTION FUNCTIONS
# ============================================================================

def validate_traversals_schema(df: pd.DataFrame, sample_size: int = 1000) -> dict:
    """
    Validate traversals dataframe against Pydantic schema.

    Args:
        df: Raw traversals dataframe from ingestion
        sample_size: Number of rows to validate (for performance on large datasets)

    Returns:
        Dictionary with validation results:
        {
            'valid': int,           # Number of valid records
            'invalid': int,         # Number of invalid records
            'sample_size': int,     # Total records checked
            'errors': list          # Sample of errors (first 10)
        }
    """
    print("\n" + "=" * 80)
    print("PYDANTIC DATA TYPE VALIDATION")
    print("=" * 80)
    print(f"\n Validating schema (sample size: {min(sample_size, len(df)):,})...")

    # Sample for validation (or use full dataset if smaller than sample_size)
    sample_df = df.sample(n=min(sample_size, len(df)), random_state=42)

    valid_count = 0
    error_count = 0
    errors = []

    # Validate each row
    for idx, row in sample_df.iterrows():
        try:
            TraversalRecord(**row.to_dict())
            valid_count += 1
        except Exception as e:
            error_count += 1
            if len(errors) < 10:  # Keep first 10 errors for inspection
                errors.append({
                    'row_index': idx,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                })

    # Print results
    print(f"\n✓ Valid records: {valid_count:,}/{len(sample_df):,} "
          f"({100 * valid_count / len(sample_df):.1f}%)")

    if error_count > 0:
        print(f"✗ Invalid records: {error_count:,}/{len(sample_df):,} "
              f"({100 * error_count / len(sample_df):.1f}%)")
        print("\nSample errors (first 10):")
        for err in errors:
            print(f"  Row {err['row_index']}: [{err['error_type']}] {err['error_message']}")
    else:
        print("✓ No validation errors found")

    return {
        'valid': valid_count,
        'invalid': error_count,
        'sample_size': len(sample_df),
        'errors': errors
    }


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Test validation independently
    from src.ingestion import ingest_data

    print("Testing Pydantic validation...")
    df = ingest_data()

    results = validate_traversals_schema(df, sample_size=1000)

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Sample size: {results['sample_size']:,}")
    print(f"Valid: {results['valid']:,}")
    print(f"Invalid: {results['invalid']:,}")

    if results['invalid'] > 0:
        print("\n  WARNING: Validation errors found. Review above.")
    else:
        print("\n All records passed validation")