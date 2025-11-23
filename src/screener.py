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

    # ATR (Average True Range) for volatility-based stops
    df['ATR14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    # ADX (Trend Strength)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    if adx_df is not None:
        df['ADX'] = adx_df['ADX_14']
    else:
        return None

    # Turnover (Approximate: Close * Volume)
    # Use 5-day average turnover
    df['Turnover'] = df['Close'] * df['Volume']
    df['AvgTurnover5'] = df['Turnover'].rolling(window=5).mean()

    # Volume Analysis
    df['VolumeSMA20'] = df['Volume'].rolling(window=20).mean()

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

    # D. RSI Filter (30 <= RSI < 45): True dip, not overheated
    if not (config.RSI_LOWER <= latest['RSI14'] < config.RSI_UPPER):
        return None

    # E. ADX Filter: Trend strength must be >= 25
    if latest['ADX'] < config.ADX_THRESHOLD:
        return None

    # F. Volume Surge: Volume must be >= 1.2x of 20-day average
    if latest['Volume'] < latest['VolumeSMA20'] * config.VOLUME_MULTIPLIER:
        return None

    # G. Support/Resistance Analysis
    # Check if price is near a support level (past 60-day low)
    recent_60d = df.tail(60)
    support_level = recent_60d['Low'].min()

    # Price should be within 5% of support level for valid dip
    price_to_support_ratio = (latest['Close'] - support_level) / support_level
    if price_to_support_ratio > 0.05:  # More than 5% above support
        return None

    # 3. Pricing Logic (IMPROVED)

    # Entry: Current price - 2% (realistic limit order)
    # This ensures the order can be filled if price dips slightly
    entry_price = int(latest['Close'] * (1 - config.ENTRY_DISCOUNT_PCT))

    # ATR-based Take Profit and Stop Loss
    atr_value = latest['ATR14']

    # Take Profit: Entry + (ATR * 2.0)
    tp_price = int(entry_price + atr_value * config.ATR_MULTIPLIER_TP)

    # Stop Loss: Entry - (ATR * 1.0)
    sl_price = int(entry_price - atr_value * config.ATR_MULTIPLIER_SL)

    # Calculate Risk/Reward Ratio
    risk = entry_price - sl_price
    reward = tp_price - entry_price
    rr_ratio = reward / risk if risk > 0 else 0

    return {
        "ticker": ticker,
        "current_price": int(latest['Close']),
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "rsi": round(latest['RSI14'], 2),
        "adx": round(latest['ADX'], 2),
        "atr": int(atr_value),
        "rr_ratio": round(rr_ratio, 2),
        "sma25": int(latest['SMA25']),
        "sma75": int(latest['SMA75']),
        "support": int(support_level),
        "turnover_avg": int(latest['AvgTurnover5'])
    }
