"""Daily closes from Yahoo Finance, cached in desk/.cache between pipeline steps."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
PRICES = CACHE / "prices.csv"

GOLD = "GC=F"
TICKERS = {
    "GC=F": "Gold",
    "SI=F": "Silver",
    "CL=F": "WTI crude",
    "^TNX": "US 10Y yield",
    "DX-Y.NYB": "Dollar index",
    "^GSPC": "S&P 500",
    "^VIX": "VIX",
}
START = "2003-01-01"
CLOSE_HOUR_NY = 17  # the Yahoo daily bar for COMEX futures is complete after 17:00 New York time


def fetch(start: str = START) -> pd.DataFrame:
    """Download closes for all tickers; rows follow the gold trading calendar."""
    import yfinance as yf

    df = yf.download(list(TICKERS), start=start, progress=False, auto_adjust=False)["Close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[df[GOLD].notna()].sort_index()
    if df.empty or (pd.Timestamp.now() - df.index[-1]).days > 7:
        raise RuntimeError(
            "No recent gold prices from Yahoo Finance. Check network access to "
            "query1.finance.yahoo.com, query2.finance.yahoo.com and fc.yahoo.com."
        )
    return drop_unfinished_day(df)


def drop_unfinished_day(df: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Drop today's row while the session is still open, so only finished closes enter the model."""
    now = now if now is not None else pd.Timestamp.now(tz="America/New_York")
    if len(df) and df.index[-1].date() == now.date() and now.hour < CLOSE_HOUR_NY:
        return df.iloc[:-1]
    return df


def save(df: pd.DataFrame) -> None:
    CACHE.mkdir(exist_ok=True)
    df.to_csv(PRICES)


def load(refresh: bool = False) -> pd.DataFrame:
    """Cached prices, or a fresh download when there is no cache (or refresh=True)."""
    if refresh or not PRICES.exists():
        df = fetch()
        save(df)
        return df
    return pd.read_csv(PRICES, index_col=0, parse_dates=True)


def gold(prices: pd.DataFrame, asof: str | None = None) -> pd.Series:
    s = prices[GOLD].dropna()
    return s.loc[:asof] if asof else s
