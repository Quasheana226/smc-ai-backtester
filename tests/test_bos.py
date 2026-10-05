"""Test for break of structure BOS detection."""

from src.detection.bos import detect_bos
from src.detection.swings import add_swings


def test_bullish_bos(make_candles):
    """Close crosses above the prior swing high = long"""
    rows = [
        (9, 10, 9, 9.5),
        (9.5, 12, 9.2, 11),  # <- swing high at 12
        (11, 11.5, 8.5, 10),  # <- swing low at 8.5
        (10, 10.5, 9.8, 10.4),
        (10.4, 13, 10.3, 12.5),  # <- closes 12.5, above 12 = BOS
        (12.5, 13.5, 12, 13),  # <- still above 12, but NOT a new cross
    ]
    df = detect_bos(add_swings(make_candles(rows), lookback=1))

    assert df.loc[4, "signal"] == 1  # Long signal on the breakout candle
    assert df["signal"].abs().sum() == 1  # Only the first close past the level counts
    assert df.loc[4, "stop_price"] < 8.5  # Stop sits below the prior swing low


def test_wick_above_but_close_below_is_not_a_bos(make_candles):
    """A wick above the prior swing high is not a BOS if it closes below the prior swing high"""
    rows = [
        (9, 10, 9, 9.5),
        (9.5, 12, 9.2, 11),  # <- swing high at 12
        (11, 11.5, 8.5, 10),  # <- swing low at 8.5
        (10, 10.5, 9.8, 10.4),
        (10.4, 13, 10.3, 11.8),  # <- wicks to 13 but closes 11.8 below 12 = NOT a BOS
    ]
    df = detect_bos(add_swings(make_candles(rows), lookback=1))

    assert df.loc[4, "signal"] == 0


def test_bearish_bos(make_candles):
    """Mirror image: Close crosses below the prior swing low = short"""
    rows = [
        (10, 11, 9.5, 10.5),
        (10.5, 11, 8, 9),  # <- swing low at 8
        (9, 12, 8.5, 11.5),  # <- swing high at 12
        (11.5, 11.5, 9, 9.5),
        (9.5, 10, 7.5, 7.6),  # <- closes 7.6, below 8 = BOS
        (7.6, 8, 7, 7.2),  # <- still below 8, but NOT a new cross
    ]
    df = detect_bos(add_swings(make_candles(rows), lookback=1))

    assert df.loc[4, "signal"] == -1  # Short signal on the breakout candle
    assert df["signal"].abs().sum() == 1  # Only the first close past the level counts
    assert df.loc[4, "stop_price"] > 12  # Stop sits above the prior swing high
