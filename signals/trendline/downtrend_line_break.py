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
    2. Need 3 peaks; draw from highest high within lookback window (turning point)
    3. All peaks AND bars must be within 2% of line during formation
    4. Cannot flatten line (steepening only); false break handling is TODO
    5. Always use steepest valid line; acceleration pivot disabled by default

    Signal fires when:
    - Bar HIGH exceeds the projected trendline price by more than break_threshold_pct
    - Previous bar HIGH was NOT a break (first-bar rule)

    Known limitations:
    - False break recovery (Rule 4): After signal fires, pattern resets fully.
      Future enhancement would track original turning point for resumption.
    - Acceleration pivot (Rule 5): Disabled by default (track_acceleration=False)
      as it can trigger false resets when price accelerates away from line.
    """

    name = "DowntrendLineBreak"
    description = "Entry on 2%+ break above validated downtrend trendline"

    def __init__(
        self,
        tolerance_pct: float = 2.0,
        min_peaks: int = 3,
        break_threshold_pct: float = 2.0,
        track_acceleration: bool = False,
        turning_point_lookback: int = 52,
        debug: bool = False,
    ):
        """
        Initialize the signal.

        Args:
            tolerance_pct: Maximum % deviation allowed for peaks and bars (Golden Rule 3).
            min_peaks: Minimum peaks required for valid line (Golden Rule 2).
            break_threshold_pct: Penetration required to trigger break signal.
            track_acceleration: Pivot to steeper lines on acceleration (Golden Rule 5).
            turning_point_lookback: Max bars to look back for turning point (default 52 = 1 year).
            debug: Print diagnostic messages during signal generation.
        """
        self._tolerance_pct = tolerance_pct
        self._min_peaks = min_peaks
        self._break_threshold_pct = break_threshold_pct
        self._track_acceleration = track_acceleration
        self._turning_point_lookback = turning_point_lookback
        self._debug = debug

        # Dependencies
        self._bearish_breakdown = Dow123BearishBreakdown()
        self._swing_high = SwingHigh()

    def _debug_log(self, bar: int, msg: str):
        """Print debug message if debug mode enabled."""
        if self._debug:
            print(f"  [Bar {bar}] {msg}")

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
        just_steepened: bool = False  # Skip acceleration check on steepen bar

        # Track swing highs for finding turning point
        # Pruned periodically to prevent unbounded memory growth
        recent_swing_highs: List[Tuple[int, float]] = []

        for i in range(len(data)):
            # Track swing highs for finding turning point
            if is_swing_high.iloc[i]:
                recent_swing_highs.append((i, highs.iloc[i]))

            # Prune old swing highs outside lookback window to prevent memory growth
            cutoff = i - self._turning_point_lookback - 1
            if cutoff > 0 and recent_swing_highs and recent_swing_highs[0][0] < cutoff:
                recent_swing_highs = [
                    (idx, price) for idx, price in recent_swing_highs
                    if idx >= cutoff
                ]

            # === STATE: WAITING_FOR_DOWNTREND ===
            if state == TrendlineState.WAITING_FOR_DOWNTREND:
                if bearish_signals.iloc[i]:
                    self._debug_log(i, "Bearish breakdown detected")
                    # Find turning point: highest swing high within lookback before this bar
                    turning_point = self._find_turning_point(
                        recent_swing_highs, i, self._turning_point_lookback
                    )

                    if turning_point is not None:
                        self._debug_log(
                            i, f"Turning point: bar {turning_point[0]} @ {turning_point[1]}"
                        )
                        state = TrendlineState.COLLECTING_PEAKS
                        peaks = [turning_point]
                        current_line = None

            # === STATE: COLLECTING_PEAKS ===
            elif state == TrendlineState.COLLECTING_PEAKS:
                if is_swing_high.iloc[i]:
                    peak_price = highs.iloc[i]

                    # Must be lower than previous peak
                    if peak_price < peaks[-1][1]:
                        peaks.append((i, peak_price))
                        self._debug_log(i, f"Added peak {len(peaks)} @ {peak_price}")

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
                                    self._debug_log(
                                        i,
                                        f"Line formed: slope={current_line.slope:.4f}"
                                    )
                                    # Note: No break check needed here - bar i is a peak
                                    # that defines the line endpoint, so it cannot break
                                    # above the line. Break detection starts next bar.
                    # else: Higher high - just skip adding this peak
                    # Only invalidate if it breaks above turning point (checked below)

                # Check for price breaking above turning point (invalidation)
                if turning_point is not None and highs.iloc[i] > turning_point[1]:
                    state = TrendlineState.WAITING_FOR_DOWNTREND
                    turning_point = None
                    peaks = []
                    current_line = None

            # === STATE: WATCHING_FOR_BREAK ===
            elif state == TrendlineState.WATCHING_FOR_BREAK:
                just_steepened = False  # Reset at start of each bar

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
                        line_price = current_line.price_at_bar(i)
                        self._debug_log(
                            i,
                            f"SIGNAL! HIGH={highs.iloc[i]:.2f} > "
                            f"line={line_price:.2f} + {self._break_threshold_pct}%"
                        )
                        # Reset to look for next pattern
                        # TODO: Golden Rule 4 says on false break + continuation,
                        # redraw from original turning point. Current implementation
                        # resets fully - a new Dow123BearishBreakdown would be needed.
                        state = TrendlineState.WAITING_FOR_DOWNTREND
                        turning_point = None
                        peaks = []
                        current_line = None
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
                                just_steepened = True
                                self._debug_log(
                                    i,
                                    f"Steepened line: new slope={steeper.slope:.4f}"
                                )
                                # Skip remaining checks for this bar - new line is at peak
                                continue

                # Handle acceleration (Golden Rule 5)
                # Skip acceleration on bar where we just steepened
                if self._track_acceleration and not just_steepened:
                    if current_line.is_break_below(
                        i, lows.iloc[i], self._break_threshold_pct
                    ):
                        # Price accelerating away - pivot to steeper line.
                        # NOTE: This sets last_peak as new turning point, which means
                        # the invalidation threshold changes. This is intentional -
                        # we're now tracking a steeper downtrend segment.
                        if len(peaks) >= 2:
                            last_peak = peaks[-1]
                            turning_point = last_peak
                            peaks = [last_peak]
                            current_line = None
                            state = TrendlineState.COLLECTING_PEAKS

                # Check bar tolerance (Golden Rule 3)
                # If a bar penetrates between tolerance_pct and break_threshold_pct,
                # it's in a gray zone - not a valid break but exceeds strict tolerance.
                # We allow minor penetrations since the line was validated at formation.
                # The pattern only ends on: true break (> break_threshold_pct) or
                # price exceeding turning point (checked below).
                #
                # Note: If tolerance_pct == break_threshold_pct (default), this section
                # never triggers because any penetration > tolerance would be a break.

                # Check for trend reversal (price breaks above turning point)
                if turning_point is not None and highs.iloc[i] > turning_point[1]:
                    state = TrendlineState.WAITING_FOR_DOWNTREND
                    turning_point = None
                    peaks = []
                    current_line = None

        return signal

    def _find_turning_point(
        self, swing_highs: List[Tuple[int, float]], breakdown_bar: int, lookback: int
    ) -> Optional[Tuple[int, float]]:
        """
        Find the turning point (highest swing high) within lookback before breakdown.

        The turning point is the highest swing high that occurred within the
        lookback window before the downtrend was confirmed. Using a lookback
        window ensures we use the swing high from the current pattern, not an
        ancient high from much earlier price action.

        Args:
            swing_highs: List of (bar_idx, price) for all swing highs.
            breakdown_bar: Bar index where downtrend was confirmed.
            lookback: Maximum bars to look back from breakdown_bar.

        Returns:
            (bar_idx, price) of highest swing high in window, or None.
        """
        # Filter swing highs within lookback window before breakdown
        earliest_bar = max(0, breakdown_bar - lookback)
        candidates = [
            (idx, price)
            for idx, price in swing_highs
            if earliest_bar <= idx < breakdown_bar
        ]

        if not candidates:
            return None

        # Return the highest within the lookback window
        return max(candidates, key=lambda x: x[1])
