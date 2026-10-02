"""conftest.py - shared test helpers and fixtures.

pytest automatically finds this file and runs it before any tests.
"""

import pandas as pd
import pytest


@pytest.fixture
def make_candles():
    """Return a function that turns (open, high, low, close) tuples into a
    candle DataFrame in the exact format fetch.py produces.
    """
    def _make(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
        df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
        df["volume"] = 1.0  # Dummy volume.
        # One-hour candles starting at a fixed date, so times are predictable.
        df.insert(0, "open_time", pd.date_range("2024-01-01", periods=len(df), freq="1h", tz="UTC"))
        return df
    return _make

