"""
summarize.py - turn backtest numbers into a plain-english summart with a local AI


The split of jobs:
- CODE does everything that must be exact: the math, the percentages,
and the decision about whether the sample is too small.
- The AI only does the writing: turning those facts into a short,
friendly paragraph.

WHY that split?
Small language models are good writers but unreliable at math, and they can
"hallucinate" (make up) numbers. So the AI never calculates anything. It gets
finished facts plus strict rules, and if the AI isn't available, the app falls
back to a plain summary written by code. The app never breaks because of it.
"""

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from src import config
from src.backtest.stats import breakdown

# The rules the AI must follow
PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You explain trading backtest results to beginners in plain English.\n"
            "Rules:\n"
            "1. Use ONLY the numbers provided. Never invent or estimate statistics.\n"
            "2. Always state how many trades the results are based on.\n"
            "3. If a sample-size warning is given, say it in your first sentence.\n"
            "4. Use the Verdict line to say whether the setup made or lost money. "
            "Never decide this yourself from the win rate.\n"
            "5. Never promise or predict future profits. This is past data, not advice.\n"
            "6. Write one short paragraph of 4-6 sentences. No bullet points.",
        ),
        (
            "human",
            "Setup: {setup_name} on {symbol}, {timeframe} candles, {start} to {end}.\n"
            "{sample_note}\n"
            "Results:\n"
            "- Closed trades: {trades}\n"
            "Verdict: {verdict}\n"
            "- Win rate: {win_rate} (breakeven before fees: {breakeven_win_rate})\n"
            "- Average result per trade: {avg_r}\n"
            "- Total result: {total_r}\n"
            "- Worst drawdown: {max_drawdown_r}\n"
            "Breakdowns:\n{breakdowns}",
        ),
    ]
)


def build_prompt_inputs(
    stats: dict,
    trades: pd.DataFrame,
    setup_name: str,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
) -> dict:
    """
    Turn the raw numbers into ready-to-read text for the prompt.

    Formatting happens HERE, in code, so the AI never has to do math
    (e.g. it receives "38.1%", not 0.381).
    """
    count = stats["trades"]

    # The code decides whether to warn. The AI only told to repeat it.
    if stats["low_sample"]:
        sample_note = (
            f"WARNING: only {count} closed trades. That is too few to trust; "
            "treat these results as a rough early look, not evidence"
        )
    else:
        sample_note = f"Sample size: {count} closed trades."

    # Profit is judged by the AVERAGE RESULT, not the win rate. The breakeven
    # win rate assumes exactly +2R wins and -1R losses, but fees shrink wins and
    # grow losses, so a win rate above breakeven can still lose money.
    avg = stats["avg_r"]
    if avg > 0:
        verdict = f"made money overall (average {_r(avg)} per trade after fees)."
    elif avg < 0:
        verdict = f"LOST money overall (average {_r(avg)} per trade after fees)."
    else:
        verdict = "broke even (average 0R per trade after fees)."

    return {
        "setup_name": setup_name,
        "symbol": symbol,
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "sample_note": sample_note,
        "verdict": verdict,
        "trades": count,
        "win_rate": _pct(stats["win_rate"]),
        "breakeven_win_rate": _pct(stats["breakeven_win_rate"]),
        "avg_r": _r(stats["avg_r"]),
        "total_r": _r(stats["total_r"]),
        "max_drawdown_r": _r(stats["max_drawdown_r"]),
        "breakdowns": _breakdown_text(trades),
    }


def summarize(inputs: dict, llm=None) -> str:
    """
    Ask the local model to write the summary. Returns plain text.

    `llm` can be swapped out (tests pass in a fake one). If it's left as None,
    we connect to the Ollama model named in config.
    """
    # Nothing to explain, so don't spend time asking the AI.
    if inputs["trades"] == 0:
        return (
            "No closed trades were found for this setup and date range, so there is nothing to summarize yet."
        )

    if llm is None:
        llm = ChatOllama(model=config.OLLAMA_MODEL, temperature=config.OLLAMA_TEMPERATURE)

    chain = PROMPT | llm  # The "|" pipes the filled-in prompt into the model.
    try:
        reply = chain.invoke(inputs)
        return reply.content.strip()
    except Exception:
        # Ollama not running, model not downloaded, etc. The app should still
        # work, so fall back to a summary written entirely by code.
        return _fallback_summary(inputs)


def _fallback_summary(inputs: dict) -> str:
    """A plain, code-written summary used when the AI is unavailable."""
    return (
        f"(AI summary unavailable; showing the basic numbers.) {inputs['sample_note']} "
        f"The setup {inputs['verdict']} "
        f"Win rate was {inputs['win_rate']} against a breakeven of {inputs['breakeven_win_rate']}, "
        f"averaging {inputs['avg_r']} per trade ({inputs['total_r']} total). "
        f"The worst drawdown was {inputs['max_drawdown_r']}."
    )


def _breakdown_text(trades: pd.DataFrame) -> str:
    """One line per group, e.g. 'London: 12 trades, 41.7% win rate, +0.15R avg'."""
    lines = []
    for column in ["direction", "trend", "session"]:
        # Skip columns that don't exist (e.g. an empty trades table has none).
        if column not in trades.columns:
            continue
        for _, row in breakdown(trades, column).iterrows():
            lines.append(
                f"- {column} {row[column]}: {int(row['trades'])} trades, "
                f"{_pct(row['win_rate'])} win rate, {_r(row['avg_r'])} avg"
            )
    return "\n".join(lines) if lines else "- none"


def _pct(value: float) -> str:
    """0.381 -> '38.1%'"""
    return f"{value * 100:.1f}%"


def _r(value: float) -> str:
    """0.124 -> '+0.12R', -2.02 -> '-2.02R'"""
    return f"{value:+.2f}R"
