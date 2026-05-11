# AI Trading Council - Macro/Fundamental Agent
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.market_data import fetch_macro_data, fetch_economic_calendar


class MacroAgent:
    """Analyzes macroeconomic conditions affecting the instrument"""
    
    def __init__(self):
        self.name = "Macro Agent"
    
    def analyze(self, symbol: str = "XAUUSD") -> dict:
        macro = fetch_macro_data()
        events = fetch_economic_calendar()
        
        bullish_score = 0
        bearish_score = 0
        rationale_parts = []
        
        # === Gold-specific analysis ===
        if symbol == "XAUUSD":
            # DXY inverse correlation with Gold
            if "dxy" in macro:
                dxy = macro["dxy"]
                dxy_change = macro.get("dxy_change", 0)
                rationale_parts.append(f"DXY: {dxy} ({dxy_change:+.2f}%)")
                
                if dxy_change < -0.3:
                    bullish_score += 30  # DXY falling = Gold rising
                    rationale_parts.append("DXY weakness supports gold")
                elif dxy_change > 0.3:
                    bearish_score += 30  # DXY rising = Gold falling
                    rationale_parts.append("DXY strength pressures gold")
            
            # VIX - fear index
            if "vix" in macro:
                vix = macro["vix"]
                rationale_parts.append(f"VIX: {vix}")
                if vix > 25:
                    bullish_score += 25  # High fear = gold safe haven
                    rationale_parts.append("High VIX → safe haven demand for gold")
                elif vix < 15:
                    bearish_score += 10  # Low fear = less gold demand
                    rationale_parts.append("Low VIX → reduced safe haven demand")
            
            # US 10Y yield
            if "us_10y" in macro:
                rationale_parts.append(f"US 10Y: {macro['us_10y']}%")
        
        # === Economic Calendar Impact ===
        high_impact_count = len(events)
        rationale_parts.append(f"High-impact events this week: {high_impact_count}")
        
        # Check for USD-related events
        usd_events = [e for e in events if e.get("country") in ["USD", "US"]]
        if usd_events:
            rationale_parts.append(f"USD events: {', '.join([e['title'] for e in usd_events[:3]])}")
            # More USD events = more volatility expected
            if len(usd_events) >= 3:
                bullish_score += 5
                bearish_score += 5
                rationale_parts.append("Multiple USD events → expect volatility")
        
        # === Signal ===
        total = bullish_score + bearish_score
        if total == 0:
            signal, confidence = "NEUTRAL", 50
        elif bullish_score > bearish_score:
            signal = "BULLISH"
            confidence = min(80, round((bullish_score / total) * 100))
        elif bearish_score > bullish_score:
            signal = "BEARISH"
            confidence = min(80, round((bearish_score / total) * 100))
        else:
            signal, confidence = "NEUTRAL", 50
        
        # If no macro data at all
        if not macro:
            rationale_parts.insert(0, "⚠️ Limited macro data available")
            signal = "NEUTRAL"
            confidence = 50
        
        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "rationale": ". ".join(rationale_parts),
            "details": {
                "macro_data": macro,
                "upcoming_events": events[:5],
                "symbol": symbol,
            }
        }
