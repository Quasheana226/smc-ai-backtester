""" app.py the streamlit screen this file only handles the 
screen: inputs, buttons, charts, and text
"""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config
from src.backtest.stats import breakdown
from src.data.fetch import fetch_candles
from src.llm.summarize import build_prompt_inputs, summarize
from src.pipeline import SETUPS, run_backtest

# Page setup

st.set_page_config(page_title="SMC Strategy Backtester", page_icon="📊", layout="wide")

st.title("SMC Strategy Backtester")
st.caption(
    "Rule-based Smart Money Concepts setups, tested on real price history "
    "and explained by a local AI. Past results are not a promise of future returns."
)


# Cached helpers so re-runs dont redo slow work
@st.cache_data(show_spinner=False)
def load_candles(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    """Steamlit hands back saved results instantly"""
    return fetch_candles(symbol, timeframe, start, end)


@st.cache_data(show_spinner=False)
def ai_summary(inputs: dict) -> str:
    """AI only runs again when the numbers change"""
    return summarize(inputs)



#  Sidebar inputs 
with st.sidebar:
    st.header("Settings")
    symbol = st.text_input("Trading pair", value="BTCUSDT").upper().strip()
    timeframe = st.selectbox(
        "Candle size", config.SUPPORTED_TIMEFRAMES, index=config.SUPPORTED_TIMEFRAMES.index("1h")
    )
    setup_name = st.selectbox("Setup to test", list(SETUPS))
    # format= controls how the date is shown; max_value blocks future dates.
    start = st.date_input(
        "Start date",
        value=date.today() - timedelta(days=365),
        max_value=date.today(),
        format="MM/DD/YYYY",
    )
    end = st.date_input("End date", value=date.today(), max_value=date.today(), format="MM/DD/YYYY")
    run_clicked = st.button("Run backtest", type="primary", width="stretch")
    
if start >= end:
    st.error("The start date must be before the end date.")
    st.stop()  # Stop drawing the rest of the page.


# Run the backtest only when the button is clicked

if run_clicked:
    # One progress box that reports each step, instead of separate spinners.
    with st.status("Running backtest...", expanded=True) as status:
        st.write(f"Downloading {symbol} {timeframe} candles...")
        try:
            candles = load_candles(symbol, timeframe, start.isoformat(), end.isoformat())
        except Exception as error:  # Bad symbol, no internet, API down, etc.
            status.update(label="Download failed", state="error")
            st.error(f"Couldn't download candles for {symbol}: {error}")
            st.stop()

        if candles.empty:
            status.update(label="No data", state="error")
            st.warning("No candles came back for those dates. Try a different range or pair.")
            st.stop()

        st.write(f"Finding {setup_name} setups and simulating trades...")
        signals, trades, stats = run_backtest(candles, setup_name)

        st.write("Asking the local AI to explain the results...")
        label = (setup_name, symbol, timeframe, start.isoformat(), end.isoformat())
        summary = ai_summary(build_prompt_inputs(stats, trades, *label))

        status.update(label="Backtest complete", state="complete", expanded=False)

    # Save everything, so later clicks (like opening a table) don't wipe the results.
    st.session_state["results"] = {
        "signals": signals,
        "trades": trades,
        "stats": stats,
        "summary": summary,
        "label": label,
    }

if "results" not in st.session_state:
    st.info("Pick your settings in the sidebar, then click **Run backtest**.")
    st.stop()

results = st.session_state["results"]
signals, trades, stats = results["signals"], results["trades"], results["stats"]
setup_label, symbol_label, timeframe_label, start_label, end_label = results["label"]



# Headline numbers 

st.subheader(f"{setup_label} on {symbol_label} · {timeframe_label} · {start_label} to {end_label}")

if stats["low_sample"]:
    st.warning(
        f"Only {stats['trades']} closed trades. That's under "
        f"{config.MIN_TRADES_FOR_CONFIDENCE}, so treat these results as a rough early look."
    )

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Closed trades", stats["trades"])
col2.metric(
    "Win rate",
    f"{stats['win_rate']:.1%}",
    help=f"Breakeven before fees at this target: {stats['breakeven_win_rate']:.1%}",
)
col3.metric("Avg result", f"{stats['avg_r']:+.2f}R", help="Average result per trade, after fees.")
col4.metric("Total result", f"{stats['total_r']:+.1f}R")
col5.metric("Worst drawdown", f"{stats['max_drawdown_r']:.1f}R")


# ---------------------------------------------------------------------------
# 6. Price chart with trade entries
# ---------------------------------------------------------------------------
fig = go.Figure(
    go.Candlestick(
        x=signals["open_time"],
        open=signals["open"],
        high=signals["high"],
        low=signals["low"],
        close=signals["close"],
        name="Price",
    )
)

# One marker per trade at its entry price: green = win, red = loss, gray = still open.
if not trades.empty:
    for outcome, color in [("win", "#22c55e"), ("loss", "#ef4444"), ("open", "#9ca3af")]:
        group = trades[trades["outcome"] == outcome]
        fig.add_trace(
            go.Scatter(
                x=group["entry_time"],
                y=group["entry"],
                mode="markers",
                name=outcome,
                marker={"size": 9, "color": color, "line": {"width": 1, "color": "white"}},
            )
        )

fig.update_layout(
    template="plotly_dark",
    height=520,
    xaxis_rangeslider_visible=False,
    margin={"l": 10, "r": 10, "t": 30, "b": 10},
    legend={"orientation": "h", "y": 1.05},
)
st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------------
# 7. AI summary + breakdowns, side by side
# ---------------------------------------------------------------------------
left, right = st.columns([3, 2])

with left:
    st.subheader("AI summary")
    st.write(results["summary"])

with right:
    st.subheader("Breakdowns")
    if trades.empty:
        st.caption("No trades to break down.")
    else:
        for column in ["session", "trend", "direction"]:
            st.caption(f"By {column}")
            st.dataframe(breakdown(trades, column), hide_index=True, width="stretch")


# ---------------------------------------------------------------------------
# 8. Every trade, for anyone who wants to check the details
# ---------------------------------------------------------------------------
with st.expander(f"All trades ({len(trades)})"):
    st.dataframe(trades, hide_index=True, width="stretch")
