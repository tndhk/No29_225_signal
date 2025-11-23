#!/usr/bin/env python3
"""
Simple test script to verify caching functionality.
This fetches data for a single ticker twice and measures execution time.
"""
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import data_loader

def test_caching():
    ticker = "7203.T"  # Toyota
    period = "1y"

    print(f"=== Cache Test for {ticker} ===")
    print(f"Period: {period}\n")

    # First fetch (from API, will cache)
    print("1. First fetch (from API, will be cached)...")
    start = time.time()
    df1 = data_loader.fetch_daily_data(ticker, period=period, refresh=True)
    time1 = time.time() - start
    print(f"   - Time taken: {time1:.2f}s")
    print(f"   - Records fetched: {len(df1) if df1 is not None else 0}")

    # Second fetch (from cache)
    print("\n2. Second fetch (from cache)...")
    start = time.time()
    df2 = data_loader.fetch_daily_data(ticker, period=period, use_cache=True)
    time2 = time.time() - start
    print(f"   - Time taken: {time2:.2f}s")
    print(f"   - Records fetched: {len(df2) if df2 is not None else 0}")

    # Verify data integrity
    print("\n3. Data integrity check...")
    if df1 is not None and df2 is not None:
        if len(df1) == len(df2):
            print(f"   ✓ Same number of records: {len(df1)}")
        else:
            print(f"   ✗ Different number of records: {len(df1)} vs {len(df2)}")

    # Speedup factor
    if time1 > 0:
        speedup = time1 / time2
        print(f"\n4. Performance improvement:")
        print(f"   - API fetch: {time1:.2f}s")
        print(f"   - Cache fetch: {time2:.2f}s")
        print(f"   - Speedup: {speedup:.1f}x faster")

    # Check cache directory
    cache_path = data_loader._get_cache_path(ticker, period)
    if cache_path.exists():
        file_size = cache_path.stat().st_size / 1024  # KB
        print(f"\n5. Cache file information:")
        print(f"   - Location: {cache_path}")
        print(f"   - Size: {file_size:.2f} KB")

    print("\n✓ Cache test completed successfully!")

if __name__ == "__main__":
    test_caching()
