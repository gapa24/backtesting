import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CSV_MAP = {
    "1min":  "NIFTY 50_minute.csv",
    "5min":  "NIFTY 50_5minute.csv",
    "15min": "NIFTY 50_15minute.csv",
}

RESAMPLE_MAP = {
    "1min":  "1T",
    "3min":  "3T",
    "5min":  "5T",
    "10min": "10T",
    "15min": "15T",
    "30min": "30T",
}

MARKET_OPEN  = "09:15"
MARKET_CLOSE = "15:29"


def load_data(interval: str, period: str) -> pd.DataFrame:
    """
    Main entry point.

    Args:
        interval : one of "1min","3min","5min","10min","15min","30min"
        period   : "full" (use CSV) or "60d" (use yfinance)

    Returns:
        Clean OHLCV DataFrame indexed by datetime,
        columns: open, high, low, close, volume
    """
    if period == "60d":
        df = _load_from_yfinance(interval)
    else:
        df = _load_from_csv(interval)

    df = _clean(df)
    return df


def _load_from_yfinance(interval: str) -> pd.DataFrame:
    yf_interval_map = {
        "1min":  "1m",
        "3min":  "3m",  # not supported by yf — will raise
        "5min":  "5m",
        "10min": "10m", # not supported by yf — will raise
        "15min": "15m",
        "30min": "30m",
    }

    yf_interval = yf_interval_map.get(interval)
    if not yf_interval:
        raise ValueError(f"Interval '{interval}' is not supported by yfinance.")

    # yfinance 60-day hard limit for intraday
    end   = datetime.today()
    start = end - timedelta(days=59)

    ticker = yf.Ticker("^NSEI")
    df = ticker.history(
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval=yf_interval,
    )

    if df.empty:
        raise ValueError("yfinance returned empty data. Check your internet connection.")

    df = df.rename(columns={
        "Open":   "open",
        "High":   "high",
        "Low":    "low",
        "Close":  "close",
        "Volume": "volume",
    })

    df = df[["open", "high", "low", "close", "volume"]]
    df.index.name = "date"
    df.index = pd.to_datetime(df.index)

    # strip timezone — yfinance returns tz-aware, we want naive IST
    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)

    return df


def _load_from_csv(interval: str) -> pd.DataFrame:
    # use pre-built CSV if available, else resample from 1min
    if interval in CSV_MAP:
        csv_file = os.path.join(DATA_DIR, CSV_MAP[interval])
        df = _read_csv(csv_file)
    else:
        # fall back to 1min CSV and resample
        csv_file = os.path.join(DATA_DIR, CSV_MAP["1min"])
        df = _read_csv(csv_file)
        df = _resample(df, interval)

    return df


def _read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"CSV not found at {path}. "
            "Make sure your data files are in the /data folder."
        )

    df = pd.read_csv(
        path,
        parse_dates=["date"],
        index_col="date",
    )

    df.columns = [c.lower().strip() for c in df.columns]

    required = {"open", "high", "low", "close", "volume"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}")

    df = df[["open", "high", "low", "close", "volume"]]
    df = df.sort_index()
    return df


def _resample(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    rule = RESAMPLE_MAP.get(interval)
    if not rule:
        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported: {list(RESAMPLE_MAP.keys())}"
        )

    df_resampled = df.resample(rule, origin="start_day").agg({
        "open":   "first",
        "high":   "max",
        "low":    "min",
        "close":  "last",
        "volume": "sum",
    })

    # drop incomplete candles (NaN from gaps/holidays)
    df_resampled = df_resampled.dropna(subset=["open", "close"])
    return df_resampled


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    # filter to NSE market hours only
    df = df.between_time(MARKET_OPEN, MARKET_CLOSE)

    # drop any remaining NaNs
    df = df.dropna()

    # ensure correct dtypes
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna()

    # drop rows where OHLC are clearly broken
    df = df[df["high"] >= df["low"]]
    df = df[df["close"] > 0]

    return df
