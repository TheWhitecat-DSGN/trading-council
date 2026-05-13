# AI Trading Council - Railway Deploy
"""
Web service that runs the trading council every hour and sends signals to Telegram.
- Only sends Telegram message when there's a valid trade setup
- Daily market summary at 09:00 Bangkok time
"""
import os
import sys
import threading
import time
import logging
from datetime import datetime, timedelta

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from flask import Flask
import config

# Hardcode telegram config as ultimate fallback
if not config.TELEGRAM_BOT_TOKEN:
    config.TELEGRAM_BOT_TOKEN = '8652434039:AAHw0wdni8Cq9qzM9ONo2itbGIG3R43ABr4'
if not config.TELEGRAM_CHAT_ID:
    config.TELEGRAM_CHAT_ID = '1027083696'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

last_runs = {}
last_daily_summary = None
running = False
is_running_now = False


def run_analysis():
    """Run the full trading council analysis"""
    global is_running_now

    if is_running_now:
        logger.info("Analysis already running, skipping...")
        return []

    is_running_now = True

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from data.market_data import fetch_candle_data
        from agents.technical_agent import TechnicalAgent
        from agents.volume_agent import VolumeAgent
        from agents.macro_agent import MacroAgent
        from agents.risk_agent import RiskAgent
        from utils.telegram_bot import send_signal_message

        if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
            logger.error("Telegram config missing!")
            return []

        symbols = [config.PRIMARY_SYMBOL] + config.FOREX_SYMBOLS
        results = []

        for symbol in symbols:
            try:
                logger.info(f"Analyzing {symbol}...")

                df = fetch_candle_data(symbol, config.TIMEFRAME, 200)
                if df is None or df.empty:
                    logger.warning(f"No data for {symbol}, skipping")
                    continue

                # Agent 1: Technical (ALMA48 + MACD-V)
                tech_agent = TechnicalAgent()
                tech_result = tech_agent.analyze(df)

                # Agent 2: Volume Analysis (replaces Price Action)
                vol_agent = VolumeAgent()
                vol_result = vol_agent.analyze(df)

                # Agent 3: Macro
                macro_agent = MacroAgent()
                macro_result = macro_agent.analyze(symbol)

                # Council Vote (need 2+ agents to agree)
                agents_list = [tech_result, vol_result, macro_result]
                bullish = sum(1 for a in agents_list if a["signal"] == "BULLISH")
                bearish = sum(1 for a in agents_list if a["signal"] == "BEARISH")

                if bullish >= 2:
                    overall = "BULLISH"
                elif bearish >= 2:
                    overall = "BEARISH"
                else:
                    overall = "NEUTRAL"

                avg_conf = sum(a["confidence"] for a in agents_list) / len(agents_list)

                # Check ALMA validity — don't trade if ALMA too close
                alma_valid = tech_result.get("details", {}).get("alma_valid", True)
                if not alma_valid:
                    avg_conf = min(avg_conf, 55)  # Cap confidence when ALMA unclear

                # Agent 4: Risk
                risk_agent = RiskAgent()
                risk_result = risk_agent.calculate(df, overall, {})

                # Summary
                summary_parts = []
                for a in agents_list:
                    if a["signal"] != "NEUTRAL":
                        summary_parts.append(a["rationale"].split(".")[0])
                if not risk_result.get("is_valid"):
                    summary_parts.append("Risk parameters not met.")
                summary = " | ".join(summary_parts[:3]) if summary_parts else "No strong signals."

                analysis = {
                    "symbol": symbol,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "council": {
                        "technical": tech_result,
                        "volume": vol_result,
                        "macro": macro_result,
                    },
                    "overall_signal": overall,
                    "overall_confidence": round(avg_conf),
                    "risk": risk_result,
                    "summary": summary,
                }

                last_runs[symbol] = datetime.now().isoformat()
                results.append(analysis)

                # 🔔 ONLY send to Telegram if valid trade setup exists
                has_valid_trade = (
                    overall in ["BULLISH", "BEARISH"]
                    and risk_result.get("is_valid", False)
                    and avg_conf >= 60  # Minimum confidence 60%
                )

                if has_valid_trade:
                    send_signal_message(analysis)
                    logger.info(f"🔔 {symbol}: {overall} ({round(avg_conf)}%) - SIGNAL SENT")
                else:
                    logger.info(f"🔇 {symbol}: {overall} ({round(avg_conf)}%) - No valid trade, skipped")

                time.sleep(5)

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)

        return results

    finally:
        is_running_now = False


def send_daily_summary():
    """Send daily market summary at 09:00 Bangkok time"""
    global last_daily_summary

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from data.market_data import fetch_candle_data, fetch_macro_data
        from agents.technical_agent import TechnicalAgent
        from agents.volume_agent import VolumeAgent
        from utils.telegram_bot import send_signal_message
        import requests

        symbols = [config.PRIMARY_SYMBOL] + config.FOREX_SYMBOLS

        # Fetch macro
        from agents.macro_agent import MacroAgent
        macro = MacroAgent()
        macro_result = macro.analyze("XAUUSD")

        # Analyze each symbol briefly
        lines = [f"☀️ <b>Daily Market Summary</b>", f"📅 {datetime.now().strftime('%d %b %Y')}", ""]

        # Macro overview
        macro_rationale = macro_result.get("rationale", "")
        if macro_rationale:
            lines.append(f"🌍 <b>Macro:</b> {macro_rationale}")
            lines.append("")

        from data.market_data import get_current_price

        # Decimal places per symbol type
        def _price_dp(sym: str) -> int:
            if sym == "XAUUSD":
                return 2
            elif "JPY" in sym:
                return 3
            else:
                return 5

        for symbol in symbols:
            try:
                df = fetch_candle_data(symbol, config.TIMEFRAME, 200)
                if df is None or df.empty:
                    continue

                tech = TechnicalAgent()
                tech_result = tech.analyze(df)

                vol = VolumeAgent()
                vol_result = vol.analyze(df)

                price = round(get_current_price(symbol), _price_dp(symbol))
                tech_signal = tech_result["signal"]
                vol_signal = vol_result["signal"]

                emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}.get(tech_signal, "🟡")

                lines.append(f"{emoji} <b>{symbol}</b> @ {price}")
                lines.append(f"  Tech: {tech_signal} ({tech_result['confidence']}%) | Vol: {vol_signal} ({vol_result['confidence']}%)")

                # Brief rationale
                brief = tech_result["rationale"].split(".")[0]
                lines.append(f"  📝 {brief}")
                lines.append("")

            except Exception as e:
                logger.error(f"Daily summary error for {symbol}: {e}")

        lines.append("⚠️ <i>Summary only — not a trade signal.</i>")

        # Send via Telegram
        message = "\n".join(lines)
        token = config.TELEGRAM_BOT_TOKEN
        chat_id = config.TELEGRAM_CHAT_ID
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        if resp.status_code == 200:
            logger.info("☀️ Daily summary sent!")
            last_daily_summary = datetime.now().isoformat()
        else:
            logger.error(f"Daily summary send failed: {resp.text}")

    except Exception as e:
        logger.error(f"Daily summary failed: {e}", exc_info=True)


def scheduled_worker():
    """Background worker: analysis every hour + daily summary at 09:00"""
    global running
    running = True

    time.sleep(15)

    # Initial run
    logger.info("=" * 50)
    logger.info("AI Trading Council starting...")
    logger.info("=" * 50)
    try:
        run_analysis()
    except Exception as e:
        logger.error(f"Initial run failed: {e}", exc_info=True)

    # Main loop
    while running:
        now = datetime.now()

        # Check if it's 09:00 Bangkok time for daily summary
        if now.hour == 9 and now.minute < 5:
            if last_daily_summary is None or not last_daily_summary.startswith(now.strftime("%Y-%m-%d")):
                try:
                    send_daily_summary()
                except Exception as e:
                    logger.error(f"Daily summary failed: {e}")

        # Wait until next hour
        next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        wait_seconds = (next_run - now).total_seconds()

        if wait_seconds < 60:
            wait_seconds += 3600

        logger.info(f"Next analysis at {next_run.strftime('%H:%M')} (waiting {int(wait_seconds)}s)")
        time.sleep(wait_seconds)

        try:
            run_analysis()
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}")


# Start background worker
worker_thread = threading.Thread(target=scheduled_worker, daemon=True)
worker_thread.start()


@app.route('/')
def index():
    return {
        "service": "AI Trading Council",
        "status": "running",
        "symbols": [config.PRIMARY_SYMBOL] + config.FOREX_SYMBOLS,
        "last_runs": last_runs,
        "last_daily_summary": last_daily_summary,
        "next_run": "Every hour at :00",
        "telegram_configured": bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID),
    }


@app.route('/health')
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
