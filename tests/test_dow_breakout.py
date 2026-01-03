"""Tests for Dow Theory breakout signals."""

import pandas as pd
import numpy as np
import pytest

from signals.dow_breakout import BreakUpSignal, BreakDownSignal


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range("2023-01-01", periods=50, freq="D")

    # Create trending data with a breakout
    np.random.seed(42)
    base_price = 100

    # First 20 days: range-bound
    prices = [base_price + np.random.randn() * 2 for _ in range(20)]
    # Days 21-30: breakout up
    prices.extend([base_price + 5 + i * 0.5 + np.random.randn() for i in range(10)])
    # Days 31-40: pullback
    prices.extend([base_price + 8 - i * 0.3 + np.random.randn() for i in range(10)])
    # Days 41-50: breakdown
    prices.extend([base_price - 2 - i * 0.5 + np.random.randn() for i in range(10)])

    df = pd.DataFrame(
        {
            "Open": prices,
            "High": [p + abs(np.random.randn()) for p in prices],
            "Low": [p - abs(np.random.randn()) for p in prices],
            "Close": prices,
            "Volume": [1000000] * 50,
        },
        index=dates,
    )

    return df


class TestBreakUpSignal:
    """Tests for BreakUpSignal."""

    def test_init_default_lookback(self):
        signal = BreakUpSignal()
        assert signal.lookback == 20

    def test_init_custom_lookback(self):
        signal = BreakUpSignal(lookback=10)
        assert signal.lookback == 10

    def test_generate_returns_series(self, sample_data):
        signal = BreakUpSignal(lookback=10)
        result = signal.generate(sample_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)

    def test_generate_returns_boolean(self, sample_data):
        signal = BreakUpSignal(lookback=10)
        result = signal.generate(sample_data)

        assert result.dtype == bool

    def test_signal_name(self):
        signal = BreakUpSignal()
        assert signal.name == "DowBreakUp"

    def test_validate_data_missing_columns(self):
        signal = BreakUpSignal()
        bad_data = pd.DataFrame({"Close": [1, 2, 3]})

        with pytest.raises(ValueError, match="Missing required columns"):
            signal.validate_data(bad_data)


class TestBreakDownSignal:
    """Tests for BreakDownSignal."""

    def test_init_default_lookback(self):
        signal = BreakDownSignal()
        assert signal.lookback == 20

    def test_init_custom_lookback(self):
        signal = BreakDownSignal(lookback=15)
        assert signal.lookback == 15

    def test_generate_returns_series(self, sample_data):
        signal = BreakDownSignal(lookback=10)
        result = signal.generate(sample_data)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)

    def test_generate_returns_boolean(self, sample_data):
        signal = BreakDownSignal(lookback=10)
        result = signal.generate(sample_data)

        assert result.dtype == bool

    def test_signal_name(self):
        signal = BreakDownSignal()
        assert signal.name == "DowBreakDown"


class TestSignalIntegration:
    """Integration tests for signal generation."""

    def test_up_and_down_signals_exclusive(self, sample_data):
        """Up and down signals should not fire on the same day."""
        up_signal = BreakUpSignal(lookback=10)
        down_signal = BreakDownSignal(lookback=10)

        up_result = up_signal.generate(sample_data)
        down_result = down_signal.generate(sample_data)

        # No day should have both signals
        overlap = up_result & down_result
        assert not overlap.any()
