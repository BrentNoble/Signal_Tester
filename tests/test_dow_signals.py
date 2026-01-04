"""Test Dow Theory 1-2-3 breakout signals on Gann data."""

import pandas as pd
import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from signals.dow_breakout.up import Dow123BullishBreakout
from signals.dow_breakout.down import Dow123BearishBreakdown
from signals.dow_breakout.reversal import DowntrendReversal
from classifiers.swings.swing_high import SwingHigh
from classifiers.swings.swing_low import SwingLow


def load_gann_data():
    """Load and prepare the Gann test data."""
    df = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "Test", "test_gann_34bars.csv"))

    # Capitalize columns for consistency
    df.columns = [c.capitalize() for c in df.columns]
    df = df.rename(columns={"Expected_type": "Expected_type", "Expected_swing": "Expected_swing"})

    return df


def load_synthetic_data():
    """Load synthetic test data with multiple signal patterns."""
    df = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "Test", "test_signals_synthetic.csv"))

    # Capitalize columns for consistency
    df.columns = [c.capitalize() for c in df.columns]

    return df


def test_bullish_breakout():
    """Test the Dow 1-2-3 bullish breakout signal on Gann data."""
    df = load_gann_data()

    # Get swing points for reference
    swing_high = SwingHigh()
    swing_low = SwingLow()
    is_high = swing_high.classify(df)
    is_low = swing_low.classify(df)

    print("=" * 60)
    print("SWING POINTS DETECTED:")
    print("=" * 60)
    for i in range(len(df)):
        if is_low.iloc[i] or is_high.iloc[i]:
            swing_type = []
            if is_low.iloc[i]:
                swing_type.append(f"LOW @ {df['Low'].iloc[i]}")
            if is_high.iloc[i]:
                swing_type.append(f"HIGH @ {df['High'].iloc[i]}")
            print(f"Bar {i}: {df['Date'].iloc[i]} - {', '.join(swing_type)}")

    # Generate bullish breakout signals
    signal = Dow123BullishBreakout()
    breakout = signal.generate(df)

    print("\n" + "=" * 60)
    print("DOW 1-2-3 BULLISH BREAKOUT SIGNALS:")
    print("=" * 60)

    signals_found = breakout.sum()
    if signals_found > 0:
        for i in range(len(df)):
            if breakout.iloc[i]:
                print(f"Bar {i}: {df['Date'].iloc[i]} - BULLISH BREAKOUT")
                print(f"   Close: {df['Close'].iloc[i]}")
    else:
        print("No bullish breakout signals found in this data")

    print(f"\nTotal bullish breakout signals: {signals_found}")
    return breakout


def test_bearish_breakdown():
    """Test the Dow 1-2-3 bearish breakdown signal on Gann data."""
    df = load_gann_data()

    # Generate bearish breakdown signals
    signal = Dow123BearishBreakdown()
    breakdown = signal.generate(df)

    print("\n" + "=" * 60)
    print("DOW 1-2-3 BEARISH BREAKDOWN SIGNALS:")
    print("=" * 60)

    signals_found = breakdown.sum()
    if signals_found > 0:
        for i in range(len(df)):
            if breakdown.iloc[i]:
                print(f"Bar {i}: {df['Date'].iloc[i]} - BEARISH BREAKDOWN")
                print(f"   Close: {df['Close'].iloc[i]}")
    else:
        print("No bearish breakdown signals found in this data")

    print(f"\nTotal bearish breakdown signals: {signals_found}")
    return breakdown


def test_downtrend_reversal():
    """Test the downtrend reversal signal on synthetic data."""
    df = load_synthetic_data()

    # Generate signals
    reversal = DowntrendReversal()
    signals = reversal.generate(df)

    print("\n" + "=" * 60)
    print("DOWNTREND REVERSAL SIGNALS:")
    print("=" * 60)

    signals_found = signals.sum()
    if signals_found > 0:
        for i in range(len(df)):
            if signals.iloc[i]:
                print(f"Bar {i}: {df['Date'].iloc[i]} - REVERSAL ENTRY")
                print(f"   Close: {df['Close'].iloc[i]}")
    else:
        print("No downtrend reversal signals found in this data")

    print(f"\nTotal reversal signals: {signals_found}")
    return signals


def test_all_signals():
    """Test all signals on synthetic data."""
    df = load_synthetic_data()

    print("\n" + "=" * 70)
    print("TESTING ALL SIGNALS WITH SYNTHETIC DATA")
    print("=" * 70)

    # Get swing points
    swing_high = SwingHigh()
    swing_low = SwingLow()
    is_high = swing_high.classify(df)
    is_low = swing_low.classify(df)

    print("\nSWING POINTS:")
    for i in range(len(df)):
        if is_low.iloc[i] or is_high.iloc[i]:
            swing_type = []
            if is_low.iloc[i]:
                swing_type.append(f"LOW @ {df['Low'].iloc[i]}")
            if is_high.iloc[i]:
                swing_type.append(f"HIGH @ {df['High'].iloc[i]}")
            print(f"  Bar {i}: {df['Date'].iloc[i]} - {', '.join(swing_type)}")

    # Create all signals
    signals = {
        "Dow123BullishBreakout": Dow123BullishBreakout(),
        "Dow123BearishBreakdown": Dow123BearishBreakdown(),
        "DowntrendReversal": DowntrendReversal(),
    }

    print("\nSIGNALS DETECTED:")
    for name, signal in signals.items():
        result = signal.generate(df)
        count = result.sum()
        print(f"  {name}: {count} signals")
        for i in range(len(df)):
            if result.iloc[i]:
                print(f"    Bar {i}: {df['Date'].iloc[i]} @ {df['Close'].iloc[i]}")


if __name__ == "__main__":
    test_bullish_breakout()
    test_bearish_breakdown()
    test_downtrend_reversal()
    print("\n" + "=" * 70)
    test_all_signals()
