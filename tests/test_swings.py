"""Test for swing detection """

import pandas as pd

from src.detection.swings import add_swings

# High go uo to a peak at index 2 then back down 
PEAK_ROWS = [
    (1, 1, 0.5, 1),
    (2, 2, 1.5, 2),
    (3, 5, 2.5, 3),
    (2, 2, 1.5, 2),
    (1, 1, 0.5, 1),
    (1, 1, 0.5, 1),
]

def test_finds_the_peak(make_candles):

    df = add_swings(make_candles(PEAK_ROWS), lookback=1)
    # The peak is at index 2, so the swing high should be marked there.
    assert df.loc[2, "is_swing_high"]
    assert df["is_swing_high"].sum() == 1 
    
def test_no_look_ahead(make_candles):
    """ The peak at index 2 needs candle 3 to close before its confirmed,
    so the earliest candle allowed to use it is index 4 
    If this test fails, every backtest result is fake."""
    
    df = add_swings(make_candles(PEAK_ROWS), lookback=1)
    assert pd.isna(df.loc[3, "prior_swing_high"])  # Candle 3 can't see the peak yet.
    assert df.loc[4, "prior_swing_high"] == 5  # Candle 4 can see the peak.
    
def test_finds_the_valley(make_candles):
    """ Swing lows are the mirror image: the lowest low in the window"""
    
    valley_rows = [
        (5, 5.5, 5, 5),
        (4, 4.5, 4, 4),
        (3, 3.5, 1, 3),
        (4, 4.5, 4, 4),
        (5, 5.5, 5, 5),
        (5, 5.5, 5, 5),
        
    ]
    df = add_swings(make_candles(valley_rows), lookback=1)
    assert df.loc[2, "is_swing_low"]
    assert df["is_swing_low"].sum() == 1    
    assert df.loc[4, "prior_swing_low"] == 1