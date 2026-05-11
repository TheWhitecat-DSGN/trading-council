# AI Trading Council - MACD-V (Zero-lag MACD)
import numpy as np


def ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average"""
    ema_vals = np.full_like(data, np.nan, dtype=float)
    if len(data) < period:
        return ema_vals
    multiplier = 2.0 / (period + 1)
    ema_vals[period - 1] = data[:period].mean()
    for i in range(period, len(data)):
        ema_vals[i] = (data[i] - ema_vals[i - 1]) * multiplier + ema_vals[i - 1]
    return ema_vals


def macd_v(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD-V (Volume-adjusted Zero-lag MACD)
    Calculate standard MACD then apply EMA smoothing to MACD line for zero-lag effect.
    
    :param close: Close price array
    :param fast: Fast EMA period
    :param slow: Slow EMA period  
    :param signal: Signal line period
    :return: dict with macd_line, signal_line, histogram
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    
    # Standard MACD line
    macd_line = ema_fast - ema_slow
    
    # Zero-lag: apply EMA smoothing to MACD line itself
    macd_v_line = ema(np.nan_to_num(macd_line), signal)
    
    # Signal line: EMA of MACD-V line
    signal_line = ema(np.nan_to_num(macd_v_line), signal)
    
    # Histogram
    histogram = macd_v_line - signal_line
    
    return {
        "macd_v": macd_v_line,
        "signal": signal_line,
        "histogram": histogram,
        "macd_raw": macd_line
    }


def detect_macd_v_signals(macd_v: dict, lookback: int = 5) -> dict:
    """
    Detect MACD-V crossover signals
    """
    hist = macd_v["histogram"]
    macd = macd_v["macd_v"]
    sig = macd_v["signal"]
    
    signals = {
        "crossover": None,  # "bullish" or "bearish"
        "divergence": None,
        "trend": None,
        "confidence": 50
    }
    
    if len(hist) < lookback + 2:
        return signals
    
    recent = hist[-lookback:]
    
    # Crossover detection
    if recent[-2] <= 0 and recent[-1] > 0:
        signals["crossover"] = "bullish"
        signals["confidence"] = 70
    elif recent[-2] >= 0 and recent[-1] < 0:
        signals["crossover"] = "bearish"
        signals["confidence"] = 70
    
    # Trend based on histogram direction
    if np.all(recent[-3:] > 0) and recent[-1] > recent[-2]:
        signals["trend"] = "bullish"
        signals["confidence"] = max(signals["confidence"], 60)
    elif np.all(recent[-3:] < 0) and recent[-1] < recent[-2]:
        signals["trend"] = "bearish"
        signals["confidence"] = max(signals["confidence"], 60)
    
    # Simple divergence check (price vs MACD)
    # Bullish divergence: price lower low, MACD higher low
    # Bearish divergence: price higher high, MACD lower high
    
    return signals
