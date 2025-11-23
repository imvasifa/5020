import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from pathlib import Path
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# ======================================================
#  CREATE usastocks.txt IF MISSING
# ======================================================
default_tickers = [
    "AAPL","MSFT","GOOGL","AMZN","TSLA","META","NVDA","NFLX","INTC","AMD",
    "ADBE","CSCO","AVGO","CRM","ORCL","PYPL","PEP","KO","WMT","DIS",
    "PFE","JNJ","V","MA","BAC","C","GS","MS","JPM","WFC",
    "T","VZ","XOM","CVX","COP","BA","GE","CAT","NKE","HD",
    "COST","MCD","IBM","AMAT","QCOM","TXN","LLY","MRK","UNH","ABBV"
]
path = Path("usastocks.txt")
if not path.exists():
    path.write_text("\n".join(default_tickers))
tickers = [t.strip().upper() for t in path.read_text().splitlines() if t.strip()]

# ======================================================
#  STREAMLIT PAGE CONFIG
# ======================================================
st.set_page_config(layout="wide", page_title="USA Volume Cross Viewer", page_icon="📈")

# ======================================================
#  SIDEBAR TITLE + SETTINGS
# ======================================================
with st.sidebar:
    st.markdown("<h5 style='text-align:center;color:gray;'>📊 USA Volume Cross (50 > 20) – Smart Viewer</h5>", unsafe_allow_html=True)
    st.markdown("---")
    st.header("⚙️ Settings")
    period = st.selectbox("Select Period", ["3mo","6mo","1y"], index=1)
    interval = st.selectbox("Select Interval", ["1d","1h","5m"], index=0)
    st.markdown("---")

# ======================================================
#  FETCH FUNCTION (CACHED)
# ======================================================
@st.cache_data(show_spinner=False)
def get_data(ticker, period, interval):
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if df.empty:
        return pd.DataFrame()
    df["vol"] = df["Volume"]
    df["vol20"] = df["vol"].rolling(20).mean()
    df["vol50"] = df["vol"].rolling(50).mean()
    df["inst_level"] = 1.8 * df["vol50"]
    df["bull_zone"] = df["vol50"] > df["vol20"]
    return df

# ======================================================
#  BUILD BULL/BEAR LISTS
# ======================================================
bulls, bears = [], []
for t in tickers:
    d = get_data(t, period, interval)
    if not d.empty:
        (bulls if d["bull_zone"].iloc[-1] else bears).append(t)

# ======================================================
#  CALLBACKS TO REMEMBER LAST ACTION
# ======================================================
def on_bull_change():
    st.session_state.last_action = "bull"
def on_bear_change():
    st.session_state.last_action = "bear"
def on_search_change():
    st.session_state.last_action = "search"

if "last_action" not in st.session_state:
    st.session_state.last_action = None
if "last_symbol" not in st.session_state:
    st.session_state.last_symbol = ""

# ======================================================
#  SIDEBAR LISTS
# ======================================================
with st.sidebar:
    st.markdown("### 🟢 Bull Zone (Gainers)")
    bull_sel = st.selectbox("Select Bull Stock", [""] + bulls, index=0, key="bull", on_change=on_bull_change)
    st.markdown("### 🔴 Bear Zone (Losers)")
    bear_sel = st.selectbox("Select Bear Stock", [""] + bears, index=0, key="bear", on_change=on_bear_change)

# ======================================================
#  MAIN SEARCH BOX
# ======================================================
st.subheader("🔍 Search or Select a Stock")
search_sel = st.selectbox(
    "Type or choose a ticker",
    [""] + tickers,
    index=0,
    key="search",
    on_change=on_search_change,
    help="Start typing (AAPL, TSLA, NVDA …)"
)

# ======================================================
#  DETERMINE WHICH STOCK TO SHOW
# ======================================================
choice = ""
if st.session_state.last_action == "bull" and bull_sel:
    choice = bull_sel
elif st.session_state.last_action == "bear" and bear_sel:
    choice = bear_sel
elif st.session_state.last_action == "search" and search_sel:
    choice = search_sel

# fallback to previous visible chart
if not choice and st.session_state.last_symbol:
    choice = st.session_state.last_symbol
if choice:
    st.session_state.last_symbol = choice

# ======================================================
#  DISPLAY CHART
# ======================================================
if not choice:
    st.info("👈 Select a stock from sidebar or search box to view its chart.")
else:
    df = get_data(choice, period, interval)
    if df.empty:
        st.error(f"No data found for {choice}")
    else:
        bullish = df["bull_zone"].iloc[-1]
        zone_text = "🟩 **BULL ZONE**" if bullish else "🟥 **BEAR ZONE**"
        st.markdown(f"### {choice} – Volume Cross (50 > 20) | {zone_text}")

        fig, ax = plt.subplots(figsize=(13,6))
        ax.bar(df.index, df["vol"], color="#2962FF", alpha=0.5)
        ax.plot(df.index, df["vol20"], color="#FFFF00", linewidth=2, label="20 SMA Vol")
        ax.plot(df.index, df["vol50"], color="#FF0000", linewidth=2, label="50 SMA Vol")
        ax.plot(df.index, df["inst_level"], color="#00FF00", linestyle="--", linewidth=1.2, label="1.8× Institutional")
        ax.fill_between(df.index, df["vol20"], df["vol50"], where=df["bull_zone"], color="green", alpha=0.25, label="Bull Zone")
        ax.fill_between(df.index, df["vol20"], df["vol50"], where=~df["bull_zone"], color="red", alpha=0.25, label="Bear Zone")

        zone_color = "green" if bullish else "red"
        ax.text(0.98, 0.98, "BULL ZONE" if bullish else "BEAR ZONE",
                transform=ax.transAxes, fontsize=13, fontweight="bold",
                color="white", ha="right", va="top",
                bbox=dict(facecolor=zone_color, edgecolor="none", boxstyle="round,pad=0.4"))

        ax.legend(); ax.grid(alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)

        st.markdown("#### 🔎 Recent Volume Summary")
        st.dataframe(
            df[["vol","vol20","vol50","inst_level"]].tail(5).rename(
                columns={
                    "vol":"Volume","vol20":"SMA20 Volume",
                    "vol50":"SMA50 Volume","inst_level":"1.8× Institutional"
                }),
            width="stretch"
        )
