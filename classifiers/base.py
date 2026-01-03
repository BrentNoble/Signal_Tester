"""Base class defining the classifier interface."""

from abc import ABC, abstractmethod

import pandas as pd


class Classifier(ABC):
    """
    Abstract base class for all market state classifiers.

    Classifiers detect primitive market states (e.g., bar types, swing points).
    They are building blocks that signals compose together.
    """

    name: str = "BaseClassifier"
    description: str = ""

    @abstractmethod
    def classify(self, data: pd.DataFrame) -> pd.Series:
        """
        Classify each bar in the data.

        Args:
            data: DataFrame with OHLCV columns (Open, High, Low, Close, Volume)

        Returns:
            Series with boolean values indicating classification, indexed by date
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
