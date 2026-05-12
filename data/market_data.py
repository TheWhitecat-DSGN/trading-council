# AI Trading Council - Market Data Fetcher
# Twelve Data API (real-time, broker-accurate prices)
import pandas as pd
import requests
from datetime import datetime, timedelta
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# Twelve Data config
TD_API_KEY = os.environ.get("TWELVE_DATA_API_KEY", "b7c20f72caaf4dc5ab0e4b04c36211a4")
TD_BASE = "https://api.twelvedata.com"


def _td_symbol(symbol: str) -> str:
    """Convert our symbol format to Twelve Data format"""
    mapping = {
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "AUDUSD": "AUD/USD",
        "USDCAD": "USD/CAD",
        "USDCNY": "USD/CNY",
    }
    return mapping.get(symbol, symbol)


def _td_interval(tf: str) -> str:
    """Convert timeframe to Twelve Data interval"""
    mapping = {
        "1m": "1min", "5m": "5min", "15m": "15min",
        "30m": "30min", "1h": "1h", "4h": "4h",
        "1d": "1day", "1w": "1week",
    }
    return mapping.get(tf, "1h")


def fetch_candle_data(symbol: str, timeframe: str = "1h", limit: int = 200) -> pd.DataFrame:
    """Fetch OHLCV candle data from Twelve Data"""
    td_sym = _td_symbol(symbol)
    interval = _td_interval(timeframe)
    outputsize = min(limit, 500)

    try:
        url = f"{TD_BASE}/time_series"
        params = {
            "symbol": td_sym,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TD_API_KEY,
            "format": "JSON",
        }
        resp = requests.get(url, params=params, timeout=15)

        if resp.status_code != 200:
            print(f"[WARN] Twelve Data HTTP {resp.status_code} for {td_sym}")
            return _fallback_yfinance(symbol, timeframe, limit)

        data = resp.json()

        # Check for API errors
        if "status" in data and data["status"] == "error":
            print(f"[WARN] Twelve Data error for {td_sym}: {data.get('message', 'unknown')}")
            return _fallback_yfinance(symbol, timeframe, limit)

        values = data.get("values", [])
        if not values:
            print(f"[WARN] No data from Twelve Data for {td_sym}")
            return _fallback_yfinance(symbol, timeframe, limit)

        df = pd.DataFrame(values)
        df = df.rename(columns={
            "datetime": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
        })

        # Convert types
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.tail(limit).reset_index(drop=True)
        return df

    except Exception as e:
        print(f"[WARN] Twelve Data failed for {symbol}: {e}")
        return _fallback_yfinance(symbol, timeframe, limit)


def _fallback_yfinance(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """Fallback to yfinance if Twelve Data fails"""
    try:
        import yfinance as yf

        yf_symbol = symbol
        if symbol == "XAUUSD":
            yf_symbol = "GC=F"
        elif symbol in ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]:
            yf_symbol = f"{symbol}=X"

        interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15m",
            "30m": "30m", "1h": "1h", "4h": "4h",
            "1d": "1d", "1w": "1wk"
        }
        interval = interval_map.get(timeframe, "1h")

        period_map = {
            "1m": "5d", "5m": "5d", "15m": "10d",
            "30m": "10d", "1h": "30d", "4h": "60d",
            "1d": "1y", "1w": "2y"
        }
        period = period_map.get(timeframe, "30d")

        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return pd.DataFrame()

        df = df.tail(limit).reset_index()
        df.columns = [c.lower() for c in df.columns]
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "date"})
        return df

    except Exception as e:
        print(f"[ERROR] yfinance fallback also failed for {symbol}: {e}")
        return pd.DataFrame()


def fetch_macro_data() -> dict:
    """Fetch macro data: DXY, VIX, US 10Y yield"""
    result = {}

    # Use yfinance for macro (Twelve Data doesn't cover indices well on free tier)
    try:
        import yfinance as yf

        # DXY
        try:
            dxy = yf.Ticker("DX-Y.NYB").history(period="5d", interval="1d")
            if not dxy.empty:
                result["dxy"] = round(dxy["Close"].iloc[-1], 3)
                result["dxy_change"] = round(
                    ((dxy["Close"].iloc[-1] / dxy["Close"].iloc[-2]) - 1) * 100, 2
                )
        except Exception as e:
            print(f"[WARN] DXY fetch failed: {e}")

        # VIX
        try:
            vix = yf.Ticker("^VIX").history(period="5d", interval="1d")
            if not vix.empty:
                result["vix"] = round(vix["Close"].iloc[-1], 2)
                result["vix_change"] = round(
                    ((vix["Close"].iloc[-1] / vix["Close"].iloc[-2]) - 1) * 100, 2
                )
        except Exception as e:
            print(f"[WARN] VIX fetch failed: {e}")

        # US 10Y Yield
        try:
            ty = yf.Ticker("^TNX").history(period="5d", interval="1d")
            if not ty.empty:
                result["us_10y"] = round(ty["Close"].iloc[-1], 3)
        except Exception as e:
            print(f"[WARN] US 10Y fetch failed: {e}")

        # Gold price (from Twelve Data for accuracy)
        try:
            url = f"{TD_BASE}/price"
            params = {"symbol": "XAU/USD", "apikey": TD_API_KEY}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if "price" in data:
                    result["gold_price"] = round(float(data["price"]), 2)
        except Exception as e:
            print(f"[WARN] Gold price fetch failed: {e}")

    except ImportError:
        print("[WARN] yfinance not available for macro data")

    return result


def fetch_economic_calendar() -> list:
    """Fetch upcoming high-impact economic events"""
    events = []
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                if item.get("impact") == "High":
                    events.append({
                        "date": item.get("date"),
                        "title": item.get("title"),
                        "country": item.get("country"),
                        "forecast": item.get("forecast"),
                        "previous": item.get("previous"),
                    })
            events = events[:10]
    except Exception as e:
        print(f"[WARN] Economic calendar fetch failed: {e}")

    return events


def get_current_price(symbol: str) -> float:
    """Get latest real-time price from Twelve Data"""
    td_sym = _td_symbol(symbol)
    try:
        url = f"{TD_BASE}/price"
        params = {"symbol": td_sym, "apikey": TD_API_KEY}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "price" in data:
                return round(float(data["price"]), 5)
    except Exception as e:
        print(f"[WARN] Price fetch failed for {symbol}: {e}")

    # Fallback
    df = fetch_candle_data(symbol, "1h", 2)
    if not df.empty and "close" in df.columns:
        return round(float(df["close"].iloc[-1]), 5)
    return 0.0
