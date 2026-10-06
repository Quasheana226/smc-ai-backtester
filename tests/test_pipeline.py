"""Test for the pipeline: candles in signal + trades + stats out"""

import pandas as pd
import pytest

from src import pipeline
from src.pipeline import SETUPS, run_backtest


def _fake_detector(df):
    df = df.copy()
    df["signal"] = 0 
    df["stop_price"] = float("nan")
    df.loc[0, ["signal", "stop_price"]] = [1, 9.0]
    return df

def test_both_setups_are_on_the_menu():
    assert set(SETUPS) == {"Liquidity Sweep", "Break of Structure"}
    
def test_pipeline_connects_every_step(make_candles, monkeypatch):
    
    monkeypatch.setattr(pipeline, "add_swings", lambda df: df)
    monkeypatch.setitem(pipeline.SETUPS, "Fake", _fake_detector)
    rows = [
        (10, 10, 9.5, 10), # <- fake signal 
        (10, 11, 9.5, 10.5 ), # <- enter at this open (10)
        (10.5, 12.5, 9.5 , 12), # <- high12.5 reaches the target (12)
        
    ]
    
    signals,  trades, stats = run_backtest(make_candles(rows), "Fake")
    
    
    assert "signal" in signals.columns
    assert len(trades) == 1
    assert trades.loc[0, "session"] == "Asia" # Signal candle opens at 00:00 UTC.
    assert stats["wins"] == 1 
    assert stats["total_r"] == 1.99
    
def test_real_setups_run_end_to_end(make_candles):
    """No fakes every real setup runs and return the right shapes """
    rows  = [
        
        (9, 10, 9, 9.5),
        (9.5, 12, 9.2, 11),
        (11, 11.5, 8.5, 10),
        (10, 10.5, 9.8, 10.4),
        (10.4, 13, 10.3, 12.5),
        (12.5, 13.5, 12, 13),
        
    ]

    for name in SETUPS:
        signals, trades, stats = run_backtest(make_candles(rows), name)

        assert isinstance(signals, pd.DataFrame)
        assert isinstance(trades, pd.DataFrame)
        assert "trades" in stats

def test_unknown_setup_gives_clear_error(make_candles):
    with pytest.raises(ValueError, match="Unknown setup"):
        run_backtest(make_candles([(10, 11, 9, 10)]), "Order Block")
