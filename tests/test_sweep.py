"""Test for liquidity sweep detection"""

from src.detection.sweep import detect_sweeps
from src.detection.swings import add_swings


def test_bullish_sweep(make_candles):
    """Wick below the swing low, close back above it = long."""
    rows = [
        (10, 11, 9, 10),
        (10, 10.5, 8, 9),  # <- 8 is the swing low
        (9, 10, 8.5, 9.5),
        (9.5, 10, 9, 9.8),
        (9.8, 10, 7.5, 8.6),  # <- wicks to 7.5 below 8 closes 8.6 above 8 = sweep
        (8.6, 9, 8.2, 8.8),
    ]
    df = detect_sweeps(add_swings(make_candles(rows), lookback=1))

    assert df.loc[4, "signal"] == 1
    assert df["signal"].abs().sum() == 1  # <-Only one signal in this test case
    assert df.loc[4, "stop_price"] < 7.5  # <- The stop sits just below the sweep wick (7.5)


def test_wick_below_but_close_below_is_not_a_sweep(make_candles):
    """A wick below the prior swing low is not a sweep if it closes below the prior swing low"""
    rows = [
        (10, 11, 9, 10),
        (10, 10.5, 8, 9),  # <- 8 is the swing low
        (9, 10, 8.5, 9.5),
        (9.5, 10, 9, 9.8),
        (9.8, 10, 7.5, 7.8),  # <- wicks to 7.5 below 8 closes below 8 = NOT a sweep
        (7.8, 8, 7.2, 7.5),
    ]

    df = detect_sweeps(add_swings(make_candles(rows), lookback=1))
    assert df.loc[4, "signal"] == 0


def test_bearish_sweep(make_candles):
    """Mirror image: Wick ABOVE the swing high close back BELOW it= short."""
    rows = [
        (10, 11, 9, 10),
        (10, 12, 9.5, 11),  # <- 12 is the swing high
        (11, 11.5, 10, 10.5),
        (10.5, 11, 10, 10.5),
        (10.8, 12.5, 10.5, 11.4),  # <- wicks to 12.5 above 12 closes 11.4 below 12 = sweep
        (11.4, 12, 11, 11.2),
    ]
    df = detect_sweeps(add_swings(make_candles(rows), lookback=1))

    assert df.loc[4, "signal"] == -1  # short signal on the sweep candle
    assert df.loc[4, "stop_price"] > 12.5  # The stop price is the prior swing high
