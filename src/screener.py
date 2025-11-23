import pandas as pd
import pandas_ta as ta
from typing import Optional, Dict, Any
from . import config

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to the DataFrame.
    """
    # SMA
    df['SMA25'] = ta.sma(df['Close'], length=config.MA_SHORT)
    df['SMA75'] = ta.sma(df['Close'], length=config.MA_LONG)
    
    # RSI
    df['RSI14'] = ta.rsi(df['Close'], length=14)
    
    # Turnover (Approximate: Close * Volume)
    # Use 5-day average turnover
    df['Turnover'] = df['Close'] * df['Volume']
    df['AvgTurnover5'] = df['Turnover'].rolling(window=5).mean()
    
    return df

def check_signal(ticker: str, row: pd.Series, prev_row: pd.Series) -> Optional[Dict[str, Any]]:
    """
    Check for entry signal on a specific day (row).
    
    Args:
        ticker (str): Ticker symbol.
        row (pd.Series): Current day's data with indicators.
        prev_row (pd.Series): Previous day's data.
        
    Returns:
        dict: Signal details if eligible, None otherwise.
    """
    # Ensure required columns exist (handle NaN at start of DF)
    if pd.isna(row['SMA75']) or pd.isna(prev_row['SMA25']):
        return None

    # 2. Screening Logic
    
    # A. Liquidity Filter
    if row['AvgTurnover5'] < config.MIN_TURNOVER:
        return None
        
    # B. Long-term Trend (Price > 75SMA)
    if row['Close'] <= row['SMA75']:
        return None
        
    # C. Medium-term Trend (25SMA Slope > 0)
    # Check if current 25SMA > previous 25SMA
    if row['SMA25'] <= prev_row['SMA25']:
        return None
        
    # D. Overheat Check (RSI < 50)
    if row['RSI14'] >= config.RSI_THRESHOLD:
        return None
        
    # 3. Pricing Logic
    
    # Entry: 25SMA (Today's value)
    entry_price = int(row['SMA25'])
    
    # Take Profit (+4%)
    tp_price = int(entry_price * (1 + config.TP_PCT))
    
    # Stop Loss (-2%)
    sl_price = int(entry_price * (1 - config.SL_PCT))
    
    return {
        "ticker": ticker,
        "date": row.name, # Index is Date
        "current_price": int(row['Close']),
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "rsi": round(row['RSI14'], 2),
        "sma25": int(row['SMA25']),
        "sma75": int(row['SMA75']),
        "turnover_avg": int(row['AvgTurnover5'])
    }

def analyze_stock(ticker: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Analyze the latest data of a stock (Wrapper for main script).
    """
    # Ensure enough data
    if len(df) < config.MA_LONG:
        return None

    df = add_indicators(df)
    
    # Get the latest row (today's close)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    return check_signal(ticker, latest, prev)
