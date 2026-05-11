# AI Trading Council - Main Entry Point
"""
AI Investment Council for XAUUSD/Forex Swing Trading
Uses ALMA48 + MACD-V indicators with multi-agent analysis

Usage:
    python main.py --symbol XAUUSD
    python main.py --symbol EURUSD
    python main.py --all
"""

import argparse
import sys
import os
from datetime import datetime

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from data.market_data import fetch_candle_data
from agents.technical_agent import TechnicalAgent
from agents.price_action_agent import PriceActionAgent
from agents.macro_agent import MacroAgent
from agents.risk_agent import RiskAgent
from utils.telegram_bot import send_signal_message, format_signal


def run_council(symbol: str = "XAUUSD") -> dict:
    """
    Run the full AI Investment Council analysis
    """
    print(f"\n{'='*50}")
    print(f"  AI Trading Council - {symbol}")
    print(f"  Timeframe: {config.TIMEFRAME} | Style: {config.TRADING_STYLE}")
    print(f"  Balance: ${config.ACCOUNT_BALANCE}")
    print(f"{'='*50}\n")
    
    # === Fetch Data ===
    print(f"[1/5] Fetching {symbol} price data...")
    df = fetch_candle_data(symbol, config.TIMEFRAME, 200)
    
    if df is None or df.empty:
        print(f"[ERROR] Could not fetch data for {symbol}")
        return {"error": f"No data for {symbol}"}
    
    print(f"  ✓ Got {len(df)} candles")
    print(f"  Latest: {df['close'].iloc[-1]:.2f}")
    
    # === Agent 1: Technical ===
    print(f"\n[2/5] Technical Agent analyzing (ALMA48 + MACD-V)...")
    tech_agent = TechnicalAgent()
    tech_result = tech_agent.analyze(df)
    print(f"  → {tech_agent.name}: {tech_result['signal']} ({tech_result['confidence']}%)")
    print(f"  → {tech_result['rationale']}")
    
    # === Agent 2: Price Action ===
    print(f"\n[3/5] Price Action Agent analyzing...")
    pa_agent = PriceActionAgent()
    pa_result = pa_agent.analyze(df)
    print(f"  → {pa_agent.name}: {pa_result['signal']} ({pa_result['confidence']}%)")
    print(f"  → {pa_result['rationale']}")
    
    # === Agent 3: Macro ===
    print(f"\n[4/5] Macro Agent analyzing...")
    macro_agent = MacroAgent()
    macro_result = macro_agent.analyze(symbol)
    print(f"  → {macro_agent.name}: {macro_result['signal']} ({macro_result['confidence']}%)")
    print(f"  → {macro_result['rationale']}")
    
    # === Council Vote ===
    print(f"\n{'='*50}")
    print(f"  COUNCIL VOTE")
    print(f"{'='*50}")
    
    agents = [tech_result, pa_result, macro_result]
    bullish_votes = sum(1 for a in agents if a["signal"] == "BULLISH")
    bearish_votes = sum(1 for a in agents if a["signal"] == "BEARISH")
    neutral_votes = sum(1 for a in agents if a["signal"] == "NEUTRAL")
    
    avg_confidence = sum(a["confidence"] for a in agents) / len(agents)
    
    if bullish_votes > bearish_votes and bullish_votes >= 2:
        overall = "BULLISH"
    elif bearish_votes > bullish_votes and bearish_votes >= 2:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"
    
    overall_confidence = round(avg_confidence)
    
    print(f"  BULLISH: {bullish_votes} | BEARISH: {bearish_votes} | NEUTRAL: {neutral_votes}")
    print(f"  → Overall: {overall} ({overall_confidence}%)")
    
    # === Agent 4: Risk Management ===
    print(f"\n[5/5] Risk Agent calculating...")
    risk_agent = RiskAgent()
    risk_result = risk_agent.calculate(df, overall, {})
    
    if risk_result.get("is_valid"):
        direction = risk_result["direction"]
        print(f"  → {direction.upper()} @ {risk_result['entry_price']}")
        print(f"  → SL: {risk_result['sl_price']} | TP: {risk_result['tp_price']}")
        print(f"  → Lot: {risk_result['lot_size']} | RR: 1:{risk_result['rr_ratio']}")
        print(f"  → Risk: ${risk_result['risk_amount_usd']} ({risk_result['risk_percent']}%)")
    else:
        print(f"  → No valid trade setup")
    
    # === Build Summary ===
    summary_parts = []
    for a in agents:
        if a["signal"] != "NEUTRAL":
            summary_parts.append(a["rationale"].split(".")[0])
    
    if not summary_parts:
        summary_parts.append("No strong signals detected. Wait for better setup.")
    
    if not risk_result.get("is_valid"):
        summary_parts.append("Risk parameters not met — skip this trade.")
    
    summary = " | ".join(summary_parts[:3])
    
    # === Full Analysis Result ===
    analysis = {
        "symbol": symbol,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "council": {
            "technical": tech_result,
            "price_action": pa_result,
            "macro": macro_result,
        },
        "overall_signal": overall,
        "overall_confidence": overall_confidence,
        "risk": risk_result,
        "summary": summary,
    }
    
    # === Send to Telegram ===
    print(f"\n{'='*50}")
    print(f"  SENDING SIGNAL")
    print(f"{'='*50}")
    sent = send_signal_message(analysis)
    if not sent:
        print("\n--- Signal Preview ---")
        print(format_signal(analysis))
    
    print(f"\n{'='*50}")
    print(f"  DONE - {symbol}")
    print(f"{'='*50}\n")
    
    return analysis


def main():
    parser = argparse.ArgumentParser(description="AI Trading Council")
    parser.add_argument("--symbol", type=str, default="XAUUSD", help="Symbol to analyze (XAUUSD, EURUSD, GBPUSD, USDJPY)")
    parser.add_argument("--all", action="store_true", help="Analyze all symbols")
    
    args = parser.parse_args()
    
    if args.all:
        symbols = [config.PRIMARY_SYMBOL] + config.FOREX_SYMBOLS
        for sym in symbols:
            try:
                run_council(sym)
            except Exception as e:
                print(f"[ERROR] Failed for {sym}: {e}")
    else:
        run_council(args.symbol)


if __name__ == "__main__":
    main()
