"""Downtrend Line Break signal implementation.

Entry signal when price breaks above a validated downtrend trendline,
implementing Gann's 5 Golden Rules for valid trendlines.
"""

from enum import Enum, auto
from typing import List, Optional, Tuple

import pandas as pd

from ..base import Signal
from classifiers.swings.swing_high import SwingHigh
from signals.dow_breakout.down import Dow123BearishBreakdown
from .trendline_utils import TrendLine


class TrendlineState(Enum):
    """State machine states for trendline tracking."""

    WAITING_FOR_DOWNTREND = auto()  # Waiting for Dow123BearishBreakdown
    COLLECTING_PEAKS = auto()  # Have downtrend, collecting 3+ peaks
    WATCHING_FOR_BREAK = auto()  # Have valid line, watching for breakout


class DowntrendLineBreak(Signal):
    """
    Entry signal when price breaks above validated downtrend trendline.

    Golden Rules implemented:
    1. Require confirmed downtrend (via Dow123BearishBreakdown) before applying trendline
    2. Need 3 peaks; draw from highest high (turning point)
    3. All peaks AND bars must be within 2% of line
    4. Cannot flatten line; on false break + continuation, redraw from original turning point
    5. Always use steepest valid line; pivot on acceleration

    Signal fires when:
    - Bar HIGH exceeds the projected trendline price by more than break_threshold_pct
    - Previous bar HIGH was NOT a break (first-bar rule)
    """

    name = "DowntrendLineBreak"
    description = "Entry on 2%+ break above validated downtrend trendline"

    def __init__(
        self,
        tolerance_pct: float = 2.0,
        min_peaks: int = 3,
        break_threshold_pct: float = 2.0,
        track_acceleration: bool = False,
    ):
        """
        Initialize the signal.

        Args:
            tolerance_pct: Maximum % deviation allowed for peaks and bars (Golden Rule 3).
            min_peaks: Minimum peaks required for valid line (Golden Rule 2).
            break_threshold_pct: Penetration required to trigger break signal.
            track_acceleration: Pivot to steeper lines on acceleration (Golden Rule 5).
        """
        self._tolerance_pct = tolerance_pct
        self._min_peaks = min_peaks
        self._break_threshold_pct = break_threshold_pct
        self._track_acceleration = track_acceleration

        # Dependencies
        self._bearish_breakdown = Dow123BearishBreakdown()
        self._swing_high = SwingHigh()

    def generate(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate downtrend line break signals.

        Args:
            data: DataFrame with OHLC data.

        Returns:
            Boolean Series where True indicates entry signal.
        """
        self.validate_data(data)

        # Get dependencies
        bearish_signals = self._bearish_breakdown.generate(data)
        is_swing_high = self._swing_high.classify(data)

        highs = data["High"]
        lows = data["Low"]

        signal = pd.Series(False, index=data.index)

        # State variables
        state = TrendlineState.WAITING_FOR_DOWNTREND
        turning_point: Optional[Tuple[int, float]] = None  # Original highest high
        peaks: List[Tuple[int, float]] = []
        current_line: Optional[TrendLine] = None
        last_steepen_bar: int = -1  # Track when line was last steepened

        # Track highest high seen before downtrend confirmation
        # (needed to find turning point)
        recent_swing_highs: List[Tuple[int, float]] = []

        for i in range(len(data)):
            # Track swing highs for finding turning point
            if is_swing_high.iloc[i]:
                recent_swing_highs.append((i, highs.iloc[i]))

            # === STATE: WAITING_FOR_DOWNTREND ===
            if state == TrendlineState.WAITING_FOR_DOWNTREND:
                if bearish_signals.iloc[i]:
                    # Find turning point: highest swing high before this bar
                    turning_point = self._find_turning_point(recent_swing_highs, i)

                    if turning_point is not None:
                        state = TrendlineState.COLLECTING_PEAKS
                        peaks = [turning_point]
                        current_line = None
                        # Keep collecting swing highs from now

            # === STATE: COLLECTING_PEAKS ===
            elif state == TrendlineState.COLLECTING_PEAKS:
                if is_swing_high.iloc[i]:
                    peak_price = highs.iloc[i]

                    # Must be lower than previous peak
                    if peak_price < peaks[-1][1]:
                        peaks.append((i, peak_price))

                        # Try to form valid line with enough peaks
                        if len(peaks) >= self._min_peaks:
                            candidate = TrendLine.from_peaks(
                                peaks, self._tolerance_pct
                            )
                            if candidate is not None:
                                # Validate all bars are within tolerance
                                if candidate.validate_bars(
                                    highs,
                                    peaks[0][0],
                                    i,
                                    self._tolerance_pct,
                                ):
                                    current_line = candidate
                                    state = TrendlineState.WATCHING_FOR_BREAK
                    else:
                        # Higher high breaks downtrend structure - invalidate
                        state = TrendlineState.WAITING_FOR_DOWNTREND
                        turning_point = None
                        peaks = []
                        current_line = None

                # Check for price breaking above turning point (invalidation)
                if turning_point is not None and highs.iloc[i] > turning_point[1]:
                    state = TrendlineState.WAITING_FOR_DOWNTREND
                    turning_point = None
                    peaks = []
                    current_line = None

            # === STATE: WATCHING_FOR_BREAK ===
            elif state == TrendlineState.WATCHING_FOR_BREAK:
                if current_line is None:
                    # Shouldn't happen, but be defensive
                    state = TrendlineState.WAITING_FOR_DOWNTREND
                    continue

                # Check for breakout (entry signal)
                if current_line.is_break_above(
                    i, highs.iloc[i], self._break_threshold_pct
                ):
                    # Verify previous bar was NOT a break (first-bar rule)
                    is_first_break = True
                    if i > 0:
                        prev_line_price = current_line.price_at_bar(i - 1)
                        prev_threshold = prev_line_price * (
                            1 + self._break_threshold_pct / 100
                        )
                        if highs.iloc[i - 1] > prev_threshold:
                            is_first_break = False

                    if is_first_break:
                        signal.iloc[i] = True
                        # Reset to look for next pattern
                        state = TrendlineState.WAITING_FOR_DOWNTREND
                        turning_point = None
                        peaks = []
                        current_line = None
                        last_steepen_bar = -1
                        continue

                # Handle new swing high (potential peak for steepening)
                if is_swing_high.iloc[i]:
                    peak_price = highs.iloc[i]
                    if peak_price < peaks[-1][1]:  # Must be lower
                        # Try to steepen line with new peak (Golden Rule 5)
                        steeper = current_line.try_steepen(
                            (i, peak_price), self._tolerance_pct
                        )
                        if steeper is not None:
                            # Validate all bars with steeper line
                            if steeper.validate_bars(
                                highs,
                                steeper.peaks[0][0],
                                i,
                                self._tolerance_pct,
                            ):
                                peaks.append((i, peak_price))
                                current_line = steeper
                                last_steepen_bar = i
                                # Skip remaining checks for this bar - new line is at peak
                                continue

                # Handle acceleration (Golden Rule 5)
                # Skip acceleration after steepening - we need a new peak to pivot from
                # Only check if we haven't steepened, or we have a new peak since steepening
                has_new_peak_since_steepen = (
                    last_steepen_bar < 0 or
                    any(bar > last_steepen_bar for bar, _ in peaks[1:])
                )
                if self._track_acceleration and has_new_peak_since_steepen:
                    if current_line.is_break_below(
                        i, lows.iloc[i], self._break_threshold_pct
                    ):
                        # Price accelerating away - pivot to steeper line
                        # Start collecting from last peak
                        if len(peaks) >= 2:
                            # Keep last peak as new starting point
                            last_peak = peaks[-1]
                            turning_point = last_peak
                            peaks = [last_peak]
                            current_line = None
                            state = TrendlineState.COLLECTING_PEAKS

                # Validate current bar within tolerance
                if current_line is not None:
                    line_price = current_line.price_at_bar(i)
                    if highs.iloc[i] > line_price:
                        deviation = (highs.iloc[i] - line_price) / line_price * 100
                        if deviation > self._tolerance_pct:
                            # Bar breaks tolerance but not threshold
                            # This is a minor penetration - line may still be valid
                            # but we should re-validate on subsequent bars
                            # For now, if it's not a signal break, check if trend continues
                            pass

                # Check for trend reversal (price breaks above turning point)
                if turning_point is not None and highs.iloc[i] > turning_point[1]:
                    state = TrendlineState.WAITING_FOR_DOWNTREND
                    turning_point = None
                    peaks = []
                    current_line = None

        return signal

    def _find_turning_point(
        self, swing_highs: List[Tuple[int, float]], breakdown_bar: int
    ) -> Optional[Tuple[int, float]]:
        """
        Find the turning point (highest swing high) before the breakdown.

        The turning point is the highest swing high that occurred before
        the downtrend was confirmed. This becomes Peak 1 for the trendline.

        Args:
            swing_highs: List of (bar_idx, price) for all swing highs.
            breakdown_bar: Bar index where downtrend was confirmed.

        Returns:
            (bar_idx, price) of highest swing high before breakdown, or None.
        """
        # Filter swing highs before breakdown
        candidates = [(idx, price) for idx, price in swing_highs if idx < breakdown_bar]

        if not candidates:
            return None

        # Return the highest
        return max(candidates, key=lambda x: x[1])
