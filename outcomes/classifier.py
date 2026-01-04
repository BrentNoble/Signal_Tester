"""Dow trend state tracker for signal analysis.

Tracks trend state based on Dow Theory patterns. Used by:
- Signal 2 (Downtrend Reversal) to detect when in confirmed downtrend
- Outcome measurement to track when exit signals fire
"""

from enum import Enum
import pandas as pd

from classifiers.swings.swing_high import SwingHigh
from classifiers.swings.swing_low import SwingLow


class DowTrendState(Enum):
    """Dow Theory trend state."""
    UNKNOWN = "unknown"
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"


class DowTrendTracker:
    """
    Tracks Dow trend state based on swing patterns.

    States:
    - UNKNOWN: No confirmed trend
    - UPTREND: Making higher highs and higher lows
    - DOWNTREND: Making lower highs and lower lows

    Trend breaks when:
    - Uptrend: LOW breaks below last swing low, OR swing high forms lower than previous
    - Downtrend: HIGH breaks above last swing high, OR swing low forms higher than previous
    """

    def __init__(self):
        self._swing_high = SwingHigh()
        self._swing_low = SwingLow()

    def classify(self, data: pd.DataFrame, bullish_signals: pd.Series = None,
                 bearish_signals: pd.Series = None) -> pd.DataFrame:
        """
        Classify each bar's trend state.

        Args:
            data: DataFrame with OHLC data
            bullish_signals: Optional Series of bool indicating bullish signal bars
            bearish_signals: Optional Series of bool indicating bearish signal bars

        Returns:
            DataFrame with columns:
            - bar_idx: int
            - state: str ("unknown", "uptrend", "downtrend")
            - support_level: float (swing low price for uptrend tracking)
            - resistance_level: float (swing high price for downtrend tracking)
        """
        is_swing_high = self._swing_high.classify(data)
        is_swing_low = self._swing_low.classify(data)

        lows = data["Low"]
        highs = data["High"]

        # Use empty signals if not provided
        if bullish_signals is None:
            bullish_signals = pd.Series(False, index=data.index)
        if bearish_signals is None:
            bearish_signals = pd.Series(False, index=data.index)

        states = []
        current_state = DowTrendState.UNKNOWN

        # Tracking variables
        support_level = None  # For uptrend: swing low we're tracking
        resistance_level = None  # For downtrend: swing high we're tracking
        last_swing_high = None  # Most recent swing high price
        last_swing_low = None  # Most recent swing low price
        trend_high = None  # Highest swing high in current uptrend
        trend_low = None  # Lowest swing low in current downtrend

        for i in range(len(data)):
            # Update swing tracking
            if is_swing_low.iloc[i]:
                last_swing_low = lows.iloc[i]
            if is_swing_high.iloc[i]:
                last_swing_high = highs.iloc[i]

            # Check for state transitions
            if current_state == DowTrendState.UNKNOWN:
                # Enter uptrend on bullish signal
                if bullish_signals.iloc[i]:
                    current_state = DowTrendState.UPTREND
                    support_level = last_swing_low
                    trend_high = last_swing_high
                    resistance_level = None
                    trend_low = None
                # Enter downtrend on bearish signal
                elif bearish_signals.iloc[i]:
                    current_state = DowTrendState.DOWNTREND
                    resistance_level = last_swing_high
                    trend_low = last_swing_low
                    support_level = None
                    trend_high = None

            elif current_state == DowTrendState.UPTREND:
                trend_broken = False

                # Break on LOW below support
                if support_level is not None and lows.iloc[i] < support_level:
                    trend_broken = True

                # Break on lower high (swing high below previous trend high)
                if is_swing_high.iloc[i] and trend_high is not None:
                    if highs.iloc[i] < trend_high:
                        trend_broken = True
                    else:
                        trend_high = highs.iloc[i]

                # Update support on new higher low
                if is_swing_low.iloc[i] and not trend_broken:
                    if support_level is None or lows.iloc[i] > support_level:
                        support_level = lows.iloc[i]

                if trend_broken:
                    current_state = DowTrendState.UNKNOWN
                    support_level = None
                    trend_high = None

            elif current_state == DowTrendState.DOWNTREND:
                trend_broken = False

                # Break on HIGH above resistance
                if resistance_level is not None and highs.iloc[i] > resistance_level:
                    trend_broken = True

                # Break on higher low (swing low above previous trend low)
                if is_swing_low.iloc[i] and trend_low is not None:
                    if lows.iloc[i] > trend_low:
                        trend_broken = True
                    else:
                        trend_low = lows.iloc[i]

                # Update resistance on new lower high
                if is_swing_high.iloc[i] and not trend_broken:
                    if resistance_level is None or highs.iloc[i] < resistance_level:
                        resistance_level = highs.iloc[i]

                if trend_broken:
                    current_state = DowTrendState.UNKNOWN
                    resistance_level = None
                    trend_low = None

            states.append({
                "bar_idx": i,
                "state": current_state.value,
                "support_level": support_level,
                "resistance_level": resistance_level
            })

        return pd.DataFrame(states)

    def is_in_downtrend(self, data: pd.DataFrame, bearish_signals: pd.Series) -> pd.Series:
        """
        Return a boolean Series indicating which bars are in a confirmed downtrend.

        Used by Signal 2 to know when to watch for reversal.

        Args:
            data: DataFrame with OHLC data
            bearish_signals: Series of bool indicating bearish breakdown bars

        Returns:
            Series of bool - True when in downtrend
        """
        states_df = self.classify(data, bearish_signals=bearish_signals)
        return states_df["state"] == "downtrend"
