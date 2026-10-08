"""Tests for explaining one trade. None of these need Ollama running."""

import pandas as pd
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda

from src.llm.explain_trade import build_trade_inputs, explain_trade


def _trade(**changes):
    """One fake trade row: a long that hit its target after 6 one-hour candles."""
    row = {
        "entry_time": pd.Timestamp("2025-03-04 14:00", tz="UTC"),
        "direction": "long",
        "entry": 61240.0,
        "stop": 60880.0,
        "target": 61960.0,
        "exit_price": 61960.0,
        "outcome": "win",
        "r_multiple": 1.84,
        "bars_held": 6,
        "session": "New York",
        "trend": "up",
    }
    row.update(changes)
    return pd.Series(row)


def _inputs(**changes):
    return build_trade_inputs(_trade(**changes), "Liquidity Sweep", "BTCUSDT", "1h")


def test_facts_are_formatted_by_code():
    """Prices, risk, time, and R come out ready to read, so the AI does no math."""
    inputs = _inputs()

    assert inputs["entry"] == "$61,240.00"
    assert inputs["risk"] == "$360.00"  # 61,240 - 60,880
    assert inputs["entry_time"] == "Mar 04, 2025 at 14:00"
    assert inputs["r_multiple"] == "+1.84R"
    assert inputs["outcome_meaning"] == "hit the profit target"


def test_duration_uses_the_candle_size():
    """6 one-hour candles is about 6 hours; 6 four-hour candles is about 24 hours."""
    assert _inputs()["duration"] == "about 6 hours"
    four_hour = build_trade_inputs(_trade(), "Liquidity Sweep", "BTCUSDT", "4h")
    assert four_hour["duration"] == "about 24 hours"


def test_short_trades_are_described_as_betting_down():
    inputs = _inputs(direction="short", stop=61600.0)

    assert inputs["direction_meaning"] == "a bet that price goes down"
    assert inputs["risk"] == "$360.00"  # Distance is always positive.


def test_explanation_returns_the_model_reply():
    fake_llm = FakeListChatModel(responses=["This long trade hit its target."])
    assert explain_trade(_inputs(), llm=fake_llm) == "This long trade hit its target."


def test_falls_back_when_the_model_is_unavailable():
    """If Ollama is off, the user still gets a plain explanation."""

    def broken_model(_prompt):
        raise ConnectionError("Ollama is not running")

    text = explain_trade(_inputs(), llm=RunnableLambda(broken_model))

    assert text.startswith("(AI unavailable")
    assert "$61,240.00" in text
    assert "about 6 hours" in text
