"""
Configuration settings for coverage metrics pipeline.
"""

from pathlib import Path

# ============================================================================
# PATHS
# ============================================================================

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Input files
TRAVERSALS_FILE = DATA_DIR / "traversals.csv"

# Output files
SCENE_COVERAGE_OUTPUT = OUTPUT_DIR / "scene_coverage.csv"
SKIP_ATTRIBUTION_OUTPUT = OUTPUT_DIR / "skip_attribution.csv"

# ============================================================================
# COVERAGE METRIC PARAMETERS
# ============================================================================

# Coverage calculation parameters
SCHEDULED_ONLY = True  # Only calculate coverage for scheduled waypoints

# Date filtering
START_DATE = "2026-04-01"  # First date to include in analysis
END_DATE = "2026-04-30"    # Last date to include in analysis

# ============================================================================
# VALIDATION PARAMETERS
# ============================================================================

# Null tolerance thresholds (for data quality checks)
MAX_NULL_PCT_CRITICAL_FIELDS = 0.0  # Critical fields must have 0% nulls
MAX_NULL_PCT_SKIP_REASON = 100.0     # Skip reason can be null (when visited=1)

MIN_ROW_COUNT = 1000  # Minimum acceptable number of rows in dataset


# Value validation
VALID_SCHEDULED_VALUES = [0, 1]
VALID_VISITED_VALUES = [0, 1]

VALID_SKIP_REASONS = [
    'dynamic',
    'static',
    'global_static',
    'immobile',
    'operator',
    'overlap',
    'failed_attempt',
    'no_reason_given'  # Our label for null skip reasons on scheduled, unvisited waypoints
]

# ============================================================================
# VISUALIZATION PARAMETERS
# ============================================================================

# Chart styling
CHART_STYLE = 'seaborn-v0_8-darkgrid'
FIGURE_DPI = 300
COLOR_COVERAGE = '#3498db'
COLOR_FAILURES = '#e74c3c'

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL