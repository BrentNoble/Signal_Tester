#!/usr/bin/env python
"""
Signal validation analysis for ASX dividend stocks.

Usage:
    python analyse.py --stock CBA
    python analyse.py --stock BHP --data path/to/BHP_weekly.csv
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

from signals.dow_breakout import Dow123BullishBreakout, Dow123BearishBreakdown, DowntrendReversal
from signals.twelve_bar import TwelveBarBreakout
from outcomes import OutcomeMeasurer, RandomBaseline


def load_stock_data(ticker: str, data_path: str = None) -> pd.DataFrame:
    """
    Load weekly OHLC data for a stock.

    Args:
        ticker: Stock ticker (e.g., "CBA")
        data_path: Optional path to CSV file. If None, looks in data/{ticker}_weekly.csv

    Returns:
        DataFrame with Open, High, Low, Close columns
    """
    if data_path:
        path = Path(data_path)
    else:
        path = Path(__file__).parent / "data" / f"{ticker}_weekly.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            f"Please provide weekly OHLC data for {ticker}"
        )

    df = pd.read_csv(path)

    # Standardize column names
    df.columns = [c.capitalize() for c in df.columns]

    # Ensure required columns exist
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse date if present
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

    return df


def analyse_stock(ticker: str, data: pd.DataFrame) -> dict:
    """
    Run full signal validation analysis on a stock.

    Args:
        ticker: Stock ticker
        data: DataFrame with OHLC data

    Returns:
        Dict with analysis results
    """
    print(f"\n{'='*60}")
    print(f"ANALYSING: {ticker}")
    print(f"{'='*60}")
    print(f"Data: {len(data)} weekly bars")

    # Initialize signals
    bullish = Dow123BullishBreakout()
    bearish = Dow123BearishBreakdown()
    reversal = DowntrendReversal()
    twelve_bar = TwelveBarBreakout()

    # Generate signals
    bullish_signals = bullish.generate(data)
    bearish_signals = bearish.generate(data)
    reversal_signals = reversal.generate(data)
    twelve_bar_signals = twelve_bar.generate(data)

    print(f"\nSignals detected:")
    print(f"  Bullish Breakout: {bullish_signals.sum()}")
    print(f"  Bearish Breakdown: {bearish_signals.sum()}")
    print(f"  Downtrend Reversal: {reversal_signals.sum()}")
    print(f"  TwelveBar Breakout: {twelve_bar_signals.sum()}")

    # Measure outcomes
    measurer = OutcomeMeasurer()

    # For bullish signals, bearish breakdown is the exit signal
    bullish_outcomes = measurer.measure_all(
        data, bullish_signals, "bullish_breakout", exit_signals=bearish_signals
    )

    # For reversal signals, bearish breakdown is also the exit signal
    reversal_outcomes = measurer.measure_all(
        data, reversal_signals, "downtrend_reversal", exit_signals=bearish_signals
    )

    # For twelve bar breakout signals, bearish breakdown is the exit signal
    twelve_bar_outcomes = measurer.measure_all(
        data, twelve_bar_signals, "twelve_bar_breakout", exit_signals=bearish_signals
    )

    # Calculate baseline
    baseline = RandomBaseline(n_samples=min(500, len(data) - 53), seed=42)
    try:
        baseline_stats = baseline.measure(data)
    except ValueError as e:
        print(f"  Warning: Could not calculate baseline - {e}")
        baseline_stats = {}

    # Summarize results
    results = {
        "ticker": ticker,
        "total_bars": len(data),
        "bullish_breakout": {
            "outcomes": bullish_outcomes,
            "summary": measurer.summarize(bullish_outcomes),
            "df": measurer.to_dataframe(bullish_outcomes),
        },
        "downtrend_reversal": {
            "outcomes": reversal_outcomes,
            "summary": measurer.summarize(reversal_outcomes),
            "df": measurer.to_dataframe(reversal_outcomes),
        },
        "twelve_bar_breakout": {
            "outcomes": twelve_bar_outcomes,
            "summary": measurer.summarize(twelve_bar_outcomes),
            "df": measurer.to_dataframe(twelve_bar_outcomes),
        },
        "baseline": baseline_stats,
    }

    # Print summaries
    for signal_type in ["bullish_breakout", "downtrend_reversal", "twelve_bar_breakout"]:
        summary = results[signal_type]["summary"]
        if summary:
            print(f"\n{signal_type.upper().replace('_', ' ')}:")
            print(f"  Total signals: {summary.get('total_signals', 0)}")
            print(f"  Win rate (12m): {summary.get('win_rate_12m', 0):.1f}%")
            print(f"  Mean return (12m): {summary.get('mean_return_12m', 0):.1f}%")
            print(f"  Mean MFE: {summary.get('mean_mfe_12m', 0):.1f}%")
            print(f"  Mean MAE: {summary.get('mean_mae_12m', 0):.1f}%")
            print(f"  Mean left on table: {summary.get('mean_left_on_table', 0):.1f}%")

            if summary.get('exit_fired_rate', 0) > 0:
                print(f"  Exit signal fired: {summary.get('exit_fired_rate', 0):.1f}%")
                print(f"  Exit useful rate: {summary.get('exit_useful_rate', 'N/A')}")

    if baseline_stats:
        print(f"\nBASELINE (Random Entry):")
        print(f"  Win rate (12m): {baseline_stats.get('baseline_win_rate', 0):.1f}%")
        print(f"  Mean return (12m): {baseline_stats.get('baseline_mean_return', 0):.1f}%")

        # Calculate lift
        for signal_type in ["bullish_breakout", "downtrend_reversal", "twelve_bar_breakout"]:
            summary = results[signal_type]["summary"]
            if summary and summary.get("total_signals", 0) > 0:
                signal_wr = summary.get("win_rate_12m", 0)
                baseline_wr = baseline_stats.get("baseline_win_rate", 0)
                if baseline_wr > 0:
                    lift = signal_wr / baseline_wr
                    print(f"  Lift ({signal_type}): {lift:.2f}x")

    return results


def export_to_excel(results: dict, output_dir: str = "results"):
    """
    Export analysis results to Excel.

    Args:
        results: Results dict from analyse_stock()
        output_dir: Directory to save Excel files
    """
    ticker = results["ticker"]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{ticker}.xlsx")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Sheet 1: All signal instances
        all_signals = []

        for signal_type in ["bullish_breakout", "downtrend_reversal", "twelve_bar_breakout"]:
            df = results[signal_type]["df"]
            if len(df) > 0:
                all_signals.append(df)

        if all_signals:
            combined = pd.concat(all_signals, ignore_index=True)
            combined.to_excel(writer, sheet_name="Signal Instances", index=False)

        # Sheet 2: Summary
        summary_data = []
        for signal_type in ["bullish_breakout", "downtrend_reversal", "twelve_bar_breakout"]:
            summary = results[signal_type]["summary"]
            if summary:
                row = {"signal_type": signal_type}
                row.update(summary)
                summary_data.append(row)

        if results.get("baseline"):
            row = {"signal_type": "random_baseline"}
            row.update(results["baseline"])
            summary_data.append(row)

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

    print(f"\nResults exported to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Signal validation analysis for ASX dividend stocks"
    )
    parser.add_argument(
        "--stock", "-s",
        required=True,
        help="Stock ticker (e.g., CBA, BHP, FMG)"
    )
    parser.add_argument(
        "--data", "-d",
        help="Path to weekly OHLC CSV file (default: data/{TICKER}_weekly.csv)"
    )
    parser.add_argument(
        "--output", "-o",
        default="results",
        help="Output directory for Excel files (default: results)"
    )

    args = parser.parse_args()

    try:
        # Load data
        data = load_stock_data(args.stock, args.data)

        # Run analysis
        results = analyse_stock(args.stock, data)

        # Export results
        export_to_excel(results, args.output)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
