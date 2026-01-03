# Signal Lab

## What This Is

A statistical validation framework for **bullish** technical analysis signals. We measure whether signals provide useful information about future upward price movement.

**Long-only.** We cannot short, so we only validate bullish entry signals.

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
- Bearish/short signal validation

If it belongs in a backtest engine, it doesn't belong here. We are validating signals as statistical predictors, not simulating trading strategies.

## Core Question

> When a bullish signal fires, what is the probability that an uptrend develops, and how does this compare to random entry?

That's it. Everything else is scope creep.

## Architecture

```
signal_lab/
├── classifiers/          # Primitives (bar types, swing points)
│   ├── bars/             # Up, Down, Inside, Outside
│   └── swings/           # SwingHigh, SwingLow
├── signals/              # Pattern detection
│   └── dow_breakout/     # Dow 1-2-3 bullish breakout
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

### Uptrend (for outcome measurement)
- **Uptrend continues**: Higher highs and higher lows maintained
- **Uptrend breaks**: LOW < last swing low OR swing high forms lower than previous

## What We Measure

For each bullish signal instance:

| Metric | Definition |
|--------|------------|
| `trend_developed` | Did a Dow-defined uptrend establish? (bool) |
| `duration_bars` | Bars from signal to trend break |
| `magnitude_pct` | % change from signal close to trend break close |
| `mfe_pct` | Max favorable excursion (best possible exit) |
| `mae_pct` | Max adverse excursion (worst drawdown during trend) |

Aggregated across all signals:

| Metric | Definition |
|--------|------------|
| `success_rate` | % of signals where uptrend developed |
| `mean_duration` | Average bars in trend |
| `mean_magnitude` | Average % gain |
| `baseline_rate` | Success rate of random entry (control) |
| `lift` | success_rate / baseline_rate |

## Validation Data

`data/Test/test_gann_34bars.csv` - 34 bars with manually verified:
- Bar type classifications
- Swing point locations

`data/Test/test_signals_synthetic.csv` - Synthetic data covering:
- Bullish breakout → uptrend → trend end

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
- Dow 1-2-3 bullish signal detection

**TODO:**
- Outcome measurement module (uptrend tracking)
- Baseline comparison (random entry)
- Multi-stock aggregation

**To Remove/Simplify:**
- Bearish signal code (keep for swing detection, but don't validate)
- Markov transition complexity in `outcomes/classifier.py`
