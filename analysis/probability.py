"""Probability analysis: hit rates, base rates, and lift calculations."""

from typing import Optional

import pandas as pd
import numpy as np


def calculate_hit_rate(
    signals: pd.Series,
    returns: pd.Series,
    forward_periods: int = 1,
) -> dict:
    """
    Calculate the hit rate (win rate) for a signal.

    Args:
        signals: Boolean Series indicating signal occurrences
        returns: Series of price returns
        forward_periods: Number of periods to look ahead for return calculation

    Returns:
        Dictionary with hit rate statistics
    """
    # Calculate forward returns
    forward_returns = returns.shift(-forward_periods)

    # Filter to signal dates only
    signal_returns = forward_returns[signals]

    if len(signal_returns) == 0:
        return {
            "hit_rate": np.nan,
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
        }

    wins = (signal_returns > 0).sum()
    losses = (signal_returns <= 0).sum()
    total = len(signal_returns)

    return {
        "hit_rate": wins / total if total > 0 else np.nan,
        "total_signals": total,
        "wins": int(wins),
        "losses": int(losses),
        "avg_win": float(signal_returns[signal_returns > 0].mean()) if wins > 0 else 0,
        "avg_loss": float(signal_returns[signal_returns <= 0].mean()) if losses > 0 else 0,
    }


def calculate_base_rate(
    returns: pd.Series,
    threshold: float = 0.0,
) -> float:
    """
    Calculate the base rate (unconditional probability) of positive returns.

    Args:
        returns: Series of price returns
        threshold: Minimum return to count as positive

    Returns:
        Base rate as a float between 0 and 1
    """
    if len(returns) == 0:
        return np.nan

    return (returns > threshold).mean()


def calculate_lift(
    signals: pd.Series,
    returns: pd.Series,
    forward_periods: int = 1,
) -> dict:
    """
    Calculate lift - how much better the signal performs vs random.

    Lift = Hit Rate / Base Rate

    Args:
        signals: Boolean Series indicating signal occurrences
        returns: Series of price returns
        forward_periods: Number of periods to look ahead

    Returns:
        Dictionary with lift statistics
    """
    hit_stats = calculate_hit_rate(signals, returns, forward_periods)
    base_rate = calculate_base_rate(returns.shift(-forward_periods).dropna())

    hit_rate = hit_stats["hit_rate"]

    if np.isnan(hit_rate) or np.isnan(base_rate) or base_rate == 0:
        lift = np.nan
    else:
        lift = hit_rate / base_rate

    return {
        "lift": lift,
        "hit_rate": hit_rate,
        "base_rate": base_rate,
        "total_signals": hit_stats["total_signals"],
    }


def calculate_expectancy(
    signals: pd.Series,
    returns: pd.Series,
    forward_periods: int = 1,
) -> float:
    """
    Calculate the expectancy (expected value) per signal.

    Args:
        signals: Boolean Series indicating signal occurrences
        returns: Series of price returns
        forward_periods: Number of periods to look ahead

    Returns:
        Expected return per signal
    """
    forward_returns = returns.shift(-forward_periods)
    signal_returns = forward_returns[signals]

    if len(signal_returns) == 0:
        return np.nan

    return float(signal_returns.mean())
