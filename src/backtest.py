import pandas as pd
import pandas_ta as ta
from tqdm import tqdm
import datetime
from typing import List, Dict, Any
import argparse
from . import config, data_loader, screener
import os

# Backtest Settings
BACKTEST_PERIOD = "2y" # Fetch 2 years
TIME_STOP_DAYS = 3

def run_backtest(refresh: bool = False, investment_per_trade: int = 1_000_000):
    print("=== Overnight Dip Sniper: Backtest Mode ===")
    print(f"Period: {BACKTEST_PERIOD}")
    if refresh:
        print("(Cache refresh enabled - fetching fresh data)")
    print(f"Investment per Trade: {investment_per_trade:,.0f} JPY")

    # Fetch Market Data (Nikkei 225) for Trend Filter
    print("Fetching Market Data (^N225)...")
    market_df = data_loader.fetch_daily_data("^N225", period=BACKTEST_PERIOD, refresh=refresh)
    if market_df is not None:
        market_df['SMA75'] = ta.sma(market_df['Close'], length=75)
        print("Market Data Loaded.")
    else:
        print("Warning: Could not load Market Data. Market filter disabled.")

    tickers = data_loader.get_prime_tickers()
    trades = []

    for ticker in tqdm(tickers):
        df = data_loader.fetch_daily_data(ticker, period=BACKTEST_PERIOD, refresh=refresh)
        if df is None or len(df) < 100:
            continue
            
        # Add indicators
        df = screener.add_indicators(df)
        
        # Iterate through days
        # Start from index where indicators are valid
        start_idx = config.MA_LONG + 1
        
        active_trade = None # {entry_price, tp, sl, entry_date, days_held}
        
        for i in range(start_idx, len(df) - 1):
            current_date = df.index[i]
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Next day data (for execution)
            next_day = df.iloc[i+1]
            next_date = df.index[i+1]
            
            # --- Manage Active Trade ---
            if active_trade:
                active_trade['days_held'] += 1
                
                # Check Exit (OHLC of next_day)
                low = next_day['Low']
                high = next_day['High']
                close = next_day['Close']
                
                # Conservative Logic: Check SL first
                # If Low hits SL -> Loss
                if low <= active_trade['sl_price']:
                    exit_price = active_trade['sl_price']
                    profit_pct = (exit_price - active_trade['entry_price']) / active_trade['entry_price']
                    trades.append({
                        "ticker": ticker,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "LOSS",
                        "profit_pct": profit_pct,
                        "exit_reason": "SL"
                    })
                    active_trade = None
                    continue
                
                # If High hits TP -> Win
                if high >= active_trade['tp_price']:
                    exit_price = active_trade['tp_price']
                    profit_pct = (exit_price - active_trade['entry_price']) / active_trade['entry_price']
                    trades.append({
                        "ticker": ticker,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "WIN",
                        "profit_pct": profit_pct,
                        "exit_reason": "TP"
                    })
                    active_trade = None
                    continue
                
                # Time Stop
                if active_trade['days_held'] >= TIME_STOP_DAYS:
                    # Force close at Close
                    exit_price = close
                    profit_pct = (exit_price - active_trade['entry_price']) / active_trade['entry_price']
                    trades.append({
                        "ticker": ticker,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "WIN" if profit_pct > 0 else "LOSS",
                        "profit_pct": profit_pct,
                        "exit_reason": "TIME_STOP"
                    })
                    active_trade = None
                    continue
                    
                # If trade continues, do not look for new signals
                continue

            # --- Look for New Signal ---
            # Market Filter: Check if Nikkei 225 is uptrending (Close > SMA75)
            market_ok = True
            if market_df is not None:
                # Find market data for current_date
                # Use asof to handle potential holiday mismatches or timezone diffs
                try:
                    if current_date in market_df.index:
                        market_row = market_df.loc[current_date]
                        if not pd.isna(market_row['SMA75']):
                            if market_row['Close'] < market_row['SMA75']:
                                market_ok = False
                except KeyError:
                    pass # Data missing for this date, assume OK or skip? Assume OK to be safe.
            
            if not market_ok:
                continue

            signal = screener.check_signal(ticker, row, prev_row, df)
            if signal:
                # Check if entry is triggered on next day
                # Entry condition: Low <= Entry Price
                if next_day['Low'] <= signal['entry_price']:
                    # Trade Executed
                    active_trade = {
                        "entry_price": signal['entry_price'],
                        "tp_price": signal['tp_price'],
                        "sl_price": signal['sl_price'],
                        "entry_date": next_date, # Executed on next day
                        "days_held": 0
                    }
    
    # Analyze Results
    if not trades:
        print("No trades generated.")
        return

    df_trades = pd.DataFrame(trades)
    
    total_trades = len(df_trades)
    wins = len(df_trades[df_trades['profit_pct'] > 0])
    losses = len(df_trades[df_trades['profit_pct'] <= 0])
    win_rate = wins / total_trades * 100
    
    avg_profit = df_trades['profit_pct'].mean() * 100
    total_return = df_trades['profit_pct'].sum() * 100
    
    print("\n=== Backtest Results (Percentage) ===")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}% ({wins}W / {losses}L)")
    print(f"Avg Profit per Trade: {avg_profit:.2f}%")
    print(f"Total Return (Simple Sum): {total_return:.2f}%")

    # Money-based analysis
    df_trades['profit_amount'] = df_trades['profit_pct'] * investment_per_trade

    total_investment = total_trades * investment_per_trade
    total_profit = df_trades['profit_amount'].sum()
    roi = (total_profit / total_investment * 100) if total_investment > 0 else 0
    avg_profit_amount = df_trades['profit_amount'].mean()

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

    print("\n=== Money-Based Analysis ===")
    print(f"Total Investment: {total_investment:,.0f} JPY")
    print(f"Total Profit: {total_profit:,.0f} JPY")
    print(f"ROI: {roi:.2f}%")
    print(f"\nAverage per Trade:")
    print(f"  Avg Profit: {avg_profit_amount:,.0f} JPY")
    print(f"  Avg Win: {avg_win_amount:,.0f} JPY")
    print(f"  Avg Loss: {avg_loss_amount:,.0f} JPY")
    print(f"\nExtreme Values:")
    print(f"  Max Win: {max_win:,.0f} JPY")
    print(f"  Max Loss: {max_loss:,.0f} JPY")
    print(f"  Profit Factor: {profit_factor:.2f}x")

    # Monthly breakdown
    df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
    df_trades['month'] = df_trades['entry_date'].dt.to_period('M')

    monthly = df_trades.groupby('month').agg({
        'profit_amount': ['count', 'sum'],
        'result': lambda x: (x == 'WIN').sum()
    })

    print(f"\nMonthly Performance (Last 24 Months):")
    for period in monthly.index[-24:]:
        count = int(monthly.loc[period, ('profit_amount', 'count')])
        total = monthly.loc[period, ('profit_amount', 'sum')]
        wins_month = int(monthly.loc[period, ('result', '<lambda>')])
        win_rate_month = wins_month / count * 100 if count > 0 else 0
        print(f"  {period}: {count:3d} trades, {total:>12,.0f} JPY, Win: {win_rate_month:5.1f}%")

    # Annual outlook
    df_trades['year'] = df_trades['entry_date'].dt.year
    yearly = df_trades.groupby('year')['profit_amount'].sum()

    print(f"\nAnnual Outlook:")
    for year in yearly.index:
        print(f"  {year}: {yearly[year]:,.0f} JPY")

    avg_annual = yearly.mean()
    print(f"\nAverage Annual Profit: {avg_annual:,.0f} JPY")
    print(f"Average Monthly Profit: {avg_annual/12:,.0f} JPY")

    # Save to CSV
    # Ensure results folder exists
    results_dir = os.path.join(os.path.dirname(__file__), '..', 'backtest_results')
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(results_dir, f"backtest_results_{timestamp}.csv")
    df_trades.to_csv(filename, index=False)
    print(f"\nDetailed logs saved to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run backtest with optional cache refresh")
    parser.add_argument("--refresh", action="store_true", help="Force refresh all data from API (ignore cache)")
    parser.add_argument("--investment", type=int, default=1_000_000,
                        help="Investment amount per trade in JPY (default: 1,000,000)")
    args = parser.parse_args()

    run_backtest(refresh=args.refresh, investment_per_trade=args.investment)
