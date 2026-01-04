"""12-month outcome measurement for signal validation.

Measures what happens after each signal fires over a 12-month (52 week) holding period.
"""

from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
import numpy as np


@dataclass
class SignalOutcome:
    """Outcome metrics for a single signal instance."""

    # Signal identification
    signal_type: str
    signal_bar: int
    signal_date: Optional[str]  # Date if available
    entry_price: float

    # 12-month return metrics
    return_12m: float  # % return at 12 months
    profitable_12m: bool  # Was return positive?
    end_price: float  # Price at 12 months

    # MFE/MAE metrics
    mfe_12m: float  # Max favourable excursion (peak gain %)
    mfe_bar: int  # Bar when peak occurred (0-51)
    mfe_price: float  # Price at peak
    mae_12m: float  # Max adverse excursion (worst drawdown %)
    mae_bar: int  # Bar when trough occurred
    mae_price: float  # Price at trough

    # Exit signal metrics
    exit_signal_fired: bool  # Did exit signal fire within 12 months?
    exit_signal_bar: Optional[int]  # Bar when exit fired (if any)
    return_at_exit: Optional[float]  # % return if exited on signal

    # Derived comparisons
    left_on_table: float  # mfe_12m - return_12m
    exit_vs_hold: Optional[float]  # return_at_exit - return_12m
    exit_vs_mfe: Optional[float]  # return_at_exit - mfe_12m


class OutcomeMeasurer:
    """
    Measures 12-month outcomes for entry signals.

    For each signal instance, calculates:
    - Return at 12 months
    - Max favorable excursion (MFE) - peak gain
    - Max adverse excursion (MAE) - worst drawdown
    - Exit signal timing and returns
    """

    HOLDING_PERIOD = 52  # 52 weekly bars = 12 months

    def __init__(self, exit_signal_generator=None):
        """
        Args:
            exit_signal_generator: Optional callable that generates exit signals.
                                   Should return pd.Series of bool.
                                   If None, exit signal metrics will be None.
        """
        self.exit_signal_generator = exit_signal_generator

    def measure_single(
        self,
        data: pd.DataFrame,
        signal_bar: int,
        signal_type: str,
        exit_signals: pd.Series = None
    ) -> Optional[SignalOutcome]:
        """
        Measure outcome for a single signal instance.

        Args:
            data: DataFrame with OHLC data
            signal_bar: Bar index where signal fired
            signal_type: Name of the signal (e.g., "bullish_breakout")
            exit_signals: Optional Series of bool indicating exit signal bars

        Returns:
            SignalOutcome or None if insufficient data for 12-month measurement
        """
        # Check we have enough forward data
        end_bar = signal_bar + self.HOLDING_PERIOD
        if end_bar >= len(data):
            return None  # Insufficient data

        # Entry price is Close on signal bar
        entry_price = data["Close"].iloc[signal_bar]

        # Get date if index is datetime
        signal_date = None
        if hasattr(data.index, 'strftime'):
            try:
                signal_date = data.index[signal_bar].strftime('%Y-%m-%d')
            except:
                pass

        # 12-month window
        window = data.iloc[signal_bar:end_bar + 1]
        closes = window["Close"]
        highs = window["High"]
        lows = window["Low"]

        # End price and return
        end_price = closes.iloc[-1]
        return_12m = (end_price - entry_price) / entry_price * 100
        profitable_12m = return_12m > 0

        # MFE - Maximum Favorable Excursion (using High prices)
        peak_prices = highs.values
        peak_returns = (peak_prices - entry_price) / entry_price * 100
        mfe_idx = np.argmax(peak_returns)
        mfe_12m = peak_returns[mfe_idx]
        mfe_bar = mfe_idx
        mfe_price = peak_prices[mfe_idx]

        # MAE - Maximum Adverse Excursion (using Low prices)
        trough_prices = lows.values
        trough_returns = (trough_prices - entry_price) / entry_price * 100
        mae_idx = np.argmin(trough_returns)
        mae_12m = trough_returns[mae_idx]
        mae_bar = mae_idx
        mae_price = trough_prices[mae_idx]

        # Exit signal metrics
        exit_signal_fired = False
        exit_signal_bar = None
        return_at_exit = None

        if exit_signals is not None:
            # Look for exit signal within the holding period
            window_exits = exit_signals.iloc[signal_bar + 1:end_bar + 1]
            exit_bars = window_exits[window_exits].index

            if len(exit_bars) > 0:
                exit_signal_fired = True
                # Get the first exit signal bar (relative to signal_bar)
                first_exit = exit_bars[0]
                if isinstance(first_exit, int):
                    exit_signal_bar = first_exit - signal_bar
                    exit_price = data["Close"].iloc[first_exit]
                else:
                    # Handle datetime index
                    exit_signal_bar = data.index.get_loc(first_exit) - signal_bar
                    exit_price = data.loc[first_exit, "Close"]
                return_at_exit = (exit_price - entry_price) / entry_price * 100

        # Derived comparisons
        left_on_table = mfe_12m - return_12m
        exit_vs_hold = return_at_exit - return_12m if return_at_exit is not None else None
        exit_vs_mfe = return_at_exit - mfe_12m if return_at_exit is not None else None

        return SignalOutcome(
            signal_type=signal_type,
            signal_bar=signal_bar,
            signal_date=signal_date,
            entry_price=entry_price,
            return_12m=return_12m,
            profitable_12m=profitable_12m,
            end_price=end_price,
            mfe_12m=mfe_12m,
            mfe_bar=mfe_bar,
            mfe_price=mfe_price,
            mae_12m=mae_12m,
            mae_bar=mae_bar,
            mae_price=mae_price,
            exit_signal_fired=exit_signal_fired,
            exit_signal_bar=exit_signal_bar,
            return_at_exit=return_at_exit,
            left_on_table=left_on_table,
            exit_vs_hold=exit_vs_hold,
            exit_vs_mfe=exit_vs_mfe
        )

    def measure_all(
        self,
        data: pd.DataFrame,
        signals: pd.Series,
        signal_type: str,
        exit_signals: pd.Series = None
    ) -> List[SignalOutcome]:
        """
        Measure outcomes for all signal instances.

        Args:
            data: DataFrame with OHLC data
            signals: Boolean Series indicating signal bars
            signal_type: Name of the signal
            exit_signals: Optional Series of bool for exit signals

        Returns:
            List of SignalOutcome for each measurable signal
        """
        outcomes = []

        # Find all signal bars
        signal_bars = signals[signals].index
        if isinstance(signal_bars[0], int) if len(signal_bars) > 0 else True:
            # Integer index
            for bar in signal_bars:
                outcome = self.measure_single(data, bar, signal_type, exit_signals)
                if outcome is not None:
                    outcomes.append(outcome)
        else:
            # Datetime index - convert to positional
            for date in signal_bars:
                bar = data.index.get_loc(date)
                outcome = self.measure_single(data, bar, signal_type, exit_signals)
                if outcome is not None:
                    outcomes.append(outcome)

        return outcomes

    def to_dataframe(self, outcomes: List[SignalOutcome]) -> pd.DataFrame:
        """
        Convert list of outcomes to DataFrame.

        Args:
            outcomes: List of SignalOutcome objects

        Returns:
            DataFrame with one row per signal instance
        """
        if not outcomes:
            return pd.DataFrame()

        records = []
        for o in outcomes:
            records.append({
                "signal_type": o.signal_type,
                "signal_bar": o.signal_bar,
                "signal_date": o.signal_date,
                "entry_price": o.entry_price,
                "return_12m": o.return_12m,
                "profitable_12m": o.profitable_12m,
                "mfe_12m": o.mfe_12m,
                "mfe_bar": o.mfe_bar,
                "mae_12m": o.mae_12m,
                "mae_bar": o.mae_bar,
                "exit_signal_fired": o.exit_signal_fired,
                "exit_signal_bar": o.exit_signal_bar,
                "return_at_exit": o.return_at_exit,
                "left_on_table": o.left_on_table,
                "exit_vs_hold": o.exit_vs_hold,
                "exit_vs_mfe": o.exit_vs_mfe
            })

        return pd.DataFrame(records)

    def summarize(self, outcomes: List[SignalOutcome]) -> dict:
        """
        Calculate aggregate statistics across all outcomes.

        Args:
            outcomes: List of SignalOutcome objects

        Returns:
            Dict with aggregate statistics
        """
        if not outcomes:
            return {}

        df = self.to_dataframe(outcomes)

        # Calculate stats
        total = len(df)
        wins = df["profitable_12m"].sum()

        summary = {
            "total_signals": total,
            "win_rate_12m": wins / total * 100 if total > 0 else 0,
            "mean_return_12m": df["return_12m"].mean(),
            "median_return_12m": df["return_12m"].median(),
            "std_return_12m": df["return_12m"].std(),
            "mean_mfe_12m": df["mfe_12m"].mean(),
            "mean_mae_12m": df["mae_12m"].mean(),
            "mean_left_on_table": df["left_on_table"].mean(),
        }

        # Exit signal stats (only if any fired)
        exits = df[df["exit_signal_fired"]]
        if len(exits) > 0:
            summary["exit_fired_rate"] = len(exits) / total * 100
            summary["mean_exit_bar"] = exits["exit_signal_bar"].mean()

            # Count where exit beat hold
            exit_useful = exits[exits["exit_vs_hold"] > 0]
            summary["exit_useful_rate"] = len(exit_useful) / len(exits) * 100 if len(exits) > 0 else 0
            summary["mean_exit_vs_hold"] = exits["exit_vs_hold"].mean()
        else:
            summary["exit_fired_rate"] = 0
            summary["exit_useful_rate"] = None
            summary["mean_exit_vs_hold"] = None

        return summary
