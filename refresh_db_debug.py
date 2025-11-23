# refresh_db_debug.py
"""
Debug refresh for usa_data.db
- Verbose logging to console + download_log.csv
- Writes failed_tickers.txt
- Commits safely and prints DB stats
Usage: python refresh_db_debug.py
"""

import sqlite3
import yfinance as yf
import pandas as pd
import os, sys, time, csv
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# CONFIG
DB_PATH = "usa_data.db"
TICKER_FILE = "usastocks.txt"
LAST_REFRESH_FILE = "last_refresh.txt"
FAILED_FILE = "failed_tickers.txt"
DOWNLOAD_LOG = "download_log.csv"

YF_PERIOD = "1y"
YF_INTERVAL = "1d"
THREADS = 12
RETRIES = 3
MIN_ROWS = 200
COMMIT_BATCH = 25
SLEEP_BETWEEN = 0.2

def clean_for_yahoo(ticker: str) -> str:
    return ticker.replace(".", "-").strip()

def load_tickers():
    if not os.path.exists(TICKER_FILE):
        print(f"[ERR] ticker file missing: {TICKER_FILE}")
        return []
    with open(TICKER_FILE, "r") as f:
        return [t.strip() for t in f if t.strip()]

def create_table_if_missing():
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

def download_one(original_ticker):
    yf_t = clean_for_yahoo(original_ticker)
    last_exception = None
    for attempt in range(1, RETRIES+1):
        try:
            df = yf.download(yf_t, period=YF_PERIOD, interval=YF_INTERVAL, progress=False, auto_adjust=False)
            if df is None or df.empty:
                last_exception = f"empty after download (attempt {attempt})"
                time.sleep(0.3)
                continue
            # success
            return original_ticker, df, None
        except Exception as e:
            last_exception = f"exc: {repr(e)} (attempt {attempt})"
            time.sleep(0.5)
    return original_ticker, None, last_exception

def refresh_all():
    tickers = load_tickers()
    if not tickers:
        print("[ERR] No tickers found. Aborting.")
        return False

    print(f"[INFO] Starting refresh for {len(tickers)} tickers with {THREADS} threads.")
    create_table_if_missing()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM stock_data")
    conn.commit()
    print("[INFO] Cleared existing stock_data table.")

    failed = []
    download_records = []

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(download_one, t): t for t in tickers}
        count = 0
        for fut in as_completed(futures):
            orig = futures[fut]
            try:
                ticker, df, err = fut.result()
            except Exception as e:
                ticker, df, err = orig, None, f"future_exception: {repr(e)}"

            if err:
                print(f"[WARN] {ticker} FAILED => {err}")
                failed.append(ticker)
                download_records.append((ticker, "FAILED", err))
                continue

            if df is None or df.empty:
                print(f"[WARN] {ticker} => empty dataframe")
                failed.append(ticker)
                download_records.append((ticker, "EMPTY", "no rows"))
                continue

            # normalize dataframe
            try:
                df = df.reset_index()[["Date","Open","High","Low","Close","Volume"]].dropna()
                df.columns = ["date","open","high","low","close","volume"]
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            except Exception as e:
                print(f"[WARN] {ticker} normalization failed: {e}")
                failed.append(ticker)
                download_records.append((ticker, "NORMALIZE_FAIL", repr(e)))
                continue

            if len(df) < MIN_ROWS:
                print(f"[WARN] {ticker} has only {len(df)} rows (<{MIN_ROWS}) - skipping")
                failed.append(ticker)
                download_records.append((ticker, "TOO_FEW_ROWS", str(len(df))))
                continue

            # prepare rows
            rows = [
                (ticker, row["date"], float(row["open"]), float(row["high"]),
                 float(row["low"]), float(row["close"]), float(row["volume"]))
                for _, row in df.iterrows()
            ]

            try:
                cur.executemany("""
                    INSERT OR REPLACE INTO stock_data
                    (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, rows)
            except Exception as e:
                print(f"[ERR] DB insert failed for {ticker}: {e}")
                failed.append(ticker)
                download_records.append((ticker, "DB_INSERT_FAIL", repr(e)))
                continue

            count += 1
            if count % COMMIT_BATCH == 0:
                conn.commit()
                print(f"[INFO] Committed {count} tickers.")

            download_records.append((ticker, "OK", str(len(df))))
            time.sleep(SLEEP_BETWEEN)

    conn.commit()
    conn.close()

    # write logs
    with open(DOWNLOAD_LOG, "w", newline="") as csvf:
        w = csv.writer(csvf)
        w.writerow(["ticker","status","info"])
        for r in download_records:
            w.writerow(r)

    with open(FAILED_FILE, "w") as ff:
        for t in failed:
            ff.write(t + "\n")

    # write last refresh time
    with open(LAST_REFRESH_FILE, "w") as lf:
        lf.write(datetime.now().isoformat())

    # Summary print
    total_rows = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        total_rows = cur.execute("SELECT COUNT(*) FROM stock_data").fetchone()[0]
        distinct = cur.execute("SELECT COUNT(DISTINCT ticker) FROM stock_data").fetchone()[0]
        sample = cur.execute("SELECT ticker, COUNT(*) FROM stock_data GROUP BY ticker ORDER BY COUNT(*) DESC LIMIT 10").fetchall()
        conn.close()
    except Exception as e:
        print(f"[ERR] DB stats error: {e}")
        distinct = 0
        sample = []

    print("=== REFRESH SUMMARY ===")
    print(f"Tickers attempted: {len(tickers)}")
    print(f"Successful tickers: {len(download_records) - len(failed)}")
    print(f"Failed tickers: {len(failed)} (written to {FAILED_FILE})")
    print(f"Total DB rows: {total_rows}")
    print(f"Distinct tickers in DB: {distinct}")
    print("Top 10 tickers by row count (ticker, rows):")
    for r in sample:
        print(" ", r)

    print(f"Download log: {DOWNLOAD_LOG}")
    return True

if __name__ == "__main__":
    ok = refresh_all()
    if not ok:
        print("[ERR] refresh did not complete successfully.")
        sys.exit(1)
    print("[OK] refresh_all completed.")
