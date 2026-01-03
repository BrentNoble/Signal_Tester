"""Swing low classifier."""

import pandas as pd

from classifiers.base import Classifier
from classifiers.bars.up import UpBar
from classifiers.bars.down import DownBar
from classifiers.bars.inside import InsideBar
from classifiers.bars.outside import OutsideBar


class SwingLow(Classifier):
    """
    Classifies swing low points.

    Rules:
    - DOWN bar followed by UP bar = Low at DOWN bar
    - DOWN bar followed by OUTSIDE then UP = Low at OUTSIDE bar
    - DOWN bar followed by OUTSIDE(s) then DOWN = Low at first DOWN bar (highs went up)
    - OUTSIDE bar with higher high AND lower low than neighbors = both High and Low
    - UP→OUTSIDE→UP with lower low = Low at OUTSIDE
    - Prior swing must be HIGH (alternating swings rule)

    Inside bars are ignored when finding directional bars.
    """

    name = "SwingLow"
    description = "Identifies trend turns from down to up (alternating swings)"

    def __init__(self):
        self._up_bar = UpBar()
        self._down_bar = DownBar()
        self._inside_bar = InsideBar()
        self._outside_bar = OutsideBar()

    def classify(self, data: pd.DataFrame) -> pd.Series:
        self.validate_data(data)

        is_up = self._up_bar.classify(data)
        is_down = self._down_bar.classify(data)
        is_inside = self._inside_bar.classify(data)
        is_outside = self._outside_bar.classify(data)
        highs = data["High"]
        lows = data["Low"]

        is_swing_low = pd.Series(False, index=data.index)
        last_swing = None

        for i in range(len(data)):
            if is_inside.iloc[i]:
                continue

            # Find neighbors (skipping inside bars)
            right_idx = None
            for j in range(i + 1, len(data)):
                if not is_inside.iloc[j]:
                    right_idx = j
                    break

            if right_idx is None:
                continue

            left_idx = None
            for j in range(i - 1, -1, -1):
                if not is_inside.iloc[j]:
                    left_idx = j
                    break

            current_high = highs.iloc[i]
            current_low = lows.iloc[i]

            # Find first directional (non-outside, non-inside) bars
            left_dir_idx = None
            for j in range(i - 1, -1, -1):
                if not is_inside.iloc[j] and not is_outside.iloc[j]:
                    left_dir_idx = j
                    break

            right_dir_idx = None
            for j in range(i + 1, len(data)):
                if not is_inside.iloc[j] and not is_outside.iloc[j]:
                    right_dir_idx = j
                    break

            # OUTSIDE bars: check for "not engulfed" (both High and Low)
            if is_outside.iloc[i] and left_idx is not None:
                not_engulfed_high = current_high > highs.iloc[left_idx] and current_high > highs.iloc[right_idx]
                not_engulfed_low = current_low < lows.iloc[left_idx] and current_low < lows.iloc[right_idx]

                if not_engulfed_high and not_engulfed_low:
                    is_swing_low.iloc[i] = True
                    last_swing = 'low'
                    continue

            # DOWN bars
            if is_down.iloc[i]:
                # DOWN → UP = Low at DOWN
                if is_up.iloc[right_idx]:
                    if highs.iloc[right_idx] > current_high:
                        if last_swing is None or last_swing == 'high':
                            is_swing_low.iloc[i] = True
                            last_swing = 'low'
                # DOWN → OUTSIDE: check what follows the outside bars
                elif is_outside.iloc[right_idx]:
                    if right_dir_idx is not None:
                        # DOWN → OUTSIDE(s) → DOWN = Low at first DOWN (if highs went up)
                        if is_down.iloc[right_dir_idx]:
                            if highs.iloc[right_idx] > current_high:
                                if last_swing is None or last_swing == 'high':
                                    is_swing_low.iloc[i] = True
                                    last_swing = 'low'
                        # DOWN → OUTSIDE(s) → UP = Low at last OUTSIDE
                        # (handled in OUTSIDE section below)

            # OUTSIDE bars: pattern matching
            elif is_outside.iloc[i] and left_idx is not None:
                left_is_down = is_down.iloc[left_dir_idx] if left_dir_idx is not None else False
                left_is_up = is_up.iloc[left_dir_idx] if left_dir_idx is not None else False
                right_is_up = is_up.iloc[right_dir_idx] if right_dir_idx is not None else False

                # DOWN → OUTSIDE(s) → UP = Low at last OUTSIDE before UP
                if left_is_down and right_is_up:
                    # Check if this is the last outside bar before the up
                    next_is_outside = is_outside.iloc[right_idx] if right_idx < len(data) else False
                    if not next_is_outside or right_idx == right_dir_idx:
                        if last_swing is None or last_swing == 'high':
                            is_swing_low.iloc[i] = True
                            last_swing = 'low'

                # UP → OUTSIDE → UP = Low at OUTSIDE (if lower low than neighbors)
                elif left_is_up and right_is_up:
                    if current_low < lows.iloc[left_idx] and current_low < lows.iloc[right_idx]:
                        if last_swing is None or last_swing == 'high':
                            is_swing_low.iloc[i] = True
                            last_swing = 'low'

            # Update state for swing HIGH (needed for alternation)
            if is_up.iloc[i] or is_outside.iloc[i]:
                if lows.iloc[right_idx] < current_low:
                    if last_swing is None or last_swing == 'low':
                        last_swing = 'high'

        return is_swing_low
