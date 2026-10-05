"""Test for trade simulation signals in trade out """

import pandas as pd 

from src.backtest.simulate import simulate_trades

def _signals(rows, signal_at=0, direction=1, stop=9.0):
    
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.insert(0, "open_time", pd.date_range("2024-01-01", periods=len(df), freq="h", tz="UTC"))
    df["signal"] = 0
    df["stop_price"] = float("nan")
    df.loc[signal_at, ["signal", "stop_price"]] = [direction, stop]
    return df 

def _signals(rows, signal_at=0, direction=1, stop=9.0):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.insert(0, "open_time", pd.date_range("2024-01-01", periods=len(df), freq="h", tz="UTC"))
    df["signal"] = 0
    df["stop_price"] = float("nan")
    df.loc[signal_at, ["signal", "stop_price"]] = [direction, stop]
    return df

"""AAA Arrange, ACT, Assert """
def test_long_hits_target():
    """Enter at 10 next open stop at 9 -> Risk 1, target 12 at 2R"""
    rows = [        # ARRANGE
        (10, 10, 9.5, 10), # <- signal candle 
        (10, 11, 9.5, 10.5), # <- enter at this open (10)
        (10.5, 12.5, 9.5, 12), # <- high 12.5 reaches the target (12) 
    ]
    trades = simulate_trades(_signals(rows))   # ACT
    
    assert len(trades) == 1
    assert trades.loc[0, "outcome"] == "win"
    assert trades.loc[0, "r_multiple"] == 1.99
    
    
def test_stop_wins_a_tie():
    """Candle touches both stop 9 and target 12 assume the wort """
    rows = [
        (10, 10, 9.5, 10),
        (10, 10.5, 9.5, 10),
        (10, 12.5, 8.5, 11), # <- LOW 8.5 hits stop and high 12.5 hits target 
        
    ]
    trades = simulate_trades(_signals(rows))
    assert trades.loc[0, "outcome"] == "loss"
    
def test_short_hits_stop():
    """Mirror image short entery at 10 stop 11 risks 1 price rises to 11.5"""
    rows =  [
        (10, 10.5, 9.5, 10),
        (10, 10.5, 9.5, 10), # <- enter short at 10 
        (10, 11.5, 9.8, 11), # <- high 11.5 hits the stop (11)
        
        
        
    ]   
    trades = simulate_trades(_signals(rows, direction=-1, stop=11.0))
    
    assert trades.loc[0, "direction"] == "short"
    assert trades.loc[0, "outcome"] == "loss"
    assert trades.loc[0, "r_multiple"] == -1.01
    
    
def test_missing_stop_means_no_trade():
    """No stop level no exit plan no trade"""
    rows = [(10, 10, 9.5, 10), (10, 11, 9.5, 10.5 )]
    trades = simulate_trades(_signals(rows, stop=float("nan")))
    assert trades.empty