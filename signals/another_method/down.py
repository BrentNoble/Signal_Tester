"""Placeholder for another down signal method."""

import pandas as pd

from ..base import Signal


class AnotherDownSignal(Signal):
    """
    Placeholder for another bearish signal implementation.

    Replace this with your custom signal logic.
    """

    name = "AnotherDown"
    description = "Placeholder bearish signal"

    def generate(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate down signals.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Boolean Series with signal values
        """
        self.validate_data(data)

        # Placeholder: simple moving average crossover
        sma_short = data["Close"].rolling(window=10).mean()
        sma_long = data["Close"].rolling(window=30).mean()

        signal = (sma_short < sma_long) & (sma_short.shift(1) >= sma_long.shift(1))

        return signal.fillna(False)
