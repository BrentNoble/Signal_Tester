"""Dow Theory 1-2-3 Bearish Breakdown signal implementation."""

import pandas as pd

from ..base import Signal
from classifiers.swings.swing_high import SwingHigh
from classifiers.swings.swing_low import SwingLow


class Dow123BearishBreakdown(Signal):
    """
    Dow Theory 1-2-3 Bearish Breakdown Signal (mirror of bullish breakout).

    Pattern:
    1. Swing High1 forms
    2. Swing Low forms (support level)
    3. Swing High2 forms where High2 < High1 (lower high confirms weakness)
    4. Price breaks below the Swing Low level

    This is the inverse of the bullish 1-2-3 breakout pattern.
    """

    name = "Dow123BearishBreakdown"
    description = "Dow 1-2-3: Lower high followed by breakdown below swing low"

    def __init__(self):
        self._swing_high = SwingHigh()
        self._swing_low = SwingLow()

    def generate(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate 1-2-3 bearish breakdown signals.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Boolean Series where True indicates a breakdown signal
        """
        self.validate_data(data)

        # Get swing points
        is_swing_high = self._swing_high.classify(data)
        is_swing_low = self._swing_low.classify(data)

        highs = data["High"]
        lows = data["Low"]
        closes = data["Close"]

        signal = pd.Series(False, index=data.index)

        # Build list of swing points: (index, type, price)
        # When both high and low occur on same bar (outside bar), order based on prior trend:
        # - After uptrend (last swing was low): HIGH comes first, then LOW
        # - After downtrend (last swing was high): LOW comes first, then HIGH
        swings = []
        last_swing_type = None
        for i in range(len(data)):
            is_low = is_swing_low.iloc[i]
            is_high = is_swing_high.iloc[i]

            if is_low and is_high:
                # Both on same bar - order based on prior trend
                if last_swing_type == "low":
                    # Was in uptrend: high forms first (continuation), then low (reversal)
                    swings.append((i, "high", highs.iloc[i]))
                    swings.append((i, "low", lows.iloc[i]))
                    last_swing_type = "low"
                else:
                    # Was in downtrend or unknown: low forms first, then high
                    swings.append((i, "low", lows.iloc[i]))
                    swings.append((i, "high", highs.iloc[i]))
                    last_swing_type = "high"
            elif is_low:
                swings.append((i, "low", lows.iloc[i]))
                last_swing_type = "low"
            elif is_high:
                swings.append((i, "high", highs.iloc[i]))
                last_swing_type = "high"

        # Track active 1-2-3 patterns waiting for breakdown
        active_patterns = []

        # Scan for High → Low → Lower High patterns
        for s in range(len(swings) - 2):
            p1, p2, p3 = swings[s], swings[s + 1], swings[s + 2]

            # Check for High → Low → High pattern
            if p1[1] == "high" and p2[1] == "low" and p3[1] == "high":
                high1_idx, high1_price = p1[0], p1[2]
                low_idx, low_price = p2[0], p2[2]
                high2_idx, high2_price = p3[0], p3[2]

                # Point 3 must be lower high
                if high2_price < high1_price:
                    active_patterns.append(
                        (high1_idx, high1_price, low_idx, low_price, high2_idx, high2_price)
                    )

        # Check for breakdowns after each pattern completes
        for pattern in active_patterns:
            high1_idx, high1_price, low_idx, low_price, high2_idx, high2_price = pattern

            # Look for breakdown after high2 forms
            for i in range(high2_idx + 1, len(data)):
                # Signal on first bar where LOW breaks below swing low
                if lows.iloc[i] < low_price:
                    # Only signal if we haven't already broken down
                    if i - 1 >= 0 and lows.iloc[i - 1] >= low_price:
                        signal.iloc[i] = True
                    break  # Stop looking for this pattern

                # Pattern invalidated if price makes new high above high1
                if highs.iloc[i] > high1_price:
                    break

        return signal
