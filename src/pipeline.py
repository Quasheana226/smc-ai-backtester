"""pipeline.py - wire the pieces together: candles in, signals + trades + stats out.

The detectors, simulator, and stats functions each do one job and know nothing
about each other. This module is the only place that knows the running order:

    candles -> add_swings -> detector -> simulate_trades -> summarize

WHY a SETUPS dict instead of an if/elif chain?
The UI needs to offer the user a list of setups to pick from. A dict means the
menu and the dispatch are the same object, so adding a setup can't leave the
two out of step.
"""

import pandas as pd

from src.backtest.simulate import simulate_trades
from src.backtest.stats import session_for_hour, summarize
from src.detection.bos import detect_bos
from src.detection.sweep import detect_sweeps
from src.detection.swings import add_swings

# Display name -> detector. Keys are what the UI shows and what run_backtest accepts.
SETUPS = {
    "Liquidity Sweep": detect_sweeps,
    "Break of Structure": detect_bos,
}


def run_backtest(candles: pd.DataFrame, setup_name: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Run one setup over `candles` and return (signals, trades, stats).

    `signals` is the candle table plus the detector's `signal`/`stop_price`
    columns, `trades` is one row per simulated trade, and `stats` is the
    headline summary dict from stats.summarize.

    Raises ValueError if `setup_name` isn't one of the SETUPS keys.
    """
    if setup_name not in SETUPS:
        raise ValueError(f"Unknown setup {setup_name!r}. Choose on of: {list(SETUPS)}")

    # Swings first: both detectors read prior_swing_high/prior_swing_low.
    detector = SETUPS[setup_name]
    signals = detector(add_swings(candles))
    trades = simulate_trades(signals)

    # An empty result has no columns at all, so only label sessions when there
    # are trades to label.
    if not trades.empty:
        trades["session"] = trades["hour_utc"].apply(session_for_hour)

    return signals, trades, summarize(trades)
