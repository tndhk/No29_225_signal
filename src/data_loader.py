import yfinance as yf
import pandas as pd
from typing import List, Optional
from . import config
from pathlib import Path
import logging

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data_cache"

# Configure logging (suppressed by default, can be enabled for debugging)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Only show warnings and errors by default

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
    """Load data from local cache if it exists.

    Args:
        ticker: Stock ticker symbol
        period: Data period

    Returns:
        DataFrame if cache exists and is valid, None otherwise
    """
    cache_path = _get_cache_path(ticker, period)
    if not cache_path.exists():
        return None

    try:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        logger.debug(f"Cache hit for {ticker} ({period})")
        return df
    except Exception as e:
        logger.warning(f"Failed to load cache for {ticker}: {e}")
        return None


def _save_to_cache(ticker: str, period: str, df: pd.DataFrame) -> bool:
    """Save data to local cache.

    Args:
        ticker: Stock ticker symbol
        period: Data period
        df: DataFrame to save

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        cache_path = _get_cache_path(ticker, period)
        df.to_csv(cache_path)
        logger.debug(f"Cached data for {ticker} ({period})")
        return True
    except Exception as e:
        logger.warning(f"Failed to save cache for {ticker}: {e}")
        return False

def fetch_daily_data(ticker: str, period: str = "1y", use_cache: bool = True, refresh: bool = False) -> Optional[pd.DataFrame]:
    """
    Fetch daily historical data for a given ticker.

    Args:
        ticker: Ticker symbol (e.g., "7203.T")
        period: Data period to download (e.g., "1y", "2y")
        use_cache: Use local cache if available (default: True)
        refresh: Force refresh from API, ignoring cache (default: False)
                Note: When refresh=True, use_cache is ignored

    Returns:
        DataFrame with daily candles (OHLCV data), or None if failed

    Note:
        - Cache is automatically saved after successful API fetch
        - refresh=True takes precedence over use_cache
        - Requires columns: Open, High, Low, Close, Volume
    """
    # Try to load from cache first (unless forcing refresh)
    if use_cache and not refresh:
        cached_df = _load_from_cache(ticker, period)
        if cached_df is not None:
            return cached_df

    # Fetch from API
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)

        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            return None

        # Handle MultiIndex columns (yfinance sometimes returns MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Validate required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns for {ticker}: {missing_columns}")
            return None

        # Remove rows with missing Close prices
        df = df.dropna(subset=['Close'])

        if df.empty:
            logger.warning(f"All rows have missing Close prices for {ticker}")
            return None

        # Save to cache
        _save_to_cache(ticker, period, df)

        return df

    except Exception as e:
        logger.error(f"Failed to fetch data for {ticker}: {type(e).__name__}: {e}")
        return None
