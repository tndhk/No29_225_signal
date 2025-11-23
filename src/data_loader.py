import yfinance as yf
import pandas as pd
from typing import List, Optional
from . import config

def get_prime_tickers() -> List[str]:
    """
    Returns a list of target tickers.
    For MVP, returns the static list from config.
    """
    return config.PRIME_TICKERS

def fetch_daily_data(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Fetch daily historical data for a given ticker.
    
    Args:
        ticker (str): Ticker symbol (e.g., "7203.T").
        period (str): Data period to download.
        
    Returns:
        pd.DataFrame: DataFrame with daily candles or None if failed.
    """
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
        
        return df
        
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None
