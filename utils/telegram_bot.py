# AI Trading Council - Telegram Bot
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def send_signal_message(analysis: dict) -> bool:
    """Send formatted trading signal to Telegram"""
    token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("[WARN] Telegram bot token or chat ID not set")
        return False

    text = format_signal(analysis)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("[OK] Signal sent to Telegram")
            return True
        else:
            print(f"[ERROR] Telegram API error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")
        return False


def _decimal_places(symbol: str) -> int:
    """How many decimal places to show for a symbol"""
    if symbol == "XAUUSD":
        return 2
    elif symbol == "USDJPY":
        return 3
    else:
        return 5  # EURUSD, GBPUSD, etc.


def format_signal(analysis: dict) -> str:
    """Format analysis result into a readable Telegram message"""
    symbol = analysis.get("symbol", "XAUUSD")
    council = analysis.get("council", {})
    risk = analysis.get("risk", {})
    dp = _decimal_places(symbol)

    # Council signals — support both old (price_action) and new (volume) keys
    tech = council.get("technical", {})
    vol = council.get("volume", council.get("price_action", {}))
    macro = council.get("macro", {})

    tech_signal = tech.get("signal", "N/A")
    tech_conf = tech.get("confidence", 0)
    vol_signal = vol.get("signal", "N/A")
    vol_conf = vol.get("confidence", 0)
    macro_signal = macro.get("signal", "N/A")
    macro_conf = macro.get("confidence", 0)

    # Overall
    overall = analysis.get("overall_signal", "NEUTRAL")
    overall_conf = analysis.get("overall_confidence", 0)

    direction_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}

    # Risk details
    entry = risk.get("entry_price", 0)
    sl = risk.get("sl_price", 0)
    tp = risk.get("tp_price", 0)
    lot = risk.get("lot_size", 0)
    rr = risk.get("rr_ratio", 0)
    risk_usd = risk.get("risk_amount_usd", 0)
    risk_pct = risk.get("risk_percent", 0)
    is_valid = risk.get("is_valid", False)

    summary = analysis.get("summary", "No summary available")

    direction = risk.get("direction", "")
    if direction == "bullish":
        trade_label = f"📈 BUY {symbol}"
    elif direction == "bearish":
        trade_label = f"📉 SELL {symbol}"
    else:
        trade_label = f"⏸️ {symbol} - NO TRADE"

    lines = [
        f"🔔 <b>AI Trading Council - {symbol}</b>",
        f"⏰ H1 Swing Trade | {analysis.get('timestamp', '')}",
        "",
        f"📊 <b>Council Vote:</b>",
        f"  • Technical (ALMA+MACD-V): {direction_emoji.get(tech_signal, '')} {tech_signal} ({tech_conf}%)",
        f"  • Volume: {direction_emoji.get(vol_signal, '')} {vol_signal} ({vol_conf}%)",
        f"  • Macro: {direction_emoji.get(macro_signal, '')} {macro_signal} ({macro_conf}%)",
        "",
        f"⚖️ <b>Overall: {direction_emoji.get(overall, '')} {overall}</b> ({overall_conf}%)",
        "",
    ]

    if is_valid:
        lines.extend([
            f"{'='*30}",
            f"💵 <b>{trade_label}</b>",
            f"  📍 Entry: <code>{round(entry, dp)}</code>",
            f"  🛑 SL: <code>{round(sl, dp)}</code>",
            f"  🎯 TP: <code>{round(tp, dp)}</code>",
            f"  📐 Lot: {lot} cents",
            f"  📊 RR: 1:{rr}",
            f"  💰 Risk: ${risk_usd} ({risk_pct}%)",
        ])
    else:
        lines.append("⚠️ <b>No valid trade setup</b> - Risk parameters not met")

    lines.extend([
        "",
        f"📝 <b>Summary:</b> {summary}",
        "",
        "⚠️ <i>Signals are advisory only. Past performance ≠ future results.</i>",
        "⚠️ <i>Always use proper risk management. Max 2% per trade.</i>",
    ])

    return "\n".join(lines)
