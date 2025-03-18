"""
Utility functions for analyzing and visualizing temperature inversions.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


def load_inversion_data(file_path):
    """Load inversion data from an Excel file."""
    try:
        return pd.read_excel(file_path)
    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def summarize_inversions(df):
    """Generate summary statistics for inversion data."""
    summary = {
        "total_inversions": len(df),
        "ground_inversions": df["Ground"].sum(),
        "elevated_inversions": len(df) - df["Ground"].sum(),
        "day_inversions": df["Day"].sum(),
        "night_inversions": df["Night"].sum(),
        "mean_temp_change": df["ΔT"].mean(),
        "max_temp_change": df["ΔT"].max(),
        "mean_height_change": df["ΔH"].mean(),
        "mean_base_height": df["HL"].mean(),
    }

    return pd.DataFrame([summary])


def plot_inversion_distribution(df, save_path=None):
    """Plot the distribution of inversion characteristics."""
    if df.empty:
        print("No data to plot")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Temperature change distribution
    sns.histplot(df["ΔT"], kde=True, ax=axes[0, 0])
    axes[0, 0].set_title("Temperature Change Distribution")
    axes[0, 0].set_xlabel("Temperature Change (°C)")

    # Height distribution
    sns.histplot(df["ΔH"], kde=True, ax=axes[0, 1])
    axes[0, 1].set_title("Inversion Depth Distribution")
    axes[0, 1].set_xlabel("Height Change (m)")

    # Base height distribution
    sns.histplot(df["HL"], kde=True, ax=axes[1, 0])
    axes[1, 0].set_title("Base Height Distribution")
    axes[1, 0].set_xlabel("Base Height (m)")

    # Inversion count by time
    time_counts = df.groupby(df["date"].dt.date).size()
    time_counts.plot(kind="bar", ax=axes[1, 1])
    axes[1, 1].set_title("Inversions by Date")
    axes[1, 1].set_xlabel("Date")
    plt.xticks(rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)

    return fig


def plot_inversion_profile(df, index=0, save_path=None):
    """Plot the vertical profile of a specific inversion."""
    if df.empty or index >= len(df):
        print("Invalid index or empty dataframe")
        return

    # Get the inversion of interest
    inversion = df.iloc[index]

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 10))

    # Plot temperature vs height
    ax.plot(inversion["TEMP"], inversion["HGHT"], "r-o", linewidth=2)

    # Add labels and title
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Height (m)")
    ax.set_title(f"Inversion Profile - {inversion['date']}")

    # Add grid
    ax.grid(True)

    # Add text with inversion characteristics
    ax.text(
        0.05,
        0.95,
        f"ΔT: {inversion['ΔT']:.2f}°C\n"
        f"ΔH: {inversion['ΔH']:.0f}m\n"
        f"Base Height: {inversion['HL']:.0f}m",
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
    )

    if save_path:
        plt.savefig(save_path)

    return fig


def find_strongest_inversions(df, n=5):
    """Find the strongest inversions based on temperature change."""
    return df.sort_values(by="ΔT", ascending=False).head(n)


def find_deepest_inversions(df, n=5):
    """Find the deepest inversions based on height change."""
    return df.sort_values(by="ΔH", ascending=False).head(n)


def compute_inversion_frequency(df):
    """Compute the frequency of inversions by day/night and ground/elevated."""
    total = len(df) if len(df) > 0 else 1  # Avoid division by zero

    frequency = {
        "ground_day": (df["Ground"] & df["Day"]).sum() / total,
        "ground_night": (df["Ground"] & df["Night"]).sum() / total,
        "elevated_day": ((~df["Ground"].astype(bool)) & df["Day"]).sum() / total,
        "elevated_night": ((~df["Ground"].astype(bool)) & df["Night"]).sum() / total,
    }

    return frequency


def seasonal_analysis(df):
    """Analyze inversion patterns by season."""
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    # Add season column
    df = df.copy()
    df["season"] = df["date"].dt.month.apply(
        lambda m: (
            "Winter"
            if m in [12, 1, 2]
            else "Spring" if m in [3, 4, 5] else "Summer" if m in [6, 7, 8] else "Fall"
        )
    )

    # Group by season
    season_stats = df.groupby("season").agg(
        {
            "ΔT": ["mean", "max", "count"],
            "ΔH": ["mean", "max"],
            "Ground": "mean",
            "Day": "mean",
            "Night": "mean",
        }
    )

    # Flatten the MultiIndex columns
    season_stats.columns = [
        "_".join(col).strip() for col in season_stats.columns.values
    ]

    return season_stats
