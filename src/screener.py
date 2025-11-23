import pandas as pd
from typing import Optional, Dict, Any, Tuple
from . import config
from . import indicators as ta


def _check_basic_filters(row: pd.Series) -> bool:
    """Check basic filters common to all strategies.

    Args:
        row: Current day data

    Returns:
        True if all basic filters pass, False otherwise
    """
    # Liquidity filter (5-day avg turnover)
    if row['AvgTurnover5'] < config.MIN_TURNOVER:
        return False

    # Long-term trend: price above 75-day SMA
    if row['Close'] <= row['SMA75']:
        return False

    return True


def _calculate_entry_prices(row: pd.Series, atr_tp_multiplier: float,
                            atr_sl_multiplier: float) -> Tuple[int, int, int, float]:
    """Calculate entry, TP, SL prices and R/R ratio.

    Args:
        row: Current day data
        atr_tp_multiplier: ATR multiplier for take profit
        atr_sl_multiplier: ATR multiplier for stop loss

    Returns:
        Tuple of (entry_price, tp_price, sl_price, rr_ratio)
    """
    entry_price = int(row['Close'] * (1 - config.ENTRY_DISCOUNT_PCT))
    atr_value = row['ATR14']

    tp_price = int(entry_price + atr_value * atr_tp_multiplier)
    sl_price = int(entry_price - atr_value * atr_sl_multiplier)

    risk = entry_price - sl_price
    reward = tp_price - entry_price
    rr_ratio = reward / risk if risk > 0 else 0

    return entry_price, tp_price, sl_price, rr_ratio


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to the DataFrame.

    This function enriches the DataFrame with SMA, RSI, ATR, ADX, turnover, volume metrics,
    Bollinger Bands, MACD, and support levels.
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

    # === Additional Indicators for New Strategies ===

    # Bollinger Bands (for Strategy A: Momentum Breakout)
    bb = ta.bbands(df['Close'], length=config.STRATEGY_A_BB_PERIOD, std=config.STRATEGY_A_BB_STD)
    if bb is not None:
        df['BB_Upper'] = bb[f'BBU_{config.STRATEGY_A_BB_PERIOD}_{config.STRATEGY_A_BB_STD}']
        df['BB_Middle'] = bb[f'BBM_{config.STRATEGY_A_BB_PERIOD}_{config.STRATEGY_A_BB_STD}']
        df['BB_Lower'] = bb[f'BBL_{config.STRATEGY_A_BB_PERIOD}_{config.STRATEGY_A_BB_STD}']
    else:
        df['BB_Upper'] = pd.NA
        df['BB_Middle'] = pd.NA
        df['BB_Lower'] = pd.NA

    # MACD (for Strategy B: Volume Climax)
    macd = ta.macd(df['Close'])
    if macd is not None:
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_Signal'] = macd['MACDs_12_26_9']
        df['MACD_Hist'] = macd['MACDh_12_26_9']
    else:
        df['MACD'] = pd.NA
        df['MACD_Signal'] = pd.NA
        df['MACD_Hist'] = pd.NA

    # 20-day high for breakout detection (Strategy A)
    df['High20'] = df['High'].rolling(window=20).max()

    # 60-day low for bottom detection (Strategy B)
    df['Low60'] = df['Low'].rolling(window=config.STRATEGY_B_LOW_PERIOD).min()

    return df


def check_signal_original(ticker: str, row: pd.Series, prev_row: pd.Series, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """ORIGINAL STRATEGY: Overnight Dip Sniper - Check for a trade entry signal.

    Returns a dictionary with signal details if all screening criteria are met, otherwise ``None``.
    """
    # Ensure required columns exist (handle NaN at start of DF)
    if pd.isna(row['SMA75']) or pd.isna(prev_row['SMA25']):
        return None

    # --- Screening Logic ---
    # Basic filters (liquidity, long-term trend)
    if not _check_basic_filters(row):
        return None

    # Medium-term trend: 25-day SMA must be rising
    if row['SMA25'] <= prev_row['SMA25']:
        return None

    # RSI filter (25-50)
    if not (config.RSI_LOWER <= row['RSI14'] < config.RSI_UPPER):
        return None

    # ADX filter (trend strength)
    if row['ADX'] < config.ADX_THRESHOLD:
        return None

    # Volume surge filter (>= 1.0× 20-day average)
    if row['Volume'] < row['VolumeSMA20'] * config.VOLUME_MULTIPLIER:
        return None

    support_level = df.tail(60)['Low'].min()  # Keep calculation for info

    # --- Pricing Logic (ATR-based) ---
    entry_price, tp_price, sl_price, rr_ratio = _calculate_entry_prices(
        row, config.ATR_MULTIPLIER_TP, config.ATR_MULTIPLIER_SL
    )

    return {
        "ticker": ticker,
        "strategy": "original",
        "date": row.name,
        "current_price": int(row['Close']),
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "time_stop_days": config.TIME_STOP_DAYS_ORIGINAL,
        "rsi": round(row['RSI14'], 2),
        "adx": round(row['ADX'], 2),
        "atr": int(row['ATR14']),
        "rr_ratio": round(rr_ratio, 2),
        "sma25": int(row['SMA25']),
        "sma75": int(row['SMA75']),
        "support": int(support_level),
        "turnover_avg": int(row['AvgTurnover5'])
    }


def check_signal_momentum_breakout(ticker: str, row: pd.Series, prev_row: pd.Series, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """STRATEGY A: Momentum Breakout - Strong trend continuation strategy.

    Entry Conditions:
    - Price > 75-day SMA (uptrend)
    - RSI(14) between 60-80 (strong momentum, not overheated)
    - Price breaking above 20-day high (new breakout)
    - ADX > 25 (strong trend)
    - Volume > 1.5x average (institutional participation)
    - Price breaking above Bollinger Band upper band
    """
    # Ensure required columns exist
    if pd.isna(row['SMA75']) or pd.isna(row['BB_Upper']) or pd.isna(prev_row['High20']):
        return None

    # Basic filters (liquidity, long-term trend)
    if not _check_basic_filters(row):
        return None

    # Perfect Order filter: SMA25 > SMA75 (confirming strong uptrend)
    if row['SMA25'] <= row['SMA75']:
        return None

    # RSI filter (60-80 for strong momentum)
    if not (config.STRATEGY_A_RSI_LOWER <= row['RSI14'] < config.STRATEGY_A_RSI_UPPER):
        return None

    # Breakout filter: Price breaking above 20-day high
    # Compare current Close to previous day's 20-day high
    if row['Close'] <= prev_row['High20']:
        return None

    # ADX filter: stronger trend requirement
    if row['ADX'] < config.STRATEGY_A_ADX_THRESHOLD:
        return None

    # Volume surge filter (higher requirement)
    if row['Volume'] < row['VolumeSMA20'] * config.STRATEGY_A_VOLUME_MULTIPLIER:
        return None

    # Bollinger Band breakout: price breaking above upper band
    if row['Close'] <= row['BB_Upper']:
        return None

    # --- Pricing Logic (ATR-based) ---
    entry_price, tp_price, sl_price, rr_ratio = _calculate_entry_prices(
        row, config.STRATEGY_A_ATR_MULTIPLIER_TP, config.STRATEGY_A_ATR_MULTIPLIER_SL
    )

    return {
        "ticker": ticker,
        "strategy": "momentum_breakout",
        "date": row.name,
        "current_price": int(row['Close']),
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "time_stop_days": config.STRATEGY_A_TIME_STOP_DAYS,
        "rsi": round(row['RSI14'], 2),
        "adx": round(row['ADX'], 2),
        "atr": int(row['ATR14']),
        "rr_ratio": round(rr_ratio, 2),
        "sma25": int(row['SMA25']),
        "sma75": int(row['SMA75']),
        "bb_upper": int(row['BB_Upper']),
        "high20": int(prev_row['High20']),
        "turnover_avg": int(row['AvgTurnover5'])
    }


def check_signal_volume_climax(ticker: str, row: pd.Series, prev_row: pd.Series, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """STRATEGY B: Volume Climax Reversal - Panic selling reversal strategy.

    Entry Conditions:
    - Price > 75-day SMA (long-term uptrend intact)
    - RSI(14) < 20 (extreme oversold)
    - Volume > 2.5x average (panic selling climax)
    - Price within 2% of 60-day low (bottom area)
    - MACD histogram turning up (reversal signal)
    - Current day is bullish candle (reversal started)
    """
    # Ensure required columns exist
    if pd.isna(row['SMA75']) or pd.isna(row['Low60']) or pd.isna(row['MACD_Hist']) or pd.isna(prev_row['MACD_Hist']):
        return None

    # Basic filters (liquidity, long-term trend)
    if not _check_basic_filters(row):
        return None

    # RSI filter: extreme oversold (< 30)
    if row['RSI14'] >= config.STRATEGY_B_RSI_THRESHOLD:
        return None

    # Volume climax filter (panic selling)
    if row['Volume'] < row['VolumeSMA20'] * config.STRATEGY_B_VOLUME_MULTIPLIER:
        return None

    # Price near 60-day low (within 10%)
    price_to_low_ratio = (row['Close'] - row['Low60']) / row['Low60']
    if price_to_low_ratio > config.STRATEGY_B_PRICE_TO_LOW_PCT:
        return None

    # MACD histogram turning up (reversal signal)
    if row['MACD_Hist'] <= prev_row['MACD_Hist']:
        return None

    # Bullish candle confirmation (Close > Open)
    if row['Close'] <= row['Open']:
        return None

    # --- Pricing Logic (ATR-based) ---
    entry_price, tp_price, sl_price, rr_ratio = _calculate_entry_prices(
        row, config.STRATEGY_B_ATR_MULTIPLIER_TP, config.STRATEGY_B_ATR_MULTIPLIER_SL
    )

    return {
        "ticker": ticker,
        "strategy": "volume_climax",
        "date": row.name,
        "current_price": int(row['Close']),
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
        "time_stop_days": config.STRATEGY_B_TIME_STOP_DAYS,
        "rsi": round(row['RSI14'], 2),
        "adx": round(row['ADX'], 2),
        "atr": int(row['ATR14']),
        "rr_ratio": round(rr_ratio, 2),
        "sma75": int(row['SMA75']),
        "low60": int(row['Low60']),
        "macd_hist": round(row['MACD_Hist'], 2),
        "volume_ratio": round(row['Volume'] / row['VolumeSMA20'], 2),
        "turnover_avg": int(row['AvgTurnover5'])
    }


def check_signal(ticker: str, row: pd.Series, prev_row: pd.Series, df: pd.DataFrame,
                 strategies: list = None) -> list:
    """Check for trade entry signals across multiple strategies.

    Args:
        ticker: Stock ticker symbol
        row: Current day data
        prev_row: Previous day data
        df: Full DataFrame
        strategies: List of strategies to check (default: from config.ACTIVE_STRATEGIES)

    Returns:
        List of signal dictionaries (one per matched strategy)
    """
    if strategies is None:
        strategies = config.ACTIVE_STRATEGIES

    signals = []

    # Check each requested strategy
    if 'original' in strategies:
        signal = check_signal_original(ticker, row, prev_row, df)
        if signal:
            signals.append(signal)

    if 'momentum_breakout' in strategies:
        signal = check_signal_momentum_breakout(ticker, row, prev_row, df)
        if signal:
            signals.append(signal)

    if 'volume_climax' in strategies:
        signal = check_signal_volume_climax(ticker, row, prev_row, df)
        if signal:
            signals.append(signal)

    return signals


def analyze_stock(ticker: str, df: pd.DataFrame, strategies: list = None) -> list:
    """Analyze the latest data of a stock (wrapper for main script).

    Returns:
        List of signal dictionaries (one per matched strategy)
    """
    # Ensure enough data for indicators
    if len(df) < config.MA_LONG:
        return []

    df = add_indicators(df)
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    return check_signal(ticker, latest, prev, df, strategies=strategies)
