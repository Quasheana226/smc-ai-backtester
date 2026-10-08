"""
stats.py turna table of trades into a summary of numbers
Most fields are self-describing (trades, wins, losses, win_rate, avg_r,
total_r). The two that aren't:
max_drawdown_r    worst peak-to-trough drop in cumulative R
breakeven_win_rate  win rate needed to break even at RR_TARGET, after fees

Only CLOSED trades are scored. A trade still open when the data ran out isn't
a result yet, so it's reported separately rather than counted as a zero.

WHY low_sample is a field and not a note in the UI: a 70% win rate on 12
trades means almost nothing. Putting the warning inside the numbers means
neither the UI nor the LLM summary can forget to mention it.
"""

import pandas as pd

from src import config


def summarize(trades: pd.DataFrame, rr_target: float = config.RR_TARGET) -> dict:
    """Return one dict of headline numbers for a table of trades."""
    # Breakeven win rate: with a 2R target, 1 win (+2) pays for 2 losses (-1, -1),
    # so you need to win 1 out of every 3 trades = 1 / (1 + 2) = 33.3%.
    breakeven = round(1 / (1 + rr_target), 3)

    # No trades at all (empty table has no columns), so return zeros instead of crashing.
    if trades.empty:
        return _empty_summary(breakeven)

    closed = trades[trades["outcome"] != "open"]
    open_count = len(trades) - len(closed)
    if closed.empty:
        return _empty_summary(breakeven, open_count)

    r = closed["r_multiple"]
    wins = int((closed["outcome"] == "win").sum())
    count = len(closed)

    # float() turns pandas' numpy numbers into plain Python numbers, which print
    # cleanly and can be sent to the AI summary as JSON later.
    return {
        "trades": count,
        "wins": wins,
        "losses": count - wins,
        "open_trades": open_count,
        "win_rate": round(wins / count, 3),
        "avg_r": float(round(r.mean(), 3)),
        "total_r": float(round(r.sum(), 3)),
        "max_drawdown_r": _max_drawdown(r),
        "breakeven_win_rate": breakeven,
        "low_sample": count < config.MIN_TRADES_FOR_CONFIDENCE,
    }


def breakdown(trades: pd.DataFrame, by: str) -> pd.DataFrame:
    """
    Group closed trades by one column (e.g. "trend" or "session") and score each group.

    Returns one row per group with: trades, win_rate, avg_r.
    """
    closed = trades[trades["outcome"] != "open"]

    # Add a True/False column so "win rate" becomes a simple average (True = 1, False = 0).
    closed = closed.assign(is_win=closed["outcome"] == "win")

    table = closed.groupby(by).agg(
        trades=("r_multiple", "size"),
        win_rate=("is_win", "mean"),
        avg_r=("r_multiple", "mean"),
    )
    return table.round(3).reset_index()


def session_for_hour(hour: int) -> str:
    """Map a UTC hour (0-23) to the main trading session open at that time."""
    if hour < 7:
        return "Asia"
    if hour < 13:
        return "London"
    if hour < 21:
        return "New York"
    return "Off-hours"


def _max_drawdown(r: pd.Series) -> float:
    """
    Worst drop from a running high, in R.

    Example: results +1.99, -1.01, -1.01, +1.99
        running total : 1.99, 0.98, -0.03, 1.96
        running peak  : 1.99, 1.99,  1.99, 1.99
        gap           : 0.00, -1.01, -2.02, -0.03  -> worst = -2.02
    """
    equity = r.cumsum()  # running total after each trade
    # Highest point so far. clip(lower=0) treats the starting balance (0R) as a peak,
    # so losing the very first trades still counts as a drawdown.
    peak = equity.cummax().clip(lower=0)
    return float(round((equity - peak).min(), 3))


def _empty_summary(breakeven: float, open_count: int = 0) -> dict:
    """Zeros for every number, flagged as low sample."""
    return {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "open_trades": open_count,
        "win_rate": 0.0,
        "avg_r": 0.0,
        "total_r": 0.0,
        "max_drawdown_r": 0.0,
        "breakeven_win_rate": breakeven,
        "low_sample": True,
    }
