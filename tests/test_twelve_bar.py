"""Tests for TwelveBar Breakout signal."""

import pandas as pd
import numpy as np
import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from signals.twelve_bar import TwelveBarBreakout
from classifiers.swings.swing_low import SwingLow
from classifiers.bars.up import UpBar
from classifiers.bars.down import DownBar


def create_test_data(prices):
    """Create test DataFrame from OHLC price tuples."""
    df = pd.DataFrame(prices, columns=["Open", "High", "Low", "Close"])
    df["Date"] = pd.date_range("2024-01-01", periods=len(df), freq="W")
    return df


def debug_bars(df):
    """Print bar types for debugging."""
    up = UpBar().classify(df)
    down = DownBar().classify(df)
    swing_low = SwingLow().classify(df)

    print("\nBar Analysis:")
    for i in range(len(df)):
        bar_type = "UP" if up.iloc[i] else ("DOWN" if down.iloc[i] else "OTHER")
        swing = " <- SWING LOW" if swing_low.iloc[i] else ""
        print(f"  Bar {i}: H={df['High'].iloc[i]}, L={df['Low'].iloc[i]} [{bar_type}]{swing}")


def test_basic_breakout():
    """Test basic breakout pattern."""
    print("\n" + "=" * 60)
    print("TEST: Basic Breakout")
    print("=" * 60)

    # Format: (Open, High, Low, Close)
    prices = [
        # Bars 0-1: Setup
        (100, 102, 99, 101),
        (101, 103, 100, 102),
        # Bar 2: DOWN bar - swing low at 95
        (102, 102, 95, 96),
        # Bar 3: UP bar confirms
        (96, 104, 96, 103),
        # Bars 4-13: Consolidation
        (103, 105, 102, 104),
        (104, 106, 103, 105),  # Resistance at 106
        (105, 105, 100, 101),
        (101, 104, 99, 103),
        (103, 105, 101, 104),
        (104, 104, 100, 101),
        (101, 103, 99, 102),
        (102, 104, 100, 103),
        (103, 105, 101, 104),
        (104, 105, 102, 103),
        # Bar 14: Breakout! HIGH > 106
        (103, 108, 102, 107),
        (107, 110, 106, 109),
    ]

    df = create_test_data(prices)
    debug_bars(df)

    signal = TwelveBarBreakout()
    result = signal.generate(df)

    signal_bars = list(result[result].index)
    print(f"\nSignal fired at bars: {signal_bars}")

    assert len(signal_bars) == 1, f"Expected 1 signal, got {len(signal_bars)}"
    assert result.iloc[14] == True, f"Expected signal at bar 14"

    print("PASSED: Signal fired at bar 14 as expected")
    return True


def test_invalidation_during_window():
    """Test pattern invalidation during consolidation window."""
    print("\n" + "=" * 60)
    print("TEST: Invalidation During Window")
    print("=" * 60)

    prices = [
        (100, 102, 99, 101),
        (101, 103, 100, 102),
        (102, 102, 95, 96),  # Swing low at 95
        (96, 104, 96, 103),
        (103, 105, 102, 104),
        (104, 106, 103, 105),
        (105, 105, 100, 101),
        (101, 102, 94, 95),  # Bar 7: LOW=94 < 95, invalidates
        (95, 100, 94, 99),
        (99, 102, 98, 101),
        (101, 103, 100, 102),
        (102, 104, 101, 103),
        (103, 105, 102, 104),
        (104, 106, 103, 105),
        (105, 110, 104, 109),
        (109, 112, 108, 111),
    ]

    df = create_test_data(prices)
    signal = TwelveBarBreakout()
    result = signal.generate(df)

    signal_bars = list(result[result].index)
    print(f"Signal fired at bars: {signal_bars}")

    assert result.sum() == 0, f"Expected 0 signals, got {result.sum()}"

    print("PASSED: No signal fired (pattern correctly invalidated)")
    return True


def test_on_real_data():
    """Test TwelveBarBreakout on FMG data."""
    print("\n" + "=" * 60)
    print("TEST: Real Data (FMG)")
    print("=" * 60)

    try:
        df = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "FMG_weekly.csv"))
        df.columns = [c.capitalize() for c in df.columns]

        signal = TwelveBarBreakout()
        result = signal.generate(df)

        signal_count = result.sum()
        print(f"TwelveBarBreakout signals on FMG: {signal_count}")

        signal_bars = list(result[result].index[:5])
        for bar in signal_bars:
            print(f"  Bar {bar}: Close = {df['Close'].iloc[bar]:.4f}")

        print(f"PASSED: Found {signal_count} signals")
        return True

    except FileNotFoundError:
        print("SKIPPED: FMG data not available")
        return True


if __name__ == "__main__":
    tests = [
        test_basic_breakout,
        test_invalidation_during_window,
        test_on_real_data,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except AssertionError as e:
            print(f"FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
