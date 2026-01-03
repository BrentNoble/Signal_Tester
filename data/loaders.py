"""Functions to fetch and load stock data."""

import os
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

RAW_DATA_DIR = Path(__file__).parent / "raw"


def fetch_stock_data(
    symbol: str,
    start: str,
    end: str,
    save: bool = True,
) -> pd.DataFrame:
    """
    Fetch stock data from Yahoo Finance.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        start: Start date in 'YYYY-MM-DD' format
        end: End date in 'YYYY-MM-DD' format
        save: Whether to save data to raw directory

    Returns:
        DataFrame with OHLCV data
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end)

    if save:
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        filepath = RAW_DATA_DIR / f"{symbol}_{start}_{end}.csv"
        df.to_csv(filepath)

    return df


def load_stock_data(
    symbol: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load stock data from local cache or fetch if not available.

    Args:
        symbol: Stock ticker symbol
        start: Optional start date filter
        end: Optional end date filter

    Returns:
        DataFrame with OHLCV data
    """
    # Look for cached files
    pattern = f"{symbol}_*.csv"
    cached_files = list(RAW_DATA_DIR.glob(pattern))

    if cached_files:
        # Load most recent cached file
        filepath = sorted(cached_files)[-1]
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)

        if start:
            df = df[df.index >= start]
        if end:
            df = df[df.index <= end]

        return df

    raise FileNotFoundError(
        f"No cached data found for {symbol}. Use fetch_stock_data() first."
    )
