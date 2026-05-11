# AI Trading Council - Configuration
import os

# Account
ACCOUNT_BALANCE = float(os.environ.get("ACCOUNT_BALANCE", "150.00"))
ACCOUNT_TYPE = "cent"
MAX_RISK_PERCENT = 2.0

# Trading
PRIMARY_SYMBOL = os.environ.get("PRIMARY_SYMBOL", "XAUUSD")
FOREX_SYMBOLS = os.environ.get("FOREX_SYMBOLS", "EURUSD,USDJPY").split(",")
TIMEFRAME = os.environ.get("TIMEFRAME", "1h")
TRADING_STYLE = "swing"

# Indicators
ALMA_WINDOW = 48
ALMA_OFFSET = 0.85
ALMA_SIGMA = 6
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Risk Management
MIN_RR_RATIO = 1.5
DEFAULT_RR_RATIO = 2.0
ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.5

# Telegram
_env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_env_chat = os.environ.get("TELEGRAM_CHAT_ID", "")

# Fallback: try reading from file (for Railway volume mount)
if not _env_token or not _env_chat:
    try:
        _secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secrets")
        if os.path.exists(_secrets_path):
            with open(_secrets_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        _env_token = _env_token or line.split("=", 1)[1]
                    elif line.startswith("TELEGRAM_CHAT_ID="):
                        _env_chat = _env_chat or line.split("=", 1)[1]
    except Exception:
        pass

TELEGRAM_BOT_TOKEN = _env_token
TELEGRAM_CHAT_ID = _env_chat

# Timezone
TIMEZONE = "Asia/Bangkok"
