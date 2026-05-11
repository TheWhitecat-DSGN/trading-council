# AI Trading Council - Railway Deploy
"""
Web service that runs the trading council every hour and sends signals to Telegram.
Deploy on Railway.app
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Track last run
last_runs = {}
running = False


def run_analysis():
    """Run the full trading council analysis"""
    # Import here to avoid issues
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from data.market_data import fetch_candle_data
    from agents.technical_agent import TechnicalAgent
    from agents.price_action_agent import PriceActionAgent
    from agents.macro_agent import MacroAgent
    from agents.risk_agent import RiskAgent
    from utils.telegram_bot import send_signal_message, format_signal

    # Check telegram config
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set! Check environment variables.")
        return []

    logger.info(f"Telegram config OK - Bot: ...{config.TELEGRAM_BOT_TOKEN[-6:]}, Chat: {config.TELEGRAM_CHAT_ID}")

    symbols = [config.PRIMARY_SYMBOL] + config.FOREX_SYMBOLS
    results = []

    for symbol in symbols:
        try:
            logger.info(f"Analyzing {symbol}...")

            # Fetch data
            df = fetch_candle_data(symbol, config.TIMEFRAME, 200)
            if df is None or df.empty:
                logger.warning(f"No data for {symbol}, skipping")
                continue

            # Agent 1: Technical
            tech_agent = TechnicalAgent()
            tech_result = tech_agent.analyze(df)

            # Agent 2: Price Action
            pa_agent = PriceActionAgent()
            pa_result = pa_agent.analyze(df)

            # Agent 3: Macro
            macro_agent = MacroAgent()
            macro_result = macro_agent.analyze(symbol)

            # Council Vote
            agents = [tech_result, pa_result, macro_result]
            bullish = sum(1 for a in agents if a["signal"] == "BULLISH")
            bearish = sum(1 for a in agents if a["signal"] == "BEARISH")

            if bullish > bearish and bullish >= 2:
                overall = "BULLISH"
            elif bearish > bullish and bearish >= 2:
                overall = "BEARISH"
            else:
                overall = "NEUTRAL"

            avg_conf = sum(a["confidence"] for a in agents) / len(agents)

            # Agent 4: Risk
            risk_agent = RiskAgent()
            risk_result = risk_agent.calculate(df, overall, {})

            # Summary
            summary_parts = []
            for a in agents:
                if a["signal"] != "NEUTRAL":
                    summary_parts.append(a["rationale"].split(".")[0])
            if not risk_result.get("is_valid"):
                summary_parts.append("Risk parameters not met - skip trade.")
            summary = " | ".join(summary_parts[:3]) if summary_parts else "No strong signals."

            analysis = {
                "symbol": symbol,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "council": {
                    "technical": tech_result,
                    "price_action": pa_result,
                    "macro": macro_result,
                },
                "overall_signal": overall,
                "overall_confidence": round(avg_conf),
                "risk": risk_result,
                "summary": summary,
            }

            # Send to Telegram
            success = send_signal_message(analysis)
            if success:
                logger.info(f"{symbol}: {overall} ({round(avg_conf)}%) - sent to Telegram OK")
            else:
                logger.error(f"{symbol}: {overall} ({round(avg_conf)}%) - FAILED to send to Telegram")

            last_runs[symbol] = datetime.now().isoformat()
            results.append(analysis)

            # Delay between symbols to avoid rate limits
            time.sleep(5)

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)

    return results


def scheduled_worker():
    """Background worker that runs analysis every hour"""
    global running
    running = True

    # Wait 10 seconds for service to fully start
    time.sleep(10)

    # Run immediately on startup
    logger.info("=" * 50)
    logger.info("Starting AI Trading Council scheduled worker...")
    logger.info("=" * 50)
    try:
        run_analysis()
    except Exception as e:
        logger.error(f"Initial run failed: {e}", exc_info=True)

    # Then every hour
    while running:
        now = datetime.now()
        # Next hour mark
        next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        wait_seconds = (next_run - now).total_seconds()

        logger.info(f"Next analysis at {next_run.strftime('%H:%M')} (waiting {int(wait_seconds)}s)")
        time.sleep(wait_seconds)

        try:
            run_analysis()
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}", exc_info=True)


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
        "next_run": "Every hour at :00",
        "telegram_configured": bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID),
    }


@app.route('/run')
def manual_run():
    """Trigger a manual analysis run"""
    try:
        results = run_analysis()
        return {"status": "ok", "results": len(results), "telegram_configured": bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID)}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500


@app.route('/health')
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
