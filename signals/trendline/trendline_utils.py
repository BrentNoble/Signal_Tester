"""Trendline geometry utilities."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd


@dataclass
class TrendLine:
    """
    Represents a downtrend trendline connecting swing high peaks.

    The line is defined by two points (start and end) and has a negative slope
    for downtrends. All intermediate peaks should be within tolerance of the line.
    """

    start_bar: int  # Bar index of first peak (turning point)
    start_price: float  # Price at first peak
    end_bar: int  # Bar index of last peak used for slope
    end_price: float  # Price at last peak
    slope: float  # Price change per bar (negative for downtrend)
    peaks: List[Tuple[int, float]] = field(default_factory=list)

    @classmethod
    def from_peaks(
        cls, peaks: List[Tuple[int, float]], tolerance_pct: float = 2.0
    ) -> Optional["TrendLine"]:
        """
        Construct a trendline from a list of peaks.

        The line is drawn from the first peak (turning point) to the last peak.
        All intermediate peaks must be within tolerance_pct of the line.

        Args:
            peaks: List of (bar_index, price) for swing highs.
                   Must be in chronological order with descending prices.
            tolerance_pct: Maximum % deviation allowed for intermediate peaks.

        Returns:
            TrendLine if valid, None if cannot form valid line.
        """
        if len(peaks) < 2:
            return None

        # All peaks must be descending
        for i in range(1, len(peaks)):
            if peaks[i][1] >= peaks[i - 1][1]:
                return None

        # Calculate slope from first to last peak
        p1 = peaks[0]
        pn = peaks[-1]

        if pn[0] == p1[0]:  # Same bar (shouldn't happen)
            return None

        slope = (pn[1] - p1[1]) / (pn[0] - p1[0])

        if slope >= 0:  # Must be negative (descending)
            return None

        line = cls(
            start_bar=p1[0],
            start_price=p1[1],
            end_bar=pn[0],
            end_price=pn[1],
            slope=slope,
            peaks=list(peaks),
        )

        # Validate all intermediate peaks within tolerance
        for bar_idx, price in peaks[1:-1]:  # Skip first and last (they define the line)
            deviation = line.deviation_pct(bar_idx, price)
            if deviation > tolerance_pct:
                return None

        return line

    def price_at_bar(self, bar_idx: int) -> float:
        """
        Calculate trendline price at given bar index.

        Uses linear projection from start point.
        """
        return self.start_price + self.slope * (bar_idx - self.start_bar)

    def deviation_pct(self, bar_idx: int, price: float) -> float:
        """
        Calculate % deviation of price from line at bar.

        Returns absolute deviation (always positive).
        Deviation = |actual - expected| / expected * 100
        """
        line_price = self.price_at_bar(bar_idx)
        if line_price == 0:
            return float("inf")
        return abs(price - line_price) / line_price * 100

    def is_price_above_line(self, bar_idx: int, price: float) -> bool:
        """Check if price is above the trendline at bar."""
        return price > self.price_at_bar(bar_idx)

    def is_price_below_line(self, bar_idx: int, price: float) -> bool:
        """Check if price is below the trendline at bar."""
        return price < self.price_at_bar(bar_idx)

    def is_break_above(
        self, bar_idx: int, high: float, threshold_pct: float = 2.0
    ) -> bool:
        """
        Check if high breaks above line by threshold %.

        A break occurs when HIGH exceeds the line by more than threshold_pct.
        """
        line_price = self.price_at_bar(bar_idx)
        if high <= line_price:
            return False
        penetration_pct = (high - line_price) / line_price * 100
        return penetration_pct > threshold_pct

    def is_break_below(
        self, bar_idx: int, low: float, threshold_pct: float = 2.0
    ) -> bool:
        """
        Check if low breaks below line by threshold %.

        For downtrends, this indicates acceleration (price falling faster).
        """
        line_price = self.price_at_bar(bar_idx)
        if low >= line_price:
            return False
        penetration_pct = (line_price - low) / line_price * 100
        return penetration_pct > threshold_pct

    def validate_bars(
        self,
        highs: pd.Series,
        start_idx: int,
        end_idx: int,
        tolerance_pct: float = 2.0,
    ) -> bool:
        """
        Validate that all bars from start_idx to end_idx have HIGH within tolerance.

        For a valid downtrend line, no bar's HIGH should penetrate the line
        by more than tolerance_pct.

        Args:
            highs: Series of high prices indexed by position.
            start_idx: Start bar index (inclusive).
            end_idx: End bar index (inclusive).
            tolerance_pct: Maximum % above line allowed.

        Returns:
            True if all bars are within tolerance.
        """
        for i in range(start_idx, min(end_idx + 1, len(highs))):
            line_price = self.price_at_bar(i)
            bar_high = highs.iloc[i]

            # Check if bar HIGH is above line
            if bar_high > line_price:
                penetration_pct = (bar_high - line_price) / line_price * 100
                if penetration_pct > tolerance_pct:
                    return False

        return True

    def try_steepen(
        self, new_peak: Tuple[int, float], tolerance_pct: float = 2.0
    ) -> Optional["TrendLine"]:
        """
        Attempt to create steeper line including new peak.

        For Golden Rule 5: always use steepest valid line.
        If new peak allows a steeper (more negative slope) line that still
        passes validation, return the new line.

        Args:
            new_peak: (bar_index, price) of new swing high.
            tolerance_pct: Tolerance for peak validation.

        Returns:
            New steeper TrendLine if valid, None otherwise.
        """
        new_bar, new_price = new_peak

        # New peak must be lower than last peak
        if self.peaks and new_price >= self.peaks[-1][1]:
            return None

        # New peak must be after current end
        if new_bar <= self.end_bar:
            return None

        # Calculate new slope from original turning point to new peak
        new_slope = (new_price - self.start_price) / (new_bar - self.start_bar)

        # Must be steeper (more negative) than current
        if new_slope >= self.slope:
            return None

        # Create new line with all peaks
        new_peaks = list(self.peaks) + [new_peak]

        return TrendLine.from_peaks(new_peaks, tolerance_pct)

    def is_steeper_than(self, other: "TrendLine") -> bool:
        """
        Check if this line is steeper than other.

        For downtrend, steeper = more negative slope.
        """
        return self.slope < other.slope
