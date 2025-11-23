import csv
import random
from collections import defaultdict
from datetime import datetime, timedelta
import statistics

# Configuration
CSV_FILE = '/Users/takahiko_tsunoda/work/dev/No29_stock_auto/backtest_results/backtest_original_momentum_breakout_volume_climax_20251123_224154.csv'
INITIAL_BUDGET = 1_000_000
MAX_POSITIONS = 3  # Approx 330k per position
SIMULATION_RUNS = 100

def load_trades(filepath):
    trades = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    # Sort by entry date
    trades.sort(key=lambda x: x['entry_date'])
    return trades

def run_simulation(all_trades, max_positions):
    # Group potential trades by entry date
    trades_by_date = defaultdict(list)
    for t in all_trades:
        trades_by_date[t['entry_date']].append(t)
    
    sorted_dates = sorted(trades_by_date.keys())
    if not sorted_dates:
        return 0, 0, 0

    start_date = datetime.strptime(sorted_dates[0], '%Y-%m-%d')
    end_date = datetime.strptime(sorted_dates[-1], '%Y-%m-%d')
    
    current_date = start_date
    active_positions = [] # List of dicts: {'exit_date': ..., 'profit_pct': ...}
    
    # Equity curve tracking
    equity = INITIAL_BUDGET
    max_equity = INITIAL_BUDGET
    max_drawdown = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # 1. Check for exits
        # We iterate backwards to safely remove items
        for i in range(len(active_positions) - 1, -1, -1):
            pos = active_positions[i]
            if pos['exit_date'] <= date_str:
                # Trade closed
                # Assume equal allocation: 1/MAX_POSITIONS of INITIAL budget (simple model)
                # or 1/MAX_POSITIONS of CURRENT equity (compounding)
                # Let's use Fixed Fractional of Initial Budget for simplicity to match user's "1M budget" mental model
                # Allocation = 330,000 JPY
                allocation = INITIAL_BUDGET / max_positions
                profit = allocation * float(pos['profit_pct'])
                equity += profit
                active_positions.pop(i)
        
        # Update High Water Mark
        if equity > max_equity:
            max_equity = equity
        drawdown = max_equity - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        # 2. Check for new entries
        if date_str in trades_by_date:
            potential_entries = trades_by_date[date_str]
            # Shuffle to simulate random selection if we can't take all
            random.shuffle(potential_entries)
            
            for trade in potential_entries:
                if len(active_positions) < max_positions:
                    # Enter trade
                    active_positions.append({
                        'exit_date': trade['exit_date'],
                        'profit_pct': trade['profit_pct']
                    })
                else:
                    # Skip trade (Budget constraint)
                    pass
        
        current_date += timedelta(days=1)
        
    total_profit = equity - INITIAL_BUDGET
    return total_profit, max_drawdown, equity

def main():
    all_trades = load_trades(CSV_FILE)
    
    profits = []
    drawdowns = []
    
    print(f"Running {SIMULATION_RUNS} simulations with Budget={INITIAL_BUDGET:,} JPY, Max Positions={MAX_POSITIONS}...")
    
    for i in range(SIMULATION_RUNS):
        profit, drawdown, final_equity = run_simulation(all_trades, MAX_POSITIONS)
        profits.append(profit)
        drawdowns.append(drawdown)
        
    avg_profit = statistics.mean(profits)
    avg_drawdown = statistics.mean(drawdowns)
    
    min_profit = min(profits)
    max_profit = max(profits)
    
    print("\n--- Simulation Results ---")
    print(f"Average Profit: {avg_profit:,.0f} JPY")
    print(f"  (Range: {min_profit:,.0f} to {max_profit:,.0f})")
    print(f"Average Max Drawdown: {avg_drawdown:,.0f} JPY")
    print(f"  (Worst Case Drawdown: {max(drawdowns):,.0f} JPY)")
    
    # Compare with "Unlimited" (Theoretical)
    # Calculate theoretical max profit if we took ALL trades with same allocation
    total_potential_profit = sum(float(t['profit_pct']) * (INITIAL_BUDGET / MAX_POSITIONS) for t in all_trades)
    print(f"\nTheoretical Profit (Unlimited Budget): {total_potential_profit:,.0f} JPY")
    print(f"Capture Rate: {avg_profit / total_potential_profit:.1%}")

if __name__ == "__main__":
    main()
