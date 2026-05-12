# AI Trading Council - Technical Agent (ALMA + MACD-V)
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.alma import alma
from indicators.macd_v import macd_v, detect_macd_v_signals
import config


class TechnicalAgent:
    """Analyzes using ALMA48 + MACD-V indicators"""

    # Minimum ALMA distance (%) to count as a valid signal
    MIN_ALMA_DISTANCE = 0.3  # 0.3% minimum distance from ALMA

    def __init__(self):
        self.name = "Technical Agent (ALMA48 + MACD-V)"

    def analyze(self, df) -> dict:
        if df is None or df.empty or "close" not in df.columns:
            return self._empty_result("No data available")

        close = df["close"].values.astype(float)
        current_price = close[-1]

        # === ALMA Analysis ===
        alma_vals = alma(close, config.ALMA_WINDOW, config.ALMA_OFFSET, config.ALMA_SIGMA)
        alma_current = alma_vals[-1] if not np.isnan(alma_vals[-1]) else None

        if alma_current is None:
            return self._empty_result("Not enough data for ALMA")

        alma_trend = "bullish" if current_price > alma_current else "bearish"
        alma_distance = ((current_price - alma_current) / alma_current) * 100

        # ALMA slope (compare last 5 candles)
        alma_recent = alma_vals[-6:-1]
        alma_slope = "rising" if alma_recent[-1] > alma_recent[0] else "falling"

        # === ALMA Distance Filter ===
        # If price too close to ALMA, reduce signal strength
        alma_signal_valid = abs(alma_distance) >= self.MIN_ALMA_DISTANCE
        if not alma_signal_valid:
            alma_trend = "neutral"  # Too close, don't trust direction

        # === MACD-V Analysis ===
        macd_data = macd_v(close, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
        macd_signals = detect_macd_v_signals(macd_data)

        macd_v_current = macd_data["macd_v"][-1]
        signal_current = macd_data["signal"][-1]
        hist_current = macd_data["histogram"][-1]

        # === Combined Signal ===
        bullish_score = 0
        bearish_score = 0

        # ALMA contribution (40%) — only if distance is valid
        if alma_signal_valid:
            if alma_trend == "bullish" and alma_slope == "rising":
                bullish_score += 40
            elif alma_trend == "bearish" and alma_slope == "falling":
                bearish_score += 40
            elif alma_trend == "bullish":
                bullish_score += 25
            elif alma_trend == "bearish":
                bearish_score += 25
        # If ALMA too close, no contribution from ALMA

        # MACD-V contribution (60%)
        if macd_signals["crossover"] == "bullish":
            bullish_score += 35
        elif macd_signals["crossover"] == "bearish":
            bearish_score += 35

        if macd_signals["trend"] == "bullish":
            bullish_score += 25
        elif macd_signals["trend"] == "bearish":
            bearish_score += 25

        # Histogram momentum
        if hist_current > 0 and hist_current > macd_data["histogram"][-2]:
            bullish_score += 15
        elif hist_current < 0 and hist_current < macd_data["histogram"][-2]:
            bearish_score += 15

        # Determine final signal
        total = bullish_score + bearish_score
        if total == 0:
            signal = "NEUTRAL"
            confidence = 50
        elif bullish_score > bearish_score:
            signal = "BULLISH"
            confidence = round((bullish_score / (bullish_score + bearish_score)) * 100)
        elif bearish_score > bullish_score:
            signal = "BEARISH"
            confidence = round((bearish_score / (bullish_score + bearish_score)) * 100)
        else:
            signal = "NEUTRAL"
            confidence = 50

        # Reduce confidence if ALMA distance is too small
        if not alma_signal_valid:
            confidence = max(30, confidence - 20)

        # Build rationale
        rationale_parts = []
        if alma_signal_valid:
            if alma_trend == "bullish":
                rationale_parts.append(f"Price above ALMA48 ({alma_current:.2f})")
            elif alma_trend == "bearish":
                rationale_parts.append(f"Price below ALMA48 ({alma_current:.2f})")
        else:
            rationale_parts.append(f"ALMA48 too close ({alma_distance:.2f}%), direction unclear")

        if alma_slope == "rising":
            rationale_parts.append("ALMA48 slope rising")
        elif alma_slope == "falling":
            rationale_parts.append("ALMA48 slope falling")

        if macd_signals["crossover"]:
            rationale_parts.append(f"MACD-V {macd_signals['crossover']} crossover")

        if macd_signals["trend"]:
            rationale_parts.append(f"MACD-V histogram {macd_signals['trend']}")

        rationale_parts.append(f"ALMA distance: {alma_distance:.2f}%")

        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "rationale": ". ".join(rationale_parts),
            "details": {
                "alma_value": round(alma_current, 2),
                "alma_trend": alma_trend,
                "alma_slope": alma_slope,
                "alma_distance_pct": round(alma_distance, 2),
                "alma_valid": alma_signal_valid,
                "macd_v": round(float(macd_v_current), 4) if not np.isnan(macd_v_current) else None,
                "macd_signal": round(float(signal_current), 4) if not np.isnan(signal_current) else None,
                "macd_hist": round(float(hist_current), 4) if not np.isnan(hist_current) else None,
                "macd_crossover": macd_signals["crossover"],
                "macd_trend": macd_signals["trend"],
                "current_price": round(current_price, 2),
            }
        }

    def _empty_result(self, reason: str) -> dict:
        return {
            "agent": self.name,
            "signal": "NEUTRAL",
            "confidence": 50,
            "rationale": reason,
            "details": {}
        }
