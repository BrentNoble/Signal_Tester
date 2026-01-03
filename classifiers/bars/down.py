"""Down bar classifier."""

import pandas as pd

from classifiers.base import Classifier


class DownBar(Classifier):
    """Classifies bars with lower high and lower low than previous bar."""

    name = "DownBar"
    description = "Identifies bars with lower high and lower low than previous"

    def classify(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)
        lower_high = data["High"] < data["High"].shift(1)
        lower_low = data["Low"] < data["Low"].shift(1)
        return lower_high & lower_low
