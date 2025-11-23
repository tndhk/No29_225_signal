import csv
from collections import defaultdict

file_path = '/Users/takahiko_tsunoda/work/dev/No29_stock_auto/backtest_results/backtest_original_momentum_breakout_volume_climax_20251123_224154.csv'

trades = []
with open(file_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        trades.append(row)

# Overall Performance
total_trades = len(trades)
total_profit = sum(float(t['profit_amount']) for t in trades)
wins = sum(1 for t in trades if t['result'] == 'WIN')
win_rate = wins / total_trades if total_trades > 0 else 0

print(f"Total Trades: {total_trades}")
print(f"Total Profit: {total_profit:,.0f}")
print(f"Win Rate: {win_rate:.2%}")

# Performance by Strategy
print("\n--- Performance by Strategy ---")
strategies = set(t['strategy'] for t in trades)
for strategy in strategies:
    strat_trades = [t for t in trades if t['strategy'] == strategy]
    count = len(strat_trades)
    profit = sum(float(t['profit_amount']) for t in strat_trades)
    strat_wins = sum(1 for t in strat_trades if t['result'] == 'WIN')
    strat_win_rate = strat_wins / count if count > 0 else 0
    
    gross_profit = sum(float(t['profit_amount']) for t in strat_trades if float(t['profit_amount']) > 0)
    gross_loss = abs(sum(float(t['profit_amount']) for t in strat_trades if float(t['profit_amount']) < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    print(f"{strategy}:")
    print(f"  Trades: {count}")
    print(f"  Profit: {profit:,.0f}")
    print(f"  Win Rate: {strat_win_rate:.2%}")
    print(f"  Profit Factor: {pf:.2f}")

# Monthly Performance
print("\n--- Monthly Performance (Top 5 Worst Months) ---")
monthly_profit = defaultdict(float)
for t in trades:
    monthly_profit[t['month']] += float(t['profit_amount'])

sorted_months = sorted(monthly_profit.items(), key=lambda x: x[1])
for month, profit in sorted_months[:5]:
    print(f"{month}: {profit:,.0f}")

print("\n--- Monthly Performance (Top 5 Best Months) ---")
for month, profit in sorted_months[-5:]:
    print(f"{month}: {profit:,.0f}")
