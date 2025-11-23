from __future__ import annotations
import sys, io
from pathlib import Path

import requests
import pandas as pd
import yfinance as yf

SAVE_DIR = Path(r"D:\usa5020")  # change if you want

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

def save_txt(filename: str, symbols) -> None:
    symbols = [s.strip().upper() for s in symbols if isinstance(s, str) and s.strip()]
    (SAVE_DIR / filename).write_text("\n".join(sorted(set(symbols))))
    print(f"✅ Saved {filename} with {len(set(symbols))} symbols")

def fetch_tables(url: str) -> list[pd.DataFrame]:
    resp = requests.get(url, headers=UA, timeout=20)
    resp.raise_for_status()
    # read_html needs lxml installed
    return pd.read_html(io.StringIO(resp.text))

def get_column_by_name(tables: list[pd.DataFrame], prefer_cols: list[str]) -> pd.Series | None:
    for df in tables:
        for col in df.columns:
            if str(col).strip().lower() in [c.lower() for c in prefer_cols]:
                return df[col].dropna()
    return None

def get_sp500() -> list[str]:
    # Try yfinance helper first (fast & reliable)
    try:
        syms = yf.tickers_sp500()
        if syms:
            return syms
    except Exception:
        pass
    # Fallback to Wikipedia
    tables = fetch_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    col = get_column_by_name(tables, ["Symbol", "Ticker"])
    if col is None:
        raise RuntimeError("Could not find S&P 500 symbol column on Wikipedia page.")
    return list(col)

def get_dow30() -> list[str]:
    # Try yfinance helper first
    try:
        syms = yf.tickers_dow()
        if syms:
            return syms
    except Exception:
        pass
    # Fallback to Wikipedia
    tables = fetch_tables("https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average")
    col = get_column_by_name(tables, ["Symbol", "Ticker"])
    if col is None:
        raise RuntimeError("Could not find Dow 30 symbol column on Wikipedia page.")
    return list(col)

def get_nasdaq100() -> list[str]:
    # Wikipedia only (yfinance doesn’t ship NASDAQ-100 list)
    tables = fetch_tables("https://en.wikipedia.org/wiki/NASDAQ-100")
    col = get_column_by_name(tables, ["Ticker", "Symbol"])
    if col is None:
        # Some page versions have the table further down; brute force all tables for a Ticker column
        for df in tables:
            for colname in df.columns:
                if str(colname).strip().lower() in ("ticker", "symbol"):
                    return list(df[colname].dropna())
        raise RuntimeError("Could not find NASDAQ-100 symbol column on Wikipedia page.")
    return list(col)

def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    print("⏳ Downloading U.S. index symbols (S&P 500, NASDAQ-100, Dow 30)...\n")

    # S&P 500
    try:
        sp = get_sp500()
        save_txt("sp500.txt", sp)
    except Exception as e:
        print(f"❌ S&P 500 fetch failed: {e}")

    # NASDAQ-100
    try:
        nq = get_nasdaq100()
        save_txt("nasdaq100.txt", nq)
    except Exception as e:
        print(f"❌ NASDAQ-100 fetch failed: {e}")

    # DOW 30
    try:
        dj = get_dow30()
        save_txt("dow30.txt", dj)
    except Exception as e:
        print(f"❌ Dow 30 fetch failed: {e}")

    print(f"\n🎯 Lists saved to {SAVE_DIR}")

if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"❌ HTTP error: {e}. If 403, your network blocks Wikipedia. Try again later or use a different connection.")
        sys.exit(1)
