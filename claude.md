# Signal Lab - Trading Signal Analysis Framework

## Project Purpose

Testing trading signals on historical stock data using Markov chains and state machine logic to find signal advantages for particular stocks.

The goal is to:
1. Generate trading signals (buy/sell) based on technical patterns
2. Track what happens AFTER each signal fires (state transitions)
3. Build transition probability matrices to identify which signals have statistical edge on specific stocks
4. Quantify expected returns and holding periods for each signal type

## Project Overview

A framework for analyzing trading signals using Dow Theory patterns and Markov state transitions. The system classifies price bars, detects swing points, generates trading signals, and tracks state transitions for probabilistic analysis.

## Directory Structure

```
signal_lab/
├── classifiers/          # Bar and swing point classifiers
│   ├── bars/            # Bar type classifiers (Up, Down, Inside, Outside)
│   └── swings/          # Swing point classifiers (SwingHigh, SwingLow)
├── signals/             # Trading signal generators
│   └── dow_breakout/    # Dow Theory 1-2-3 breakout signals
├── outcomes/            # State tracking and Markov analysis
│   └── classifier.py    # SignalStateTracker, DowTrendState
├── data/                # Input data files
│   ├── Gann/           # W.D. Gann reference data
│   └── Test/           # Test data files (CSV inputs only)
└── tests/              # Test scripts and output charts
```

## Key Concepts

### Bar Types (Gann Classification)
- **Up Bar**: Higher high AND higher low than previous bar
- **Down Bar**: Lower high AND lower low than previous bar
- **Inside Bar**: Lower high AND higher low (contained within previous)
- **Outside Bar**: Higher high AND lower low (engulfs previous)
- **Reference Bar**: First bar (no comparison available)

### Swing Points
- **Swing High**: Local peak where price reverses from up to down
- **Swing Low**: Local trough where price reverses from down to up
- Swings alternate (high-low-high-low pattern)
- Detection uses bar type patterns, not simple N-bar lookback

### Dow Theory 1-2-3 Signals
**Bullish Breakout**:
1. Swing Low₁ forms (Point 1)
2. Swing High forms (Point 2 - resistance)
3. Swing Low₂ forms where Low₂ > Low₁ (Point 3 - higher low)
4. HIGH breaks above Swing High level → Signal fires

**Bearish Breakdown**:
1. Swing High₁ forms (Point 1)
2. Swing Low forms (Point 2 - support)
3. Swing High₂ forms where High₂ < High₁ (Point 3 - lower high)
4. LOW breaks below Swing Low level → Signal fires

### Markov States
States for transition analysis:
- `unknown` - Before first signal or after trend ends
- `bullish_signal` - ONE bar when bullish signal fires
- `uptrend` - After bullish signal, while structure holds
- `bearish_signal` - ONE bar when bearish signal fires
- `downtrend` - After bearish signal, while structure holds
- `trend_end` - Bar where trend breaks

### Trend Break Conditions
**Uptrend breaks when**:
- Price break: LOW < support level (last swing low)
- Swing break: A swing high forms lower than the previous swing high

**Downtrend breaks when**:
- Price break: HIGH > resistance level (last swing high)
- Swing break: A swing low forms higher than the previous swing low

## Conventions

### Data Format
- CSV files with columns: `Open, High, Low, Close` (minimum)
- Column names are case-insensitive (auto-capitalized on load)
- Test data may include `Expected swing`, `State`, `Signal`, `Note` columns

### Output Files
- Test charts and outputs go in `tests/` folder
- Input data stays in `data/` folder
- Chart format: PNG at 150 DPI

### Signal Detection
- Signals use HIGH/LOW for breakout detection (not CLOSE)
- Signals only fire from `unknown` state (no duplicate signals in existing trends)
- Each signal is a ONE-BAR state that transitions to trend on next bar

## Analysis Workflow

1. **Load historical stock data** (OHLC format)
2. **Classify bars and swings** - Identify market structure
3. **Generate signals** - Detect entry points based on patterns
4. **Track state transitions** - Record what state follows each signal
5. **Build transition matrix** - Calculate probabilities: P(next_state | current_signal)
6. **Evaluate edge** - Compare expected returns across different stocks/timeframes

Example output:
```
From: Dow123BullishBreakout
  -> Dow123BearishBreakdown:
      Count: 5
      P(transition): 62.5%
      Mean % move: +3.2%
      Mean bars: 15.3
```

This tells us: After a bullish breakout, there's a 62.5% chance the next signal is bearish, with an average +3.2% gain over 15 bars.

## Testing

Run tests:
```bash
python tests/test_gann_data.py      # Bar/swing classifier accuracy
python tests/test_dow_signals.py    # Signal and state tests
```

Expected results:
- Gann classifier: 100% accuracy on bar types and swing points
- Synthetic data: Validates all state transitions and break conditions

## Key Files

| File | Purpose |
|------|---------|
| `classifiers/bars/*.py` | Up, Down, Inside, Outside bar classifiers |
| `classifiers/swings/*.py` | SwingHigh, SwingLow classifiers |
| `signals/dow_breakout/up.py` | Bullish 1-2-3 breakout signal |
| `signals/dow_breakout/down.py` | Bearish 1-2-3 breakdown signal |
| `outcomes/classifier.py` | SignalStateTracker, Markov state machine |
| `data/Test/test_signals_synthetic.csv` | Synthetic test data with all scenarios |
