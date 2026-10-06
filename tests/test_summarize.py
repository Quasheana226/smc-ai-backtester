"""Test for the AI summary """

import pandas as pd 
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda

from src.backtest.stats import summarize as summarize_stats
from src.llm.summarize import build_promt_inputs, summarize


def _trades(r_values):
    n = len(r_values)
    return pd.DataFrame(
        {
            "r_multiple": r_values,
            "outcome": ["win" if r > 0 else "lose" for r in r_values],
            "direction": ["long"] * n,
            "trend": ["up"] * n,
            "session": ["London" * n],
        }
    )
def _inputs(r_values):
    trades = _trades(r_values)
    stats = summarize_stats(trades)
    return build_promt_inputs(
        stats, trades, "Liquidity Sweep", "BTCUSDT", "1h", "2024-01-01", "2024-06-01"
    )
    
def test_small_sample_gets_a_warning():
    """The AI gets '50.0%' and '+0.49R, never raw decimals it might misread """
    inputs = _inputs([1.99, -1.01, 1.99, -1.01])
    
    assert inputs["trades"] == 4
    assert inputs["win_rate"] == "50.0%"
    assert inputs["breakeven-win_rate"] == "33.3%"
    assert inputs["avg_r"] == "+0.49R"
    
def test_small_sample_gets_a_warning():
    """4 trades is low sample so the promt must carry a warning for the AI """
    inputs = _inputs([1.99, -1.01, 1.99, -1.01])
    assert inputs["sample_note"].startswith("WARNING")
    
def test_breakdowns_are_listed():
    inputs = _inputs([1.99, -1.01,])
    assert "session london: 2 trades, 50.0% win rate" in  inputs["breakdowns"]
    
def test_summary_returns_the_model_reply():
    """A fake model stands in for ollama, so this test runs in milliseconds"""
    fake_llm = FakeListChatModel(responses=["Across 4 trades, this setup won half the time."])
    text = summarize(_inputs([1.99, -1.01, 1.99, -1.01]), llm=fake_llm)
    assert text == "Across 4 trades, this setup won half the time"
    
    
def test_falls_back_when_the_model_is_unavilable():
    """IF ollama is off, the app still shows a summary instead of crashing. """
    
    def broken_model(_promt):
        raise ConnectionError("Ollama is not running")
    
    text = summarize(_inputs([1.99, -1.01]), llm=RunnableLambda(broken_model))
    
    assert text.startswith("(AI summary unavailable)"
    
                           
                           
                           
                           )
    
    
    
    