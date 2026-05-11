# AI Trading Council - Price Action Agent
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PriceActionAgent:
    """Analyzes candlestick patterns and support/resistance"""
    
    def __init__(self):
        self.name = "Price Action Agent"
    
    def analyze(self, df) -> dict:
        if df is None or df.empty:
            return self._empty_result("No data")
        
        required = ["open", "high", "low", "close"]
        for col in required:
            if col not in df.columns:
                return self._empty_result(f"Missing {col} column")
        
        recent = df.tail(50)
        o = recent["open"].values.astype(float)
        h = recent["high"].values.astype(float)
        l = recent["low"].values.astype(float)
        c = recent["close"].values.astype(float)
        
        # === Candlestick Pattern Detection ===
        patterns = self._detect_patterns(o, h, l, c)
        
        # === Support/Resistance ===
        sr = self._find_sr_levels(h, l)
        
        # === Market Structure ===
        structure = self._analyze_structure(h, l)
        
        # === Scoring ===
        bullish_score = 0
        bearish_score = 0
        
        # Pattern scoring
        for p in patterns:
            if p["type"] == "bullish":
                bullish_score += 20
            elif p["type"] == "bearish":
                bearish_score += 20
        
        # Structure scoring
        if structure == "uptrend":
            bullish_score += 30
        elif structure == "downtrend":
            bearish_score += 30
        
        # S/R proximity
        current_price = c[-1]
        if sr:
            nearest_support = min([s for s in sr["supports"] if s < current_price], default=None)
            nearest_resist = min([r for r in sr["resistances"] if r > current_price], default=None)
            
            if nearest_support:
                dist_support = ((current_price - nearest_support) / current_price) * 100
                if dist_support < 0.3:  # Very close to support
                    bullish_score += 25
                elif dist_support < 0.8:
                    bullish_score += 15
            
            if nearest_resist:
                dist_resist = ((nearest_resist - current_price) / current_price) * 100
                if dist_resist < 0.3:  # Very close to resistance
                    bearish_score += 25
                elif dist_resist < 0.8:
                    bearish_score += 15
        
        # Final signal
        total = bullish_score + bearish_score
        if total == 0:
            signal, confidence = "NEUTRAL", 50
        elif bullish_score > bearish_score:
            signal = "BULLISH"
            confidence = round((bullish_score / total) * 100)
        elif bearish_score > bullish_score:
            signal = "BEARISH"
            confidence = round((bearish_score / total) * 100)
        else:
            signal, confidence = "NEUTRAL", 50
        
        # Rationale
        parts = []
        if structure == "uptrend":
            parts.append("Market structure: uptrend (HH, HL)")
        elif structure == "downtrend":
            parts.append("Market structure: downtrend (LH, LL)")
        else:
            parts.append("Market structure: ranging/sideways")
        
        for p in patterns[:3]:
            parts.append(f"Pattern: {p['name']} ({p['type']})")
        
        if nearest_support:
            parts.append(f"Nearest support: {nearest_support:.2f}")
        if nearest_resist:
            parts.append(f"Nearest resistance: {nearest_resist:.2f}")
        
        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "rationale": ". ".join(parts),
            "details": {
                "patterns": patterns[:5],
                "structure": structure,
                "supports": [round(s, 2) for s in sr["supports"][:3]],
                "resistances": [round(r, 2) for r in sr["resistances"][:3]],
                "current_price": round(current_price, 2),
            }
        }
    
    def _detect_patterns(self, o, h, l, c) -> list:
        """Detect candlestick patterns in last 5 candles"""
        patterns = []
        n = len(c)
        lookback = min(5, n)
        
        for i in range(n - lookback, n):
            body = abs(c[i] - o[i])
            full_range = h[i] - l[i]
            upper_wick = h[i] - max(o[i], c[i])
            lower_wick = min(o[i], c[i]) - l[i]
            
            if full_range == 0:
                continue
            
            is_bullish = c[i] > o[i]
            
            # Hammer
            if lower_wick > body * 2 and upper_wick < body * 0.5:
                patterns.append({"name": "Hammer", "type": "bullish", "idx": i})
            
            # Shooting Star
            if upper_wick > body * 2 and lower_wick < body * 0.5:
                patterns.append({"name": "Shooting Star", "type": "bearish", "idx": i})
            
            # Bullish Engulfing
            if i > 0 and not is_bullish is False:
                prev_bearish = c[i-1] < o[i-1]
                if prev_bearish and is_bullish and c[i] > o[i-1] and o[i] < c[i-1]:
                    patterns.append({"name": "Bullish Engulfing", "type": "bullish", "idx": i})
            
            # Bearish Engulfing
            if i > 0 and is_bullish is False:
                prev_bullish = c[i-1] > o[i-1]
                if prev_bullish and o[i] > c[i-1] and c[i] < o[i-1]:
                    patterns.append({"name": "Bearish Engulfing", "type": "bearish", "idx": i})
            
            # Doji
            if body < full_range * 0.1:
                patterns.append({"name": "Doji", "type": "neutral", "idx": i})
        
        return patterns
    
    def _find_sr_levels(self, h, l, n_levels=3) -> dict:
        """Find support and resistance levels"""
        current = h[-1]
        
        supports = []
        resistances = []
        
        # Use swing lows as support, swing highs as resistance
        for i in range(2, len(h) - 2):
            # Swing low
            if l[i] < l[i-1] and l[i] < l[i-2] and l[i] < l[i+1] and l[i] < l[i+2]:
                if l[i] < current:
                    supports.append(l[i])
            # Swing high
            if h[i] > h[i-1] and h[i] > h[i-2] and h[i] > h[i+1] and h[i] > h[i+2]:
                if h[i] > current:
                    resistances.append(h[i])
        
        # Cluster nearby levels
        if supports:
            supports = sorted(set([round(s, 2) for s in supports]))[-n_levels:]
        if resistances:
            resistances = sorted(set([round(r, 2) for r in resistances]))[:n_levels]
        
        return {"supports": supports, "resistances": resistances}
    
    def _analyze_structure(self, h, l) -> str:
        """Determine market structure from last 20 candles"""
        recent_h = h[-20:]
        recent_l = l[-20:]
        
        hh_count = sum(1 for i in range(2, len(recent_h)) 
                       if recent_h[i] > recent_h[i-1] and recent_h[i-1] > recent_h[i-2])
        hl_count = sum(1 for i in range(2, len(recent_l)) 
                       if recent_l[i] > recent_l[i-1] and recent_l[i-1] > recent_l[i-2])
        
        lh_count = sum(1 for i in range(2, len(recent_h)) 
                       if recent_h[i] < recent_h[i-1] and recent_h[i-1] < recent_h[i-2])
        ll_count = sum(1 for i in range(2, len(recent_l)) 
                       if recent_l[i] < recent_l[i-1] and recent_l[i-1] < recent_l[i-2])
        
        bull_struct = hh_count + hl_count
        bear_struct = lh_count + ll_count
        
        if bull_struct > bear_struct + 2:
            return "uptrend"
        elif bear_struct > bull_struct + 2:
            return "downtrend"
        else:
            return "ranging"
    
    def _empty_result(self, reason: str) -> dict:
        return {
            "agent": self.name,
            "signal": "NEUTRAL",
            "confidence": 50,
            "rationale": reason,
            "details": {}
        }
