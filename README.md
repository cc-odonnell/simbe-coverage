# Simbe Robotics Coverage Metrics Pipeline

## Project Overview

This project calculates scene-level physical coverage metrics for Simbe Robotics' Tally autonomous retail audit robot. The pipeline processes traversal data to measure how effectively Tally covers scheduled waypoints across retail store environments, providing operational insights into robot performance and identifying areas where coverage fails.

**Key Metrics:**

* **Scene-level coverage:** Percentage of unique scenes with at least one visited waypoint per store per day
* **Skip attribution:** Breakdown of reasons why waypoints were not visited (e.g., dynamic obstacles, static obstacles, operator intervention)

The pipeline is designed to showcase production-ready data engineering practices including modular architecture, comprehensive validation at each stage, and clear separation between data ingestion, transformation, business logic, and outputs.

## Design Decisions

### Assertion Tests

Assertion tests are currently implemented in DuckDB with Jinja templating for reusability. In a production environment, these would migrate to dbt tests (`tests/` folder with `.yml` schema definitions), enabling version control, lineage tracking, and integration with an orchestration tool (e.g., Airflow).

### Pydantic Schemas

Data type validation uses Pydantic models defined in Python. For a dbt-based pipeline, these could be ported to YAML schema definitions (`schema.yml`) alongside dbt models, consolidating validation logic in a single declarative format.

### Outputs

Pipeline outputs are currently pandas DataFrames written to disk. In production, these would be materialized as tables in a data warehouse (e.g., BigQuery) and surfaced through data visualization dashboards for stakeholder consumption.

### Visualizations

Example visualizations are provided using matplotlib. In production, these would be rebuilt in a data viz dashboard (e.g., Looker Studio) with interactive filtering, drill-down capabilities, and scheduled refresh.

## Production Pipeline Notes

### Notes on Validations

In a production pipeline, I would have separate YAML files (e.g., `data_type_check_raw.yml`, `data_type_check_transformed.yml`, `data_type_check_calc.yml`) to validate data at each stage. For this case study, these validation functions are consolidated within the Python scripts to keep the file structure simple.

The pipeline currently validates data at two stages: post-ingestion (`assertions_raw.py`) and post-transformation (`assertions_transformed.py`). In a production pipeline, I would add a third validation stage (`assertions_coverage.py`) to validate calculated metrics (e.g., coverage percentages between 0-100, no negative counts, scene counts match input data). For this case study, the validation pattern has been demonstrated at the ingestion and transformation stages.

Skip reasons are currently validated against a hardcoded list in `config.py`. In production, this would be externalized to a YAML configuration file to accommodate new skip reasons added by the engineering team without requiring code changes.

### Notes on Visualizations

Currently, the script generates three chart types per store: 
1. **Coverage trends over time** - Daily scene-level coverage percentages
2. **Spatial heatmaps** - Failed waypoints aggregated across the full date range to identify problem areas in store layout
3. **Skip reason breakdowns** - Distribution of why waypoints were not visited

In a production pipeline, I would write the visualizations as functions if being used outside of a dashboard platform. Otherwise, these would be rebuilt as interactive dashboards in Looker Studio with date filters, drill-down capabilities, store selection dropdowns, and scheduled refresh. The heatmaps in particular would benefit from daily granularity with interactive date selection to identify temporal patterns in coverage failures.

## Module Overview

**Key modules:**
- `ingestion.py` - Load CSV into DuckDB
- `data_type_checks.py` - Pydantic schema validation (raw data)
- `transformations.py` - Data reshaping: scene aggregation, skip reason categorization, date-level rollups
- `assertions_raw.py` - SQL assertions validating raw ingested data
- `assertions_transformed.py` - SQL assertions validating transformed data (pre-metrics)
- `coverage_metrics.py` - Business logic for coverage calculations
- `visualizations.py` - Chart generation (matplotlib)
- `pipeline.py` - Orchestration

**Validation Strategy:**
- **Stage 1 (Post-Ingestion):** Pydantic type checks + `assertions_raw.py` validate schema and raw data quality
- **Stage 2 (Post-Transformation):** `assertions_transformed.py` validates aggregation logic and data integrity before metrics calculation
- **Stage 3 (Metrics):** Coverage calculations assume validated inputs; assertions could be added here in production (see Production Deployment Notes)

## Setup & Running

### Prerequisites
- Python 3.9+
- Input data: `traversals.csv` in `data/` folder

### Installation
```bash
pip install -r requirements.txt
```

### Run Pipeline
```bash
cd src
python pipeline.py
```

### Expected Outputs
- `output/scene_coverage.csv` - Scene-level coverage by store and date
- `output/skip_attribution.csv` - Skip reason breakdown by responsibility category
- `output/*.png` - Visualization charts (coverage trends, failure heatmaps, skip breakdowns)

### Generate Visualizations Separately
```bash
python src/visualizations.py
```

