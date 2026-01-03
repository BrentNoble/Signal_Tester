"""Main entry point for signal analysis."""

import argparse
from datetime import datetime, timedelta

import pandas as pd

from data.loaders import fetch_stock_data, load_stock_data
from signals.dow_breakout import Dow123BullishBreakout, Dow123BearishBreakdown
from signals.another_method import AnotherUpSignal, AnotherDownSignal
from analysis.probability import calculate_hit_rate, calculate_lift, calculate_expectancy
from analysis.duration import calculate_trend_duration, calculate_max_favorable_excursion


def run_signal_analysis(
    symbol: str,
    start: str,
    end: str,
    forward_periods: int = 5,
) -> pd.DataFrame:
    """
    Run analysis on all available signals for a given symbol.

    Args:
        symbol: Stock ticker symbol
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        forward_periods: Periods to look ahead for return calculation

    Returns:
        DataFrame with analysis results for each signal
    """
    # Fetch data
    print(f"Fetching data for {symbol}...")
    try:
        data = load_stock_data(symbol, start, end)
        print(f"Loaded cached data: {len(data)} rows")
    except FileNotFoundError:
        data = fetch_stock_data(symbol, start, end)
        print(f"Fetched fresh data: {len(data)} rows")

    # Calculate returns
    returns = data["Close"].pct_change()

    # Define signals to analyze
    signals = [
        Dow123BullishBreakout(),
        Dow123BearishBreakdown(),
        AnotherUpSignal(),
        AnotherDownSignal(),
    ]

    results = []

    for signal in signals:
        print(f"\nAnalyzing {signal.name}...")

        # Generate signals
        signal_series = signal.generate(data)
        signal_count = signal_series.sum()

        if signal_count == 0:
            print(f"  No signals generated")
            continue

        print(f"  Generated {signal_count} signals")

        # Calculate statistics
        lift_stats = calculate_lift(signal_series, returns, forward_periods)
        expectancy = calculate_expectancy(signal_series, returns, forward_periods)

        # Determine direction for duration analysis
        direction = "up" if "Bullish" in signal.name or "Up" in signal.name else "down"
        duration_stats = calculate_trend_duration(data, signal_series, direction)
        mfe_stats = calculate_max_favorable_excursion(
            data, signal_series, direction, max_periods=forward_periods
        )

        results.append({
            "signal": signal.name,
            "total_signals": lift_stats["total_signals"],
            "hit_rate": lift_stats["hit_rate"],
            "base_rate": lift_stats["base_rate"],
            "lift": lift_stats["lift"],
            "expectancy": expectancy,
            "mean_duration": duration_stats["mean_duration"],
            "mean_mfe": mfe_stats["mean_mfe"],
        })

    return pd.DataFrame(results)


def compare_signals(results: pd.DataFrame) -> None:
    """Print a comparison of signal performance."""
    print("\n" + "=" * 60)
    print("SIGNAL COMPARISON")
    print("=" * 60)

    if results.empty:
        print("No results to compare.")
        return

    # Sort by lift
    results_sorted = results.sort_values("lift", ascending=False)

    for _, row in results_sorted.iterrows():
        print(f"\n{row['signal']}")
        print("-" * 40)
        print(f"  Signals:     {row['total_signals']:>10}")
        print(f"  Hit Rate:    {row['hit_rate']:>10.2%}")
        print(f"  Base Rate:   {row['base_rate']:>10.2%}")
        print(f"  Lift:        {row['lift']:>10.2f}x")
        print(f"  Expectancy:  {row['expectancy']:>10.4f}")
        print(f"  Avg Duration:{row['mean_duration']:>10.1f} periods")
        print(f"  Avg MFE:     {row['mean_mfe']:>10.2%}")


def main():
    parser = argparse.ArgumentParser(description="Stock Signal Analysis")
    parser.add_argument(
        "--symbol",
        type=str,
        default="SPY",
        help="Stock ticker symbol (default: SPY)",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=(datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d"),
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=datetime.now().strftime("%Y-%m-%d"),
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--forward",
        type=int,
        default=5,
        help="Forward periods for return calculation (default: 5)",
    )

    args = parser.parse_args()

    results = run_signal_analysis(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        forward_periods=args.forward,
    )

    compare_signals(results)

    # Save results
    output_file = f"results_{args.symbol}_{args.start}_{args.end}.csv"
    results.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
