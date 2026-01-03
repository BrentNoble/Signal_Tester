"""Inside bar classifier."""

import pandas as pd

from classifiers.base import Classifier


class InsideBar(Classifier):
    """Classifies bars contained within the previous bar's range."""

    name = "InsideBar"
    description = "Identifies bars where high/low are within previous bar's range"

    def classify(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        high_inside = data["High"] <= data["High"].shift(1)
        low_inside = data["Low"] >= data["Low"].shift(1)
        return high_inside & low_inside
