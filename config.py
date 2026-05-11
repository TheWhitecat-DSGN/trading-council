# AI Trading Council - Configuration
import os

# Account
ACCOUNT_BALANCE = float(os.environ.get("ACCOUNT_BALANCE", "150.00"))
ACCOUNT_TYPE = "cent"
MAX_RISK_PERCENT = 2.0

# Trading
PRIMARY_SYMBOL = os.environ.get("PRIMARY_SYMBOL", "XAUUSD")
FOREX_SYMBOLS = os.environ.get("FOREX_SYMBOLS", "EURUSD,GBPUSD,USDJPY").split(",")
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

# Telegram - from env vars (secure)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Timezone
TIMEZONE = "Asia/Bangkok"
