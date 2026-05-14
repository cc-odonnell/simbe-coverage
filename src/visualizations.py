"""
Example visualizations for coverage metrics.

Generates three chart types per store:
1. Coverage over time (line chart)
2. Failure heatmap (spatial visualization of unvisited waypoints)
3. Skip reason breakdown (bar chart)

Note: In a production environment, these would be rebuilt as interactive
dashboards in Looker Studio with date filters, drill-down capabilities,
and scheduled refresh. The visualizations here demonstrate the insights
that would be surfaced in such a dashboard.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from src import config


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_coverage_over_time(coverage_df: pd.DataFrame, store_name: str) -> None:
    """
    Create line chart showing coverage percentage over time for a store.

    Args:
        coverage_df: Scene coverage DataFrame
        store_name: Store to plot (e.g., 'Store A')
    """
    print(f"\nGenerating coverage over time chart for {store_name}...")

    # Filter to store
    store_data = coverage_df[coverage_df['store_name'] == store_name].copy()
    store_data = store_data.sort_values('traversal_date')

    # Create figure
    plt.style.use(config.CHART_STYLE)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=config.FIGURE_DPI)

    # Plot line
    ax.plot(store_data['traversal_date'],
            store_data['coverage_pct'],
            color=config.COLOR_COVERAGE,
            linewidth=2,
            marker='o',
            markersize=4)

    # Labels and title
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Coverage Percentage', fontsize=12)
    ax.set_title(f'Scene-Level Coverage Over Time - {store_name}',
                 fontsize=14, fontweight='bold')

    # Format y-axis
    ax.set_ylim(0, 100)
    ax.axhline(y=store_data['coverage_pct'].mean(),
               color='gray',
               linestyle='--',
               linewidth=1,
               label=f"Mean: {store_data['coverage_pct'].mean():.1f}%")

    # Grid and legend
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right')

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()

    # Save
    filename = f"coverage_over_time_{store_name.replace(' ', '_')}.png"
    filepath = config.OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=config.FIGURE_DPI, bbox_inches='tight')
    plt.close()

    print(f"Saved: {filepath}")


def plot_failure_heatmap(traversals_df: pd.DataFrame, store_name: str) -> None:
    """
    Create heatmap showing spatial distribution of failed waypoints.
    Aggregated across all days in dataset.

    Note: In production, this would have date filtering in an interactive dashboard.

    Args:
        traversals_df: Full traversals DataFrame from DuckDB
        store_name: Store to plot (e.g., 'Store A')
    """
    print(f"\nGenerating failure heatmap for {store_name}...")

    # Filter to store and unvisited waypoints
    store_data = traversals_df[
        (traversals_df['store_name'] == store_name) &
        (traversals_df['visited'] == 0)
        ].copy()

    # Create figure
    plt.style.use(config.CHART_STYLE)
    fig, ax = plt.subplots(figsize=(12, 8), dpi=config.FIGURE_DPI)

    # Create 2D histogram (heatmap)
    heatmap, xedges, yedges = np.histogram2d(
        store_data['x'],
        store_data['y'],
        bins=50
    )

    # Plot heatmap
    im = ax.imshow(heatmap.T,
                   origin='lower',
                   extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]],
                   cmap='Reds',
                   aspect='auto',
                   interpolation='bilinear')

    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Number of Failed Visits', fontsize=12)

    # Labels and title
    ax.set_xlabel('X Coordinate', fontsize=12)
    ax.set_ylabel('Y Coordinate', fontsize=12)
    ax.set_title(f'Spatial Distribution of Failed Waypoints - {store_name}\n(Aggregated across all days)',
                 fontsize=14, fontweight='bold')

    plt.tight_layout()

    # Save
    filename = f"failure_heatmap_{store_name.replace(' ', '_')}.png"
    filepath = config.OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=config.FIGURE_DPI, bbox_inches='tight')
    plt.close()

    print(f"Saved: {filepath}")


def plot_skip_reasons(skip_df: pd.DataFrame, store_name: str) -> None:
    """
    Create bar chart showing distribution of skip reasons.
    Aggregated across all days in dataset.

    Args:
        skip_df: Skip attribution DataFrame
        store_name: Store to plot (e.g., 'Store A')
    """
    print(f"\nGenerating skip reasons chart for {store_name}...")

    # Filter to store and aggregate across dates
    store_data = skip_df[skip_df['store_name'] == store_name].copy()
    skip_summary = store_data.groupby('skip_reason')['skip_count'].sum().sort_values(ascending=False)

    # Create figure
    plt.style.use(config.CHART_STYLE)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=config.FIGURE_DPI)

    # Create bar chart
    colors = plt.cm.tab10(np.linspace(0, 1, len(skip_summary)))
    bars = ax.bar(range(len(skip_summary)),
                  skip_summary.values,
                  color=colors)

    # Labels and title
    ax.set_xlabel('Skip Reason', fontsize=12)
    ax.set_ylabel('Total Skip Count', fontsize=12)
    ax.set_title(f'Distribution of Skip Reasons - {store_name}\n(Aggregated across all days)',
                 fontsize=14, fontweight='bold')

    # X-axis labels
    ax.set_xticks(range(len(skip_summary)))
    ax.set_xticklabels(skip_summary.index, rotation=45, ha='right')

    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, skip_summary.values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{int(value):,}',
                ha='center', va='bottom', fontsize=10)

    # Grid
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # Save
    filename = f"skip_reasons_{store_name.replace(' ', '_')}.png"
    filepath = config.OUTPUT_DIR / filename
    plt.savefig(filepath, dpi=config.FIGURE_DPI, bbox_inches='tight')
    plt.close()

    print(f"Saved: {filepath}")


# ============================================================================
# MAIN VISUALIZATION GENERATION
# ============================================================================

def generate_all_visualizations(coverage_df: pd.DataFrame,
                                skip_df: pd.DataFrame,
                                traversals_df: pd.DataFrame) -> None:
    """
    Generate all visualizations for both stores.

    Args:
        coverage_df: Scene coverage DataFrame
        skip_df: Skip attribution DataFrame
        traversals_df: Full traversals DataFrame (for heatmap)
    """
    print("=" * 80)
    print("GENERATING VISUALIZATIONS")
    print("=" * 80)

    stores = ['Store A', 'Store B']

    for store in stores:
        print(f"\n{'-' * 60}")
        print(f"Processing {store}")
        print('-' * 60)

        # Coverage over time
        plot_coverage_over_time(coverage_df, store)

        # Failure heatmap
        plot_failure_heatmap(traversals_df, store)

        # Skip reasons
        plot_skip_reasons(skip_df, store)

    print("\n" + "=" * 80)
    print("VISUALIZATION GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nGenerated 6 visualization files in: {config.OUTPUT_DIR}")
    print("\nFiles created:")
    print("  - coverage_over_time_Store_A.png")
    print("  - coverage_over_time_Store_B.png")
    print("  - failure_heatmap_Store_A.png")
    print("  - failure_heatmap_Store_B.png")
    print("  - skip_reasons_Store_A.png")
    print("  - skip_reasons_Store_B.png")


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    from src.ingestion import ingest_data
    from src.transformations import transform_data
    from src.coverage_metrics import calculate_all_metrics

    print("Generating visualizations from pipeline outputs...")

    # Run full pipeline
    df = ingest_data()
    con = transform_data(df)
    metrics = calculate_all_metrics(con)

    # Get traversals data for heatmap
    traversals_df = con.execute("SELECT * FROM traversals_clean").df()

    # Generate visualizations
    generate_all_visualizations(
        coverage_df=metrics['scene_coverage'],
        skip_df=metrics['skip_attribution'],
        traversals_df=traversals_df
    )