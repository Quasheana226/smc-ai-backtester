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


def test_summarize_headline_numbers():
    """Two wins and two losses: the counts, win rate, and R totals.

    1.99 / -1.01 are the real after-fee results of a 2R win and a 1R loss,
    so these numbers match what simulate_trades actually produces.
    """
    summary = summarize(_trades([1.99, -1.01, -1.01, 1.99]))

    assert summary["trades"] == 4
    assert summary["wins"] == 2
    assert summary["losses"] == 2
    assert summary["win_rate"] == 0.5
    assert summary["total_r"] == 1.96
    assert summary["avg_r"] == 0.49
    assert summary["breakeven_win_rate"] == 0.333

    # low_sample guards the headline: on at the default 30-trade threshold,
    # off once there are enough trades to mean anything.
    assert summary["low_sample"] is True
    assert summarize(_trades([1.0] * 30))["low_sample"] is False


def test_max_drawdown_matches_worked_example():
    """The exact series from _max_drawdown's docstring: worst gap is -2.02."""
    summary = summarize(_trades([1.99, -1.01, -1.01, 1.99]))

    assert summary["max_drawdown_r"] == -2.02


def test_drawdown_counts_an_early_losing_streak():
    """Losing from the first trade is still a drawdown.

    Without clip(lower=0) the running peak would start at the first (negative)
    result, hiding the fact that the account is down 2.02R from where it began.
    """
    summary = summarize(_trades([-1.01, -1.01]))

    assert summary["max_drawdown_r"] == -2.02


def test_open_trades_are_counted_but_not_scored():
    """An unfinished trade is reported separately, never as a win or a zero."""
    trades = _trades([1.99, -1.01, 0.0], outcomes=["win", "loss", "open"])
    summary = summarize(trades)

    assert summary["open_trades"] == 1
    assert summary["trades"] == 2  # only the two closed trades are scored
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["total_r"] == 0.98  # the open trade's 0.0 is excluded


def test_empty_table_returns_zeros():
    """No trades at all returns zeros rather than crashing on missing columns."""
    summary = summarize(pd.DataFrame())

    assert summary["trades"] == 0
    assert summary["win_rate"] == 0.0
    assert summary["total_r"] == 0.0
    assert summary["max_drawdown_r"] == 0.0
    assert summary["low_sample"] is True
    assert summary["breakeven_win_rate"] == 0.333  # still known without trades


def test_breakdown_by_trend_scores_each_group():
    """One row per trend, each scored on its own trades."""
    trades = _trades(
        [1.99, -1.01, 1.99, 1.99],
        trends=["up", "up", "down", "down"],
    )
    table = breakdown(trades, "trend").set_index("trend")

    assert list(table.index) == ["down", "up"]
    assert table.loc["up", "trades"] == 2
    assert table.loc["up", "win_rate"] == 0.5
    assert table.loc["up", "avg_r"] == 0.49
    assert table.loc["down", "win_rate"] == 1.0
    assert table.loc["down", "avg_r"] == 1.99


def test_session_for_hour_maps_utc_hours():
    """Session boundaries, checked on both sides of each cutoff."""
    assert session_for_hour(0) == "Asia"
    assert session_for_hour(6) == "Asia"
    assert session_for_hour(7) == "London"
    assert session_for_hour(12) == "London"
    assert session_for_hour(13) == "New York"
    assert session_for_hour(20) == "New York"
    assert session_for_hour(21) == "Off-hours"
    assert session_for_hour(23) == "Off-hours"
