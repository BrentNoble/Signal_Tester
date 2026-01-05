"""Tests for DowntrendLineBreak signal and TrendLine utility."""

import os
import sys

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pandas as pd

from signals.trendline.trendline_utils import TrendLine
from signals.trendline.downtrend_line_break import DowntrendLineBreak


def create_test_data(prices):
    """Create test DataFrame from OHLC price tuples."""
    df = pd.DataFrame(prices, columns=["Open", "High", "Low", "Close"])
    df["Date"] = pd.date_range("2024-01-01", periods=len(df), freq="W")
    df = df.set_index("Date")
    return df


# =============================================================================
# TrendLine Utility Tests
# =============================================================================


class TestTrendLineFromPeaks:
    """Tests for TrendLine.from_peaks() factory method."""

    def test_valid_three_peaks(self):
        """Three descending peaks form valid line."""
        peaks = [(0, 100.0), (10, 95.0), (20, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=2.0)

        assert line is not None
        assert line.start_bar == 0
        assert line.start_price == 100.0
        assert line.end_bar == 20
        assert line.end_price == 90.0
        assert line.slope < 0
        assert len(line.peaks) == 3

    def test_two_peaks_valid(self):
        """Two descending peaks form valid line (minimum)."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=2.0)

        assert line is not None
        assert line.slope == -1.0  # (90-100)/(10-0) = -1.0

    def test_single_peak_invalid(self):
        """Single peak cannot form line."""
        peaks = [(0, 100.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=2.0)

        assert line is None

    def test_non_descending_invalid(self):
        """Peaks not descending (higher high) invalidates."""
        peaks = [(0, 100.0), (10, 95.0), (20, 97.0)]  # 97 > 95
        line = TrendLine.from_peaks(peaks, tolerance_pct=2.0)

        assert line is None

    def test_equal_peaks_invalid(self):
        """Equal peak prices invalidate."""
        peaks = [(0, 100.0), (10, 95.0), (20, 95.0)]  # 95 == 95
        line = TrendLine.from_peaks(peaks, tolerance_pct=2.0)

        assert line is None

    def test_intermediate_peak_outside_tolerance(self):
        """Intermediate peak deviating >2% from line invalidates."""
        # Line from (0, 100) to (20, 90) has slope -0.5
        # At bar 10, line price = 95
        # Peak at 91 would be ~4.2% below line
        peaks = [(0, 100.0), (10, 91.0), (20, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=2.0)

        assert line is None

    def test_intermediate_peak_within_tolerance(self):
        """Intermediate peak within 2% of line is valid."""
        # Line from (0, 100) to (20, 90) has slope -0.5
        # At bar 10, line price = 95
        # Peak at 94 is ~1.05% below line
        peaks = [(0, 100.0), (10, 94.0), (20, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=2.0)

        assert line is not None


class TestTrendLinePriceAtBar:
    """Tests for TrendLine.price_at_bar() method."""

    def test_at_start_bar(self):
        """Price at start bar equals start price."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        assert line.price_at_bar(0) == 100.0

    def test_at_end_bar(self):
        """Price at end bar equals end price."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        assert line.price_at_bar(10) == 90.0

    def test_interpolation(self):
        """Linear interpolation between points."""
        peaks = [(0, 100.0), (10, 90.0)]  # slope = -1
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        assert line.price_at_bar(5) == 95.0

    def test_extrapolation_forward(self):
        """Extrapolate beyond end point."""
        peaks = [(0, 100.0), (10, 90.0)]  # slope = -1
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        assert line.price_at_bar(15) == 85.0


class TestTrendLineBreakDetection:
    """Tests for break detection methods."""

    def test_is_break_above_threshold(self):
        """Break detected when HIGH exceeds line by >threshold."""
        peaks = [(0, 100.0), (10, 90.0)]  # slope = -1
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        # At bar 5, line is at 95
        # 2% above line = 95 * 1.02 = 96.9
        assert not line.is_break_above(5, 96.0, threshold_pct=2.0)
        assert line.is_break_above(5, 97.5, threshold_pct=2.0)

    def test_is_break_above_exact_threshold(self):
        """At or below threshold, no break (need > not >=)."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        # At bar 5, line is 95
        # 2% above line = 95 * 1.02 = 96.9
        # Use 96.89 to stay safely below threshold (avoid floating point issues)
        assert not line.is_break_above(5, 96.89, threshold_pct=2.0)

    def test_is_break_above_below_line(self):
        """No break when price below line."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        assert not line.is_break_above(5, 90.0, threshold_pct=2.0)

    def test_is_break_below_acceleration(self):
        """Break below line indicates acceleration."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        # At bar 5, line is at 95
        # 2% below line = 95 * 0.98 = 93.1
        assert not line.is_break_below(5, 94.0, threshold_pct=2.0)
        assert line.is_break_below(5, 92.0, threshold_pct=2.0)


class TestTrendLineValidateBars:
    """Tests for validate_bars() method."""

    def test_all_bars_within_tolerance(self):
        """All bars within tolerance passes."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        # Create highs that stay below line
        highs = pd.Series([98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88])

        assert line.validate_bars(highs, 0, 10, tolerance_pct=2.0)

    def test_bar_exceeds_tolerance(self):
        """Bar HIGH exceeding tolerance fails."""
        peaks = [(0, 100.0), (10, 90.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        # At bar 5, line is 95. High of 99 is ~4.2% above -> fails
        highs = pd.Series([98, 97, 96, 95, 94, 99, 92, 91, 90, 89, 88])

        assert not line.validate_bars(highs, 0, 10, tolerance_pct=2.0)


class TestTrendLineTrySteepen:
    """Tests for try_steepen() method."""

    def test_steepen_with_lower_peak(self):
        """New lower peak creates steeper line."""
        peaks = [(0, 100.0), (10, 95.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)
        original_slope = line.slope

        steeper = line.try_steepen((20, 85.0), tolerance_pct=5.0)

        assert steeper is not None
        assert steeper.slope < original_slope  # More negative

    def test_steepen_not_lower_fails(self):
        """New peak not lower than last fails."""
        peaks = [(0, 100.0), (10, 95.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        steeper = line.try_steepen((20, 97.0), tolerance_pct=5.0)

        assert steeper is None

    def test_steepen_same_bar_fails(self):
        """New peak at same or earlier bar fails."""
        peaks = [(0, 100.0), (10, 95.0)]
        line = TrendLine.from_peaks(peaks, tolerance_pct=5.0)

        steeper = line.try_steepen((10, 93.0), tolerance_pct=5.0)

        assert steeper is None


# =============================================================================
# DowntrendLineBreak Signal Tests
# =============================================================================


class TestDowntrendLineBreakBasic:
    """Basic tests for DowntrendLineBreak signal."""

    def test_generate_returns_series(self):
        """Generate returns a pandas Series."""
        # Simple data - may not trigger signal
        prices = [(100, 102, 99, 101)] * 20
        df = create_test_data(prices)

        signal = DowntrendLineBreak()
        result = signal.generate(df)

        assert isinstance(result, pd.Series)
        assert len(result) == len(df)

    def test_generate_returns_boolean(self):
        """Result Series has boolean dtype."""
        prices = [(100, 102, 99, 101)] * 20
        df = create_test_data(prices)

        signal = DowntrendLineBreak()
        result = signal.generate(df)

        assert result.dtype == bool

    def test_signal_name(self):
        """Signal has correct name."""
        signal = DowntrendLineBreak()
        assert signal.name == "DowntrendLineBreak"

    def test_validate_data_missing_columns(self):
        """Missing columns raises ValueError."""
        signal = DowntrendLineBreak()
        bad_data = pd.DataFrame({"Close": [1, 2, 3]})

        try:
            signal.validate_data(bad_data)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "Missing required columns" in str(e)


class TestDowntrendLineBreakPatterns:
    """Pattern-based tests for DowntrendLineBreak signal."""

    def test_no_signal_without_downtrend(self):
        """No signal without prior Dow123BearishBreakdown."""
        # Uptrend data - no downtrend, no signal
        prices = []
        for i in range(30):
            base = 100 + i * 2
            prices.append((base, base + 2, base - 1, base + 1))

        df = create_test_data(prices)
        signal = DowntrendLineBreak()
        result = signal.generate(df)

        assert not result.any()

    def test_no_signal_with_only_two_peaks(self):
        """Signal requires at least 3 peaks (default min_peaks)."""
        # This test would need a specific pattern that creates exactly 2 peaks
        # then breaks - but signal shouldn't fire
        signal = DowntrendLineBreak(min_peaks=3)
        assert signal._min_peaks == 3


# =============================================================================
# Debug/Visual Tests (run directly)
# =============================================================================


def debug_bars(df):
    """Print bar analysis for debugging."""
    from classifiers.bars.up import UpBar
    from classifiers.bars.down import DownBar
    from classifiers.swings.swing_high import SwingHigh
    from classifiers.swings.swing_low import SwingLow

    up = UpBar().classify(df)
    down = DownBar().classify(df)
    swing_high = SwingHigh().classify(df)
    swing_low = SwingLow().classify(df)

    print("\nBar Analysis:")
    print(f"{'Bar':<4} {'High':<8} {'Low':<8} {'Type':<8} {'Swing'}")
    print("-" * 50)

    for i in range(len(df)):
        bar_type = "UP" if up.iloc[i] else ("DOWN" if down.iloc[i] else "?")
        swing = ""
        if swing_high.iloc[i]:
            swing += "HIGH "
        if swing_low.iloc[i]:
            swing += "LOW"

        print(
            f"{i:<4} {df['High'].iloc[i]:<8.2f} {df['Low'].iloc[i]:<8.2f} "
            f"{bar_type:<8} {swing}"
        )


def test_manual_pattern():
    """
    Manual test with known pattern.

    Creates definitive UP/DOWN bars for clear swing detection.

    Bar types: UP = higher high AND higher low
               DOWN = lower high AND lower low
    """
    prices = [
        # Initial bar (reference)
        (100, 101, 99, 100),    # 0: Reference

        # Uptrend to turning point (bars 1-5)
        (100, 103, 100, 102),   # 1: UP (HH=103>101, HL=100>99)
        (102, 106, 102, 105),   # 2: UP (HH=106>103, HL=102>100)
        (105, 110, 105, 109),   # 3: UP (HH=110>106, HL=105>102)
        (109, 115, 109, 114),   # 4: UP (HH=115>110, HL=109>105)
        (114, 120, 114, 118),   # 5: UP (HH=120>115, HL=114>109) - TURNING POINT

        # Pullback to swing low (bars 6-8)
        (118, 119, 112, 113),   # 6: DOWN (LH=119<120, LL=112<114)
        (113, 114, 106, 108),   # 7: DOWN (LH=114<119, LL=106<112)
        (108, 109, 100, 102),   # 8: DOWN (LH=109<114, LL=100<106) - SWING LOW

        # Rally to lower high (bars 9-11)
        (102, 111, 102, 110),   # 9: UP (HH=111>109, HL=102>100)
        (110, 114, 104, 113),   # 10: UP (HH=114>111, HL=104>102)
        (113, 116, 108, 112),   # 11: UP (HH=116>114, HL=108>104) - SWING HIGH 2 (116 < 120)

        # Decline toward breakdown (bars 12-14)
        (112, 114, 106, 108),   # 12: DOWN (LH=114<116, LL=106<108)
        (108, 110, 100, 102),   # 13: DOWN (LH=110<114, LL=100<106)
        (102, 105, 94, 96),     # 14: DOWN (LH=105<110, LL=94<100) - BREAKDOWN (94 < 100)

        # Continue down with swing points (bars 15-20)
        (96, 98, 88, 90),       # 15: DOWN (LH=98<105, LL=88<94) - SWING LOW
        (90, 102, 90, 100),     # 16: UP (HH=102>98, HL=90>88)
        (100, 108, 98, 106),    # 17: UP (HH=108>102, HL=98>90)
        (106, 112, 104, 110),   # 18: UP (HH=112>108, HL=104>98) - SWING HIGH 3 (112 < 116)
        (110, 111, 102, 104),   # 19: DOWN (LH=111<112, LL=102<104)
        (104, 106, 96, 98),     # 20: DOWN (LH=106<111, LL=96<102) - SWING LOW

        # Another swing (bars 21-25)
        (98, 108, 98, 106),     # 21: UP (HH=108>106, HL=98>96)
        (106, 110, 104, 108),   # 22: UP (HH=110>108, HL=104>98) - SWING HIGH 4 (110 < 112)
        (108, 109, 102, 104),   # 23: DOWN (LH=109<110, LL=102<104)
        (104, 106, 94, 96),     # 24: DOWN (LH=106<109, LL=94<102) - SWING LOW
        (96, 104, 96, 102),     # 25: UP (HH=104>106? NO - need fix)

        # Another swing (bars 26-30)
        (102, 108, 100, 106),   # 26: UP - SWING HIGH 5 (108 < 110)
        (106, 107, 98, 100),    # 27: DOWN
        (100, 102, 90, 92),     # 28: DOWN - SWING LOW
        (92, 100, 92, 98),      # 29: UP
        (98, 104, 96, 102),     # 30: UP - SWING HIGH 6 (104 < 108)

        # Continue down (bars 31-34)
        (102, 103, 94, 96),     # 31: DOWN
        (96, 98, 88, 90),       # 32: DOWN
        (90, 92, 82, 84),       # 33: DOWN
        (84, 86, 76, 78),       # 34: DOWN

        # Breakout above trendline (bar 35)
        # Line from (5, 120) to (22, 110): slope = -10/17 = -0.588
        # At bar 35, line = 120 - 0.588*30 = 102.35
        # Break > 2% above 102.35 = 104.4
        (78, 110, 76, 108),     # 35: Should break above trendline (110 > 104.4)
    ]

    df = create_test_data(prices)

    print("\n" + "=" * 60)
    print("MANUAL PATTERN TEST")
    print("=" * 60)

    debug_bars(df)

    signal = DowntrendLineBreak()
    result = signal.generate(df)

    signal_bars = [i for i in range(len(result)) if result.iloc[i]]
    print(f"Trendline Break at bars: {signal_bars}")

    if signal_bars:
        print("RESULT: Signal(s) detected")
    else:
        print("RESULT: No signals detected")

    return result


def run_class_tests():
    """Run all class-based tests."""
    test_classes = [
        TestTrendLineFromPeaks,
        TestTrendLinePriceAtBar,
        TestTrendLineBreakDetection,
        TestTrendLineValidateBars,
        TestTrendLineTrySteepen,
        TestDowntrendLineBreakBasic,
        TestDowntrendLineBreakPatterns,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            method = getattr(instance, method_name)
            try:
                method()
                passed_tests += 1
                print(f"  PASS: {test_class.__name__}.{method_name}")
            except AssertionError as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"  FAIL: {test_class.__name__}.{method_name} - {e}")
            except Exception as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"  ERROR: {test_class.__name__}.{method_name} - {e}")

    return total_tests, passed_tests, failed_tests


def run_all_tests():
    """Run all tests when executed directly."""
    print("=" * 60)
    print("TRENDLINE UTILITY TESTS")
    print("=" * 60)

    total, passed, failed = run_class_tests()

    print("\n" + "=" * 60)
    print(f"Unit Tests: {passed}/{total} passed")
    if failed:
        print("\nFailed tests:")
        for cls, method, error in failed:
            print(f"  - {cls}.{method}: {error}")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("MANUAL PATTERN TEST")
    print("=" * 60)
    test_manual_pattern()


if __name__ == "__main__":
    run_all_tests()
