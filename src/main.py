import pandas as pd
from tqdm import tqdm
import datetime
import os
from . import config, data_loader, screener

def main():
    print("=== Overnight Dip Sniper ===")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}")
    print("Fetching and analyzing data...")
    
    tickers = data_loader.get_prime_tickers()
    results = []
    
    # Iterate with progress bar
    for ticker in tqdm(tickers):
        df = data_loader.fetch_daily_data(ticker, period=config.DATE_RANGE)
        if df is not None:
            result = screener.analyze_stock(ticker, df)
            if result:
                results.append(result)
    
    print("\n=== Analysis Complete ===")
    
    if not results:
        print("No stocks matched the criteria today.")
        return

    # Create DataFrame for results
    results_df = pd.DataFrame(results)

    # Reorder columns for display
    display_cols = ["ticker", "current_price", "entry_price", "tp_price", "sl_price",
                    "rsi", "adx", "atr", "rr_ratio", "support"]
    results_df = results_df[display_cols]

    # Rename columns for Japanese output
    results_df.columns = ["銘柄", "現在値", "指値(買)", "利確", "損切", "RSI", "ADX", "ATR", "R/R比", "サポート"]
    
    # Display to console
    print("\n[推奨銘柄リスト]")
    print(results_df.to_markdown(index=False))
    
    # Save to CSV
    filename = f"recommendations_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    results_df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\nSaved results to {filename}")

if __name__ == "__main__":
    main()
