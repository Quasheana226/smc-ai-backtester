"""swings.py - marks swing highs/lows and tracks when each becomes usable."""

import pandas as pd

from src import config


def add_swings(df: pd.DataFrame, lookback: int = config.SWING_LOOKBACK) -> pd.DataFrame:
    """Mark swing highs/lows and the most recent one usable without look-ahead.

    A candle is a swing high if its high is strictly greater than the highs
    of `lookback` candles on each side (swing low is the mirror on lows). A
    swing is only confirmed once the candle `lookback` positions after it has
    closed, so `prior_swing_high`/`prior_swing_low` stay NaN until the first
    candle that could legally have known about them, then forward-fill.
    """
    df = df.copy()
    highs = df["high"]
    lows = df["low"]
    n = len(df)

    is_swing_high = pd.Series(False, index=df.index)
    is_swing_low = pd.Series(False, index=df.index)

    for i in range(lookback, n - lookback):
        left = slice(i - lookback, i)
        right = slice(i + 1, i + lookback + 1)

        if highs.iloc[i] > highs.iloc[left].max() and highs.iloc[i] > highs.iloc[right].max():
            is_swing_high.iloc[i] = True

        if lows.iloc[i] < lows.iloc[left].min() and lows.iloc[i] < lows.iloc[right].min():
            is_swing_low.iloc[i] = True

    df["is_swing_high"] = is_swing_high
    df["is_swing_low"] = is_swing_low
    df["prior_swing_high"] = _usable_from_next_candle(highs, is_swing_high, lookback)
    df["prior_swing_low"] = _usable_from_next_candle(lows, is_swing_low, lookback)

    return df


def _usable_from_next_candle(values: pd.Series, is_swing: pd.Series, lookback: int) -> pd.Series:
    """Shift confirmed swing values to the first candle allowed to use them."""
    swing_values = values.where(is_swing)
    return swing_values.shift(lookback + 1).ffill()
