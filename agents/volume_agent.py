# Volume Analysis Agent
# Replaces Price Action Agent with OBV + Volume Zone + Activity analysis
import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class VolumeAgent:
    """Analyzes volume/activity patterns for trade signals"""

    def __init__(self):
        self.name = "Volume Analysis"
        self.indicators = "OBV + Volume Zone + Activity"

    def _get_volumes(self, df: pd.DataFrame) -> pd.Series:
        """Get volume data. Uses proxy volume (candle range) if real volume unavailable."""
        if "volume" in df.columns:
            volumes = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
            if volumes.sum() > 0:
                return volumes

        # Proxy volume: candle range (high - low) as activity measure
        highs = pd.to_numeric(df["high"], errors="coerce")
        lows = pd.to_numeric(df["low"], errors="coerce")
        proxy_vol = (highs - lows).abs().fillna(0)
        if proxy_vol.sum() > 0:
            proxy_vol = proxy_vol * 10000
        return proxy_vol

    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < 20:
            return self._neutral("Insufficient data")

        closes = pd.to_numeric(df["close"], errors="coerce")
        volumes = self._get_volumes(df)

        # OBV analysis
        obv_signal, obv_score = self._analyze_obv(closes, volumes)

        # Volume zone analysis
        vz_signal, vz_score = self._analyze_volume_zones(closes, volumes)

        # Activity spike / exhaustion
        spike_signal, spike_score = self._analyze_activity_spikes(closes, volumes)

        # Activity trend
        trend_signal, trend_score = self._analyze_activity_trend(closes, volumes)

        # Weighted score
        total_score = (
            obv_score * 0.30
            + vz_score * 0.25
            + spike_score * 0.20
            + trend_score * 0.25
        )

        if total_score >= 0.25:
            signal = "BULLISH"
        elif total_score <= -0.25:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        confidence = min(100, max(30, int(50 + abs(total_score) * 200)))

        # Build rationale
        rationale_parts = []
        if obv_signal != "NEUTRAL":
            rationale_parts.append(f"OBV {obv_signal.lower()}")
        if vz_signal != "NEUTRAL":
            rationale_parts.append(f"Activity zone {vz_signal.lower()}")
        if spike_signal != "NEUTRAL":
            rationale_parts.append(f"Activity {spike_signal.lower()}")
        if trend_signal != "NEUTRAL":
            rationale_parts.append(f"Confirms {trend_signal.lower()}")

        avg_vol = float(volumes.tail(20).mean())
        latest_vol = float(volumes.iloc[-1])
        vol_ratio = round(latest_vol / avg_vol, 2) if avg_vol > 0 else 0

        if rationale_parts:
            rationale = ". ".join(rationale_parts[:3]) + f". Activity ratio: {vol_ratio}x"
        else:
            rationale = f"Volume neutral. Activity ratio: {vol_ratio}x. No clear conviction."

        return {
            "agent": self.name,
            "indicators": self.indicators,
            "signal": signal,
            "confidence": confidence,
            "rationale": rationale,
        }

    def _analyze_obv(self, closes: pd.Series, volumes: pd.Series) -> tuple:
        """On-Balance Volume analysis"""
        if len(closes) < 20:
            return "NEUTRAL", 0

        price_change = closes.diff()
        obv = pd.Series(0.0, index=closes.index)
        for i in range(1, len(closes)):
            if price_change.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i - 1] + volumes.iloc[i]
            elif price_change.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i - 1] - volumes.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i - 1]

        obv_recent = obv.tail(20)
        obv_slope = (obv_recent.iloc[-1] - obv_recent.iloc[0]) / len(obv_recent)

        price_recent = closes.tail(20)
        price_slope = (price_recent.iloc[-1] - price_recent.iloc[0]) / len(price_recent)

        score = 0

        if obv_slope > 0:
            score += 0.3
            obv_dir = "BULLISH"
        elif obv_slope < 0:
            score -= 0.3
            obv_dir = "BEARISH"
        else:
            obv_dir = "NEUTRAL"

        # Confirmation: same direction = strong
        if (obv_slope > 0 and price_slope > 0) or (obv_slope < 0 and price_slope < 0):
            score += 0.2

        # Divergence = don't trade
        if (obv_slope > 0 and price_slope < 0):
            return "NEUTRAL", 0.1
        elif (obv_slope < 0 and price_slope > 0):
            return "NEUTRAL", -0.1

        return obv_dir, score

    def _analyze_volume_zones(self, closes: pd.Series, volumes: pd.Series) -> tuple:
        """Compare activity on up-candles vs down-candles"""
        if len(closes) < 20:
            return "NEUTRAL", 0

        recent_close = closes.tail(20)
        recent_vol = volumes.tail(20)

        up_vol = float(recent_vol[recent_close.diff() > 0].sum())
        down_vol = float(recent_vol[recent_close.diff() < 0].sum())
        total_vol = up_vol + down_vol

        if total_vol == 0:
            return "NEUTRAL", 0

        vz_ratio = (up_vol - down_vol) / total_vol

        if vz_ratio > 0.2:
            return "BULLISH", vz_ratio * 0.5
        elif vz_ratio < -0.2:
            return "BEARISH", vz_ratio * 0.5
        return "NEUTRAL", 0

    def _analyze_activity_spikes(self, closes: pd.Series, volumes: pd.Series) -> tuple:
        """Detect activity spikes and exhaustion"""
        if len(volumes) < 20:
            return "NEUTRAL", 0

        avg_vol = float(volumes.tail(20).mean())
        latest_vol = float(volumes.iloc[-1])

        if avg_vol == 0:
            return "NEUTRAL", 0

        vol_ratio = latest_vol / avg_vol

        if vol_ratio > 2.0:
            price_change_5 = float(closes.tail(5).iloc[-1] - closes.tail(5).iloc[0])
            if price_change_5 > 0:
                return "BEARISH", -0.2  # Exhaustion after rally
            else:
                return "BULLISH", 0.2  # Selling climax
        elif vol_ratio < 0.5:
            return "NEUTRAL", 0

        return "NEUTRAL", 0

    def _analyze_activity_trend(self, closes: pd.Series, volumes: pd.Series) -> tuple:
        """Is activity increasing or decreasing?"""
        if len(volumes) < 20:
            return "NEUTRAL", 0

        vol_5 = float(volumes.tail(5).mean())
        vol_15 = float(volumes.iloc[-20:-5].mean())

        if vol_15 == 0:
            return "NEUTRAL", 0

        vol_trend = (vol_5 - vol_15) / vol_15
        price_change = float(closes.iloc[-1] - closes.iloc[-10])
        price_dir = 1 if price_change > 0 else -1

        if vol_trend > 0.1 and price_dir > 0:
            return "BULLISH", 0.3
        elif vol_trend > 0.1 and price_dir < 0:
            return "BEARISH", -0.3
        elif vol_trend < -0.2:
            return "NEUTRAL", 0.05

        return "NEUTRAL", vol_trend * 0.3

    def _neutral(self, reason: str = "") -> dict:
        return {
            "agent": self.name,
            "indicators": self.indicators,
            "signal": "NEUTRAL",
            "confidence": 30,
            "rationale": reason or "No data available",
        }
