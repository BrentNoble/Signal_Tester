"""Trend duration analysis."""

from typing import Optional, Tuple

import pandas as pd
import numpy as np


def calculate_trend_duration(
    data: pd.DataFrame,
    signals: pd.Series,
    direction: str = "up",
) -> dict:
    """
    Calculate statistics on trend duration following signals.

    Args:
        data: DataFrame with OHLCV data
        signals: Boolean Series indicating signal occurrences
        direction: 'up' for bullish signals, 'down' for bearish signals

    Returns:
        Dictionary with duration statistics
    """
    if direction not in ("up", "down"):
        raise ValueError("direction must be 'up' or 'down'")

    signal_dates = signals[signals].index
    durations = []

    for date in signal_dates:
        duration = _measure_trend_duration(data, date, direction)
        if duration is not None:
            durations.append(duration)

    if not durations:
        return {
            "mean_duration": np.nan,
            "median_duration": np.nan,
            "max_duration": np.nan,
            "min_duration": np.nan,
            "std_duration": np.nan,
            "total_signals": 0,
        }

    return {
        "mean_duration": np.mean(durations),
        "median_duration": np.median(durations),
        "max_duration": max(durations),
        "min_duration": min(durations),
        "std_duration": np.std(durations),
        "total_signals": len(durations),
    }


def _measure_trend_duration(
    data: pd.DataFrame,
    start_date: pd.Timestamp,
    direction: str,
) -> Optional[int]:
    """
    Measure how long a trend continues from a given start date.

    Args:
        data: DataFrame with OHLCV data
        start_date: Date when trend started
        direction: 'up' or 'down'

    Returns:
        Number of periods the trend continued, or None if invalid
    """
    try:
        start_idx = data.index.get_loc(start_date)
    except KeyError:
        return None

    if start_idx >= len(data) - 1:
        return None

    start_price = data.iloc[start_idx]["Close"]
    duration = 0

    for i in range(start_idx + 1, len(data)):
        current_price = data.iloc[i]["Close"]

        if direction == "up":
            # Trend continues while price stays above start
            if current_price >= start_price:
                duration += 1
            else:
                break
        else:
            # Trend continues while price stays below start
            if current_price <= start_price:
                duration += 1
            else:
                break

    return duration


def calculate_max_favorable_excursion(
    data: pd.DataFrame,
    signals: pd.Series,
    direction: str = "up",
    max_periods: int = 20,
) -> dict:
    """
    Calculate maximum favorable excursion (MFE) statistics.

    MFE measures the maximum profit potential during a trade.

    Args:
        data: DataFrame with OHLCV data
        signals: Boolean Series indicating signal occurrences
        direction: 'up' for bullish signals, 'down' for bearish signals
        max_periods: Maximum periods to look ahead

    Returns:
        Dictionary with MFE statistics
    """
    signal_dates = signals[signals].index
    mfe_values = []

    for date in signal_dates:
        mfe = _calculate_single_mfe(data, date, direction, max_periods)
        if mfe is not None:
            mfe_values.append(mfe)

    if not mfe_values:
        return {
            "mean_mfe": np.nan,
            "median_mfe": np.nan,
            "max_mfe": np.nan,
            "total_signals": 0,
        }

    return {
        "mean_mfe": np.mean(mfe_values),
        "median_mfe": np.median(mfe_values),
        "max_mfe": max(mfe_values),
        "total_signals": len(mfe_values),
    }


def _calculate_single_mfe(
    data: pd.DataFrame,
    start_date: pd.Timestamp,
    direction: str,
    max_periods: int,
) -> Optional[float]:
    """Calculate MFE for a single signal."""
    try:
        start_idx = data.index.get_loc(start_date)
    except KeyError:
        return None

    end_idx = min(start_idx + max_periods + 1, len(data))
    if start_idx >= len(data) - 1:
        return None

    start_price = data.iloc[start_idx]["Close"]
    future_data = data.iloc[start_idx + 1 : end_idx]

    if len(future_data) == 0:
        return None

    if direction == "up":
        max_price = future_data["High"].max()
        mfe = (max_price - start_price) / start_price
    else:
        min_price = future_data["Low"].min()
        mfe = (start_price - min_price) / start_price

    return float(mfe)
