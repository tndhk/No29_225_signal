import pandas as pd
from tqdm import tqdm
import datetime
import os
import argparse
from . import config, data_loader, screener

def main(refresh: bool = False, strategies: list = None):
    if strategies is None:
        strategies = config.ACTIVE_STRATEGIES

    print("=== Multi-Strategy Stock Screener ===")
    print(f"Active Strategies: {', '.join(strategies)}")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}")
    if refresh:
        print("(Cache refresh enabled - fetching fresh data)")
    print("Fetching and analyzing data...")

    tickers = data_loader.get_prime_tickers()
    results = []

    # Iterate with progress bar
    for ticker in tqdm(tickers):
        df = data_loader.fetch_daily_data(ticker, period=config.DATE_RANGE, refresh=refresh)
        if df is not None:
            signals = screener.analyze_stock(ticker, df, strategies=strategies)
            if signals:
                results.extend(signals)

    print("\n=== Analysis Complete ===")

    if not results:
        print("No stocks matched the criteria today.")
        return

    # Create DataFrame for results
    results_df = pd.DataFrame(results)

    # Display results by strategy
    for strategy in strategies:
        strategy_df = results_df[results_df['strategy'] == strategy]

        if len(strategy_df) == 0:
            print(f"\n[{strategy.upper()}]: No matches today")
            continue

        print(f"\n{'='*80}")
        print(f"[{strategy.upper()}]: {len(strategy_df)} signals")
        print('='*80)

        # Select columns based on strategy
        if strategy == 'original':
            display_cols = ["ticker", "current_price", "entry_price", "tp_price", "sl_price",
                            "rsi", "adx", "atr", "rr_ratio", "support"]
            col_names = ["銘柄", "現在値", "指値(買)", "利確", "損切", "RSI", "ADX", "ATR", "R/R比", "サポート"]
        elif strategy == 'momentum_breakout':
            display_cols = ["ticker", "current_price", "entry_price", "tp_price", "sl_price",
                            "rsi", "adx", "atr", "rr_ratio", "bb_upper", "high20"]
            col_names = ["銘柄", "現在値", "指値(買)", "利確", "損切", "RSI", "ADX", "ATR", "R/R比", "BB上限", "20日高値"]
        elif strategy == 'volume_climax':
            display_cols = ["ticker", "current_price", "entry_price", "tp_price", "sl_price",
                            "rsi", "atr", "rr_ratio", "low60", "macd_hist", "volume_ratio"]
            col_names = ["銘柄", "現在値", "指値(買)", "利確", "損切", "RSI", "ATR", "R/R比", "60日安値", "MACD", "出来高倍率"]
        else:
            display_cols = ["ticker", "current_price", "entry_price", "tp_price", "sl_price"]
            col_names = ["銘柄", "現在値", "指値(買)", "利確", "損切"]

        # Reorder and rename columns
        display_df = strategy_df[display_cols].copy()
        display_df.columns = col_names

        # Display to console
        print(display_df.to_markdown(index=False))

    # Save to CSV (all strategies combined)
    filename = f"recommendations_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    results_df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n✅ All results saved to {filename}")
    print(f"Total signals: {len(results_df)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run daily analysis with optional cache refresh and strategy selection")
    parser.add_argument("--refresh", action="store_true", help="Force refresh all data from API (ignore cache)")
    parser.add_argument("--strategies", nargs='+',
                        choices=['original', 'momentum_breakout', 'volume_climax', 'all'],
                        help="Strategies to use (space-separated). Use 'all' for all strategies.")
    args = parser.parse_args()

    # Process strategies argument
    strategies = args.strategies
    if strategies and 'all' in strategies:
        strategies = ['original', 'momentum_breakout', 'volume_climax']
    elif not strategies:
        strategies = config.ACTIVE_STRATEGIES

    main(refresh=args.refresh, strategies=strategies)
