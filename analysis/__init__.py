"""Analysis utilities for signal evaluation."""

from .probability import calculate_hit_rate, calculate_base_rate, calculate_lift
from .duration import calculate_trend_duration

__all__ = [
    "calculate_hit_rate",
    "calculate_base_rate",
    "calculate_lift",
    "calculate_trend_duration",
]
