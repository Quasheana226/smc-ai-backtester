"""run_demo.py - run the full pipeline on real candles and print the results.

Usage (from the project root):
    uv run python -m scripts.run_demo
"""

from src import config
from src.data.fetch import fetch_candles
from src.llm.summarize import build_prompt_inputs, summarize
from src.pipeline import run_backtest

# --- Settings: change these to test a different market or period ---
SYMBOL = "BTCUSDT"  # Trading pair as Binance.US names it.
TIMEFRAME = "1h"  # Candle size; one of config.SUPPORTED_TIMEFRAMES.
SETUP = "Liquidity Sweep"  # A key from src.pipeline.SETUPS.
START = "2025-01-01"  # First day of data (inclusive).
END = "2026-10-01"  # Last day of data.


def main() -> None:
    """Fetch candles, backtest SETUP, and print stats, a fee check, and the AI summary."""
    # Download (or load from cache) the candles, then run the backtest.
    candles = fetch_candles(SYMBOL, TIMEFRAME, START, END)
    _, trades, stats = run_backtest(candles, SETUP)

    # The headline numbers.
    print(stats)
    print()

    # Fee check: shows how much fees cost each trade, in R. Open trades are
    # skipped because they haven't finished, so their result isn't final.
    if not trades.empty:
        closed = trades[trades["outcome"] != "open"]
        print("Average r_multiple by outcome:")
        print(closed.groupby("outcome")["r_multiple"].mean())
        fee_r = config.FEE_PCT * closed["entry"] / (closed["entry"] - closed["stop"]).abs()
        print(f"Average fee per closed trade: {fee_r.mean():.3f}R")
        print()

    # Turn the numbers into prompt text, then let the local AI write the summary.
    inputs = build_prompt_inputs(stats, trades, SETUP, SYMBOL, TIMEFRAME, START, END)
    print(summarize(inputs))


# This guard means main() only runs when the file is executed directly
# (python -m scripts.run_demo), not when another file imports it. Without it,
# a simple import would start a network download and an AI call.
if __name__ == "__main__":
    main()
