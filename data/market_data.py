# AI Trading Council - Market Data Fetcher
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def fetch_candle_data(symbol: str, timeframe: str = "1h", limit: int = 200) -> pd.DataFrame:
    """
    Fetch OHLCV candle data
    For XAUUSD, use GC=F (Gold Futures) or XAUUSD=X
    """
    yf_symbol = symbol
    if symbol == "XAUUSD":
        yf_symbol = "GC=F"  # Gold futures
    elif symbol == "EURUSD":
        yf_symbol = "EURUSD=X"
    elif symbol == "GBPUSD":
        yf_symbol = "GBPUSD=X"
    elif symbol == "USDJPY":
        yf_symbol = "USDJPY=X"
    
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
    
    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            print(f"[WARN] No data for {yf_symbol}, trying alternative...")
            # Fallback: try XAUUSD=X for gold
            if symbol == "XAUUSD":
                df = yf.Ticker("XAUUSD=X").history(period=period, interval=interval)
        
        if df.empty:
            raise Exception(f"Cannot fetch data for {symbol}")
        
        df = df.tail(limit).reset_index()
        df.columns = [c.lower() for c in df.columns]
        if "datetime" in df.columns:
            df = df.rename(columns={"datetime": "date"})
        if "close" not in df.columns:
            raise Exception(f"Missing close column for {symbol}")
        
        return df
    except Exception as e:
        print(f"[ERROR] Failed to fetch {symbol}: {e}")
        return pd.DataFrame()


def fetch_macro_data() -> dict:
    """
    Fetch macro data: DXY, VIX, US 10Y yield, Gold price
    """
    result = {}
    
    # DXY (US Dollar Index)
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
    
    # Gold current price
    try:
        gold = yf.Ticker("GC=F").history(period="2d", interval="1d")
        if not gold.empty:
            result["gold_price"] = round(gold["Close"].iloc[-1], 2)
            result["gold_change"] = round(
                ((gold["Close"].iloc[-1] / gold["Close"].iloc[-2]) - 1) * 100, 2
            )
    except Exception as e:
        print(f"[WARN] Gold price fetch failed: {e}")
    
    return result


def fetch_economic_calendar() -> list:
    """
    Fetch upcoming high-impact economic events
    Uses ForexFactory (basic scrape)
    """
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
            events = events[:10]  # Top 10
    except Exception as e:
        print(f"[WARN] Economic calendar fetch failed: {e}")
    
    return events


def get_current_price(symbol: str) -> float:
    """Get latest price for a symbol"""
    df = fetch_candle_data(symbol, "1h", 2)
    if not df.empty and "close" in df.columns:
        return round(df["close"].iloc[-1], 2)
    return 0.0
