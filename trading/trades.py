"""Trade tracking and management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import pandas as pd
import numpy as np

from .risk import RiskParams, calculate_position_size, calculate_r_multiple


@dataclass
class Trade:
    """A single trade with entry, exit, and risk metrics.

    Attributes:
        signal_type: "bullish" or "bearish"
        entry_bar: Bar index where trade was entered
        entry_date: Date of entry
        entry_price: Price at entry
        stop_price: Stop loss price (swing level)
        risk_per_share: Dollar risk per share (entry - stop)
        position_size: Number of shares
        exit_bar: Bar index where trade was closed
        exit_date: Date of exit
        exit_price: Price at exit
        exit_reason: "stop", "signal", "trend_end", or "end_of_data"
        pnl: Profit/loss in dollars
        r_multiple: PnL expressed as multiple of risk
    """
    signal_type: str
    entry_bar: int
    entry_date: datetime
    entry_price: float
    stop_price: float
    risk_per_share: float
    position_size: int

    # Filled on exit
    exit_bar: Optional[int] = None
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    r_multiple: Optional[float] = None

    @property
    def is_open(self) -> bool:
        """Check if trade is still open."""
        return self.exit_bar is None

    @property
    def is_winner(self) -> bool:
        """Check if trade was profitable."""
        return self.pnl is not None and self.pnl > 0

    def close(
        self,
        exit_bar: int,
        exit_date: datetime,
        exit_price: float,
        exit_reason: str
    ) -> None:
        """Close the trade and calculate P&L metrics."""
        self.exit_bar = exit_bar
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = exit_reason

        # Calculate R-multiple
        self.r_multiple = calculate_r_multiple(
            self.entry_price,
            exit_price,
            self.stop_price,
            direction="long" if self.signal_type == "bullish" else "short"
        )

        # Calculate dollar P&L
        if self.signal_type == "bullish":
            self.pnl = (exit_price - self.entry_price) * self.position_size
        else:
            self.pnl = (self.entry_price - exit_price) * self.position_size


@dataclass
class TradeTracker:
    """Tracks all trades and calculates statistics.

    Attributes:
        trades: List of all trades (open and closed)
        risk_params: Risk parameters for position sizing
    """
    risk_params: RiskParams = field(default_factory=RiskParams)
    trades: List[Trade] = field(default_factory=list)

    def open_trade(
        self,
        signal_type: str,
        entry_bar: int,
        entry_date: datetime,
        entry_price: float,
        stop_price: float
    ) -> Trade:
        """Open a new trade.

        Args:
            signal_type: "bullish" or "bearish"
            entry_bar: Bar index of entry
            entry_date: Date of entry
            entry_price: Entry price
            stop_price: Stop loss price

        Returns:
            The opened Trade object
        """
        risk_per_share = abs(entry_price - stop_price)
        position_size = calculate_position_size(
            entry_price, stop_price, self.risk_params
        )

        trade = Trade(
            signal_type=signal_type,
            entry_bar=entry_bar,
            entry_date=entry_date,
            entry_price=entry_price,
            stop_price=stop_price,
            risk_per_share=risk_per_share,
            position_size=position_size
        )

        self.trades.append(trade)
        return trade

    def get_open_trade(self) -> Optional[Trade]:
        """Get the currently open trade, if any."""
        for trade in reversed(self.trades):
            if trade.is_open:
                return trade
        return None

    def close_trade(
        self,
        exit_bar: int,
        exit_date: datetime,
        exit_price: float,
        exit_reason: str
    ) -> Optional[Trade]:
        """Close the currently open trade.

        Args:
            exit_bar: Bar index of exit
            exit_date: Date of exit
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            The closed Trade object, or None if no open trade
        """
        trade = self.get_open_trade()
        if trade is None:
            return None

        trade.close(exit_bar, exit_date, exit_price, exit_reason)
        return trade

    def get_closed_trades(self) -> List[Trade]:
        """Get all closed trades."""
        return [t for t in self.trades if not t.is_open]

    def get_statistics(self) -> dict:
        """Calculate trading statistics.

        Returns:
            Dictionary with trading metrics
        """
        closed = self.get_closed_trades()

        if not closed:
            return {
                "total_trades": 0,
                "winners": 0,
                "losers": 0,
                "win_rate": 0.0,
                "avg_win_r": 0.0,
                "avg_loss_r": 0.0,
                "expectancy_r": 0.0,
                "total_r": 0.0,
                "total_pnl": 0.0,
                "max_drawdown_r": 0.0,
            }

        winners = [t for t in closed if t.is_winner]
        losers = [t for t in closed if not t.is_winner]

        win_rate = len(winners) / len(closed) if closed else 0
        avg_win_r = np.mean([t.r_multiple for t in winners]) if winners else 0
        avg_loss_r = np.mean([t.r_multiple for t in losers]) if losers else 0

        # Expectancy = (Win% × Avg Win) + (Loss% × Avg Loss)
        # Note: avg_loss_r is negative, so we add it
        expectancy = (win_rate * avg_win_r) + ((1 - win_rate) * avg_loss_r)

        total_r = sum(t.r_multiple for t in closed)
        total_pnl = sum(t.pnl for t in closed)

        # Calculate max drawdown in R terms
        cumulative_r = np.cumsum([t.r_multiple for t in closed])
        running_max = np.maximum.accumulate(cumulative_r)
        drawdown = cumulative_r - running_max
        max_drawdown_r = drawdown.min() if len(drawdown) > 0 else 0

        return {
            "total_trades": len(closed),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": win_rate,
            "avg_win_r": avg_win_r,
            "avg_loss_r": avg_loss_r,
            "expectancy_r": expectancy,
            "total_r": total_r,
            "total_pnl": total_pnl,
            "max_drawdown_r": max_drawdown_r,
        }

    def get_equity_curve(self) -> pd.Series:
        """Get cumulative R-multiple over time.

        Returns:
            Series with cumulative R at each trade exit
        """
        closed = self.get_closed_trades()
        if not closed:
            return pd.Series(dtype=float)

        r_values = [t.r_multiple for t in closed]
        dates = [t.exit_date for t in closed]

        cumulative_r = np.cumsum(r_values)
        return pd.Series(cumulative_r, index=dates, name="Cumulative R")

    def print_summary(self) -> None:
        """Print a formatted summary of trading results."""
        stats = self.get_statistics()

        print("\n" + "=" * 50)
        print("TRADING RESULTS")
        print("=" * 50)
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Winners: {stats['winners']} | Losers: {stats['losers']}")
        print(f"Win Rate: {stats['win_rate']*100:.1f}%")
        print(f"Avg Win: {stats['avg_win_r']:+.2f}R")
        print(f"Avg Loss: {stats['avg_loss_r']:+.2f}R")
        print(f"Expectancy: {stats['expectancy_r']:+.2f}R per trade")
        print(f"Total R: {stats['total_r']:+.2f}R")
        print(f"Total P&L: ${stats['total_pnl']:,.2f}")
        print(f"Max Drawdown: {stats['max_drawdown_r']:.2f}R")
        print("=" * 50)
