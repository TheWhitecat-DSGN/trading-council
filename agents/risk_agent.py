# AI Trading Council - Risk Management Agent
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


class RiskAgent:
    """Manages position sizing, SL, TP based on account and volatility"""
    
    def __init__(self):
        self.name = "Risk Agent"
    
    def calculate(self, df, signal: str, agents_result: dict) -> dict:
        """
        Calculate position size, SL, TP for a trade
        
        :param df: OHLCV DataFrame
        :param signal: "BULLISH" or "BEARISH"
        :param agents_result: Combined result from all agents
        """
        if df is None or df.empty:
            return self._empty_result()
        
        close = df["close"].values.astype(float)
        high = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        current_price = close[-1]
        
        # === ATR Calculation ===
        atr = self._calculate_atr(high, low, close, config.ATR_PERIOD)
        atr_value = atr[-1] if not np.isnan(atr[-1]) else (high[-1] - low[-1])
        
        # === Risk Parameters ===
        account_balance = config.ACCOUNT_BALANCE  # $150
        risk_amount = account_balance * (config.MAX_RISK_PERCENT / 100)  # $3
        
        # === Stop Loss (based on ATR) ===
        sl_distance = atr_value * config.ATR_SL_MULTIPLIER
        
        if signal == "BULLISH":
            entry_price = current_price
            sl_price = round(entry_price - sl_distance, 2)
        elif signal == "BEARISH":
            entry_price = current_price
            sl_price = round(entry_price + sl_distance, 2)
        else:
            return self._empty_result()
        
        # === Take Profit (based on RR ratio) ===
        risk_pips = abs(entry_price - sl_price)
        tp_price = round(
            entry_price + (risk_pips * config.DEFAULT_RR_RATIO) if signal == "BULLISH"
            else entry_price - (risk_pips * config.DEFAULT_RR_RATIO),
            2
        )
        
        # === Lot Size Calculation ===
        # For cent account: lot size calculation
        # Each 0.01 lot (micro lot) = ~$0.01 per pip on standard account
        # On cent account, same but in cents
        # Simplified: risk_amount / (sl_distance * pip_value)
        # For XAUUSD, 1 lot = $1 per $0.01 move roughly
        # So for cent account: lot = risk_cents / (sl_distance * 100)
        
        risk_cents = risk_amount * 100  # 300 cents
        sl_points = sl_distance  # In price units
        
        # Conservative lot for XAUUSD cent account
        # 0.01 lot = ~1 cent per point on cent account
        lot_size = risk_cents / (sl_points * 100)
        
        # Round to nearest 0.01
        lot_size = round(max(0.01, lot_size), 2)
        
        # Cap maximum lot size for $150 account
        max_lot = 0.10  # Don't risk more than 10 cents lot
        lot_size = min(lot_size, max_lot)
        
        # === Actual Risk Calculation ===
        actual_risk = (sl_points * lot_size * 100) / 100  # In USD
        actual_risk_pct = (actual_risk / account_balance) * 100
        
        # === RR Verification ===
        actual_rr = abs(tp_price - entry_price) / abs(entry_price - sl_price)
        
        return {
            "agent": self.name,
            "direction": signal.lower(),
            "entry_price": round(entry_price, 2),
            "sl_price": sl_price,
            "tp_price": tp_price,
            "lot_size": lot_size,
            "sl_distance": round(sl_distance, 2),
            "tp_distance": round(abs(tp_price - entry_price), 2),
            "risk_amount_usd": round(actual_risk, 2),
            "risk_percent": round(actual_risk_pct, 2),
            "rr_ratio": round(actual_rr, 1),
            "atr_value": round(atr_value, 2),
            "account_balance": account_balance,
            "is_valid": actual_rr >= config.MIN_RR_RATIO and actual_risk_pct <= config.MAX_RISK_PERCENT,
            "rationale": (
                f"ATR({config.ATR_PERIOD})={round(atr_value, 2)}, "
                f"SL={sl_distance:.2f}pts, "
                f"Lot={lot_size}, "
                f"Risk=${actual_risk:.2f} ({actual_risk_pct:.1f}%), "
                f"RR=1:{actual_rr:.1f}"
            )
        }
    
    def _calculate_atr(self, high, low, close, period: int = 14) -> np.ndarray:
        """Average True Range"""
        tr = np.zeros(len(close))
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(close)):
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
        
        atr = np.full(len(close), np.nan)
        atr[period - 1] = np.mean(tr[:period])
        
        for i in range(period, len(close)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr
    
    def _empty_result(self) -> dict:
        return {
            "agent": self.name,
            "direction": None,
            "entry_price": 0,
            "sl_price": 0,
            "tp_price": 0,
            "lot_size": 0,
            "is_valid": False,
            "rationale": "No valid trade setup"
        }
