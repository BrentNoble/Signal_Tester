"""Dow Theory Downtrend Reversal signal implementation.

Signal 2: Mean Reversion entry when a confirmed downtrend breaks.
"""

import pandas as pd

from ..base import Signal
from classifiers.swings.swing_high import SwingHigh
from classifiers.swings.swing_low import SwingLow
from .down import Dow123BearishBreakdown


class DowntrendReversal(Signal):
    """
    Downtrend Reversal Signal (Mean Reversion).

    Entry when a confirmed downtrend breaks:
    1. Downtrend confirmed via Dow123BearishBreakdown
    2. Entry when EITHER:
       - Swing Low forms HIGHER than previous Swing Low (higher low), OR
       - Bar HIGH breaks above the last Swing High

    This is a mean reversion signal for buying beaten-down stocks
    when selling exhaustion is indicated.
    """

    name = "DowntrendReversal"
    description = "Entry on downtrend break: higher low or breakout above swing high"

    def __init__(self):
        self._swing_high = SwingHigh()
        self._swing_low = SwingLow()
        self._bearish_breakdown = Dow123BearishBreakdown()

    def generate(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate downtrend reversal signals.

        Args:
            data: DataFrame with OHLC data

        Returns:
            Boolean Series where True indicates a reversal entry signal
        """
        self.validate_data(data)

        # Get swing points
        is_swing_high = self._swing_high.classify(data)
        is_swing_low = self._swing_low.classify(data)

        # Get bearish breakdown signals (marks start of downtrend)
        bearish_signals = self._bearish_breakdown.generate(data)

        highs = data["High"]
        lows = data["Low"]

        signal = pd.Series(False, index=data.index)

        # State tracking
        in_downtrend = False
        last_swing_high_price = None  # Resistance level to break above
        last_swing_low_price = None  # Previous swing low for higher low detection
        trend_low_price = None  # Lowest swing low in current downtrend

        for i in range(len(data)):
            # Update swing prices BEFORE checking for signals
            # (swing is confirmed at this bar)
            current_swing_high = None
            current_swing_low = None

            if is_swing_high.iloc[i]:
                current_swing_high = highs.iloc[i]
            if is_swing_low.iloc[i]:
                current_swing_low = lows.iloc[i]

            # Check for downtrend entry
            if bearish_signals.iloc[i] and not in_downtrend:
                in_downtrend = True
                last_swing_high_price = current_swing_high or last_swing_high_price
                trend_low_price = current_swing_low or last_swing_low_price
                # Continue to next bar - signal fires on reversal, not on breakdown

            elif in_downtrend:
                reversal_triggered = False

                # Check for breakout above last swing high (resistance)
                if last_swing_high_price is not None:
                    if highs.iloc[i] > last_swing_high_price:
                        # Only signal on the first bar that breaks
                        if i > 0 and highs.iloc[i - 1] <= last_swing_high_price:
                            reversal_triggered = True

                # Check for higher low (new swing low above trend low)
                if current_swing_low is not None and trend_low_price is not None:
                    if current_swing_low > trend_low_price:
                        reversal_triggered = True

                if reversal_triggered:
                    signal.iloc[i] = True
                    in_downtrend = False
                    last_swing_high_price = None
                    trend_low_price = None
                else:
                    # Update tracking within downtrend
                    if current_swing_high is not None:
                        # Track the most recent swing high as resistance
                        last_swing_high_price = current_swing_high

                    if current_swing_low is not None:
                        # Track lower lows
                        if trend_low_price is None or current_swing_low < trend_low_price:
                            trend_low_price = current_swing_low

            # Always update last swing prices for next iteration
            if current_swing_high is not None:
                last_swing_high_price = current_swing_high
            if current_swing_low is not None:
                last_swing_low_price = current_swing_low

        return signal
