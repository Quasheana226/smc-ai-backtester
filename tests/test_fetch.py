"""
Tests for fetch.py — without touching the internet.

We use pytest's `monkeypatch` to swap `requests.get` for a fake function.
WHY: tests that call a real API are slow, break when the API is down, and
can't be run offline. Faking the network lets us test OUR code only.
"""

import pandas as pd

from src import config
from src.data import fetch

# Two candles in Binance's raw format: [open_time_ms, open, high, low, close, volume, ...extra]
# Prices come as strings, exactly like the real API sends them.
RAW_ROWS = [
    [1704070800000, "101.0", "103.0", "100.0", "102.0", "5.0", 0, "0", 0, "0", "0", "0"],
    [1704067200000, "100.0", "102.0", "99.0", "101.0", "7.0", 0, "0", 0, "0", "0", "0"],
]


class FakeResponse:
    """Stands in for a requests.Response object."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass  # Pretend the request succeeded.

    def json(self):
        return self._payload


def test_rows_are_cleaned_and_sorted():
    df = fetch._rows_to_dataframe(RAW_ROWS)

    assert list(df.columns) == fetch.KLINE_COLUMNS
    assert df["close"].dtype == float  # Strings became numbers.
    assert str(df["open_time"].dt.tz) == "UTC"  # Times are UTC.
    assert df["open_time"].is_monotonic_increasing  # Oldest first, even though the input wasn't.


def test_downloads_once_then_uses_cache(tmp_path, monkeypatch):
    # Point the cache at a temporary folder so the test never touches real files.
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    # No real pauses in tests. Tests should be fast.
    monkeypatch.setattr(config, "REQUEST_PAUSE_SECONDS", 0)

    # First call: the fake API returns one page, then an empty page (end of data).
    pages = iter([RAW_ROWS, []])
    monkeypatch.setattr(fetch.requests, "get", lambda *args, **kwargs: FakeResponse(next(pages)))
    first = fetch.fetch_candles("BTCUSDT", "1h", "2024-01-01", "2024-01-02")
    assert len(first) == 2

    # Second call: make the network explode if it's used. It shouldn't be.
    def no_network(*args, **kwargs):
        raise AssertionError("Should have used the cache, not the API")

    monkeypatch.setattr(fetch.requests, "get", no_network)
    second = fetch.fetch_candles("BTCUSDT", "1h", "2024-01-01", "2024-01-02")

    # Same data back, including the timestamp type.
    pd.testing.assert_frame_equal(first, second)


def test_empty_result_is_not_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(fetch.requests, "get", lambda *args, **kwargs: FakeResponse([]))

    result = fetch.fetch_candles("BTCUSDT", "1h", "2024-01-01", "2024-01-02")

    assert result.empty
    assert list(tmp_path.iterdir()) == []  # Nothing was saved.
