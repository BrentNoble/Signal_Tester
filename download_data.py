#!/usr/bin/env python
"""
Download weekly OHLC data for ASX stocks from Yahoo Finance.

Usage:
    python download_data.py CBA BHP WES TLS
    python download_data.py --all
"""

import argparse
import os
from pathlib import Path

import yfinance as yf
import pandas as pd


# Default stocks to download
DEFAULT_STOCKS = ["CBA", "BHP", "WES", "TLS", "FMG"]


def download_stock(ticker: str, output_dir: str = "data") -> str:
    """
    Download weekly OHLC data for an ASX stock.

    Args:
        ticker: ASX ticker (e.g., "CBA")
        output_dir: Directory to save CSV files

    Returns:
        Path to saved CSV file
    """
    # ASX tickers on Yahoo Finance use .AX suffix
    yf_ticker = f"{ticker}.AX"

    print(f"Downloading {ticker} ({yf_ticker})...")

    # Download max history, weekly interval
    stock = yf.Ticker(yf_ticker)
    df = stock.history(period="max", interval="1wk")

    if len(df) == 0:
        raise ValueError(f"No data found for {yf_ticker}")

    # Reset index to get Date as column
    df = df.reset_index()

    # Keep only OHLC columns
    df = df[["Date", "Open", "High", "Low", "Close"]]

    # Save to CSV
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{ticker}_weekly.csv")
    df.to_csv(output_path, index=False)

    print(f"  Saved {len(df)} weekly bars to {output_path}")
    print(f"  Date range: {df['Date'].min()} to {df['Date'].max()}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Download weekly OHLC data for ASX stocks"
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Stock tickers to download (e.g., CBA BHP)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Download all default stocks: {', '.join(DEFAULT_STOCKS)}"
    )

    args = parser.parse_args()

    if args.all:
        tickers = DEFAULT_STOCKS
    elif args.tickers:
        tickers = [t.upper() for t in args.tickers]
    else:
        print("No tickers specified. Use --all or provide tickers.")
        print(f"Example: python download_data.py CBA BHP")
        return

    print(f"\nDownloading {len(tickers)} stocks...\n")

    for ticker in tickers:
        try:
            download_stock(ticker)
        except Exception as e:
            print(f"  Error downloading {ticker}: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
