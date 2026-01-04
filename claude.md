# Signal Lab

## Purpose

Statistical validation of entry signals for **dividend stock investing** with a **12-month minimum holding period** (Australian CGT discount).

## What This Is NOT

**Do not add:**
- P&L calculations or equity curves
- Position sizing or portfolio management
- Trade simulation or backtesting engines
- Sharpe ratios or risk-adjusted return metrics
- Compounding or reinvestment logic

We are validating whether signals provide useful information. We are not simulating a trading system.

## Core Questions

> When an entry signal fires:
> 1. What's the probability of positive return at 12 months?
> 2. What's the typical return at 12 months?
> 3. What's the peak gain within 12 months (MFE)?
> 4. What's the worst drawdown within 12 months (MAE)?
> 5. How does this compare to random entry?

## Investment Context

- **Asset class**: ASX dividend stocks
- **Holding period**: 12+ months (CGT discount target)
- **Entry**: Signal fires → buy
- **Success criteria**: Positive return at 12 months

## Architecture

```
signal_lab/
├── classifiers/          # Primitives (bar types, swing points)
│   ├── bars/             # Up, Down, Inside, Outside
│   └── swings/           # SwingHigh, SwingLow
├── signals/              # Entry signal detection
│   └── dow_breakout/     # Dow 1-2-3 patterns
├── outcomes/             # 12-month outcome measurement
├── analysis/             # Statistical aggregation
├── data/
│   └── Test/             # Validated test data
└── tests/
```

## What We Measure

### Per Signal Instance

| Metric | Definition |
|--------|------------|
| `return_12m` | % return if held exactly 12 months |
| `profitable_12m` | Was return positive at 12 months? (bool) |
| `mfe_12m` | Max favourable excursion within 12 months (peak gain) |
| `mfe_bar` | Bar index when peak occurred (0-51) |
| `mae_12m` | Max adverse excursion within 12 months (worst drawdown) |
| `exit_signal_fired` | Did an exit signal fire within 12 months? (bool) |
| `exit_signal_bar` | Bar index when exit signal fired (if any) |
| `return_at_exit` | % return if exited on exit signal |

### Derived Comparisons

| Metric | Definition |
|--------|------------|
| `left_on_table` | mfe_12m - return_12m (how much holding cost you) |
| `exit_vs_hold` | return_at_exit - return_12m (was exit signal better?) |
| `exit_vs_mfe` | return_at_exit - mfe_12m (how close to peak was exit?) |

### Aggregated Statistics

| Metric | Definition |
|--------|------------|
| `win_rate_12m` | % of signals profitable at 12 months |
| `mean_return_12m` | Average 12-month return |
| `median_return_12m` | Median 12-month return |
| `mean_mfe_12m` | Average peak gain |
| `mean_mae_12m` | Average worst drawdown |
| `mean_left_on_table` | Average forgone gains from holding |
| `exit_signal_useful_rate` | % where exit beat hold (return_at_exit > return_12m) |
| `baseline_win_rate` | Win rate of random entry (control) |
| `lift` | win_rate_12m / baseline_win_rate |

## Definitions

### Bar Types (Gann)
| Type | Rule |
|------|------|
| Up | Higher high AND higher low |
| Down | Lower high AND lower low |
| Inside | High ≤ prior high AND low ≥ prior low |
| Outside | High > prior high AND low < prior low |

### Swing Points
- **Swing High**: Trend reversed from up to down
- **Swing Low**: Trend reversed from down to up
- Swings alternate (High → Low → High → Low)
- Inside bars are invisible to swing detection

---

## Entry Signals

### Signal 1: Bullish Breakout (Momentum)

Buy when an emerging uptrend confirms via breakout.

**Pattern:**
1. Swing Low₁ forms
2. Swing High forms (resistance)
3. Swing Low₂ forms where Low₂ > Low₁ (higher low confirms trend)
4. Bar HIGH breaks above Swing High → **ENTRY**

```
        /\  ← Swing High (resistance)
       /  \
      /    \    /
     /      \  / ← Swing Low₂ (higher low)
    /        \/
   / 
  / ← Swing Low₁
 
  [1]    [2]   [3]        [4] ← Break above [2] = ENTRY
```

**Thesis:** Higher low indicates buyers stepping in at higher prices. Breakout above resistance confirms demand.

---

### Signal 2: Downtrend Reversal (Mean Reversion)

Buy when a confirmed downtrend breaks.

**Step 1 - Identify Downtrend via Bearish Breakdown:**
1. Swing High₁ forms
2. Swing Low forms (support)
3. Swing High₂ forms where High₂ < High₁ (lower high confirms weakness)
4. Bar LOW breaks below Swing Low → **Downtrend confirmed**

```
  \ ← Swing High₁
   \
    \  /\ ← Swing High₂ (lower high)
     \/  \
      ← Swing Low (support)
          \
           \ ← Break below support = DOWNTREND CONFIRMED
```

**Step 2 - Wait for Downtrend Break:**

Once in confirmed downtrend, track swing points. Entry when:
- Swing Low forms HIGHER than previous Swing Low (higher low), OR
- Price breaks above the last Swing High

```
  Downtrend:        Reversal:
  
  \                      /
   \  /\                / ← Break above last swing high = ENTRY
    \/  \    /\        /
         \  /  \      /
          \/    \    /
                 \  / ← Higher low = ENTRY
                  \/
```

**Thesis:** Downtrend identifies beaten-down stock. Reversal signal indicates selling exhaustion and new buying interest.

---

## Data Requirements

- **Timeframe**: Weekly bars (52 bars = 12 months)
- **History needed**: Signal date + 52 weeks forward
- **Test data**: `data/Test/` contains validated classifier tests

## Code Conventions

- DataFrame columns: `Open`, `High`, `Low`, `Close` (capitalised)
- Classifiers return `pd.Series` of bool
- Signals return `pd.Series` of bool
- 12 months = 52 weekly bars

## Status

### Working
- Bar classifiers (100% accuracy on Gann test data)
- Swing classifiers (100% accuracy on Gann test data)
- Dow 1-2-3 Bullish Breakout signal (Signal 1)
- Dow 1-2-3 Bearish Breakdown detection (for Signal 2 downtrend identification)

### TODO
- Downtrend Reversal signal (Signal 2 - entry on break)
- Outcome measurement module (12-month metrics)
- Baseline comparison (random entry)
- Multi-stock aggregation

### To Remove
- Markov transition complexity in `outcomes/classifier.py`
