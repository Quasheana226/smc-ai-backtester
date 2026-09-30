"""
fetch.py - downloads historical candles (OHLCV) and caches them to disk.
"""

import time
from pathlib import Path

import pandas as pd
import requests

from src import config

# Binance returns each candle as a list of 12 values. Only pulling the first 6.
KLINE_COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]


def _to_milliseconds(timestamp: pd.Timestamp) -> int:
    """Convert a pandas Timestamp to milliseconds since epoch."""
    return int(timestamp.timestamp() * 1000)


def _to_utc(values, unit=None):
    """Convert a list of timestamps to UTC timezone."""
    return pd.to_datetime(values, unit=unit, utc=True).dt.as_unit("ns")


def _cache_path(symbol: str, timeframe: str, start: str, end: str) -> Path:
    """Return the path to the cache file for a given symbol and interval."""
    return Path(config.CACHE_DIR) / f"{symbol}_{timeframe}_{start}_{end}.csv"


def _rows_to_dataframe(rows: list) -> pd.DataFrame:
    """Convert raw Binance kline rows into a cleaned, typed DataFrame."""
    if not rows:
        return pd.DataFrame(columns=KLINE_COLUMNS)

    trimmed = [row[:6] for row in rows]
    df = pd.DataFrame(trimmed, columns=KLINE_COLUMNS)

    price_columns = ["open", "high", "low", "close", "volume"]
    df[price_columns] = df[price_columns].astype(float)

    df["open_time"] = _to_utc(df["open_time"], unit="ms")
    df = df.drop_duplicates("open_time").sort_values("open_time", ascending=True).reset_index(drop=True)
    return df


def fetch_candles(symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV candles for a symbol/timeframe/date range, using a local cache."""
    cache_file = _cache_path(symbol, timeframe, start, end)

    if cache_file.exists():
        cached = pd.read_csv(cache_file)
        cached["open_time"] = _to_utc(cached["open_time"])
        return cached

    start_ms = _to_milliseconds(pd.Timestamp(start, tz="UTC"))
    end_ms = _to_milliseconds(pd.Timestamp(end, tz="UTC"))
    all_rows = []

    while start_ms < end_ms:
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": config.MAX_CANDLES_PER_REQUEST,
        }
        response = requests.get(config.KLINES_URL, params=params, timeout=15)
        response.raise_for_status()
        page = response.json()

        if not page:
            break  # No more data to fetch.

        all_rows.extend(page)
        start_ms = page[-1][0] + 1  # Start after the last candle we got.
        time.sleep(config.REQUEST_PAUSE_SECONDS)

    candles = _rows_to_dataframe(all_rows)

    if candles.empty:
        return candles  # Don't cache empty results.

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    candles.to_csv(cache_file, index=False)
    return candles
