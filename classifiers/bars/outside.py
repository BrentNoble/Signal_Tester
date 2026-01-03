"""Outside bar classifier."""

import pandas as pd

from classifiers.base import Classifier


class OutsideBar(Classifier):
    """Classifies bars that engulf the previous bar's range."""

    name = "OutsideBar"
    description = "Identifies bars where high/low exceed previous bar's range"

    def classify(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        high_outside = data["High"] > data["High"].shift(1)
        low_outside = data["Low"] < data["Low"].shift(1)
        return high_outside & low_outside
