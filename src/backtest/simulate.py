"""simulate.py turn signals into simulated trades 
Trades rules from claude.md 
1. signal appears on candle i -> enter at candle i+1's OPEN
you cant buy at the close of a candle your still watching form
2. stop = the detectors stop_price.
Target = entry +/- RR_TARGET x risk (risk = distance to stop) 
3 walk forward candle by candle untitl the stop or target is hit 
4. walk forward candle by candle unitil the sae candle, assume the STOP hit first 
candles dont tell us the orderm, so we pick the pessmistic answer 
5. Only one trade open at a time 


Results are measured in "R" (multiples of risk):
-1R = lost what you risked +2R = made twice what you risked
Using R instead of dollars makes results comparable across any account size.

WHY a for-loop here when the detectors avoided them
Trades are path-dependent: whether you can take trade #5 depends on when
trade #4 closed That "memory" is awkward to vectorize, and a clear loop
is easier to read and defend than a clever one-liner

"""

import pandas as pd

from src import config


def simulate_trades(signals: pd.DataFrame, rr_target: float = config.RR_TARGET) -> pd.DataFrame:
    """ 
    Simulate trades from a Dataframe that has signal + stop_price colums 
    Return one row per trade with entry/exit details and the results in R 
    """
        
    df = signals.reset_index(drop=True)
    
    #price vs moving average 
    sma = df["close"].rolling(config.TREND_SMA_PERIOD).mean()
     
    trades: list[dict] = []
    i = 0
    last_index = len(df) - 1
    
    while i < last_index: # Need at least one candle after the signal to enter
        direction = df.at[i, "signal"]
        if direction == 0:
            i += 1
            continue
        
        
        entry_index = i + 1 
        entry = df.at[entry_index, "open"]
        stop = df.at[i, "stop_price"]
        
        
        if pd.isna(stop):
            i += 1
            continue
        
        # Risk is always postive distance direction flips the math for shorts 
        
        risk = (entry - stop) * direction
        if risk <= 0:
            i += 1
            continue
        
        target = entry + direction * rr_target * risk
        exit_index, exit_price, outcome = _walk_forward(df, entry_index, direction, stop, target)
        # Fees are paid in dollars; convert them into R so they reduce the result.
        fee_in_r = (config.FEE_PCT * entry) / risk
        r_multiple = (exit_price - entry) * direction / risk - fee_in_r

        trades.append(
            {
                "signal_time": df.at[i, "open_time"],
                "entry_time": df.at[entry_index, "open_time"],
                "exit_time": df.at[exit_index, "open_time"],
                "direction": "long" if direction == 1 else "short",
                "entry": entry,
                "stop": stop,
                "target": target,
                "exit_price": exit_price,
                "outcome": outcome,
                "r_multiple": round(r_multiple, 3),
                "bars_held": exit_index - entry_index + 1,
                "hour_utc": df.at[i, "open_time"].hour,
                "trend": _trend_label(df.at[i, "close"], sma.iat[i]),
            }
        )

        # Rule 5: don't look for the next signal until this trade has closed.
        i = exit_index + 1

    return pd.DataFrame(trades)


def _walk_forward(
    df: pd.DataFrame, start: int, direction: int, stop: float, target: float
) -> tuple[int, float, str]:
    """
    Step through candles from `start` until stop or target is hit.

    Returns (exit_index, exit_price, outcome) where outcome is
    "win", "loss", or "open" (data ran out before either was hit).
    """
    for j in range(start, len(df)):
        high, low = df.at[j, "high"], df.at[j, "low"]

        if direction == 1:  # Long: stop is below, target is above.
            hit_stop, hit_target = low <= stop, high >= target
        else:  # Short: stop is above, target is below.
            hit_stop, hit_target = high >= stop, low <= target

        # Stop is checked FIRST on purpose (rule 4: pessimistic tie-break).
        if hit_stop:
            return j, stop, "loss"
        if hit_target:
            return j, target, "win"

    # Ran out of data: close at the last candle's close so the trade still counts.
    last = len(df) - 1
    return last, df.at[last, "close"], "open"


def _trend_label(close: float, sma_value: float) -> str:
    """'up' if price is above its moving average, 'down' if below, 'unknown' early on."""
    if pd.isna(sma_value):
        return "unknown"
    return "up" if close > sma_value else "down"