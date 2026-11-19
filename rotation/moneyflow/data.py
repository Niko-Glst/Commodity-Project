"""Free sources for where money is moving: ETF prices (Yahoo), futures positioning (CFTC), cash (FRED).

Every fetch is saved in rotation/data/ so a note can be rebuilt from the snapshot.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HEADERS = {"User-Agent": "research-script/1.0"}

# Total-return ETFs, so cash (BIL pays T-bill interest) compares fairly with everything else.
UNIVERSE = {
    "BIL": ("Cash: 1-3 month T-bills", "Cash and bonds"),
    "IEF": ("Treasuries 7-10 years", "Cash and bonds"),
    "TLT": ("Treasuries 20+ years", "Cash and bonds"),
    "UUP": ("US dollar (long vs basket)", "Dollar"),
    "SPY": ("S&P 500", "US stocks"),
    "RSP": ("S&P 500 equal weight", "US stocks"),
    "QQQ": ("Nasdaq-100", "US stocks"),
    "IWM": ("Russell 2000 small caps", "US stocks"),
    "SMH": ("Semiconductors", "Sectors"),
    "IGV": ("Software", "Sectors"),
    "XLK": ("Technology", "Sectors"),
    "XLC": ("Communication services", "Sectors"),
    "XLY": ("Consumer discretionary", "Sectors"),
    "XLF": ("Financials", "Sectors"),
    "XLI": ("Industrials", "Sectors"),
    "XLE": ("Energy", "Sectors"),
    "XLB": ("Materials", "Sectors"),
    "XLV": ("Health care", "Sectors"),
    "XLP": ("Consumer staples", "Sectors"),
    "XLU": ("Utilities", "Sectors"),
    "XLRE": ("Real estate", "Sectors"),
    "GLD": ("Gold", "Metals and oil"),
    "SLV": ("Silver", "Metals and oil"),
    "CPER": ("Copper", "Metals and oil"),
    "COPX": ("Copper miners", "Metals and oil"),
    "USO": ("Oil", "Metals and oil"),
    "EFA": ("Developed markets ex US", "Abroad and crypto"),
    "EEM": ("Emerging markets", "Abroad and crypto"),
    "BTC-USD": ("Bitcoin", "Abroad and crypto"),
}
CASH = "BIL"

# CFTC Commitments of Traders: (dataset, contract code, trader group long/short columns)
COT = {
    "Gold": ("72hh-3qpy", "088691", "m_money_positions_long_all", "m_money_positions_short_all", "Managed money"),
    "Copper": ("72hh-3qpy", "085692", "m_money_positions_long_all", "m_money_positions_short_all", "Managed money"),
    "Nasdaq-100 (mini)": ("gpe5-46if", "209742", "asset_mgr_positions_long", "asset_mgr_positions_short", "Asset managers"),
    "S&P 500 (mini)": ("gpe5-46if", "13874A", "asset_mgr_positions_long", "asset_mgr_positions_short", "Asset managers"),
    "Nasdaq-100 (mini), leveraged": ("gpe5-46if", "209742", "lev_money_positions_long", "lev_money_positions_short",
                                     "Leveraged funds"),
    "US dollar index": ("gpe5-46if", "098662", "lev_money_positions_long", "lev_money_positions_short", "Leveraged funds"),
}
FRED = {"RRPONTSYD": "Fed overnight reverse repo, $bn", "WRMFNS": "Retail money market funds, $bn",
        "M2SL": "M2 money supply, $bn"}


def prices(start: str = "2024-01-01") -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(list(UNIVERSE), start=start, progress=False, auto_adjust=True)["Close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[df["SPY"].notna()]                      # US trading days (bitcoin trades every day)
    now = pd.Timestamp.now(tz="America/New_York")
    if df.index[-1].date() == now.date() and now.hour < 17:
        df = df.iloc[:-1]                           # drop today's unfinished session
    return df


def cot(start: str = "2024-01-01") -> pd.DataFrame:
    """Weekly net positions (long minus short contracts) for each COT series, as of Tuesday."""
    out = {}
    for name, (dataset, code, long_col, short_col, _) in COT.items():
        url = (f"https://publicreporting.cftc.gov/resource/{dataset}.json?"
               f"$where=cftc_contract_market_code='{code}' AND report_date_as_yyyy_mm_dd >= '{start}'"
               f"&$select=report_date_as_yyyy_mm_dd,{long_col},{short_col},open_interest_all"
               f"&$order=report_date_as_yyyy_mm_dd&$limit=5000")
        rows = requests.get(url, headers=HEADERS, timeout=60).json()
        f = pd.DataFrame(rows)
        f.index = pd.to_datetime(f.pop("report_date_as_yyyy_mm_dd"))
        f = f.astype(float)
        out[name] = (f[long_col] - f[short_col])
        out[name + " | OI"] = f["open_interest_all"]
    return pd.DataFrame(out)


def fred() -> dict[str, pd.Series]:
    out = {}
    for sid in FRED:
        r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=HEADERS, timeout=60)
        s = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True).iloc[:, 0]
        out[sid] = pd.to_numeric(s, errors="coerce").dropna()
    return out


def load(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.Series]]:
    DATA.mkdir(exist_ok=True)
    files = {"prices": DATA / "prices.csv", "cot": DATA / "cot.csv", "fred": DATA / "fred.csv"}
    if refresh or not all(f.exists() for f in files.values()):
        p, c, f = prices(), cot(), fred()
        p.to_csv(files["prices"])
        c.to_csv(files["cot"])
        pd.DataFrame(f).to_csv(files["fred"])
        return p, c, f
    p = pd.read_csv(files["prices"], index_col=0, parse_dates=True)
    c = pd.read_csv(files["cot"], index_col=0, parse_dates=True)
    fr = pd.read_csv(files["fred"], index_col=0, parse_dates=True)
    return p, c, {k: fr[k].dropna() for k in fr}
