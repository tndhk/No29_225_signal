import pandas as pd
import pandas_ta as ta
from typing import Optional, Dict, Any
from . import config


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to the DataFrame.

    This function enriches the DataFrame with SMA, RSI, ATR, ADX, turnover, and volume metrics.
    """
    # Simple Moving Averages
    df['SMA25'] = ta.sma(df['Close'], length=config.MA_SHORT)
    df['SMA75'] = ta.sma(df['Close'], length=config.MA_LONG)

    # RSI (14)
    df['RSI14'] = ta.rsi(df['Close'], length=14)

    # ATR (Average True Range) for volatility-based stops
    df['ATR14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

    # ADX (Trend Strength)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    if adx_df is not None:
        df['ADX'] = adx_df['ADX_14']
    else:
        df['ADX'] = pd.NA

    # Turnover (approximate: Close * Volume) and 5‑day average turnover
    df['Turnover'] = df['Close'] * df['Volume']
    df['AvgTurnover5'] = df['Turnover'].rolling(window=5).mean()

    # 20‑day average volume for surge detection
    df['VolumeSMA20'] = df['Volume'].rolling(window=20).mean()

    return df


def check_signal(ticker: str, row: pd.Series, prev_row: pd.Series, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Check for a trade entry signal on a specific day.

    Returns a dictionary with signal details if all screening criteria are met, otherwise ``None``.
    """
    # Ensure required columns exist (handle NaN at start of DF)
    if pd.isna(row['SMA75']) or pd.isna(prev_row['SMA25']):
        return None

    # --- Screening Logic ---
    # Liquidity filter (5‑day avg turnover)
    if row['AvgTurnover5'] < config.MIN_TURNOVER:
        return None

    # Long‑term trend: price above 75‑day SMA
    if row['Close'] <= row['SMA75']:
        return None

    # Medium‑term trend: 25‑day SMA must be rising
    if row['SMA25'] <= prev_row['SMA25']:
        return None

    # RSI filter (30‑45)
    if not (config.RSI_LOWER <= row['RSI14'] < config.RSI_UPPER):
        return None

    # ADX filter (trend strength)
    if row['ADX'] < config.ADX_THRESHOLD:
        return None

    # Volume surge filter (>= 1.0× 20‑day average)
    if row['Volume'] < row['VolumeSMA20'] * config.VOLUME_MULTIPLIER:
        return None

    # Support analysis: price should be within 5% above the 60‑day low
    # recent_60d = df.tail(60)
    # support_level = recent_60d['Low'].min()
    # price_to_support_ratio = (row['Close'] - support_level) / support_level
    # if price_to_support_ratio > 0.05:
    #     return None
    support_level = df.tail(60)['Low'].min() # Keep calculation for info, but remove filter

    # --- Pricing Logic (ATR‑based) ---
    # Entry price: current close discounted by ENTRY_DISCOUNT_PCT
    entry_price = int(row['Close'] * (1 - config.ENTRY_DISCOUNT_PCT))

    # Take Profit and Stop Loss based on ATR
    atr_value = row['ATR14']
    tp_price = int(entry_price + atr_value * config.ATR_MULTIPLIER_TP)
    sl_price = int(entry_price - atr_value * config.ATR_MULTIPLIER_SL)

    # Risk/Reward ratio
    risk = entry_price - sl_price
    reward = tp_price - entry_price
    rr_ratio = reward / risk if risk > 0 else 0

    return {
        "ticker": ticker,
        "date": row.name,
        "current_price": int(row['Close']),
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "rsi": round(row['RSI14'], 2),
        "adx": round(row['ADX'], 2),
        "atr": int(atr_value),
        "rr_ratio": round(rr_ratio, 2),
        "sma25": int(row['SMA25']),
        "sma75": int(row['SMA75']),
        "support": int(support_level),
        "turnover_avg": int(row['AvgTurnover5'])
    }


def analyze_stock(ticker: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Analyze the latest data of a stock (wrapper for main script)."""
    # Ensure enough data for indicators
    if len(df) < config.MA_LONG:
        return None

    df = add_indicators(df)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    return check_signal(ticker, latest, prev, df)
