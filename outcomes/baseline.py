"""Baseline comparison via random entry.

Measures what happens with random entry for comparison against signal-based entry.
"""

from typing import List, Optional
import pandas as pd
import numpy as np

from .measurement import SignalOutcome, OutcomeMeasurer


class RandomBaseline:
    """
    Generate baseline statistics from random entry points.

    This provides a control to compare signal-based entry against.
    If signals don't beat random entry, they provide no edge.
    """

    HOLDING_PERIOD = 52  # 52 weekly bars = 12 months

    def __init__(self, n_samples: int = 1000, seed: Optional[int] = None):
        """
        Args:
            n_samples: Number of random entry points to sample
            seed: Random seed for reproducibility
        """
        self.n_samples = n_samples
        self.seed = seed

    def generate_random_entries(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate random entry signals.

        Only selects bars that have enough forward data for 12-month measurement.

        Args:
            data: DataFrame with OHLC data

        Returns:
            Boolean Series with random True values for entry points
        """
        if self.seed is not None:
            np.random.seed(self.seed)

        # Valid entry points: must have 52 bars of forward data
        max_entry_bar = len(data) - self.HOLDING_PERIOD - 1
        if max_entry_bar <= 0:
            raise ValueError(f"Insufficient data: need at least {self.HOLDING_PERIOD + 1} bars")

        # Sample random entry points
        n_samples = min(self.n_samples, max_entry_bar)
        entry_bars = np.random.choice(range(max_entry_bar), size=n_samples, replace=False)

        # Create boolean series
        signals = pd.Series(False, index=data.index)
        for bar in entry_bars:
            signals.iloc[bar] = True

        return signals

    def measure(self, data: pd.DataFrame) -> dict:
        """
        Measure outcomes for random entry points.

        Args:
            data: DataFrame with OHLC data

        Returns:
            Dict with baseline statistics
        """
        # Generate random entries
        random_signals = self.generate_random_entries(data)

        # Measure outcomes
        measurer = OutcomeMeasurer()
        outcomes = measurer.measure_all(data, random_signals, "random_baseline")

        if not outcomes:
            return {}

        # Calculate statistics
        df = measurer.to_dataframe(outcomes)

        total = len(df)
        wins = df["profitable_12m"].sum()

        return {
            "total_samples": total,
            "baseline_win_rate": wins / total * 100 if total > 0 else 0,
            "baseline_mean_return": df["return_12m"].mean(),
            "baseline_median_return": df["return_12m"].median(),
            "baseline_std_return": df["return_12m"].std(),
            "baseline_mean_mfe": df["mfe_12m"].mean(),
            "baseline_mean_mae": df["mae_12m"].mean(),
        }

    def compare(self, signal_summary: dict, baseline_summary: dict) -> dict:
        """
        Compare signal performance against baseline.

        Args:
            signal_summary: Summary stats from OutcomeMeasurer.summarize()
            baseline_summary: Stats from RandomBaseline.measure()

        Returns:
            Dict with comparison metrics including lift
        """
        if not signal_summary or not baseline_summary:
            return {}

        signal_win_rate = signal_summary.get("win_rate_12m", 0)
        baseline_win_rate = baseline_summary.get("baseline_win_rate", 0)

        # Lift: how much better is the signal than random?
        lift = signal_win_rate / baseline_win_rate if baseline_win_rate > 0 else None

        signal_return = signal_summary.get("mean_return_12m", 0)
        baseline_return = baseline_summary.get("baseline_mean_return", 0)

        return {
            "signal_win_rate": signal_win_rate,
            "baseline_win_rate": baseline_win_rate,
            "lift": lift,
            "signal_mean_return": signal_return,
            "baseline_mean_return": baseline_return,
            "return_advantage": signal_return - baseline_return,
        }
