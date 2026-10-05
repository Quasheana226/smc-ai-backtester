"""bos.py - detect break of structure: price closing past a swing and holding.

The contrast with sweep.py: a sweep pokes past the level and comes back,
a BOS closes past it and stays. Sweep trades the reversal, BOS the continuation.
"""

import numpy as np
import pandas as pd

from src import config


def detect_bos(candles: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `candles` with `signal` and `stop_price` columns added.

    Expects the swing columns from `add_swings` (`prior_swing_high`,
    `prior_swing_low`), which are already lagged so no look-ahead is possible.

    Bullish BOS: this candle closes above `prior_swing_high` while the previous
    candle closed at or below it; bearish mirrors it on `prior_swing_low`.
    `signal` is 1 long / -1 short / 0 none.

    The stop sits beyond the opposite swing plus `config.STOP_BUFFER_PCT` - a
    long is invalidated if price falls back under the swing low it broke out
    from. Rows with no opposite swing confirmed yet produce no signal, per the
    "no stop level available, no trade" rule.
    """
    df = candles.copy()

    # shift(1) moves every close down one row, so row i lines up with row i-1's
    # close. Row 0 becomes NaN, which compares False and so can never signal.
    prev_close = df["close"].shift(1)

    # Requiring the previous close on the near side of the level is what makes
    # this the FIRST close past it. Without it every candle in a sustained trend
    # re-reports the same break and we massively overcount setups.
    # The opposite swing must also exist, because that is where the stop goes
    # and a setup with no stop level is not tradeable.
    bullish = (
        (df["close"] > df["prior_swing_high"])
        & (prev_close <= df["prior_swing_high"])
        & df["prior_swing_low"].notna()
    )
    bearish = (
        (df["close"] < df["prior_swing_low"])
        & (prev_close >= df["prior_swing_low"])
        & df["prior_swing_high"].notna()
    )

    # np.select picks a value per row based on the first condition that's True.
    df["signal"] = np.select(
        [bullish, bearish],
        [1, -1],  # 1 = long, -1 = short
        default=0,  # 0 = no signal
    )

    # Buffer is a fraction of close, the same base sweep.py uses, so both
    # setups pad their stops consistently.
    buffer = df["close"] * config.STOP_BUFFER_PCT
    df["stop_price"] = np.select(
        [bullish, bearish],
        [df["prior_swing_low"] - buffer, df["prior_swing_high"] + buffer],
        default=np.nan,
    )
    return df
