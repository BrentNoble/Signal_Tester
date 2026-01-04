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
- **Income**: Dividends received during holding period
- **Success criteria**: Positive total return (price + dividends) at 12 months
- **Analysis level**: Per-stock first, then cross-stock comparison

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

## Stock Universe

ASX 50 dividend payers with 10+ years history. Analyse per-stock (some may be too volatile).

### Banks (Stable, Fully Franked)
| Ticker | Name | Notes |
|--------|------|-------|
| CBA | Commonwealth Bank | Largest, most stable |
| WBC | Westpac | Big 4 |
| NAB | National Australia Bank | Big 4 |
| ANZ | ANZ Banking Group | Big 4 |
| MQG | Macquarie Group | Investment bank, more volatile |

### Miners (Cyclical, High Yield)
| Ticker | Name | Notes |
|--------|------|-------|
| BHP | BHP Group | Diversified, global |
| RIO | Rio Tinto | Iron ore, aluminium |
| FMG | Fortescue | Iron ore, high yield ~7% |
| S32 | South32 | BHP spin-off |

### Energy
| Ticker | Name | Notes |
|--------|------|-------|
| WDS | Woodside Energy | Oil & gas |
| STO | Santos | Oil & gas |
| ORG | Origin Energy | Electricity + gas |

### Retail / Consumer
| Ticker | Name | Notes |
|--------|------|-------|
| WES | Wesfarmers | Bunnings, Kmart, Officeworks |
| WOW | Woolworths | Supermarkets |
| COL | Coles | Supermarkets (spun off 2018) |

### Telco / Infrastructure
| Ticker | Name | Notes |
|--------|------|-------|
| TLS | Telstra | Stable, low growth |
| TCL | Transurban | Toll roads |

### Insurance / Financials
| Ticker | Name | Notes |
|--------|------|-------|
| SUN | Suncorp | Insurance + banking |
| QBE | QBE Insurance | Global insurer |
| IAG | Insurance Australia Group | General insurance |

### Healthcare
| Ticker | Name | Notes |
|--------|------|-------|
| CSL | CSL Limited | Biotech, lower yield but growth |
| SHL | Sonic Healthcare | Pathology |
| RMD | ResMed | Sleep apnea devices |

### REITs (Property)
| Ticker | Name | Notes |
|--------|------|-------|
| GMG | Goodman Group | Industrial/logistics |
| SCG | Scentre Group | Westfield malls |
| GPT | GPT Group | Diversified property |

### Industrials
| Ticker | Name | Notes |
|--------|------|-------|
| BXB | Brambles | Pallets, global logistics |
| AMC | Amcor | Packaging |

**Start with**: CBA, BHP, WES, TLS, FMG (mix of sectors, varying volatility)

## Output Structure

Analysis is **per stock**. No cross-stock aggregation - each stock is its own validation.

### Per Stock: `results/{TICKER}.xlsx`

**Sheet 1: Signal Instances** (one row per signal fired)
| Column | Description |
|--------|-------------|
| `signal_type` | "bullish_breakout" or "downtrend_reversal" |
| `signal_date` | Date signal fired |
| `entry_price` | Close on signal bar |
| `return_12m` | % return at 12 months |
| `profitable_12m` | True/False |
| `mfe_12m` | Peak gain % within 12 months |
| `mfe_bar` | Week when peak occurred (0-51) |
| `mae_12m` | Max drawdown % within 12 months |
| `exit_signal_fired` | Did exit signal fire? (bool) |
| `exit_signal_bar` | Week when exit fired (if any) |
| `return_at_exit` | % return if exited on signal |
| `left_on_table` | mfe_12m - return_12m |
| `exit_vs_hold` | return_at_exit - return_12m |

**Sheet 2: Summary**
| Metric | Bullish Breakout | Downtrend Reversal | Random Baseline |
|--------|------------------|-------------------|-----------------|
| Total signals | | | |
| Win rate 12m | | | |
| Mean return 12m | | | |
| Mean MFE | | | |
| Mean left on table | | | |
| Exit useful % | | | |
| Lift vs baseline | | | |

### Verification Charts (optional)
`charts/{TICKER}/signal_{N}.png` - one chart per signal instance showing:
- Price bars for 52 weeks from signal
- Entry point marked
- MFE point marked
- Exit signal marked (if fired)
- 12-month endpoint marked

Can be disabled for production runs.

### Usage
```bash
python analyse.py --stock CBA
python analyse.py --stock FMG --no-charts
```

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
- `trading/` module (traditional backtest cruft)
- Markov transition complexity in `outcomes/classifier.py`
- Any P&L or position sizing logic
