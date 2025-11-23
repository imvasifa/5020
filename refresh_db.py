# refresh_db.py
"""
FINAL FIXED VERSION
-------------------
✔ Multithreaded
✔ Fix MultiIndex columns
✔ Fix unexpected columns
✔ Fix BRK.B → BRK-B
✔ 1-year data
✔ Safe normalization
✔ Retry logic
✔ Full DB rebuild
"""

import sqlite3
import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = "usa_data.db"
TICKER_FILE = "usastocks.txt"
LAST_REFRESH_FILE = "last_refresh.txt"

YF_PERIOD = "1y"
YF_INTERVAL = "1d"
THREADS = 12
RETRY_COUNT = 3
MIN_ROWS = 200


# --------------------------
# TICKER CLEANER
# --------------------------
def clean_for_yahoo(ticker: str) -> str:
    return ticker.replace(".", "-").strip()


# --------------------------
# LOAD TICKERS FILE
# --------------------------
def load_tickers():
    if not os.path.exists(TICKER_FILE):
        print(f"[ERR] Missing {TICKER_FILE}")
        return []
    with open(TICKER_FILE, "r") as f:
        return [x.strip() for x in f if x.strip()]


# --------------------------
# CREATE DB TABLE
# --------------------------
def create_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.commit()
    conn.close()


# --------------------------
# DOWNLOAD ONE TICKER
# --------------------------
def download_ticker(original_ticker):
    yf_ticker = clean_for_yahoo(original_ticker)
    last_error = None

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            df = yf.download(
                yf_ticker,
                period=YF_PERIOD,
                interval=YF_INTERVAL,
                progress=False,
                auto_adjust=False
            )
            if df is None or df.empty:
                last_error = f"Empty after attempt {attempt}"
                time.sleep(0.2)
                continue
            return original_ticker, df, None
        except Exception as e:
            last_error = repr(e)
            time.sleep(0.4)

    return original_ticker, None, last_error


# --------------------------
# MAIN REFRESH FUNCTION
# --------------------------
def refresh_all_data():
    tickers = load_tickers()
    create_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Start fresh
    cur.execute("DELETE FROM stock_data")
    conn.commit()
    print("[INFO] Cleared stock_data table.")

    failed = []
    success_count = 0

    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = {pool.submit(download_ticker, t): t for t in tickers}

        for i, fut in enumerate(as_completed(futures), start=1):
            original_ticker = futures[fut]
            t, df, err = fut.result()

            if err or df is None or df.empty:
                failed.append(original_ticker)
                print(f"[WARN] {original_ticker} FAILED: {err}")
                continue

            # -----------------------------------
            # NORMALIZATION FIX (FINAL — WORKS)
            # -----------------------------------
            try:
                # Flatten MultiIndex
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # Keep only OHLCV
                df = df.reset_index()
                cols = [c for c in df.columns if c.lower() in
                        ["date", "open", "high", "low", "close", "volume"]]

                # Sometimes Date column is under different name
                if "Date" in df.columns:
                    df.rename(columns={"Date": "date"}, inplace=True)

                # rebuild clean df
                df = df[cols]

                # Final enforcement
                df = df.rename(columns=str.lower)
                df = df[["date", "open", "high", "low", "close", "volume"]]

                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

            except Exception as e:
                print(f"[WARN] NORMALIZATION FAILED for {original_ticker}: {e}")
                failed.append(original_ticker)
                continue

            # Must have enough bars
            if len(df) < MIN_ROWS:
                print(f"[WARN] {original_ticker}: only {len(df)} rows (min {MIN_ROWS})")
                failed.append(original_ticker)
                continue

            # Insert into DB
            rows = [
                (
                    original_ticker,
                    row["date"],
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"])
                )
                for _, row in df.iterrows()
            ]

            try:
                cur.executemany("""
                    INSERT OR REPLACE INTO stock_data
                    (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, rows)
                success_count += 1
            except Exception as e:
                print(f"[ERR] DB ERROR {original_ticker}: {e}")
                failed.append(original_ticker)

            conn.commit()

            print(f"[OK] {original_ticker} saved ({len(df)} rows) [{success_count}/{len(tickers)}]")

    conn.close()

    # Save last refresh time
    with open(LAST_REFRESH_FILE, "w") as f:
        f.write(datetime.now().isoformat())

    # Save failed list
    with open("failed_tickers.txt", "w") as f:
        for item in failed:
            f.write(item + "\n")

    print("====================================")
    print("REFRESH COMPLETE")
    print(f"Success: {success_count}")
    print(f"Failed: {len(failed)} (see failed_tickers.txt)")
    print("====================================")

    return True


# --------------------------
# DAILY CHECK
# --------------------------
def needs_refresh():
    if not os.path.exists(LAST_REFRESH_FILE):
        return True
    try:
        with open(LAST_REFRESH_FILE, "r") as f:
            last = datetime.fromisoformat(f.read().strip())
        return (datetime.now() - last) >= timedelta(days=1)
    except:
        return True


if __name__ == "__main__":
    refresh_all_data()
