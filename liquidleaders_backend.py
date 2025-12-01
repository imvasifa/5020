# liquidleaders_backend.py
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

THRESHOLDS = {
    "min_price": 3.0,
    "min_avg_volume": 100_000,
    "atr_pct_min": 0.2,
    "atr_pct_max": 8.0,
    "dcr_min": 60.0,
    "return21_min": 5.0,
    "rr_max": 6.0,
    "atre20_min": -1.0,
    "atre50_min": -1.0,
}

CLASS_RULES = {
    "set3": {"return21_min": 5, "dcr_min": 60, "rr_max": 6},
    "set2": {"return21_min": 3, "dcr_min": 50, "rr_max": 8},
    "set1": {"return21_min": 1, "dcr_min": 40, "rr_max": 12},
}

def atr(df, n=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def compute_metrics(df):
    df = df.dropna()
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    atr14 = atr(df, 14)
    atr20 = atr(df, 20)
    atr50 = atr(df, 50)
    today_close = close.iloc[-1]
    today_high = high.iloc[-1]
    today_low = low.iloc[-1]
    dcr = (today_close - today_low) / (today_high - today_low) * 100 if today_high != today_low else 50
    return21 = (today_close / close.iloc[-21] - 1) * 100 if len(df) > 21 else np.nan
    atr_pct = atr14.iloc[-1] / today_close * 100 if today_close > 0 else np.nan
    high50 = high.rolling(50).max().iloc[-1]
    rr = (high50 - today_close) / atr14.iloc[-1] if atr14.iloc[-1] > 0 else np.nan
    ema20 = ema(close, 20).iloc[-1]
    ema50 = ema(close, 50).iloc[-1]
    atre20 = (today_close - ema20) / atr20.iloc[-1] if atr20.iloc[-1] > 0 else np.nan
    atre50 = (today_close - ema50) / atr50.iloc[-1] if atr50.iloc[-1] > 0 else np.nan
    avg_vol = volume.tail(20).mean()
    return {
        "close": today_close,
        "dcr": dcr,
        "return21": return21,
        "atr_pct": atr_pct,
        "rr": rr,
        "atre20": atre20,
        "atre50": atre50,
        "avg_vol_21": avg_vol,
    }

def classify_stock(m):
    for label in ["set3", "set2", "set1"]:
        rules = CLASS_RULES[label]
        if m["return21"] >= rules["return21_min"] and \
           m["dcr"] >= rules["dcr_min"] and \
           m["rr"] <= rules["rr_max"]:
            return label
    return None

def run_liquid_leaders(ticker_file="usastocks.txt", soft_mode=False):
    with open(ticker_file, "r") as f:
        tickers = [t.strip().upper() for t in f.read().splitlines() if t.strip()]
    raw = yf.download(
        tickers,
        period="300d",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        progress=False
    )
    results = []
    for t in tickers:
        try:
            df = raw[t].dropna()
        except:
            continue
        metrics = compute_metrics(df)
        if metrics is None:
            continue
        if metrics["close"] < THRESHOLDS["min_price"]: continue
        if metrics["avg_vol_21"] < THRESHOLDS["min_avg_volume"]: continue
        if not (THRESHOLDS["atr_pct_min"] <= metrics["atr_pct"] <= THRESHOLDS["atr_pct_max"]): continue
        cls = classify_stock(metrics)
        if cls is None:
            continue
        results.append({"ticker": t, "set": cls, **metrics})
    df_final = pd.DataFrame(results)
    if df_final.empty:
        return pd.DataFrame()
    df_final["rank"] = df_final["set"].map({"set3": 3, "set2": 2, "set1": 1})
    df_final = df_final.sort_values(["rank", "return21"], ascending=[False, False])
    df_final.drop(columns=["rank"], inplace=True)
    return df_final.reset_index(drop=True)
