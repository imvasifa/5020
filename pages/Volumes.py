# Volumes.py — Full working SMA-only screener with scrollable mplfinance chart (PNG-scroll)
# App icon set to "✅"
# Requirements: pandas, numpy, yfinance, streamlit, mplfinance, matplotlib, ta

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import sqlite3
import datetime as dt
from datetime import timedelta
from typing import Optional
import io

import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import ta

from matplotlib.lines import Line2D
from mplfinance import make_marketcolors, make_mpf_style

# ---------------- Streamlit config (icon = checkmark) ----------------
st.set_page_config(layout="wide", page_title="USA Volume Screener", page_icon="✅")
DB_PATH = "usa_data.db"

# ---------------- DB init ----------------
def init_db():
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

init_db()

# ---------------- Load tickers from usastocks.txt ----------------
def load_ticker_list(path="usastocks.txt"):
    try:
        with open(path, "r") as f:
            tickers = [line.strip().upper() for line in f.readlines()]
        tickers = [t for t in tickers if t]
        return list(dict.fromkeys(tickers))
    except Exception:
        st.error("❌ usastocks.txt not found or unreadable. Please add the file in project folder.")
        return []

tickers = load_ticker_list()
st.sidebar.info(f"Loaded {len(tickers)} tickers")

# ---------------- DB Helpers ----------------
def clean_for_yahoo(ticker: str) -> str:
    return ticker.replace(".", "-")

def upsert_rows(ticker: str, df: pd.DataFrame):
    if df.empty:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for _, r in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO stock_data
            (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticker, str(r["date"]), float(r["open"]), float(r["high"]),
              float(r["low"]), float(r["close"]), float(r["volume"])))
    conn.commit()
    conn.close()

def max_date_in_db(ticker: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT MAX(date) FROM stock_data WHERE ticker=?", (ticker,)).fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def fetch_latest_1d_from_yf(ticker: str, start_date: Optional[str]):
    try:
        yf_ticker = clean_for_yahoo(ticker)
        if start_date:
            start = (pd.to_datetime(start_date) - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
            raw = yf.download(yf_ticker, start=start, interval="1d", progress=False, auto_adjust=False)
        else:
            raw = yf.download(yf_ticker, period="1y", interval="1d", progress=False, auto_adjust=False)

        if raw is None or raw.empty:
            return pd.DataFrame()

        df = raw.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        needed = ["date","open","high","low","close","volume"]
        if not all(n in df.columns for n in needed):
            return pd.DataFrame()
        df = df[["date","open","high","low","close","volume"]].copy()
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        return df
    except Exception:
        return pd.DataFrame()

def ensure_today_updated(ticker: str):
    last = max_date_in_db(ticker)
    df_new = fetch_latest_1d_from_yf(ticker, last)
    if df_new.empty:
        return
    if last:
        df_new = df_new[df_new["date"] > last]
    if not df_new.empty:
        upsert_rows(ticker, df_new)

def load_from_db(ticker: str, days: int = 365) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    since = (dt.date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    df = pd.read_sql_query("""
        SELECT date, open, high, low, close, volume
        FROM stock_data
        WHERE ticker=? AND date>=?
        ORDER BY date
    """, conn, params=(ticker, since))
    conn.close()
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    # price SMAs
    df["sma20"] = df["close"].rolling(20).mean()
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    # volume SMAs
    df["vol20"] = df["volume"].rolling(20).mean()
    df["vol50"] = df["volume"].rolling(50).mean()
    df["vol200"] = df["volume"].rolling(200).mean()
    df["inst_level"] = 1.8 * df["vol50"]
    df["bull_zone"] = df["vol50"] > df["vol20"]

    # dropna because SMA200 needs 200 rows to exist
    return df.dropna()

# ---------------- Sidebar / scanning ----------------
period = st.sidebar.selectbox("Chart Lookback", ["3mo","6mo","1y"], index=2)
days_lookup = {"3mo":90, "6mo":180, "1y":365}
days_lookback = days_lookup[period]

want_rescan = st.sidebar.button("🔁 Update today's bar for ALL stocks")

status = st.info(f"Scanning {len(tickers)} tickers...")
progress = st.progress(0)

bulls, bears = [], []
for i, t in enumerate(tickers, start=1):
    try:
        if want_rescan:
            ensure_today_updated(t)
        d = load_from_db(t, days_lookback)
        if not d.empty:
            (bulls if d["bull_zone"].iloc[-1] else bears).append(t)
    except Exception:
        pass
    progress.progress(i / len(tickers))

progress.empty(); status.empty()

st.sidebar.markdown(f"### 🟢 Bull Zone ({len(bulls)})")
bull_sel = st.sidebar.selectbox("Select Bull Stock", [""] + bulls)
st.sidebar.markdown(f"### 🔴 Bear Zone ({len(bears)})")
bear_sel = st.sidebar.selectbox("Select Bear Stock", [""] + bears)

search_sel = st.selectbox("🔍 Search or Type Ticker", [""] + tickers)
choice = bull_sel or bear_sel or search_sel
if not choice:
    st.info("Select a stock to view details."); st.stop()

# Ensure DB up-to-date for selected ticker
ensure_today_updated(choice)
df = load_from_db(choice, days=days_lookback)
if df.empty:
    st.error(f"No data found for {choice}"); st.stop()

st.markdown(f"## {choice} — {'🟢 BULL ZONE' if df['bull_zone'].iloc[-1] else '🔴 BEAR ZONE'}")

# ---------------- Chart controls above the chart ----------------
#st.markdown("### 🔍 Chart Controls (candle width, minor height)")
col1, col2 = st.columns([1,1])
with col1:
    candle_width = st.slider("Candle width", 0.4, 1.2, 0.8, step=0.05)
with col2:
    chart_height_mult = st.slider("Chart height multiplier (visual)", 0.8, 4.0, 1.0, step=0.1)

# ---------------- Prepare data for plotting ----------------
df_mpf = df[["open","high","low","close","volume"]].copy()
df_mpf.index.name = "Date"

# Manual volume bar colors (green if close>=open)
vol_bar_colors = ["green" if df["close"].iloc[i] >= df["open"].iloc[i] else "red" for i in range(len(df))]

# ----- Corrected fill_between configuration (use .values) -----
fill_cfg = [
    dict(
        panel=0,
        y1=df["sma20"].values,
        y2=df["sma50"].values,
        where=(df["sma20"].values >= df["sma50"].values),
        color="green",
        alpha=0.12,
    ),
    dict(
        panel=0,
        y1=df["sma20"].values,
        y2=df["sma50"].values,
        where=(df["sma20"].values < df["sma50"].values),
        color="red",
        alpha=0.12,
    ),
    dict(
        panel=1,
        y1=df["vol20"].values,
        y2=df["vol50"].values,
        where=(df["vol20"].values >= df["vol50"].values),
        color="green",
        alpha=0.15,
    ),
    dict(
        panel=1,
        y1=df["vol20"].values,
        y2=df["vol50"].values,
        where=(df["vol20"].values < df["vol50"].values),
        color="red",
        alpha=0.15,
    ),
]

# price SMAs and volume SMAs & inst line as addplots
apds = [
    mpf.make_addplot(df["sma20"], panel=0, color="blue", width=1.2),
    mpf.make_addplot(df["sma50"], panel=0, color="red", width=1.2),
    mpf.make_addplot(df["sma200"], panel=0, color="green", width=1.4),

    mpf.make_addplot(df["vol20"], panel=1, color="blue", width=1.0),
    mpf.make_addplot(df["vol50"], panel=1, color="red", width=1.0),
    mpf.make_addplot(df["vol200"], panel=1, color="green", width=1.0),
    mpf.make_addplot(df["inst_level"], panel=1, color="lime", linestyle="--", width=1.0),
]

# Manual colored volume bars as an addplot (type='bar')
vol_bar_ap = mpf.make_addplot(df["volume"], type="bar", panel=1, color=vol_bar_colors, alpha=0.6)

apds_final = [vol_bar_ap] + apds

# style and market colors
mc = make_marketcolors(up="green", down="red", inherit=True)
style = make_mpf_style(marketcolors=mc, base_mpl_style="classic")

# ---------------- Scrollable wide chart config ----------------
fig_width_inches = 14
fig_height_inches = 6 * chart_height_mult

fig, axes = mpf.plot(
    df_mpf,
    type="candle",
    style=style,
    addplot=apds_final,
    fill_between=fill_cfg,
    volume=False,
    panel_ratios=(4,4),           # kept as your value
    figsize=(fig_width_inches, fig_height_inches),
    returnfig=True,
    tight_layout=True,
    update_width_config=dict(candle_linewidth=0.8, candle_width=candle_width)
)

# Export to PNG (use 200 DPI as requested) and show via st.image inside scroll container
png_buf = io.BytesIO()
fig.savefig(png_buf, format="png", dpi=350, bbox_inches="tight")
png_buf.seek(0)

# Legend handles
legend_handles = [
    Line2D([0], [0], color="blue", lw=2),
    Line2D([0], [0], color="red", lw=2),
    Line2D([0], [0], color="green", lw=2),
    Line2D([0], [0], color="lime", lw=2, linestyle="--"),
]
legend_labels = ["SMA20", "SMA50", "SMA200", "1.8× Institutional"]

# ---------------- Scrollable container CSS & render (PNG) ----------------
st.markdown("""
<style>
.scroll-x {
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
    padding-bottom: 8px;
}
.scroll-x img {
    max-width: none !important;
    height: auto;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="scroll-x">', unsafe_allow_html=True)
st.image(png_buf, width="content", caption=f"{choice} — Price + Volume")
st.markdown('</div>', unsafe_allow_html=True)

# show legend below PNG separately (matplotlib legend not needed because image includes it visually)
st.markdown('<div style="text-align:center; margin-top:6px;">', unsafe_allow_html=True)
for h, lab in zip(legend_handles, legend_labels):
    # small inline legend
    st.markdown(f"<span style='display:inline-block; margin:0 12px;'><svg width='18' height='8'><rect width='18' height='8' style='fill:{'blue' if lab=='SMA20' else 'red' if lab=='SMA50' else 'green' if lab=='SMA200' else 'lime'};'/></svg> {lab}</span>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Standalone Volume Chart (matplotlib) ----------------
st.markdown("### 📊 Standalone Volume Chart")
fig2, ax2 = plt.subplots(figsize=(16, 5))

bar_colors = ["green" if df["close"].iloc[i] >= df["open"].iloc[i] else "red" for i in range(len(df))]
ax2.bar(df.index, df["volume"], color=bar_colors, alpha=0.6)
ax2.plot(df.index, df["vol20"], color="blue", linewidth=2)
ax2.plot(df.index, df["vol50"], color="red", linewidth=2)
ax2.plot(df.index, df["vol200"], color="green", linewidth=2)
ax2.plot(df.index, df["inst_level"], color="lime", linestyle="--", linewidth=1.4)

green_zone = df["vol20"] > df["vol50"]
ax2.fill_between(df.index, df["vol20"], df["vol50"], where=green_zone, color="green", alpha=0.15)
ax2.fill_between(df.index, df["vol20"], df["vol50"], where=~green_zone, color="red", alpha=0.15)

ax2.grid(alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
plt.setp(ax2.get_xticklabels(), rotation=25)
ax2.legend(["Volume", "SMA20 Vol", "SMA50 Vol", "SMA200 Vol", "1.8× Institutional"], loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=5, frameon=False)

st.pyplot(fig2, use_container_width=True)

# ---------------- Indicators (last 5 days) ----------------
st.markdown("### 🧮 Indicators (Last 5 Days)")

def compute_indicators(df):
    df = df.copy()
    df["RSI (14)"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()

    macd = ta.trend.MACD(df["close"])
    df["MACD"] = macd.macd()
    df["MACD Signal"] = macd.macd_signal()
    df["MACD Hist"] = macd.macd_diff()

    df["CCI (20)"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], 20).cci()

    stoch = ta.momentum.StochasticOscillator(df["high"], df["low"], df["close"])
    df["Stoch %K"] = stoch.stoch()
    df["Stoch %D"] = stoch.stoch_signal()

    bb = ta.volatility.BollingerBands(df["close"], 20, 2)
    df["BB High"] = bb.bollinger_hband()
    df["BB Low"] = bb.bollinger_lband()

    df["Pivot"] = (df["high"] + df["low"] + df["close"]) / 3
    df["R1"] = 2 * df["Pivot"] - df["low"]
    df["S1"] = 2 * df["Pivot"] - df["high"]

    df["ATR (14)"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    df["ADX (14)"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()

    return df.tail(5).reset_index()

st.dataframe(compute_indicators(df).round(2), use_container_width=True)

# ---------------- Recent Volume Summary ----------------
st.markdown("### 🔎 Recent Volume Summary (Last 5 Days)")
summary = df[["volume","vol20","vol50","vol200","inst_level"]].tail(5)
summary = summary.rename(columns={
    "volume":"Volume",
    "vol20":"SMA20 Volume",
    "vol50":"SMA50 Volume",
    "vol200":"SMA200 Volume",
    "inst_level":"1.8× Institutional"
})
st.dataframe(summary.applymap(lambda x: f"{x/1e6:.2f}M"), use_container_width=True)
