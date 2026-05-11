# AI Trading Council - ALMA Indicator
import numpy as np


def alma(series: np.ndarray, window: int = 48, offset: float = 0.85, sigma: float = 6) -> np.ndarray:
    """
    Arnaud Legoux Moving Average
    :param series: Price series (numpy array)
    :param window: Window period (default 48)
    :param offset: Offset (default 0.85)
    :param sigma: Sigma (default 6)
    :return: ALMA values as numpy array
    """
    m = offset * (window - 1)
    s = window / sigma
    
    weights = np.array([np.exp(-((i - m) ** 2) / (2 * s * s)) for i in range(window)])
    weights = weights / weights.sum()
    
    alma_vals = np.full_like(series, np.nan, dtype=float)
    
    for i in range(window - 1, len(series)):
        window_data = series[i - window + 1:i + 1]
        alma_vals[i] = np.dot(window_data, weights)
    
    return alma_vals
