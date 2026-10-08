"""
explain_trade.py — explain ONE trade in plain English with the local AI.

Same split of jobs as summarize.py:
    - CODE pulls every fact from the trade row and formats it (prices, times,
      risk in dollars, how long the trade lasted).
    - The AI only turns those facts into a few friendly sentences.
If the AI isn't available, a plain explanation written by code is returned instead.
"""

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src import config

# How many minutes one candle covers, so "6 bars" can become "about 6 hours".
MINUTES_PER_CANDLE = {"15m": 15, "1h": 60, "4h": 240, "1d": 1440}

# What each outcome means, written by code so the AI can't get it wrong.
OUTCOME_MEANING = {
    "win": "hit the profit target",
    "loss": "hit the stop loss",
    "open": "was still open when the data ended, so it was closed at the last price",
}

TRADE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You explain a single backtested trade to a beginner in plain English.\n"
            "Rules:\n"
            "1. Use ONLY the facts provided. Never invent prices, times, or reasons.\n"
            "2. Say the direction, when it entered, the entry, stop, and target prices, "
            "how it ended, how long it lasted, and the result in R.\n"
            "3. Explain R once in simple words: R means the amount risked on the trade.\n"
            "4. Do not give advice or predict the future. This is past data.\n"
            "5. Write 3-5 short sentences. No bullet points.",
        ),
        (
            "human",
            "Trade facts:\n"
            "- Setup: {setup_name} on {symbol}, {timeframe} candles\n"
            "- Direction: {direction} ({direction_meaning})\n"
            "- Entered: {entry_time} UTC, during the {session} session, in an {trend} trend\n"
            "- Entry price: {entry}\n"
            "- Stop loss: {stop_price} (risk: {risk} per coin)\n"
            "- Profit target: {target}\n"
            "- How it ended: the trade {outcome_meaning}, at {exit_price}\n"
            "- How long it lasted: {bars_held} candles ({duration})\n"
            "- Result after fees: {r_multiple}",
        ),
    ]
)


def build_trade_inputs(trade: pd.Series, setup_name: str, symbol: str, timeframe: str) -> dict:
    """Turn one row of the trades table into ready-to-read facts for the prompt."""
    bars = int(trade["bars_held"])
    is_long = trade["direction"] == "long"
    return {
        "setup_name": setup_name,
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": trade["direction"],
        "direction_meaning": "a bet that price goes up" if is_long else "a bet that price goes down",
        "entry_time": pd.Timestamp(trade["entry_time"]).strftime("%b %d, %Y at %H:%M"),
        "session": trade["session"],
        "trend": trade["trend"],
        "entry": _price(trade["entry"]),
        "stop_price": _price(trade["stop"]),  # "stop" is reserved by LangChain
        "risk": _price(abs(trade["entry"] - trade["stop"])),
        "target": _price(trade["target"]),
        "outcome_meaning": OUTCOME_MEANING.get(trade["outcome"], trade["outcome"]),
        "exit_price": _price(trade["exit_price"]),
        "bars_held": bars,
        "duration": _duration(bars, timeframe),
        "r_multiple": f"{trade['r_multiple']:+.2f}R",
    }


def explain_trade(inputs: dict, llm=None) -> str:
    """Ask the local model to explain the trade. Falls back to plain text if it can't."""
    if llm is None:
        llm = ChatOllama(model=config.OLLAMA_MODEL, temperature=config.OLLAMA_TEMPERATURE)

    chain = TRADE_PROMPT | llm
    try:
        return chain.invoke(inputs).content.strip()
    except Exception:
        # Ollama not running, model missing, etc.: explain it with code instead.
        return _fallback_explanation(inputs)


def _fallback_explanation(inputs: dict) -> str:
    """A plain, code-written explanation used when the AI is unavailable."""
    return (
        f"(AI unavailable; showing the basic facts.) This {inputs['direction']} trade "
        f"entered at {inputs['entry']} on {inputs['entry_time']} UTC, with a stop at "
        f"{inputs['stop_price']} and a target at {inputs['target']}. The trade "
        f"{inputs['outcome_meaning']}, at {inputs['exit_price']}, after "
        f"{inputs['bars_held']} candles ({inputs['duration']}), for {inputs['r_multiple']}."
    )


def _price(value: float) -> str:
    """61240.5 -> '$61,240.50'"""
    return f"${value:,.2f}"


def _duration(bars: int, timeframe: str) -> str:
    """6 bars of 1h -> 'about 6 hours'. Unknown timeframe -> 'length unknown'."""
    minutes = bars * MINUTES_PER_CANDLE.get(timeframe, 0)
    if minutes == 0:
        return "length unknown"
    if minutes < 60:
        return f"about {minutes} minutes"
    if minutes < 48 * 60:
        hours = round(minutes / 60)
        return f"about {hours} hour" + ("s" if hours != 1 else "")
    days = round(minutes / 1440)
    return f"about {days} days"
