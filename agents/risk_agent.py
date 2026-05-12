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
        
        # Determine decimal places based on symbol type
        # This is passed in via agents_result or detected from price magnitude
        if current_price > 100:  # XAUUSD, USDJPY
            dp = 2 if current_price > 1000 else 3  # Gold vs JPY pairs
        else:
            dp = 5  # EURUSD, GBPUSD etc.

        if signal == "BULLISH":
            entry_price = current_price
            sl_price = round(entry_price - sl_distance, dp)
        elif signal == "BEARISH":
            entry_price = current_price
            sl_price = round(entry_price + sl_distance, dp)
        else:
            return self._empty_result()
        
        # === Take Profit (based on RR ratio) ===
        risk_pips = abs(entry_price - sl_price)
        tp_price = round(
            entry_price + (risk_pips * config.DEFAULT_RR_RATIO) if signal == "BULLISH"
            else entry_price - (risk_pips * config.DEFAULT_RR_RATIO),
            dp
        )
        
        # === Lot Size Calculation ===
        # For cent account: lot size calculation
        # Each 0.01 lot (micro lot) = ~$0.01 per pip on standard account
        # On cent account, same but in cents
        # Simplified: risk_amount / (sl_distance * pip_value)
        # For XAUUSD, 1 lot = $1 per $0.01 move roughly
        # So for cent account: lot = risk_cents / (sl_distance * 100)
        
        risk_cents = risk_amount * 100  # 300 cents ($3 = 300 cents)
        sl_points = abs(entry_price - sl_price)  # Distance in price

        # === SL Sanity Check ===
        if sl_points < 1e-6:
            return self._empty_result()

        # === Lot Size Calculation ===
        # Pip value depends on the pair
        # XAUUSD: 1 lot = ~$1 per $0.01 move → 100 cents per $0.01
        # EURUSD: 1 lot = ~$10 per 0.0001 move → $0.01 per pip per 0.001 lot
        # USDJPY: 1 lot = ~¥1000 per 0.01 move
        # Simplified for cent account:
        #   lot = risk_cents / (sl_points / pip_size * pip_value_cents)

        if current_price > 1000:  # XAUUSD
            pip_size = 0.01
            pip_value_cents = 1  # 1 cent per pip per 0.01 lot
        elif current_price > 100:  # USDJPY
            pip_size = 0.01
            pip_value_cents = 0.65  # Approximate for JPY pairs
        else:  # EURUSD, GBPUSD etc.
            pip_size = 0.0001
            pip_value_cents = 1  # 1 cent per pip per 0.01 lot

        sl_pips = sl_points / pip_size
        lot_size = risk_cents / (sl_pips * pip_value_cents) * 0.01
        lot_size = round(max(0.01, min(lot_size, 0.10)), 2)  # Cap 0.01-0.10

        # === Actual Risk Calculation ===
        actual_risk_cents = sl_pips * pip_value_cents * (lot_size / 0.01)
        actual_risk = actual_risk_cents / 100  # Convert cents to USD
        actual_risk_pct = (actual_risk / account_balance) * 100

        # === RR Verification ===
        actual_rr = abs(tp_price - entry_price) / abs(entry_price - sl_price)

        return {
            "agent": self.name,
            "direction": signal.lower(),
            "entry_price": round(entry_price, dp),
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
