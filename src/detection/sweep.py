"""sweep.py - detect liquidity seeps
Many traders put stop-losses just past an obvious
peak or valley. A sweep is when price pokes past that level
triggering those stops and then snaps back. SMC traders read
that big players grabbbing liquidity befor moving pice the
other way"""

import numpy as np
import pandas as pd

from src import config


def detect_sweeps(candles: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `candles` must already have a swing colums with signals + stop_price"""
    df = candles.copy()

    # Boolean Masks : True on rows the conditions holds
    # Vectorized operations are faster than iterating over rows with a for loop
    bullish = (df["low"] < df["prior_swing_low"]) & (df["close"] > df["prior_swing_low"])
    bearish = (df["high"] > df["prior_swing_high"]) & (df["close"] < df["prior_swing_high"])

    # np.select picks a value per row based on the first condition thats True.
    df["signal"] = np.select(
        [bullish, bearish],
        [1, -1],  # 1 = long, -1 = short
        default=0,  # 0 = no signal
    )

    buffer = df["close"] * config.STOP_BUFFER_PCT
    df["stop_price"] = np.select(
        [bullish, bearish],
        [df["low"] - buffer, df["high"] + buffer],
        default=np.nan,
    )
    return df
