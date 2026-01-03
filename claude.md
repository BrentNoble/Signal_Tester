# Signal Lab

## What This Is

A statistical validation framework for technical analysis signals. We measure whether signals provide useful information about future price movement.

## What This Is NOT

**Do not add:**
- P&L calculations
- Position sizing
- Equity curves
- Drawdown analysis
- Trade simulation
- Portfolio management
- Risk-adjusted returns
- Sharpe ratios or any "strategy performance" metrics

If it belongs in a backtest engine, it doesn't belong here. We are validating signals as statistical predictors, not simulating trading strategies.

## Core Question

> When signal X fires, what is the probability that outcome Y occurs, and how does this compare to random entry?

That's it. Everything else is scope creep.

## Architecture

```
signal_lab/
├── classifiers/          # Primitives (bar types, swing points)
│   ├── bars/             # Up, Down, Inside, Outside
│   └── swings/           # SwingHigh, SwingLow
├── signals/              # Pattern detection
│   └── dow_breakout/     # Dow 1-2-3 patterns
├── outcomes/             # Outcome measurement
├── analysis/             # Statistical aggregation
├── data/
│   └── Test/             # Validated test data
└── tests/
```

## Definitions

### Bar Types (Gann)
| Type | Rule |
|------|------|
| Up | Higher high AND higher low |
| Down | Lower high AND lower low |
| Inside | High ≤ prior high AND low ≥ prior low |
| Outside | High > prior high AND low < prior low |

### Swing Points
- **Swing High**: Price reversed from up to down
- **Swing Low**: Price reversed from down to up
- Swings alternate (High → Low → High → Low)
- Inside bars are invisible to swing detection

### Dow 1-2-3 Bullish Breakout
1. Swing Low₁ forms
2. Swing High forms (resistance)
3. Swing Low₂ forms where Low₂ > Low₁ (higher low)
4. Bar HIGH breaks above Swing High → **Signal fires**

### Dow 1-2-3 Bearish Breakdown
1. Swing High₁ forms
2. Swing Low forms (support)
3. Swing High₂ forms where High₂ < High₁ (lower high)
4. Bar LOW breaks below Swing Low → **Signal fires**

### Trend (for outcome measurement)
- **Uptrend continues**: Higher highs and higher lows maintained
- **Uptrend breaks**: LOW < last swing low OR swing high forms lower than previous
- **Downtrend continues**: Lower highs and lower lows maintained
- **Downtrend breaks**: HIGH > last swing high OR swing low forms higher than previous

Note: Up and down are NOT symmetric. Measure them separately.

## What We Measure

For each signal instance:

| Metric | Definition |
|--------|------------|
| `trend_developed` | Did a Dow-defined trend establish? (bool) |
| `duration_bars` | Bars from signal to trend break |
| `magnitude_pct` | % change from signal close to trend break close |
| `mfe_pct` | Max favorable excursion (best possible exit) |
| `mae_pct` | Max adverse excursion (worst point during trend) |

Aggregated across all signals:

| Metric | Definition |
|--------|------------|
| `success_rate` | % of signals where trend developed |
| `mean_duration` | Average bars in trend |
| `mean_magnitude` | Average % gain/loss |
| `baseline_rate` | Success rate of random entry (control) |
| `lift` | success_rate / baseline_rate |

## Validation Data

`data/Test/test_gann_34bars.csv` - 34 bars with manually verified:
- Bar type classifications
- Swing point locations

`data/Test/test_signals_synthetic.csv` - Synthetic data covering:
- Bullish breakout → uptrend → trend end
- Bearish breakdown → downtrend → trend end
- All trend break conditions

Classifiers must achieve 100% accuracy on test data.

## Running Tests

```bash
python tests/test_gann_data.py      # Classifier accuracy
python tests/test_dow_signals.py    # Signal detection
```

## Code Conventions

- DataFrame columns: `Open`, `High`, `Low`, `Close` (capitalized)
- Classifiers return `pd.Series` of bool
- Signals return `pd.Series` of bool
- No lookahead in signal generation (outcomes can look forward)

## Status

**Working:**
- Bar classifiers (100% on Gann data)
- Swing classifiers (100% on Gann data)
- Dow 1-2-3 signal detection

**TODO:**
- Outcome measurement module
- Baseline comparison (random entry)
- Multi-stock aggregation

**To Remove:**
- `trading/` module (backtest cruft)
- Markov transition complexity in `outcomes/classifier.py`
