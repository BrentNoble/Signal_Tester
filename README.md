# Signal Lab

A framework for analyzing and comparing trading signals.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run analysis on a stock:

```bash
python main.py --symbol SPY --start 2022-01-01 --end 2024-01-01 --forward 5
```

### Arguments

- `--symbol`: Stock ticker (default: SPY)
- `--start`: Start date in YYYY-MM-DD format
- `--end`: End date in YYYY-MM-DD format
- `--forward`: Forward periods for return calculation (default: 5)

## Project Structure

```
signal_lab/
├── data/              # Data loading utilities
├── signals/           # Signal implementations
│   ├── base.py        # Signal base class
│   ├── dow_breakout/  # Dow Theory breakout signals
│   └── another_method/# Additional signal methods
├── analysis/          # Analysis utilities
└── tests/             # Test suite
```

## Adding New Signals

1. Create a new directory under `signals/`
2. Implement signal classes inheriting from `Signal` base class
3. Implement the `generate()` method returning a boolean Series

## Running Tests

```bash
pytest tests/
```
