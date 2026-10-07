"""Tests for backtest status: trades in summary numbers out"""

import pandas as pd

from src.backtest.stats import breakdown, session_for_hour, summarize


def _trades(r_values, outcomes=None, hours=None, trends=None):
    n = len(r_values)
    return pd.DataFrame(
        {
            "r_multiple": r_values,
            "outcome": outcomes or ["win" if r > 0 else "loss" for r in r_values],
            "hour_utc": hours or [0] * n,
            "trend": trends or ["up"] * n,
        }
    )


def test_summary_counts_and_win_rate():
    """2 wins at +1.99R, 2 losses at -1.01R -> 50% win rate, +1.96R total"""
    stats = summarize(_trades([1.99, -1.01, 1.99, -1.01]))

    assert stats["trades"] == 4
    assert stats["wins"] == 2
    assert stats["losses"] == 2
    assert stats["win_rate"] == 0.5
    assert stats["total_r"] == 1.96
    assert stats["avg_r"] == 0.49


def test_max_drawdown_measures_the_worst_dip():
    """Running total: 1.99, 0.98, -0.03, 1.96. Peak 1.99 -> low -0.03 = a 2.02R dip."""
    stats = summarize(_trades([1.99, -1.01, -1.01, 1.99]))
    assert stats["max_drawdown_r"] == -2.02


def test_open_trades_are_not_counted():
    """A trade that never hit stop or target isn't a real result yet."""
    trades = _trades([1.99, 0.5], outcomes=["win", "open"])
    stats = summarize(trades)

    assert stats["trades"] == 1
    assert stats["open_trades"] == 1


def test_empty_trades_do_not_crash():
    """No trades at all should give zeros and a low-sample warning, not an error."""
    stats = summarize(pd.DataFrame())

    assert stats["trades"] == 0
    assert stats["win_rate"] == 0.0
    assert stats["low_sample"] is True


def test_small_sample_is_flagged():
    """4 trades is far below MIN_TRADES_FOR_CONFIDENCE, so the result can't be trusted yet."""
    stats = summarize(_trades([1.99, -1.01, 1.99, -1.01]))
    assert stats["low_sample"] is True


def test_session_labels():
    """UTC hours map to the trading session that was open at the time."""
    assert session_for_hour(3) == "Asia"
    assert session_for_hour(8) == "London"
    assert session_for_hour(14) == "New York"
    assert session_for_hour(22) == "Off-hours"


def test_breakdown_by_trend():
    """Uptrend: 1 win, 1 loss (50%). Downtrend: 1 loss (0%)."""
    trades = _trades([1.99, -1.01, -1.01], trends=["up", "up", "down"])
    table = breakdown(trades, "trend").set_index("trend")

    assert table.loc["up", "trades"] == 2
    assert table.loc["up", "win_rate"] == 0.5
    assert table.loc["down", "win_rate"] == 0.0
