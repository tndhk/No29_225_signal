import pandas as pd
from tqdm import tqdm
import datetime
import os
import argparse
from . import config, data_loader, screener

# Display column configuration for each strategy
STRATEGY_DISPLAY_COLUMNS = {
    'original': {
        'columns': ["ticker", "current_price", "entry_price", "tp_price", "sl_price",
                   "rsi", "adx", "atr", "rr_ratio", "support"],
        'names': ["銘柄", "現在値", "指値(買)", "利確", "損切", "RSI", "ADX", "ATR", "R/R比", "サポート"]
    },
    'momentum_breakout': {
        'columns': ["ticker", "current_price", "entry_price", "tp_price", "sl_price",
                   "rsi", "adx", "atr", "rr_ratio", "bb_upper", "high20"],
        'names': ["銘柄", "現在値", "指値(買)", "利確", "損切", "RSI", "ADX", "ATR", "R/R比", "BB上限", "20日高値"]
    },
    'volume_climax': {
        'columns': ["ticker", "current_price", "entry_price", "tp_price", "sl_price",
                   "rsi", "atr", "rr_ratio", "low60", "macd_hist", "volume_ratio"],
        'names': ["銘柄", "現在値", "指値(買)", "利確", "損切", "RSI", "ATR", "R/R比", "60日安値", "MACD", "出来高倍率"]
    }
}

# Default display columns for unknown strategies
DEFAULT_DISPLAY_COLUMNS = ["ticker", "current_price", "entry_price", "tp_price", "sl_price"]
DEFAULT_DISPLAY_NAMES = ["銘柄", "現在値", "指値(買)", "利確", "損切"]

def main(refresh: bool = False, strategies: list = None, budget: int = 1_000_000):
    if strategies is None:
        strategies = config.ACTIVE_STRATEGIES

    print("=== Stock Screener & Order Generator ===")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}")
    print(f"Strategies: {', '.join(strategies)}")
    if refresh:
        print("(Cache refresh enabled)")
    print("Scanning market...")

    tickers = data_loader.get_prime_tickers()
    results = []

    # Iterate with progress bar
    for ticker in tqdm(tickers):
        df = data_loader.fetch_daily_data(ticker, period=config.DATE_RANGE, refresh=refresh)
        if df is not None:
            signals = screener.analyze_stock(ticker, df, strategies=strategies)
            if signals:
                results.extend(signals)

    if not results:
        print("\nNo stocks matched the criteria today.")
        return

    # Create DataFrame for results
    results_df = pd.DataFrame(results)
    
    # Ensure sorting columns exist
    if 'rr_ratio' not in results_df.columns:
        results_df['rr_ratio'] = 0.0
    if 'adx' not in results_df.columns:
        results_df['adx'] = 0.0
        
    # --- GENERATE BUY ORDERS (Budget: {budget:,} JPY) ---
    BUDGET = budget
    current_total_cost = 0
    action_plan = []
    
    # Sort candidates by Priority: R/R Ratio (desc), then ADX (desc)
    # This ensures we pick the best quality trades first
    candidates_df = results_df.sort_values(by=['rr_ratio', 'adx'], ascending=[False, False])
    
    for _, row in candidates_df.iterrows():
        ticker = row['ticker']
        entry_price = row['entry_price']
        
        # Standard unit is 100 shares in Japan
        shares = 100
        cost = entry_price * shares
        
        # 1. Check if single unit is too expensive (over total budget)
        if cost > BUDGET:
            continue 
            
        # 2. Check if we have enough remaining budget
        if current_total_cost + cost <= BUDGET:
            action_plan.append({
                "コード": ticker.replace('.T', ''), # Remove .T for easier input
                "売買": "現物買",
                "株数": shares,
                "指値": int(entry_price),
                "約定代金(概算)": int(cost),
                "利確(指値)": int(row['tp_price']),
                "損切(逆指値)": int(row['sl_price']),
                "戦略": row['strategy'],
                "R/R": round(row['rr_ratio'], 2)
            })
            current_total_cost += cost

    # --- OUTPUT ---
    print(f"\n{'='*80}")
    print(f"💰 本日の発注指示書 (予算: {BUDGET:,} JPY)")
    print(f"{'='*80}")

    if not action_plan:
        print("本日の予算内で購入可能な推奨銘柄はありません。")
        print("(シグナルはありましたが、単元株価格が予算を超過しているか、条件に合うものがありませんでした)")
    else:
        action_df = pd.DataFrame(action_plan)
        # Show clear table
        print(action_df.to_markdown(index=False))
        
        print(f"\n合計予想約定代金: {int(current_total_cost):,} JPY")
        print(f"残余予算:       {int(BUDGET - current_total_cost):,} JPY")
        print(f"発注銘柄数:     {len(action_df)}")

        # Save Action Plan to CSV
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'recommendations')
        os.makedirs(output_dir, exist_ok=True)
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        
        # Save the Order List (Simple)
        order_filename = os.path.join(output_dir, f"orders_{date_str}.csv")
        action_df.to_csv(order_filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ 発注指示書を保存しました: {order_filename}")
        
        # Save Full Analysis (Detailed)
        full_filename = os.path.join(output_dir, f"full_analysis_{date_str}.csv")
        results_df.to_csv(full_filename, index=False, encoding='utf-8-sig')
        print(f"ℹ️  詳細分析データはこちら: {full_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily analysis and generate buy orders")
    parser.add_argument("--refresh", action="store_true", help="Force refresh all data from API")
    parser.add_argument("--strategies", nargs='+',
                        choices=['original', 'momentum_breakout', 'volume_climax', 'all'],
                        help="Strategies to use")
    parser.add_argument("--budget", type=int, default=1_000_000, 
                        help="Total budget for today's trades in JPY (default: 1,000,000)")
    args = parser.parse_args()

    strategies = args.strategies
    if strategies and 'all' in strategies:
        strategies = ['original', 'momentum_breakout', 'volume_climax']
    elif not strategies:
        strategies = config.ACTIVE_STRATEGIES

    main(refresh=args.refresh, strategies=strategies, budget=args.budget)
