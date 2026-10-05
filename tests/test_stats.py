"""Tests for backtest stats: trades in, summary numbers out."""

import pandas as pd

from src.backtest.stats import breakdown, session_for_hour, summarize


def _trades(r_values, outcomes=None, hours=None, trends=None):
    """Build a trades frame with just the columns the stats functions read.

    Mirrors the schema simulate_trades produces, so these tests stay honest
    about the real column names without re-running a whole simulation.
    """
    # Outcome is redundant with the sign of R, so derive it unless a test
    # needs to pin an odd case (a break-even, a hand-labelled row).
    if outcomes is None:
        outcomes = ["win" if r > 0 else "loss" for r in r_values]
    if hours is None:
        hours = [0] * len(r_values)
    if trends is None:
        trends = ["up"] * len(r_values)

    return pd.DataFrame(
        {
            "r_multiple": r_values,
            "outcome": outcomes,
            "hour_utc": hours,
            "trend": trends,
        }
    )
