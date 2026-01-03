"""Up bar classifier."""

import pandas as pd

from classifiers.base import Classifier


class UpBar(Classifier):
    """Classifies bars with higher high and higher low than previous bar."""

    name = "UpBar"
    description = "Identifies bars with higher high and higher low than previous"

    def classify(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        higher_high = data["High"] > data["High"].shift(1)
        higher_low = data["Low"] > data["Low"].shift(1)
        return higher_high & higher_low
