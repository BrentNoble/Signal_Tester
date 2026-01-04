"""TwelveBar Breakout signal implementation."""

import pandas as pd

from ..base import Signal
from classifiers.swings.swing_low import SwingLow


class TwelveBarBreakout(Signal):
    """
    Twelve Bar Consolidation Breakout Signal.

    Pattern:
    1. Valid swing low forms - this is Bar 0. Valid means: previous swing low
       is NOT lower than current (i.e., current is at or below prior).
       This filters out "higher lows" which indicate mid-uptrend continuation.
    2. Track highest HIGH in bars 0-11 (12-bar window) as resistance
    3. Signal fires on first bar (12+) where HIGH > resistance

    Invalidation:
    - Any bar's LOW < anchor swing low price during window kills the pattern
    """

    name = "TwelveBarBreakout"
    description = "Breakout above 12-bar consolidation resistance from valid swing low"

    WINDOW_SIZE = 12  # Bars 0-11

    def __init__(self):
        self._swing_low = SwingLow()

    def generate(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate twelve bar breakout signals.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Boolean Series where True indicates a breakout signal
        """
        self.validate_data(data)

        is_swing_low = self._swing_low.classify(data)
        highs = data["High"]
        lows = data["Low"]

        signal = pd.Series(False, index=data.index)

        # Find all swing lows with their prices
        swing_lows = []  # List of (index, price)
        for i in range(len(data)):
            if is_swing_low.iloc[i]:
                swing_lows.append((i, lows.iloc[i]))

        # Identify valid anchors (previous swing low is not lower)
        valid_anchors = []  # List of (index, price)
        for idx, (swing_idx, swing_price) in enumerate(swing_lows):
            is_valid = True
            # Check only the immediately preceding swing low
            if idx > 0:
                prior_idx, prior_price = swing_lows[idx - 1]
                if prior_price < swing_price:
                    # Previous swing low is lower (this is a "higher low") - not valid anchor
                    is_valid = False
            if is_valid:
                valid_anchors.append((swing_idx, swing_price))

        # Track each valid anchor for breakout
        for anchor_idx, anchor_price in valid_anchors:
            window_end = anchor_idx + self.WINDOW_SIZE - 1  # Bar 11 (inclusive)

            # Need at least the full window plus one bar for breakout
            if window_end >= len(data) - 1:
                continue

            # Check for invalidation during window and find resistance
            invalidated = False
            resistance = highs.iloc[anchor_idx]  # Start with bar 0's high

            for i in range(anchor_idx, min(anchor_idx + self.WINDOW_SIZE, len(data))):
                # Check invalidation
                if lows.iloc[i] < anchor_price:
                    invalidated = True
                    break
                # Track highest high
                if highs.iloc[i] > resistance:
                    resistance = highs.iloc[i]

            if invalidated:
                continue

            # Look for breakout starting at bar 12 (index anchor_idx + 12)
            breakout_start = anchor_idx + self.WINDOW_SIZE
            for i in range(breakout_start, len(data)):
                # Check if this bar breaks out
                if highs.iloc[i] > resistance:
                    signal.iloc[i] = True
                    break  # Only signal once per pattern

                # Check if pattern invalidated (price drops below anchor)
                if lows.iloc[i] < anchor_price:
                    break

        return signal
