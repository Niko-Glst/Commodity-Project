"""Daily closes from Yahoo Finance; the snapshot used by a run is saved in copper/data/."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "data" / "prices.csv"

COPPER = "HG=F"
TICKERS = {
    "HG=F": "Copper (COMEX, $/lb)",
    "GC=F": "Gold (COMEX, $/oz)",
    "^IXIC": "Nasdaq Composite",
    "^NDX": "Nasdaq-100",
    "^SOX": "PHLX Semiconductor",
    "^GSPC": "S&P 500",
    "^TNX": "US 10Y yield",
    "DX-Y.NYB": "Dollar index",
    "FCX": "Freeport-McMoRan",
    "COPX": "Global X Copper Miners ETF",
}
START = "2000-01-01"
CLOSE_HOUR_NY = 17   # Yahoo's daily bar for COMEX futures is complete after 17:00 New York time


def fetch(start: str = START) -> pd.DataFrame:
    """Download closes for all tickers (prices not adjusted for dividends: index levels and futures)."""
    import yfinance as yf

    df = yf.download(list(TICKERS), start=start, progress=False, auto_adjust=False)["Close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna(how="all").sort_index()
    if df.empty or (pd.Timestamp.now() - df[COPPER].dropna().index[-1]).days > 7:
        raise RuntimeError("No recent copper prices from Yahoo Finance; check network access.")
    return drop_unfinished_day(df)


def drop_unfinished_day(df: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Drop today's row while the session is still open, so only finished closes are used."""
    now = now if now is not None else pd.Timestamp.now(tz="America/New_York")
    if len(df) and df.index[-1].date() == now.date() and now.hour < CLOSE_HOUR_NY:
        return df.iloc[:-1]
    return df


def load(refresh: bool = False) -> pd.DataFrame:
    """The saved snapshot, or a fresh download when there is none (or refresh=True)."""
    if refresh or not PRICES.exists():
        df = fetch()
        PRICES.parent.mkdir(exist_ok=True)
        df.to_csv(PRICES)
        return df
    return pd.read_csv(PRICES, index_col=0, parse_dates=True)
