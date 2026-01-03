"""Run backtest on FMG weekly data."""

import pandas as pd
from trading.backtest import backtest, plot_backtest
from trading.risk import RiskParams

# Load FMG weekly data
df = pd.read_csv('data/FMG_weekly.csv', index_col=0)

# Parse dates and remove timezone
df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)

print(f'FMG Weekly: {len(df)} bars')
print(f'Date range: {df.index[0].date()} to {df.index[-1].date()}')

# Skip early penny stock years (pre-2008)
df_filtered = df.loc['2008-01-01':]
print(f'Filtered (2008+): {len(df_filtered)} bars')
print()

# Run backtest with default params ($100k account, 1% risk)
risk_params = RiskParams(account_size=100000, risk_per_trade_pct=0.01)
result = backtest(df_filtered, risk_params)

# Print results
result.tracker.print_summary()

# Show individual trades
print()
print('TRADE LOG:')
print('-' * 80)
for i, trade in enumerate(result.tracker.get_closed_trades()[:10], 1):
    print(f'{i:2}. {trade.entry_date.date()} @ ${trade.entry_price:.2f} -> '
          f'{trade.exit_date.date()} @ ${trade.exit_price:.2f} | '
          f'{trade.r_multiple:+.2f}R | {trade.exit_reason}')

if len(result.tracker.get_closed_trades()) > 10:
    print(f'... and {len(result.tracker.get_closed_trades()) - 10} more trades')

# Save chart
plot_backtest(result, title='FMG Weekly - Dow 1-2-3 Strategy',
              save_path='tests/FMG_backtest.png', show=False)
