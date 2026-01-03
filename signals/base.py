"""Base class defining the signal interface."""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class Signal(ABC):
    """
    Abstract base class for all trading signals.

    All signal implementations must inherit from this class and implement
    the generate() method.
    """

    name: str = "BaseSignal"
    description: str = ""

    @abstractmethod
    def generate(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate signal values from price data.

        Args:
            data: DataFrame with OHLCV columns (Open, High, Low, Close, Volume)

        Returns:
            Series with boolean or numeric signal values, indexed by date
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> None:
        """Validate that required columns exist in the data."""
        required_columns = {"Open", "High", "Low", "Close"}
        missing = required_columns - set(data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
