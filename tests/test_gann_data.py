"""Test classifiers against Gann test data with expected values."""

import sys
sys.path.insert(0, "e:/Signal analysis/signal_lab")

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from classifiers.bars import UpBar, DownBar, InsideBar, OutsideBar
from classifiers.swings import SwingHigh, SwingLow


def load_test_data() -> pd.DataFrame:
    """Load the Gann test data."""
    df = pd.read_csv("e:/Signal analysis/signal_lab/data/Test/test_gann_34bars.csv")
    # Rename columns to match our convention
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close"
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


def run_classification_test(data: pd.DataFrame):
    """Run classifiers and compare against expected values."""
    up_bar = UpBar()
    down_bar = DownBar()
    inside_bar = InsideBar()
    outside_bar = OutsideBar()
    swing_high = SwingHigh()
    swing_low = SwingLow()

    is_up = up_bar.classify(data)
    is_down = down_bar.classify(data)
    is_inside = inside_bar.classify(data)
    is_outside = outside_bar.classify(data)
    is_swing_high = swing_high.classify(data)
    is_swing_low = swing_low.classify(data)

    # Build actual classification
    def get_actual_type(i):
        if is_up.iloc[i]:
            return "Up"
        elif is_down.iloc[i]:
            return "Down"
        elif is_inside.iloc[i]:
            return "Inside"
        elif is_outside.iloc[i]:
            return "Outside"
        return "Reference"

    def get_actual_swing(i):
        swings = []
        if is_swing_high.iloc[i]:
            swings.append("High")
        if is_swing_low.iloc[i]:
            swings.append("Low")
        if len(swings) == 2:
            return "Low and High"
        elif len(swings) == 1:
            return swings[0]
        return ""

    # Print comparison
    print("\n" + "=" * 100)
    print("CLASSIFICATION COMPARISON: Expected vs Actual")
    print("=" * 100)
    print(f"{'Bar':<4} {'H':<6} {'L':<6} {'Exp Type':<10} {'Act Type':<10} {'Type OK':<8} "
          f"{'Exp Swing':<14} {'Act Swing':<14} {'Swing OK':<8}")
    print("-" * 100)

    type_matches = 0
    swing_matches = 0
    total = len(data)

    for i in range(len(data)):
        exp_type = data["expected_type"].iloc[i]
        act_type = get_actual_type(i)
        type_ok = "OK" if exp_type == act_type else "MISS"
        if exp_type == act_type:
            type_matches += 1

        exp_swing = str(data["expected_swing"].iloc[i]) if pd.notna(data["expected_swing"].iloc[i]) else ""
        act_swing = get_actual_swing(i)
        swing_ok = "OK" if exp_swing == act_swing else ("MISS" if exp_swing or act_swing else "-")
        if exp_swing == act_swing:
            swing_matches += 1

        print(f"{i:<4} {data['High'].iloc[i]:<6} {data['Low'].iloc[i]:<6} "
              f"{exp_type:<10} {act_type:<10} {type_ok:<8} "
              f"{exp_swing:<14} {act_swing:<14} {swing_ok:<8}")

    print("=" * 100)
    print(f"Bar Type Accuracy: {type_matches}/{total} ({100*type_matches/total:.1f}%)")
    print(f"Swing Accuracy: {swing_matches}/{total} ({100*swing_matches/total:.1f}%)")
    print("=" * 100)

    return is_up, is_down, is_inside, is_outside, is_swing_high, is_swing_low


def plot_gann_test(data: pd.DataFrame, is_up, is_down, is_inside, is_outside, is_swing_high, is_swing_low):
    """Plot the Gann test data with OHLC bars."""
    _, ax = plt.subplots(figsize=(20, 10))

    # Track colors for inside bars (inherit from prior)
    prev_color = "black"

    for i in range(len(data)):
        row = data.iloc[i]

        # Determine bar color based on type
        if is_up.iloc[i]:
            color = "green"
        elif is_down.iloc[i]:
            color = "red"
        elif is_outside.iloc[i]:
            color = "blue"
        elif is_inside.iloc[i]:
            color = prev_color  # Same as prior bar
        else:
            color = "black"  # Reference/unknown

        prev_color = color

        # Draw OHLC bar (not candle)
        # Vertical line for high-low range
        ax.plot([i, i], [row["Low"], row["High"]], color=color, linewidth=2)
        # Left tick for open
        ax.plot([i - 0.2, i], [row["Open"], row["Open"]], color=color, linewidth=2)
        # Right tick for close
        ax.plot([i, i + 0.2], [row["Close"], row["Close"]], color=color, linewidth=2)

        # Swing markers
        if is_swing_high.iloc[i]:
            ax.plot(i, row["High"] + 0.3, marker="v", markersize=12, color="gold", markeredgecolor="black")
        if is_swing_low.iloc[i]:
            ax.plot(i, row["Low"] - 0.3, marker="^", markersize=12, color="cyan", markeredgecolor="black")

        # Expected swing (for comparison) - show below bar
        exp_swing = str(data["expected_swing"].iloc[i]) if pd.notna(data["expected_swing"].iloc[i]) else ""
        if exp_swing:
            ax.text(i, row["Low"] - 1.2, f"E:{exp_swing}", ha="center", fontsize=7, color="gray")

        # Bar number at bottom
        ax.text(i, data["Low"].min() - 2.5, str(i), ha="center", fontsize=7, color="black")

    ax.set_xlim(-1, len(data))
    ax.set_ylim(data["Low"].min() - 4, data["High"].max() + 3)
    ax.set_xlabel("Bar Index")
    ax.set_ylabel("Price")
    ax.set_title("Gann Test Data - OHLC Bars\nGreen=Up, Red=Down, Blue=Outside, Inside=inherit prior")
    ax.grid(True, alpha=0.3)

    legend_elements = [
        plt.Line2D([0], [0], color="green", linewidth=2, label="Up Bar"),
        plt.Line2D([0], [0], color="red", linewidth=2, label="Down Bar"),
        plt.Line2D([0], [0], color="blue", linewidth=2, label="Outside Bar"),
        plt.Line2D([0], [0], marker="v", color="w", markerfacecolor="gold",
                   markersize=10, label="Swing High"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="cyan",
                   markersize=10, label="Swing Low"),
    ]
    ax.legend(handles=legend_elements, loc="upper left")

    plt.tight_layout()
    plt.savefig("e:/Signal analysis/signal_lab/tests/gann_test_results.png", dpi=150)
    print("\nChart saved to: tests/gann_test_results.png")
    plt.show(block=False)
    plt.pause(1)
    plt.close()


if __name__ == "__main__":
    data = load_test_data()
    print("\nLoaded Gann Test Data:")
    print(data[["Open", "High", "Low", "Close", "expected_type", "expected_swing"]].to_string())

    results = run_classification_test(data)
    plot_gann_test(data, *results)
