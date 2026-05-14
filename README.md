# Simbe Robotics Coverage Metrics Pipeline

## Project Overview

This project calculates scene-level physical coverage metrics for Simbe Robotics' Tally autonomous retail audit robot. The pipeline processes traversal data to measure how effectively Tally covers scheduled waypoints across retail store environments, providing operational insights into robot performance and identifying areas where coverage fails.


Key Metrics:

Scene-level coverage: Percentage of unique scenes with at least one visited waypoint per store per day
Skip attribution: Breakdown of reasons why waypoints were not visited (e.g., dynamic obstacles, static obstacles, operator intervention)


The pipeline is designed to showcase production-ready data engineering practices including modular architecture, comprehensive validation at each stage, and clear separation between data ingestion, transformation, business logic, and outputs.

## Design Considerations

### Assertion Tests

Assertion tests are currently implemented in DuckDB with Jinja templating for reusability. In a production environment, these would migrate to dbt tests (tests folder with .yml schema definitions), enabling version control, lineage tracking, and integration with an orchestration tool (e.g., Airflow).

### Pydantic Schemas

Data type validation uses Pydantic models defined in Python. For a dbt-based pipeline, these could be ported to YAML schema definitions (schema.yml) alongside dbt models, consolidating validation logic in a single declarative format.
Outputs

Pipeline outputs are currently pandas DataFrames written to disk. In production, these would be materialized as tables in a data warehouse (e.g., BigQuery) and surfaced through data visualization dashboards for stakeholder consumption.

### Visualizations
Example visualizations are provided using matplotlib. In production, these would be rebuilt in a data viz dashboard (e.g., Looker Studio) with interactive filtering, drill-down capabilities, and scheduled refresh.

## Product Migration Notes 

### Notes on Validations

In a production pipeline, I would have a separate yaml files (e.g., data_type_check_raw, data_type_check_transformed, data_type_check_calc) but to keep the file structure simple for the case study, I'm merging these functions together in a few of the scripts.

In a production pipeline, I would include assertions_coverage.py to validate the calculated metrics (e.g., coverage percentages between 0-100, no negative counts, scene counts match input data). For this case study, the validation pattern has been demonstrated at the ingestion and transformation stages of the pipeline. 

Skip reasons are currently validated against a hardcoded list in config.py. In production, this would be externalized to a YAML configuration file to accommodate new skip reasons added by the engineering team without requiring code changes.

### Notes on Visualizations

Currently, the script generates three chart types per store: 

1) coverage trends over time showing daily scene-level coverage percentages, 
2) spatial heatmaps of failed waypoints aggregated across the full date range to identify problem areas in the store layout, and 
3) skip reason breakdowns showing the distribution of why waypoints were not visited. 

In a production pipeline, I would write the visualizations as functions if being used outside of a dashboard platform. Otherwise, these would be rebuilt as interactive dashboards in Looker Studio with date filters, drill-down capabilities, store selection dropdowns, and scheduled refresh. The heatmaps in particular would benefit from daily granularity with interactive date selection to identify temporal patterns in coverage failures.



