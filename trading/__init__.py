"""Trading module for risk-managed signal execution."""

from .risk import RiskParams, calculate_position_size, calculate_r_multiple
from .trades import Trade, TradeTracker
from .backtest import backtest, BacktestResult

__all__ = [
    "RiskParams",
    "calculate_position_size",
    "calculate_r_multiple",
    "Trade",
    "TradeTracker",
    "backtest",
    "BacktestResult",
]
