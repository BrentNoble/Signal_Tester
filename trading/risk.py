"""Risk management utilities for position sizing and R-multiple calculations."""

from dataclasses import dataclass


@dataclass
class RiskParams:
    """Risk parameters for position sizing.

    Attributes:
        account_size: Total account equity in dollars
        risk_per_trade_pct: Maximum risk per trade as decimal (0.01 = 1%)
    """
    account_size: float = 100000.0
    risk_per_trade_pct: float = 0.01  # 1% risk per trade

    @property
    def risk_per_trade(self) -> float:
        """Dollar amount risked per trade."""
        return self.account_size * self.risk_per_trade_pct


def calculate_position_size(
    entry_price: float,
    stop_price: float,
    risk_params: RiskParams
) -> int:
    """Calculate position size based on risk parameters.

    Args:
        entry_price: Expected entry price
        stop_price: Stop loss price
        risk_params: Risk parameters with account size and risk %

    Returns:
        Number of shares/units to trade (rounded down)
    """
    if entry_price <= 0 or stop_price <= 0:
        return 0

    risk_per_share = abs(entry_price - stop_price)

    if risk_per_share == 0:
        return 0

    position_size = risk_params.risk_per_trade / risk_per_share
    return int(position_size)  # Round down to whole shares


def calculate_r_multiple(
    entry_price: float,
    exit_price: float,
    stop_price: float,
    direction: str = "long"
) -> float:
    """Calculate R-multiple (profit/loss expressed as multiple of risk).

    R-multiple tells you how many "R" you made or lost:
    - 2R = made 2x your initial risk
    - -1R = lost exactly your initial risk (stopped out)
    - 0R = breakeven

    Args:
        entry_price: Actual entry price
        exit_price: Actual exit price
        stop_price: Stop loss price (defines 1R)
        direction: "long" or "short"

    Returns:
        R-multiple as float
    """
    risk_per_share = abs(entry_price - stop_price)

    if risk_per_share == 0:
        return 0.0

    if direction == "long":
        profit_per_share = exit_price - entry_price
    else:
        profit_per_share = entry_price - exit_price

    return profit_per_share / risk_per_share
