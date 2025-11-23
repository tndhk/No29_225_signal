import yfinance as yf
import pandas as pd
from typing import List, Optional
from . import config
from pathlib import Path

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data_cache"

def get_prime_tickers() -> List[str]:
    """
    Returns a list of target tickers.
    For MVP, returns the static list from config.
    """
    return config.PRIME_TICKERS

def _get_cache_path(ticker: str, period: str) -> Path:
    """Get the cache file path for a given ticker and period."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{ticker}_{period}.csv"

def _load_from_cache(ticker: str, period: str) -> Optional[pd.DataFrame]:
    """Load data from local cache if it exists."""
    cache_path = _get_cache_path(ticker, period)
    if cache_path.exists():
        try:
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            print(f"Error loading cache for {ticker}: {e}")
            return None
    return None

def _save_to_cache(ticker: str, period: str, df: pd.DataFrame) -> None:
    """Save data to local cache."""
    try:
        cache_path = _get_cache_path(ticker, period)
        df.to_csv(cache_path)
    except Exception as e:
        print(f"Error saving cache for {ticker}: {e}")

def fetch_daily_data(ticker: str, period: str = "1y", use_cache: bool = True, refresh: bool = False) -> Optional[pd.DataFrame]:
    """
    Fetch daily historical data for a given ticker.

    Args:
        ticker (str): Ticker symbol (e.g., "7203.T").
        period (str): Data period to download.
        use_cache (bool): Use local cache if available (default: True).
        refresh (bool): Force refresh from API, ignoring cache (default: False).

    Returns:
        pd.DataFrame: DataFrame with daily candles or None if failed.
    """
    # Try to load from cache first (if not forcing refresh)
    if use_cache and not refresh:
        cached_df = _load_from_cache(ticker, period)
        if cached_df is not None:
            return cached_df

    try:
        # yfinance downloads data as a pandas DataFrame
        df = yf.download(ticker, period=period, interval="1d", progress=False)

        if df.empty:
            return None

        # Handle MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
             df.columns = df.columns.get_level_values(0)

        # Ensure required columns exist
        # yfinance usually returns: Open, High, Low, Close, Adj Close, Volume
        df = df.dropna(subset=['Close'])

        # Save to cache
        _save_to_cache(ticker, period, df)

        return df

    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None
