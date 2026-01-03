"""Swing high classifier."""

import pandas as pd

from classifiers.base import Classifier
from classifiers.bars.up import UpBar
from classifiers.bars.down import DownBar
from classifiers.bars.inside import InsideBar
from classifiers.bars.outside import OutsideBar


class SwingHigh(Classifier):
    """
    Classifies swing high points.

    Rules:
    - UP bar followed by DOWN bar = High at UP bar
    - UP bar followed by OUTSIDE then DOWN = High at OUTSIDE bar
    - UP bar followed by OUTSIDE(s) then UP = High at first UP bar (lows went down)
    - OUTSIDE bar with higher high AND lower low than neighbors = both High and Low
    - DOWN→OUTSIDE→DOWN with higher high = High at OUTSIDE
    - Prior swing must be LOW (alternating swings rule)

    Inside bars are ignored when finding directional bars.
    """

    name = "SwingHigh"
    description = "Identifies trend turns from up to down (alternating swings)"

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

        is_swing_high = pd.Series(False, index=data.index)
        last_swing = None

        for i in range(len(data)):
            detected_swing_this_bar = False
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

            # Find first directional (UP or DOWN) bars
            left_dir_idx = None
            for j in range(i - 1, -1, -1):
                if is_up.iloc[j] or is_down.iloc[j]:
                    left_dir_idx = j
                    break

            right_dir_idx = None
            for j in range(i + 1, len(data)):
                if is_up.iloc[j] or is_down.iloc[j]:
                    right_dir_idx = j
                    break

            # OUTSIDE bars: check for "not engulfed" (both High and Low)
            if is_outside.iloc[i] and left_idx is not None:
                not_engulfed_high = current_high > highs.iloc[left_idx] and current_high > highs.iloc[right_idx]
                not_engulfed_low = current_low < lows.iloc[left_idx] and current_low < lows.iloc[right_idx]

                if not_engulfed_high and not_engulfed_low:
                    is_swing_high.iloc[i] = True
                    last_swing = 'high'
                    detected_swing_this_bar = True
                    continue

            # UP bars
            if is_up.iloc[i]:
                # UP → DOWN = High at UP
                if is_down.iloc[right_idx]:
                    if lows.iloc[right_idx] < current_low:
                        if last_swing is None or last_swing == 'low':
                            is_swing_high.iloc[i] = True
                            last_swing = 'high'
                            detected_swing_this_bar = True
                # UP → OUTSIDE: check what follows the outside bars
                elif is_outside.iloc[right_idx]:
                    if right_dir_idx is not None:
                        # UP → OUTSIDE(s) → UP = High at first UP (if lows went down)
                        if is_up.iloc[right_dir_idx]:
                            if lows.iloc[right_idx] < current_low:
                                if last_swing is None or last_swing == 'low':
                                    is_swing_high.iloc[i] = True
                                    last_swing = 'high'
                                    detected_swing_this_bar = True
                        # UP → OUTSIDE(s) → DOWN = High at last OUTSIDE
                        # (handled in OUTSIDE section below)

            # OUTSIDE bars: pattern matching
            elif is_outside.iloc[i] and left_idx is not None:
                left_is_up = is_up.iloc[left_dir_idx] if left_dir_idx is not None else False
                left_is_down = is_down.iloc[left_dir_idx] if left_dir_idx is not None else False
                right_is_down = is_down.iloc[right_dir_idx] if right_dir_idx is not None else False

                # UP → OUTSIDE(s) → DOWN = High at last OUTSIDE before DOWN
                if left_is_up and right_is_down:
                    # Check if this is the last outside bar before the down
                    next_is_outside = is_outside.iloc[right_idx] if right_idx < len(data) else False
                    if not next_is_outside or right_idx == right_dir_idx:
                        if last_swing is None or last_swing == 'low':
                            is_swing_high.iloc[i] = True
                            last_swing = 'high'
                            detected_swing_this_bar = True

                # DOWN → OUTSIDE → DOWN = High at OUTSIDE (if higher high than neighbors)
                elif left_is_down and right_is_down:
                    if current_high > highs.iloc[left_idx] and current_high > highs.iloc[right_idx]:
                        if last_swing is None or last_swing == 'low':
                            is_swing_high.iloc[i] = True
                            last_swing = 'high'
                            detected_swing_this_bar = True

            # Update state for swing LOW (needed for alternation)
            # Skip if we already detected a swing this bar
            if not detected_swing_this_bar and (is_down.iloc[i] or is_outside.iloc[i]):
                if highs.iloc[right_idx] > current_high:
                    if last_swing is None or last_swing == 'high':
                        last_swing = 'low'

        return is_swing_high
