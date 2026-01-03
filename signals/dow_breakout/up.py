"""Dow Theory 1-2-3 Bullish Breakout signal implementation."""

import pandas as pd

from ..base import Signal
from classifiers.swings.swing_high import SwingHigh
from classifiers.swings.swing_low import SwingLow


class Dow123BullishBreakout(Signal):
    """
    Dow Theory 1-2-3 Bullish Breakout Signal.

    Pattern:
    1. Swing Low₁ forms (Point 1)
    2. Swing High forms (Point 2 - resistance level)
    3. Swing Low₂ forms where Low₂ > Low₁ (Point 3 - higher low)
    4. Price breaks above the Swing High level

    This pattern indicates a potential bullish trend reversal/continuation.
    """

    name = "Dow123BullishBreakout"
    description = "Dow 1-2-3: Higher low followed by breakout above swing high"

    def __init__(self):
        self._swing_high = SwingHigh()
        self._swing_low = SwingLow()

    def generate(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate 1-2-3 bullish breakout signals.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Boolean Series where True indicates a breakout signal
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
        swings = []
        for i in range(len(data)):
            if is_swing_low.iloc[i]:
                swings.append((i, "low", lows.iloc[i]))
            if is_swing_high.iloc[i]:
                swings.append((i, "high", highs.iloc[i]))

        # Track active 1-2-3 patterns waiting for breakout
        # Each pattern: (low1_idx, low1_price, high_idx, high_price, low2_idx, low2_price)
        active_patterns = []

        # Scan for 1-2-3 patterns
        for s in range(len(swings) - 2):
            p1, p2, p3 = swings[s], swings[s + 1], swings[s + 2]

            # Check for Low → High → Low pattern
            if p1[1] == "low" and p2[1] == "high" and p3[1] == "low":
                low1_idx, low1_price = p1[0], p1[2]
                high_idx, high_price = p2[0], p2[2]
                low2_idx, low2_price = p3[0], p3[2]

                # Point 3 must be higher low
                if low2_price > low1_price:
                    active_patterns.append(
                        (low1_idx, low1_price, high_idx, high_price, low2_idx, low2_price)
                    )

        # Check for breakouts after each pattern completes
        for pattern in active_patterns:
            low1_idx, low1_price, high_idx, high_price, low2_idx, low2_price = pattern

            # Look for breakout after low2 forms
            for i in range(low2_idx + 1, len(data)):
                # Signal on first bar where HIGH breaks above swing high
                if highs.iloc[i] > high_price:
                    # Only signal if we haven't already broken out
                    if i - 1 >= 0 and highs.iloc[i - 1] <= high_price:
                        signal.iloc[i] = True
                    break  # Stop looking for this pattern

                # Pattern invalidated if price makes new low below low2
                if lows.iloc[i] < low2_price:
                    break

        return signal
