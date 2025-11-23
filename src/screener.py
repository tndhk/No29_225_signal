import pandas as pd
import pandas_ta as ta
from typing import Optional, Dict, Any
from . import config

def analyze_stock(ticker: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Analyze a single stock dataframe to check if it meets the criteria.
    
    Args:
        ticker (str): Ticker symbol.
        df (pd.DataFrame): Daily OHLCV data.
        
    Returns:
        dict: Analysis result if eligible, None otherwise.
    """
    # Ensure enough data
    if len(df) < config.MA_LONG:
        return None

    # 1. Calculate Indicators
    # SMA
    df['SMA25'] = ta.sma(df['Close'], length=config.MA_SHORT)
    df['SMA75'] = ta.sma(df['Close'], length=config.MA_LONG)
    
    # RSI
    df['RSI14'] = ta.rsi(df['Close'], length=14)
    
    # Turnover (Approximate: Close * Volume)
    # Use 5-day average turnover
    df['Turnover'] = df['Close'] * df['Volume']
    df['AvgTurnover5'] = df['Turnover'].rolling(window=5).mean()
    
    # Get the latest row (today's close)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 2. Screening Logic
    
    # A. Liquidity Filter
    if latest['AvgTurnover5'] < config.MIN_TURNOVER:
        return None
        
    # B. Long-term Trend (Price > 75SMA)
    if latest['Close'] <= latest['SMA75']:
        return None
        
    # C. Medium-term Trend (25SMA Slope > 0)
    # Check if current 25SMA > previous 25SMA
    if latest['SMA25'] <= prev['SMA25']:
        return None
        
    # D. Overheat Check (RSI < 50)
    if latest['RSI14'] >= config.RSI_THRESHOLD:
        return None
        
    # 3. Pricing Logic
    
    # Entry: 25SMA (Today's value)
    # Note: In a real scenario, we might want tomorrow's projected 25SMA, 
    # but using today's 25SMA is a standard approximation for "dip to support".
    entry_price = int(latest['SMA25'])
    
    # Take Profit (+4%)
    tp_price = int(entry_price * (1 + config.TP_PCT))
    
    # Stop Loss (-2%)
    sl_price = int(entry_price * (1 - config.SL_PCT))
    
    return {
        "ticker": ticker,
        "current_price": int(latest['Close']),
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "rsi": round(latest['RSI14'], 2),
        "sma25": int(latest['SMA25']),
        "sma75": int(latest['SMA75']),
        "turnover_avg": int(latest['AvgTurnover5'])
    }
