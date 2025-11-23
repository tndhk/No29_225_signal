import pandas as pd
from tqdm import tqdm
import datetime
from typing import List, Dict, Any
from . import config, data_loader, screener

# Backtest Settings
BACKTEST_PERIOD = "2y" # Fetch 2 years
TIME_STOP_DAYS = 3

def run_backtest():
    print("=== Overnight Dip Sniper: Backtest Mode ===")
    print(f"Period: {BACKTEST_PERIOD}")
    
    tickers = data_loader.get_prime_tickers()
    trades = []
    
    for ticker in tqdm(tickers):
        df = data_loader.fetch_daily_data(ticker, period=BACKTEST_PERIOD)
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
                    trades.append({
                        "ticker": ticker,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "LOSS",
                        "profit_pct": -config.SL_PCT,
                        "exit_reason": "SL"
                    })
                    active_trade = None
                    continue
                
                # If High hits TP -> Win
                if high >= active_trade['tp_price']:
                    trades.append({
                        "ticker": ticker,
                        "entry_date": active_trade['entry_date'],
                        "exit_date": next_date,
                        "result": "WIN",
                        "profit_pct": config.TP_PCT,
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
    
    print("\n=== Backtest Results ===")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}% ({wins}W / {losses}L)")
    print(f"Avg Profit per Trade: {avg_profit:.2f}%")
    print(f"Total Return (Simple Sum): {total_return:.2f}%")
    
    # Save to CSV
    filename = f"backtest_results_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    df_trades.to_csv(filename, index=False)
    print(f"Detailed logs saved to {filename}")

if __name__ == "__main__":
    run_backtest()
