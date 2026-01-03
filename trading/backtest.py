"""Backtesting engine for signal strategies."""

from dataclasses import dataclass
from typing import Optional
import pandas as pd
import matplotlib.pyplot as plt

from .risk import RiskParams
from .trades import TradeTracker
from classifiers.swings.swing_low import SwingLow
from signals.dow_breakout.up import Dow123BullishBreakout
from signals.dow_breakout.down import Dow123BearishBreakdown


@dataclass
class BacktestResult:
    """Results from a backtest run.

    Attributes:
        tracker: TradeTracker with all trades
        data: Original price data
        signals_df: DataFrame with signal columns
        statistics: Trading statistics dict
    """
    tracker: TradeTracker
    data: pd.DataFrame
    signals_df: pd.DataFrame
    statistics: dict


def backtest(
    data: pd.DataFrame,
    risk_params: Optional[RiskParams] = None,
    start_bar: int = 0
) -> BacktestResult:
    """Run backtest on historical data.

    Strategy:
    - Long only: Enter on bullish breakout
    - Stop: Last swing low
    - Exit: Stop hit, bearish signal, or trend end

    Args:
        data: DataFrame with OHLC columns
        risk_params: Risk parameters (default: $100k, 1% risk)
        start_bar: Bar to start trading from (skip early data)

    Returns:
        BacktestResult with trades and statistics
    """
    if risk_params is None:
        risk_params = RiskParams()

    # Initialize
    tracker = TradeTracker(risk_params=risk_params)
    swing_low = SwingLow()
    bullish_signal = Dow123BullishBreakout()
    bearish_signal = Dow123BearishBreakdown()

    # Generate signals
    is_swing_low = swing_low.classify(data)
    is_bullish = bullish_signal.generate(data)
    is_bearish = bearish_signal.generate(data)

    signals_df = pd.DataFrame({
        "swing_low": is_swing_low,
        "bullish": is_bullish,
        "bearish": is_bearish
    }, index=data.index)

    # Track last swing low for stop placement
    last_swing_low_price = None

    highs = data["High"]
    lows = data["Low"]
    closes = data["Close"]

    # Get dates (handle both DatetimeIndex and regular index)
    if isinstance(data.index, pd.DatetimeIndex):
        dates = data.index
    else:
        dates = pd.to_datetime(data.index) if hasattr(data.index[0], 'date') else data.index

    for i in range(start_bar, len(data)):
        # Update swing low tracking
        if is_swing_low.iloc[i]:
            last_swing_low_price = lows.iloc[i]

        current_trade = tracker.get_open_trade()

        # Check exits first (if we have an open trade)
        if current_trade is not None:
            exit_reason = None
            exit_price = None

            # Priority 1: Stop hit (LOW < stop)
            if lows.iloc[i] < current_trade.stop_price:
                exit_reason = "stop"
                exit_price = current_trade.stop_price  # Assume filled at stop

            # Priority 2: Bearish signal
            elif is_bearish.iloc[i]:
                exit_reason = "bearish_signal"
                exit_price = closes.iloc[i]

            # Execute exit if triggered
            if exit_reason:
                try:
                    exit_date = dates[i].to_pydatetime() if hasattr(dates[i], 'to_pydatetime') else dates[i]
                except:
                    exit_date = dates[i]

                tracker.close_trade(
                    exit_bar=i,
                    exit_date=exit_date,
                    exit_price=exit_price,
                    exit_reason=exit_reason
                )
                current_trade = None

        # Check entries (if no open trade)
        if current_trade is None and is_bullish.iloc[i]:
            # Need a valid swing low for stop
            if last_swing_low_price is not None:
                entry_price = highs.iloc[i]  # Entry at breakout high
                stop_price = last_swing_low_price

                # Only enter if risk makes sense (entry > stop)
                if entry_price > stop_price:
                    try:
                        entry_date = dates[i].to_pydatetime() if hasattr(dates[i], 'to_pydatetime') else dates[i]
                    except:
                        entry_date = dates[i]

                    tracker.open_trade(
                        signal_type="bullish",
                        entry_bar=i,
                        entry_date=entry_date,
                        entry_price=entry_price,
                        stop_price=stop_price
                    )

    # Close any remaining open trade at end of data
    open_trade = tracker.get_open_trade()
    if open_trade is not None:
        try:
            exit_date = dates[-1].to_pydatetime() if hasattr(dates[-1], 'to_pydatetime') else dates[-1]
        except:
            exit_date = dates[-1]

        tracker.close_trade(
            exit_bar=len(data) - 1,
            exit_date=exit_date,
            exit_price=closes.iloc[-1],
            exit_reason="end_of_data"
        )

    return BacktestResult(
        tracker=tracker,
        data=data,
        signals_df=signals_df,
        statistics=tracker.get_statistics()
    )


def plot_backtest(
    result: BacktestResult,
    title: str = "Backtest Results",
    save_path: Optional[str] = None,
    show: bool = True
) -> None:
    """Plot backtest results with trades marked.

    Args:
        result: BacktestResult from backtest()
        title: Chart title
        save_path: Path to save chart (optional)
        show: Whether to display the chart
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                    gridspec_kw={'height_ratios': [3, 1]})

    data = result.data
    trades = result.tracker.get_closed_trades()

    # Price chart
    ax1.plot(range(len(data)), data["Close"], color="black", linewidth=0.5, alpha=0.7)

    # Mark trades
    for trade in trades:
        color = "green" if trade.is_winner else "red"

        # Entry marker
        ax1.plot(trade.entry_bar, trade.entry_price, "^",
                 color="blue", markersize=10, markeredgecolor="black")

        # Exit marker
        ax1.plot(trade.exit_bar, trade.exit_price, "v",
                 color=color, markersize=10, markeredgecolor="black")

        # Stop level line
        ax1.hlines(trade.stop_price, trade.entry_bar, trade.exit_bar,
                   colors="red", linestyles="dashed", alpha=0.5)

        # Trade line
        ax1.plot([trade.entry_bar, trade.exit_bar],
                 [trade.entry_price, trade.exit_price],
                 color=color, linewidth=2, alpha=0.7)

    ax1.set_ylabel("Price")
    ax1.set_title(f"{title}\n{result.statistics['total_trades']} trades | "
                  f"Win rate: {result.statistics['win_rate']*100:.1f}% | "
                  f"Expectancy: {result.statistics['expectancy_r']:+.2f}R")
    ax1.grid(True, alpha=0.3)

    # Equity curve (cumulative R)
    equity = result.tracker.get_equity_curve()
    if len(equity) > 0:
        ax2.plot(range(len(equity)), equity.values, color="blue", linewidth=2)
        ax2.fill_between(range(len(equity)), 0, equity.values,
                         where=equity.values >= 0, color="green", alpha=0.3)
        ax2.fill_between(range(len(equity)), 0, equity.values,
                         where=equity.values < 0, color="red", alpha=0.3)
        ax2.axhline(0, color="black", linewidth=0.5)

    ax2.set_xlabel("Trade Number")
    ax2.set_ylabel("Cumulative R")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Chart saved to: {save_path}")

    if show:
        plt.show(block=False)
        plt.pause(0.1)
