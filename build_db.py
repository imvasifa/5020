import yfinance as yf
import pandas as pd
import sqlite3
import time

# ======================================================
#  INIT DATABASE (create if missing)
# ======================================================
def init_db():
    conn = sqlite3.connect("usa_data.db")
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
    print("✅ usa_data.db ready.")

# ======================================================
#  FETCH AND STORE FUNCTION
# ======================================================
def fetch_and_store(ticker, period="6mo", interval="1d"):
    print(f"⏳ Fetching {ticker} ...", end=" ")
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         progress=False, auto_adjust=False, threads=True)

        if df.empty:
            print("⚠️ No data")
            return

        # Normalize dataframe
        df = df.reset_index()
        if "Date" not in df.columns:
            print("⚠️ Missing Date column.")
            return

        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].dropna()
        df.columns = ["date", "open", "high", "low", "close", "volume"]  # lowercase for SQLite
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["ticker"] = ticker

        conn = sqlite3.connect("usa_data.db")
        df[["ticker", "date", "open", "high", "low", "close", "volume"]].to_sql(
            "stock_data", conn, if_exists="append", index=False)
        conn.commit()
        conn.close()

        print(f"✅ Stored {len(df)} rows.")

    except KeyboardInterrupt:
        print("\n🛑 Stopped manually.")
        raise
    except Exception as e:
        print(f"❌ {e}")
    finally:
        time.sleep(0.3)  # polite delay for Yahoo API

# ======================================================
#  MAIN
# ======================================================
if __name__ == "__main__":
    init_db()

    tickers = list(dict.fromkeys("""
    AAPL MSFT AMZN NVDA TSLA META GOOGL GOOG AMD INTC ADBE ORCL AVGO CRM NFLX CSCO QCOM TXN AMAT
    PEP KO WMT DIS PFE JNJ V MA BAC JPM WFC XOM CVX UNH HD COST MCD IBM PYPL MRK LLY ABBV CAT BA GE
    """.split()))

    for i, t in enumerate(tickers, start=1):
        fetch_and_store(t)
        print(f"[{i}/{len(tickers)}] done.")

    print("\n🎯 Database build complete!")
