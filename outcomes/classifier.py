"""Signal state transition tracker for Markov model analysis.

Each signal IS a state. This module tracks:
- Which signal fires next after a given signal (state transition)
- The intermediate state (up/down/sideways) between signals
- The % price move between signal transitions
- Transition probabilities and statistics
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from signals.base import Signal
from classifiers.bars.up import UpBar
from classifiers.bars.down import DownBar
from classifiers.bars.inside import InsideBar
from classifiers.bars.outside import OutsideBar
from classifiers.swings.swing_high import SwingHigh
from classifiers.swings.swing_low import SwingLow


class MarketState(Enum):
    """Market state between signals."""
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class DowTrendState(Enum):
    """Dow Theory trend state."""
    UNKNOWN = "unknown"
    BULLISH_SIGNAL = "bullish_signal"  # One-bar state when bullish signal fires
    UPTREND = "uptrend"
    BEARISH_SIGNAL = "bearish_signal"  # One-bar state when bearish signal fires
    DOWNTREND = "downtrend"
    TREND_END = "trend_end"


@dataclass
class Transition:
    """A single state transition between two signals."""
    from_signal: str
    from_idx: int
    from_price: float
    to_signal: str
    to_idx: int
    to_price: float
    pct_change: float
    bars_between: int
    intermediate_state: str  # up/down/sideways between signals


class SignalStateTracker:
    """
    Tracks state transitions between signals for Markov model analysis.

    Each signal type is a state. When signal A fires, we look for the
    next signal that fires (B) and record:
    - The transition A → B
    - The intermediate market state (up/down/sideways)
    - The % price change from A to B
    - The number of bars between signals
    """

    # State colors for visualization
    COLORS = {
        # Bar type colors (for price chart)
        "bullish_signal": "blue",
        "bearish_signal": "gold",
        "up_bar": "green",
        "down_bar": "red",
        "outside_bar": "purple",
        "inside_bar": "grey",
        "reference": "black",
        # Markov state colors (for state panel)
        "unknown": "grey",
        "uptrend": "green",
        "downtrend": "red",
        "trend_end": "orange",
    }

    def __init__(self, signals: Dict[str, Signal]):
        """
        Args:
            signals: Dict mapping signal names to Signal instances
                     e.g., {"Dow123BullishBreakout": Dow123BullishBreakout(), ...}
        """
        self.signals = signals

    def generate_all_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate all signal series and combine into a single DataFrame.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with a column for each signal (boolean values)
        """
        result = pd.DataFrame(index=data.index)

        for name, signal in self.signals.items():
            result[name] = signal.generate(data)

        return result

    def classify_intermediate_state(
        self,
        data: pd.DataFrame,
        from_idx: int,
        to_idx: int
    ) -> str:
        """
        Classify the market state between two signal points.

        Uses the net price change to determine if market went up, down, or sideways.

        Args:
            data: DataFrame with OHLCV data
            from_idx: Starting bar index
            to_idx: Ending bar index

        Returns:
            "up", "down", or "sideways"
        """
        from_price = data["Close"].iloc[from_idx]
        to_price = data["Close"].iloc[to_idx]

        pct_change = (to_price - from_price) / from_price

        # Simple classification based on net move
        # Could be enhanced with swing analysis later
        if pct_change > 0.005:  # More than 0.5% up
            return "up"
        elif pct_change < -0.005:  # More than 0.5% down
            return "down"
        else:
            return "sideways"

    def find_transitions(self, data: pd.DataFrame) -> List[Transition]:
        """
        Find all state transitions in the data.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            List of Transition objects
        """
        # Generate all signals
        signals_df = self.generate_all_signals(data)
        closes = data["Close"]

        # Build ordered list of all signal events: (idx, signal_name, price)
        events = []
        for i in range(len(data)):
            for name in self.signals.keys():
                if signals_df[name].iloc[i]:
                    events.append((i, name, closes.iloc[i]))

        # Sort by index
        events.sort(key=lambda x: x[0])

        # Find transitions (consecutive signals)
        transitions = []
        for i in range(len(events) - 1):
            from_idx, from_signal, from_price = events[i]
            to_idx, to_signal, to_price = events[i + 1]

            pct_change = (to_price - from_price) / from_price
            bars_between = to_idx - from_idx
            intermediate = self.classify_intermediate_state(data, from_idx, to_idx)

            transitions.append(Transition(
                from_signal=from_signal,
                from_idx=from_idx,
                from_price=from_price,
                to_signal=to_signal,
                to_idx=to_idx,
                to_price=to_price,
                pct_change=pct_change,
                bars_between=bars_between,
                intermediate_state=intermediate
            ))

        return transitions

    def get_bar_states(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Get the state for each bar based on bar type and signals.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with columns: bar_idx, state, bar_type, color, has_signal
        """
        signals_df = self.generate_all_signals(data)

        # Classify bar types
        up_bar = UpBar()
        down_bar = DownBar()
        inside_bar = InsideBar()
        outside_bar = OutsideBar()

        is_up = up_bar.classify(data)
        is_down = down_bar.classify(data)
        is_inside = inside_bar.classify(data)
        is_outside = outside_bar.classify(data)

        # Assign states to each bar
        states = []
        for i in range(len(data)):
            # Determine bar type
            if is_up.iloc[i]:
                bar_type = "up"
                color = self.COLORS["up_bar"]
            elif is_down.iloc[i]:
                bar_type = "down"
                color = self.COLORS["down_bar"]
            elif is_outside.iloc[i]:
                bar_type = "outside"
                color = self.COLORS["outside_bar"]
            elif is_inside.iloc[i]:
                bar_type = "inside"
                color = self.COLORS["inside_bar"]
            else:
                bar_type = "reference"
                color = self.COLORS["reference"]

            # Check if this bar has a signal
            signal_at_bar = None
            for name in self.signals.keys():
                if signals_df[name].iloc[i]:
                    signal_at_bar = name
                    break

            # Signal overrides bar type color in state panel
            if signal_at_bar:
                if "bullish" in signal_at_bar.lower():
                    state_color = self.COLORS["bullish_signal"]
                elif "bearish" in signal_at_bar.lower():
                    state_color = self.COLORS["bearish_signal"]
                else:
                    state_color = color
                state = signal_at_bar
            else:
                state_color = color
                state = bar_type

            states.append({
                "bar_idx": i,
                "state": state,
                "bar_type": bar_type,
                "bar_color": color,
                "state_color": state_color,
                "has_signal": signal_at_bar is not None
            })

        return pd.DataFrame(states)

    def compute_transition_matrix(
        self,
        data: pd.DataFrame,
        include_intermediate: bool = True
    ) -> Dict[str, Dict[str, dict]]:
        """
        Compute transition probabilities and statistics.

        Args:
            data: DataFrame with OHLCV data
            include_intermediate: If True, include intermediate states in matrix

        Returns:
            Nested dict: matrix[from_state][to_state] = {
                "count": int,
                "probability": float,
                "mean_pct": float,
                "std_pct": float,
                "mean_bars": float
            }
        """
        transitions = self.find_transitions(data)

        if not transitions:
            return {}

        # Count transitions
        from_counts = {}
        transition_data = {}

        for t in transitions:
            # Signal → Signal transition
            if t.from_signal not in from_counts:
                from_counts[t.from_signal] = 0
                transition_data[t.from_signal] = {}

            # Direct signal transition
            if t.to_signal not in transition_data[t.from_signal]:
                transition_data[t.from_signal][t.to_signal] = {
                    "pct_changes": [],
                    "bars": []
                }

            from_counts[t.from_signal] += 1
            transition_data[t.from_signal][t.to_signal]["pct_changes"].append(t.pct_change)
            transition_data[t.from_signal][t.to_signal]["bars"].append(t.bars_between)

            # Also track intermediate state transitions
            if include_intermediate:
                intermediate_key = f"[{t.intermediate_state}]"
                if intermediate_key not in transition_data[t.from_signal]:
                    transition_data[t.from_signal][intermediate_key] = {
                        "pct_changes": [],
                        "bars": []
                    }
                transition_data[t.from_signal][intermediate_key]["pct_changes"].append(t.pct_change)
                transition_data[t.from_signal][intermediate_key]["bars"].append(t.bars_between)

        # Build result matrix
        matrix = {}
        for from_sig in transition_data:
            matrix[from_sig] = {}
            total_from = from_counts[from_sig]

            for to_state in transition_data[from_sig]:
                pct_changes = transition_data[from_sig][to_state]["pct_changes"]
                bars = transition_data[from_sig][to_state]["bars"]

                matrix[from_sig][to_state] = {
                    "count": len(pct_changes),
                    "probability": len(pct_changes) / total_from,
                    "mean_pct": np.mean(pct_changes),
                    "std_pct": np.std(pct_changes) if len(pct_changes) > 1 else 0.0,
                    "mean_bars": np.mean(bars)
                }

        return matrix

    def get_transitions_df(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Get transitions as a DataFrame for analysis.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with transition details
        """
        transitions = self.find_transitions(data)

        if not transitions:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                "from_signal": t.from_signal,
                "from_idx": t.from_idx,
                "from_price": t.from_price,
                "intermediate_state": t.intermediate_state,
                "to_signal": t.to_signal,
                "to_idx": t.to_idx,
                "to_price": t.to_price,
                "pct_change": t.pct_change,
                "bars_between": t.bars_between
            }
            for t in transitions
        ])

    def plot_states(
        self,
        data: pd.DataFrame,
        save_path: Optional[str] = None,
        show: bool = True
    ) -> None:
        """
        Plot price chart with colored bars and state markers.

        Bar colors (price chart):
        - Green: Up bar (HH + HL)
        - Red: Down bar (LH + LL)
        - Purple: Outside bar
        - Grey: Inside bar
        - Black: Reference bar

        Signal markers:
        - Blue triangle up: Bullish signal
        - Gold triangle down: Bearish signal

        Args:
            data: DataFrame with OHLCV data
            save_path: Optional path to save the chart
            show: Whether to display the chart
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                        gridspec_kw={'height_ratios': [3, 1]},
                                        sharex=True)

        bar_states_df = self.get_bar_states(data)  # For price chart coloring
        markov_states_df = self.classify_dow_trend_state(data)  # For state panel
        signals_df = self.generate_all_signals(data)
        highs = data["High"]
        lows = data["Low"]

        # Calculate marker offset
        price_range = highs.max() - lows.min()
        marker_offset = price_range * 0.05

        # Top chart: Price with OHLC bars colored by bar type
        for i in range(len(data)):
            row = data.iloc[i]
            bar_color = bar_states_df.iloc[i]["bar_color"]

            # Draw OHLC bar
            ax1.plot([i, i], [row["Low"], row["High"]], color=bar_color, linewidth=2)
            ax1.plot([i - 0.2, i], [row["Open"], row["Open"]], color=bar_color, linewidth=2)
            ax1.plot([i, i + 0.2], [row["Close"], row["Close"]], color=bar_color, linewidth=2)

        # Add signal markers on price chart
        for name in self.signals.keys():
            for i in range(len(data)):
                if signals_df[name].iloc[i]:
                    if "bullish" in name.lower():
                        # Blue triangle pointing up below the bar
                        ax1.plot(i, lows.iloc[i] - marker_offset,
                                marker="^", markersize=15,
                                color=self.COLORS["bullish_signal"],
                                markeredgecolor="black", markeredgewidth=1)
                        ax1.annotate("BUY", (i, lows.iloc[i] - marker_offset * 2),
                                    ha="center", fontsize=8, fontweight="bold",
                                    color=self.COLORS["bullish_signal"])
                    elif "bearish" in name.lower():
                        # Gold triangle pointing down above the bar
                        ax1.plot(i, highs.iloc[i] + marker_offset,
                                marker="v", markersize=15,
                                color=self.COLORS["bearish_signal"],
                                markeredgecolor="black", markeredgewidth=1)
                        ax1.annotate("SELL", (i, highs.iloc[i] + marker_offset * 2),
                                    ha="center", fontsize=8, fontweight="bold",
                                    color=self.COLORS["bearish_signal"])

        ax1.set_ylabel("Price")
        ax1.set_title("Price Chart with Bar Types and Signals")
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(lows.min() - marker_offset * 4, highs.max() + marker_offset * 4)

        # Bottom chart: Markov states as colored bars
        for i, row in markov_states_df.iterrows():
            state = row["state"]
            color = self.COLORS.get(state, "grey")
            ax2.bar(row["bar_idx"], 1, color=color, width=0.8, alpha=0.8)

        ax2.set_ylabel("Markov State")
        ax2.set_xlabel("Bar Index")
        ax2.set_ylim(0, 1.2)
        ax2.set_yticks([])

        # Add legend for Markov states
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=self.COLORS["unknown"], label="Unknown"),
            plt.Rectangle((0, 0), 1, 1, color=self.COLORS["bullish_signal"], label="Bullish Signal"),
            plt.Rectangle((0, 0), 1, 1, color=self.COLORS["uptrend"], label="Uptrend"),
            plt.Rectangle((0, 0), 1, 1, color=self.COLORS["bearish_signal"], label="Bearish Signal"),
            plt.Rectangle((0, 0), 1, 1, color=self.COLORS["downtrend"], label="Downtrend"),
            plt.Rectangle((0, 0), 1, 1, color=self.COLORS["trend_end"], label="Trend End"),
        ]
        ax2.legend(handles=legend_elements, loc="upper right", ncol=6)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150)
            print(f"Chart saved to: {save_path}")

        if show:
            plt.show(block=False)
            plt.pause(1)

    def print_transition_matrix(self, data: pd.DataFrame) -> None:
        """Print a formatted transition matrix."""
        matrix = self.compute_transition_matrix(data, include_intermediate=True)

        if not matrix:
            print("No transitions found")
            return

        print("\n" + "=" * 80)
        print("SIGNAL STATE TRANSITION MATRIX")
        print("=" * 80)

        for from_sig in matrix:
            print(f"\nFrom: {from_sig}")
            print("-" * 60)

            # Sort: signals first, then intermediate states
            to_states = sorted(matrix[from_sig].keys(),
                             key=lambda x: (x.startswith("["), x))

            for to_state in to_states:
                stats = matrix[from_sig][to_state]
                print(f"  -> {to_state}:")
                print(f"      Count: {stats['count']}")
                print(f"      P(transition): {stats['probability']*100:.1f}%")
                print(f"      Mean % move: {stats['mean_pct']*100:.2f}%")
                print(f"      Std % move: {stats['std_pct']*100:.2f}%")
                print(f"      Mean bars: {stats['mean_bars']:.1f}")

    def classify_dow_trend_state(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Classify each bar's Dow trend state based on signals and swing patterns.

        States:
        - unknown: Before first signal or after trend ends
        - uptrend: After bullish signal, making higher highs and higher lows
        - downtrend: After bearish signal, making lower highs and lower lows
        - trend_end: Bar where price breaks the last swing level

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with columns: bar_idx, state, last_swing_price, broke_level
        """
        signals_df = self.generate_all_signals(data)

        # Get swing points
        swing_high = SwingHigh()
        swing_low = SwingLow()
        is_swing_high = swing_high.classify(data)
        is_swing_low = swing_low.classify(data)

        closes = data["Close"]
        lows = data["Low"]
        highs = data["High"]

        # Track state for each bar
        states = []
        current_state = DowTrendState.UNKNOWN
        pending_state = None  # State to transition to on next bar
        last_higher_low_price = None  # For uptrend - the swing low we're tracking
        last_lower_high_price = None  # For downtrend - the swing high we're tracking
        last_swing_low_price = None  # Most recent swing low
        last_swing_high_price = None  # Most recent swing high
        trend_high_price = None  # The swing high when trend started (for uptrend)
        trend_low_price = None  # The swing low when trend started (for downtrend)

        for i in range(len(data)):
            # Apply pending transition from previous bar
            if pending_state is not None:
                current_state = pending_state
                pending_state = None

            # Check for signals at this bar
            bullish_signal = False
            bearish_signal = False
            for name in self.signals.keys():
                if signals_df[name].iloc[i]:
                    if "bullish" in name.lower():
                        bullish_signal = True
                    elif "bearish" in name.lower():
                        bearish_signal = True

            # Update swing tracking
            if is_swing_low.iloc[i]:
                last_swing_low_price = lows.iloc[i]
            if is_swing_high.iloc[i]:
                last_swing_high_price = highs.iloc[i]

            # State transitions
            broke_level = False

            if bullish_signal and current_state == DowTrendState.UNKNOWN:
                # Signal is a one-bar state - only from UNKNOWN state
                current_state = DowTrendState.BULLISH_SIGNAL
                pending_state = DowTrendState.UPTREND  # Next bar enters uptrend
                last_higher_low_price = last_swing_low_price
                trend_high_price = last_swing_high_price  # Track the high at signal
                last_lower_high_price = None
                trend_low_price = None

            elif bearish_signal and current_state == DowTrendState.UNKNOWN:
                # Signal is a one-bar state - only from UNKNOWN state
                current_state = DowTrendState.BEARISH_SIGNAL
                pending_state = DowTrendState.DOWNTREND  # Next bar enters downtrend
                last_lower_high_price = last_swing_high_price
                trend_low_price = last_swing_low_price  # Track the low at signal
                last_higher_low_price = None
                trend_high_price = None

            elif current_state == DowTrendState.UPTREND:
                # Check for trend breaks
                trend_broken = False

                # Check if LOW breaks below support level (last swing low)
                if last_higher_low_price is not None and lows.iloc[i] < last_higher_low_price:
                    trend_broken = True

                # Check for lower high on swing high
                if is_swing_high.iloc[i]:
                    if trend_high_price is not None and highs.iloc[i] < trend_high_price:
                        # Lower high - trend is broken
                        trend_broken = True
                    elif highs.iloc[i] > (trend_high_price or 0):
                        # New higher high - update tracking
                        trend_high_price = highs.iloc[i]

                # Update tracking on new swing low (if trend not broken)
                if is_swing_low.iloc[i] and not trend_broken:
                    if last_higher_low_price is not None and lows.iloc[i] > last_higher_low_price:
                        # New higher low - update support level
                        last_higher_low_price = lows.iloc[i]

                if trend_broken:
                    current_state = DowTrendState.TREND_END
                    pending_state = DowTrendState.UNKNOWN  # Reset next bar before signal checks
                    broke_level = True

            elif current_state == DowTrendState.DOWNTREND:
                # Check for trend breaks
                trend_broken = False

                # Check if HIGH breaks above resistance level (last swing high)
                if last_lower_high_price is not None and highs.iloc[i] > last_lower_high_price:
                    trend_broken = True

                # Check for higher low on swing low
                if is_swing_low.iloc[i]:
                    if trend_low_price is not None and lows.iloc[i] > trend_low_price:
                        # Higher low - trend is broken
                        trend_broken = True
                    elif lows.iloc[i] < (trend_low_price or float('inf')):
                        # New lower low - update tracking
                        trend_low_price = lows.iloc[i]

                # Update tracking on new swing high (if trend not broken)
                if is_swing_high.iloc[i] and not trend_broken:
                    if last_lower_high_price is not None and highs.iloc[i] < last_lower_high_price:
                        # New lower high - update resistance level
                        last_lower_high_price = highs.iloc[i]

                if trend_broken:
                    current_state = DowTrendState.TREND_END
                    pending_state = DowTrendState.UNKNOWN  # Reset next bar before signal checks
                    broke_level = True

            elif current_state == DowTrendState.TREND_END:
                # Fallback: if pending_state wasn't set, transition to UNKNOWN
                # (This should not happen with proper pending_state handling above)
                current_state = DowTrendState.UNKNOWN

            states.append({
                "bar_idx": i,
                "state": current_state.value,
                "last_swing_price": last_higher_low_price or last_lower_high_price,
                "broke_level": broke_level
            })

        return pd.DataFrame(states)
