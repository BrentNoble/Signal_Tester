"""Test Dow Theory 1-2-3 breakout signals on Gann data."""

import pandas as pd
import sys
sys.path.insert(0, "e:\\Signal analysis\\signal_lab")

from signals.dow_breakout.up import Dow123BullishBreakout
from signals.dow_breakout.down import Dow123BearishBreakdown
from classifiers.swings.swing_high import SwingHigh
from classifiers.swings.swing_low import SwingLow
from outcomes.classifier import SignalStateTracker


def load_gann_data():
    """Load and prepare the Gann test data."""
    df = pd.read_csv("e:\\Signal analysis\\signal_lab\\data\\Test\\test_gann_34bars.csv")

    # Capitalize columns for consistency
    df.columns = [c.capitalize() for c in df.columns]
    df = df.rename(columns={"Expected_type": "Expected_type", "Expected_swing": "Expected_swing"})

    return df


def load_synthetic_data():
    """Load synthetic test data with multiple signal patterns."""
    df = pd.read_csv("e:\\Signal analysis\\signal_lab\\data\\Test\\test_signals_synthetic.csv")

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


def test_state_transitions():
    """Test signal state transitions (Markov model)."""
    df = load_gann_data()

    # Create tracker with all Dow signals
    signals = {
        "Dow123BullishBreakout": Dow123BullishBreakout(),
        "Dow123BearishBreakdown": Dow123BearishBreakdown(),
    }
    tracker = SignalStateTracker(signals)

    # Show individual transitions
    print("\n" + "=" * 60)
    print("SIGNAL STATE TRANSITIONS:")
    print("=" * 60)

    transitions_df = tracker.get_transitions_df(df)
    if len(transitions_df) > 0:
        print("\nTransition events:")
        for _, row in transitions_df.iterrows():
            print(f"  Bar {row['from_idx']} ({row['from_signal']})")
            print(f"    via [{row['intermediate_state']}]")
            print(f"    → Bar {row['to_idx']} ({row['to_signal']})")
            print(f"    % change: {row['pct_change']*100:.2f}%, bars: {row['bars_between']}")
    else:
        print("No transitions found (need at least 2 signals)")

    # Print transition matrix
    tracker.print_transition_matrix(df)


def test_state_visualization():
    """Test the state visualization chart."""
    df = load_gann_data()

    # Create tracker with all Dow signals
    signals = {
        "Dow123BullishBreakout": Dow123BullishBreakout(),
        "Dow123BearishBreakdown": Dow123BearishBreakdown(),
    }
    tracker = SignalStateTracker(signals)

    # Plot states
    tracker.plot_states(
        df,
        save_path="e:\\Signal analysis\\signal_lab\\tests\\state_chart.png",
        show=True
    )


def test_synthetic_data():
    """Test signals and transitions on synthetic data with multiple patterns."""
    df = load_synthetic_data()

    print("\n" + "=" * 70)
    print("TESTING WITH SYNTHETIC DATA (75 bars)")
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

    # Create tracker with all Dow signals
    signals = {
        "Dow123BullishBreakout": Dow123BullishBreakout(),
        "Dow123BearishBreakdown": Dow123BearishBreakdown(),
    }
    tracker = SignalStateTracker(signals)

    # Generate signals
    signals_df = tracker.generate_all_signals(df)

    print("\nSIGNALS DETECTED:")
    for name in signals.keys():
        count = signals_df[name].sum()
        print(f"  {name}: {count} signals")
        for i in range(len(df)):
            if signals_df[name].iloc[i]:
                print(f"    Bar {i}: {df['Date'].iloc[i]} @ {df['Close'].iloc[i]}")

    # Show transitions
    print("\nTRANSITIONS:")
    transitions_df = tracker.get_transitions_df(df)
    if len(transitions_df) > 0:
        for _, row in transitions_df.iterrows():
            print(f"  {row['from_signal']}")
            print(f"    via [{row['intermediate_state']}] ({row['pct_change']*100:+.2f}%)")
            print(f"    -> {row['to_signal']}")
            print()
    else:
        print("  No transitions found")

    # Print transition matrix
    tracker.print_transition_matrix(df)

    # Plot with signal markers
    tracker.plot_states(
        df,
        save_path="e:\\Signal analysis\\signal_lab\\tests\\synthetic_signals_chart.png",
        show=True
    )


if __name__ == "__main__":
    # Test with synthetic data that has expected values
    test_synthetic_data()
