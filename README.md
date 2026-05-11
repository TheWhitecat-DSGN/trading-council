# AI Trading Council 🏛️

Multi-agent AI system for XAUUSD/Forex swing trading signals on H1 timeframe.

## Features
- **Technical Agent**: ALMA48 + MACD-V indicator analysis
- **Price Action Agent**: Candlestick patterns, S/R, market structure
- **Macro Agent**: DXY, VIX, US 10Y yield, economic calendar
- **Risk Agent**: Position sizing, SL/TP, risk-reward calculation
- **Council Vote**: All agents vote → combined signal
- **Telegram Alerts**: Signals sent directly to your phone

## Deploy to Railway (Free)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "AI Trading Council v1"
git remote add origin https://github.com/YOUR_USERNAME/trading-council.git
git push -u origin main
```

### Step 2: Deploy on Railway
1. Go to [railway.app](https://railway.app) → Login with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `trading-council` repo
4. Railway auto-detects Python and deploys

### Step 3: Set Environment Variables
In Railway dashboard → your service → **Variables** → Add:
```
TELEGRAM_BOT_TOKEN = 8652434039:AAHw0wdni8Cq9qzM9ONo2itbGIG3R43ABr4
TELEGRAM_CHAT_ID = 1027083696
PRIMARY_SYMBOL = XAUUSD
FOREX_SYMBOLS = EURUSD,GBPUSD,USDJPY
TIMEFRAME = 1h
ACCOUNT_BALANCE = 150
```

### Step 4: Done!
The service will:
- Start automatically
- Run analysis every hour at :00
- Send trading signals to your Telegram

## Local Testing
```bash
pip install -r requirements.txt
python main.py --symbol XAUUSD
```

## Endpoints (when deployed)
- `GET /` — Service status + last run times
- `GET /health` — Health check
- `GET /run` — Trigger manual analysis

## ⚠️ Disclaimer
Trading signals are advisory only. Past performance ≠ future results. Always use proper risk management.
