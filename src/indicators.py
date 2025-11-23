"""
Simple technical indicators library as a replacement for pandas_ta
"""
import pandas as pd
import numpy as np


def sma(close: pd.Series, length: int = 20) -> pd.Series:
    """Simple Moving Average"""
    return close.rolling(window=length).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range"""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())

    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)

    return true_range.rolling(window=length).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """Average Directional Index"""
    # Calculate +DM and -DM
    high_diff = high.diff()
    low_diff = -low.diff()

    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

    # Calculate True Range
    tr = atr(high, low, close, length=1) * length  # Get TR before smoothing

    # Smooth the values
    plus_di = 100 * (plus_dm.rolling(window=length).mean() / tr.rolling(window=length).mean())
    minus_di = 100 * (minus_dm.rolling(window=length).mean() / tr.rolling(window=length).mean())

    # Calculate DX and ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx_value = dx.rolling(window=length).mean()

    return pd.DataFrame({
        f'ADX_{length}': adx_value,
        f'DMP_{length}': plus_di,
        f'DMN_{length}': minus_di
    })


def bbands(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands"""
    middle = sma(close, length)
    std_dev = close.rolling(window=length).std()

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    return pd.DataFrame({
        f'BBU_{length}_{std}': upper,
        f'BBM_{length}_{std}': middle,
        f'BBL_{length}_{std}': lower
    })


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD (Moving Average Convergence Divergence)"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame({
        f'MACD_{fast}_{slow}_{signal}': macd_line,
        f'MACDs_{fast}_{slow}_{signal}': signal_line,
        f'MACDh_{fast}_{slow}_{signal}': histogram
    })
