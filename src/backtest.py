import pandas as pd
from tqdm import tqdm
import datetime
from typing import List, Dict, Any, Optional
import argparse
from . import config, data_loader, screener
from . import indicators as ta
import os
from itertools import combinations

# Backtest Settings
BACKTEST_PERIOD = "2y" # Fetch 2 years


def _calculate_trade_metrics(df_trades: pd.DataFrame, investment_per_trade: int) -> Dict[str, Any]:
    """Calculate trade metrics from trades DataFrame.

    Args:
        df_trades: DataFrame containing trade results
        investment_per_trade: Investment amount per trade in JPY

    Returns:
        Dictionary containing calculated metrics
    """
    if len(df_trades) == 0:
        return None

    total_trades = len(df_trades)
    wins = len(df_trades[df_trades['profit_pct'] > 0])
    losses = total_trades - wins
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    avg_profit = df_trades['profit_pct'].mean() * 100
    total_return = df_trades['profit_pct'].sum() * 100

    # Calculate profit amounts
    if 'profit_amount' not in df_trades.columns:
        df_trades['profit_amount'] = df_trades['profit_pct'] * investment_per_trade

    total_profit = df_trades['profit_amount'].sum()

    # Win/Loss analysis
    wins_df = df_trades[df_trades['result'] == 'WIN']
    losses_df = df_trades[df_trades['result'] == 'LOSS']
    total_wins_amount = wins_df['profit_amount'].sum() if len(wins_df) > 0 else 0
    total_losses_amount = abs(losses_df['profit_amount'].sum()) if len(losses_df) > 0 else 1
    profit_factor = total_wins_amount / total_losses_amount if total_losses_amount > 0 else 0

    return {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'total_return': total_return,
        'total_profit': total_profit,
        'profit_factor': profit_factor
    }


def run_backtest(refresh: bool = False, investment_per_trade: int = 1_000_000,
                 strategies: list = None, verbose: bool = True):
    """Run backtest for specified strategies.

    Args:
        refresh: Force refresh data from API
        investment_per_trade: Investment amount per trade in JPY
        strategies: List of strategies to test (default: from config.ACTIVE_STRATEGIES)
        verbose: Print detailed output

    Returns:
        DataFrame of all trades
    """
    if strategies is None:
        strategies = config.ACTIVE_STRATEGIES

    if verbose:
        print("=== Multi-Strategy Backtest Mode ===")
        print(f"Active Strategies: {', '.join(strategies)}")
        print(f"Period: {BACKTEST_PERIOD}")
        if refresh:
            print("(Cache refresh enabled - fetching fresh data)")
        print(f"Investment per Trade: {investment_per_trade:,.0f} JPY")

    # Fetch Market Data (Nikkei 225) for Trend Filter
    if verbose:
        print("Fetching Market Data (^N225)...")
    market_df = data_loader.fetch_daily_data("^N225", period=BACKTEST_PERIOD, refresh=refresh)
    if market_df is not None:
        market_df['SMA75'] = ta.sma(market_df['Close'], length=75)
        if verbose:
            print("Market Data Loaded.")
    else:
        if verbose:
            print("Warning: Could not load Market Data. Market filter disabled.")

    tickers = data_loader.get_prime_tickers()
    trades = []

    iterator = tqdm(tickers) if verbose else tickers
    for ticker in iterator:
        df = data_loader.fetch_daily_data(ticker, period=BACKTEST_PERIOD, refresh=refresh)
        if df is None or len(df) < 100:
            continue

        # Add indicators
        df = screener.add_indicators(df)

        # Iterate through days
        # Ensure enough lookback for all indicators
        start_idx = max(config.MA_LONG, config.STRATEGY_A_BB_PERIOD, config.STRATEGY_B_LOW_PERIOD, 35) + 1

        # Track active trades (one per strategy)
        active_trades = {}  # {strategy_name: trade_dict}

        for i in range(start_idx, len(df) - 1):
            current_date = df.index[i]
            row = df.iloc[i]
            prev_row = df.iloc[i-1]

            # Next day data (for execution)
            next_day = df.iloc[i+1]
            next_date = df.index[i+1]

            # --- Manage Active Trades ---
            completed_strategies = []
            for strategy_name, active_trade in active_trades.items():
                active_trade['days_held'] += 1

                # Check Exit (OHLC of next_day)
                low = next_day['Low']
                high = next_day['High']
                close = next_day['Close']

                # Conservative Logic: Check SL first
                if low <= active_trade['sl_price']:
                    exit_price = active_trade['sl_price']
                    profit_pct = (exit_price - active_trade['entry_price']) / active_trade['entry_price']
                    trades.append({
                        "ticker": ticker,
                        "strategy": strategy_name,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "LOSS",
                        "profit_pct": profit_pct,
                        "exit_reason": "SL"
                    })
                    completed_strategies.append(strategy_name)
                    continue

                # If High hits TP -> Win
                if high >= active_trade['tp_price']:
                    exit_price = active_trade['tp_price']
                    profit_pct = (exit_price - active_trade['entry_price']) / active_trade['entry_price']
                    trades.append({
                        "ticker": ticker,
                        "strategy": strategy_name,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "WIN",
                        "profit_pct": profit_pct,
                        "exit_reason": "TP"
                    })
                    completed_strategies.append(strategy_name)
                    continue

                # Time Stop (strategy-specific)
                if active_trade['days_held'] >= active_trade['time_stop_days']:
                    exit_price = close
                    profit_pct = (exit_price - active_trade['entry_price']) / active_trade['entry_price']
                    trades.append({
                        "ticker": ticker,
                        "strategy": strategy_name,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "WIN" if profit_pct > 0 else "LOSS",
                        "profit_pct": profit_pct,
                        "exit_reason": "TIME_STOP"
                    })
                    completed_strategies.append(strategy_name)
                    continue

            # Remove completed trades
            for strategy_name in completed_strategies:
                del active_trades[strategy_name]

            # --- Look for New Signals ---
            # Market Filter: Check if Nikkei 225 is uptrending (SMA75)
            market_ok = True
            if market_df is not None:
                try:
                    # asof to get the latest available market data on or before current_date
                    idx = market_df.index.asof(current_date)
                    if not pd.isna(idx):
                        market_row = market_df.loc[idx]
                        if not pd.isna(market_row['SMA75']):
                            if market_row['Close'] < market_row['SMA75']:
                                market_ok = False
                except KeyError:
                    pass

            if not market_ok:
                continue

            # Check for signals across all strategies
            signals = screener.check_signal(ticker, row, prev_row, df, strategies=strategies)

            for signal in signals:
                strategy_name = signal['strategy']

                # Skip if already have active trade for this strategy
                if strategy_name in active_trades:
                    continue

                # Check if entry is triggered on next day
                if next_day['Low'] <= signal['entry_price']:
                    # Trade Executed
                    active_trades[strategy_name] = {
                        "entry_price": signal['entry_price'],
                        "tp_price": signal['tp_price'],
                        "sl_price": signal['sl_price'],
                        "time_stop_days": signal['time_stop_days'],
                        "entry_date": next_date,
                        "days_held": 0
                    }

    # Analyze Results
    if not trades:
        if verbose:
            print("No trades generated.")
        return pd.DataFrame()

    df_trades = pd.DataFrame(trades)

    if verbose:
        print_backtest_results(df_trades, investment_per_trade, strategies)

    return df_trades


def print_backtest_results(df_trades: pd.DataFrame, investment_per_trade: int, strategies: list):
    """Print detailed backtest results."""

    print("\n" + "="*80)
    print("OVERALL RESULTS")
    print("="*80)

    total_trades = len(df_trades)
    wins = len(df_trades[df_trades['profit_pct'] > 0])
    losses = len(df_trades[df_trades['profit_pct'] <= 0])
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0

    avg_profit = df_trades['profit_pct'].mean() * 100
    total_return = df_trades['profit_pct'].sum() * 100

    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}% ({wins}W / {losses}L)")
    print(f"Avg Profit per Trade: {avg_profit:.2f}%")
    print(f"Total Return (Simple Sum): {total_return:.2f}%")

    # Money-based analysis
    df_trades['profit_amount'] = df_trades['profit_pct'] * investment_per_trade

    total_investment = total_trades * investment_per_trade
    total_profit = df_trades['profit_amount'].sum()
    roi = (total_profit / total_investment * 100) if total_investment > 0 else 0

    wins_df = df_trades[df_trades['result'] == 'WIN']
    losses_df = df_trades[df_trades['result'] == 'LOSS']

    avg_win_amount = wins_df['profit_amount'].mean() if len(wins_df) > 0 else 0
    avg_loss_amount = losses_df['profit_amount'].mean() if len(losses_df) > 0 else 0
    max_win = wins_df['profit_amount'].max() if len(wins_df) > 0 else 0
    max_loss = losses_df['profit_amount'].min() if len(losses_df) > 0 else 0

    # Profit Factor
    total_wins_amount = wins_df['profit_amount'].sum() if len(wins_df) > 0 else 0
    total_losses_amount = abs(losses_df['profit_amount'].sum()) if len(losses_df) > 0 else 1
    profit_factor = total_wins_amount / total_losses_amount if total_losses_amount > 0 else 0

    print(f"\nTotal Investment: {total_investment:,.0f} JPY")
    print(f"Total Profit: {total_profit:,.0f} JPY")
    print(f"ROI: {roi:.2f}%")
    print(f"\nAverage per Trade:")
    print(f"  Avg Profit: {df_trades['profit_amount'].mean():,.0f} JPY")
    print(f"  Avg Win: {avg_win_amount:,.0f} JPY")
    print(f"  Avg Loss: {avg_loss_amount:,.0f} JPY")
    print(f"\nExtreme Values:")
    print(f"  Max Win: {max_win:,.0f} JPY")
    print(f"  Max Loss: {max_loss:,.0f} JPY")
    print(f"  Profit Factor: {profit_factor:.2f}x")

    # Strategy Breakdown
    print("\n" + "="*80)
    print("STRATEGY BREAKDOWN")
    print("="*80)

    for strategy in strategies:
        strategy_df = df_trades[df_trades['strategy'] == strategy]
        if len(strategy_df) == 0:
            print(f"\n[{strategy.upper()}]: No trades")
            continue

        strat_total = len(strategy_df)
        strat_wins = len(strategy_df[strategy_df['profit_pct'] > 0])
        strat_losses = strat_total - strat_wins
        strat_win_rate = strat_wins / strat_total * 100 if strat_total > 0 else 0
        strat_avg_profit = strategy_df['profit_pct'].mean() * 100
        strat_total_return = strategy_df['profit_pct'].sum() * 100
        strat_profit_amount = strategy_df['profit_amount'].sum()

        strat_wins_df = strategy_df[strategy_df['result'] == 'WIN']
        strat_losses_df = strategy_df[strategy_df['result'] == 'LOSS']
        strat_total_wins_amount = strat_wins_df['profit_amount'].sum() if len(strat_wins_df) > 0 else 0
        strat_total_losses_amount = abs(strat_losses_df['profit_amount'].sum()) if len(strat_losses_df) > 0 else 1
        strat_profit_factor = strat_total_wins_amount / strat_total_losses_amount if strat_total_losses_amount > 0 else 0

        print(f"\n[{strategy.upper()}]")
        print(f"  Trades: {strat_total}")
        print(f"  Win Rate: {strat_win_rate:.2f}% ({strat_wins}W / {strat_losses}L)")
        print(f"  Avg Profit/Trade: {strat_avg_profit:.2f}%")
        print(f"  Total Return: {strat_total_return:.2f}%")
        print(f"  Total Profit: {strat_profit_amount:,.0f} JPY")
        print(f"  Profit Factor: {strat_profit_factor:.2f}x")

    # Monthly breakdown
    print("\n" + "="*80)
    print("MONTHLY PERFORMANCE")
    print("="*80)
    
    df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
    df_trades['month'] = df_trades['entry_date'].dt.to_period('M')

    monthly = df_trades.groupby('month').agg({
        'profit_amount': ['count', 'sum'],
        'profit_pct': 'sum'
    })
    
    # Calculate wins per month
    monthly['wins'] = df_trades[df_trades['profit_pct'] > 0].groupby('month')['profit_amount'].count()
    monthly['wins'] = monthly['wins'].fillna(0)

    for period in monthly.index:
        count = int(monthly.loc[period, ('profit_amount', 'count')])
        total_profit = monthly.loc[period, ('profit_amount', 'sum')]
        wins = int(monthly.loc[period, 'wins'])
        win_rate = wins / count * 100 if count > 0 else 0
        
        print(f"  {period}: {count:3d} trades, {total_profit:>12,.0f} JPY, Win: {win_rate:5.1f}%")

    # Annual outlook
    print("\n" + "="*80)
    print("ANNUAL OUTLOOK")
    print("="*80)
    
    df_trades['year'] = df_trades['entry_date'].dt.year
    yearly = df_trades.groupby('year')['profit_amount'].sum()

    for year in yearly.index:
        print(f"  {year}: {yearly[year]:,.0f} JPY")

    avg_annual = yearly.mean()
    print(f"\n  Average Annual Profit: {avg_annual:,.0f} JPY")
    print(f"  Average Monthly Profit: {avg_annual/12:,.0f} JPY")



def _test_strategy_combination(strategies: List[str], refresh: bool, investment_per_trade: int,
                               verbose: bool = True) -> Optional[Dict[str, Any]]:
    """Test a single strategy combination and return metrics.

    Args:
        strategies: List of strategy names to test
        refresh: Force refresh data from API
        investment_per_trade: Investment amount per trade
        verbose: Print detailed output

    Returns:
        Dictionary with strategy combination metrics, or None if no trades
    """
    combo_name = ' + '.join(strategies)
    print(f"\n>>> Testing {'Strategy' if len(strategies) == 1 else 'Combination'}: [{combo_name.upper()}]")

    df_trades = run_backtest(refresh=refresh, investment_per_trade=investment_per_trade,
                             strategies=strategies, verbose=verbose)

    if len(df_trades) == 0:
        return None

    metrics = _calculate_trade_metrics(df_trades, investment_per_trade)
    if metrics:
        metrics['strategies'] = combo_name if len(strategies) > 1 else strategies[0]
        return metrics

    return None


def run_combination_backtest(refresh: bool = False, investment_per_trade: int = 1_000_000):
    """Run backtest for all possible strategy combinations and compare results."""

    all_strategies = ['original', 'momentum_breakout', 'volume_climax']

    print("="*80)
    print("COMBINATION BACKTEST - Testing All Strategy Combinations")
    print("="*80)
    print(f"Available Strategies: {', '.join(all_strategies)}")
    print(f"Period: {BACKTEST_PERIOD}")
    print(f"Investment per Trade: {investment_per_trade:,.0f} JPY\n")

    results_summary = []

    # Test each individual strategy
    print("\n" + "="*80)
    print("TESTING INDIVIDUAL STRATEGIES")
    print("="*80)

    for strategy in all_strategies:
        metrics = _test_strategy_combination([strategy], refresh, investment_per_trade, verbose=True)
        if metrics:
            results_summary.append(metrics)

    # Test 2-strategy combinations
    print("\n" + "="*80)
    print("TESTING 2-STRATEGY COMBINATIONS")
    print("="*80)

    for combo in combinations(all_strategies, 2):
        combo_list = list(combo)
        metrics = _test_strategy_combination(combo_list, False, investment_per_trade, verbose=True)
        if metrics:
            results_summary.append(metrics)

    # Test all 3 strategies combined
    print("\n" + "="*80)
    print("TESTING ALL 3 STRATEGIES COMBINED")
    print("="*80)

    metrics = _test_strategy_combination(all_strategies, False, investment_per_trade, verbose=True)
    if metrics:
        results_summary.append(metrics)

    # Print Summary Comparison
    print("\n" + "="*80)
    print("FINAL COMPARISON - ALL COMBINATIONS")
    print("="*80)

    df_summary = pd.DataFrame(results_summary)
    df_summary = df_summary.sort_values('total_profit', ascending=False)

    print("\nRanked by Total Profit:")
    print("-" * 80)
    for idx, row in df_summary.iterrows():
        print(f"\n{row['strategies']}")
        print(f"  Total Trades: {int(row['total_trades'])}")
        print(f"  Win Rate: {row['win_rate']:.2f}%")
        print(f"  Avg Profit/Trade: {row['avg_profit']:.2f}%")
        print(f"  Total Return: {row['total_return']:.2f}%")
        print(f"  Total Profit: {row['total_profit']:,.0f} JPY 💰")
        print(f"  Profit Factor: {row['profit_factor']:.2f}x")

    # Save summary to CSV
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'backtest_results')
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(results_dir, f"combination_summary_{timestamp}.csv")
    df_summary.to_csv(filename, index=False)

    print(f"\n✅ Summary saved to {filename}")

    # Print the winner
    winner = df_summary.iloc[0]
    print("\n" + "="*80)
    print("🏆 WINNING COMBINATION 🏆")
    print("="*80)
    print(f"Strategy: {winner['strategies']}")
    print(f"Total Profit: {winner['total_profit']:,.0f} JPY")
    print(f"Total Trades: {int(winner['total_trades'])}")
    print(f"Win Rate: {winner['win_rate']:.2f}%")
    print(f"Profit Factor: {winner['profit_factor']:.2f}x")
    print("="*80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run backtest with strategy selection")
    parser.add_argument("--refresh", action="store_true", help="Force refresh all data from API (ignore cache)")
    parser.add_argument("--investment", type=int, default=1_000_000,
                        help="Investment amount per trade in JPY (default: 1,000,000)")
    parser.add_argument("--strategies", nargs='+',
                        choices=['original', 'momentum_breakout', 'volume_climax', 'all'],
                        help="Strategies to test (space-separated). Use 'all' for all strategies.")
    parser.add_argument("--compare", action="store_true",
                        help="Run combination backtest to compare all strategy combinations")

    args = parser.parse_args()

    if args.compare:
        # Run combination backtest
        run_combination_backtest(refresh=args.refresh, investment_per_trade=args.investment)
    else:
        # Run regular backtest
        strategies = args.strategies
        if strategies and 'all' in strategies:
            strategies = ['original', 'momentum_breakout', 'volume_climax']
        elif not strategies:
            strategies = config.ACTIVE_STRATEGIES

        df_trades = run_backtest(refresh=args.refresh, investment_per_trade=args.investment,
                                 strategies=strategies, verbose=True)

        # Save detailed results
        if len(df_trades) > 0:
            results_dir = os.path.join(os.path.dirname(__file__), '..', 'backtest_results')
            os.makedirs(results_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            strategy_name = '_'.join(strategies)
            filename = os.path.join(results_dir, f"backtest_{strategy_name}_{timestamp}.csv")
            df_trades.to_csv(filename, index=False)
            print(f"\n✅ Detailed trades saved to {filename}")