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
FRED = {
    "BAMLH0A0HYM2": "High-yield credit spread (ICE BofA OAS), %",
    "BAMLC0A0CM": "Investment-grade credit spread (ICE BofA OAS), %",
    "DGS2": "2-year Treasury yield, %", "DGS10": "10-year Treasury yield, %",
    "DFII10": "10-year real yield (TIPS), %", "T10YIE": "10-year breakeven inflation, %",
    "WALCL": "Fed total assets, $m", "WTREGEN": "Treasury General Account, $m",
    "RRPONTSYD": "Fed overnight reverse repo, $bn", "WRESBAL": "Bank reserves, $m",
    "M2SL": "M2 money supply, $bn",
}
# Stress and factor gauges, and the biggest consumer-discretionary names (XLY is cap-weighted)
MARKET = ["^VIX9D", "^VIX", "^VIX3M", "^MOVE", "MTUM", "USMV", "SPY", "RSPD", "XLY", "AMZN", "TSLA", "HD", "MCD"]
# State Street publishes daily shares outstanding for its SPDR funds: flows = change in shares x NAV
SSGA = ["SPY", "BIL", "XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE", "XSD", "XME"]
SSGA_NAMES = {"SPY": "S&P 500", "BIL": "T-bills 1-3 months", "XLK": "Technology", "XLC": "Communication services",
              "XLY": "Consumer discretionary", "XLF": "Financials", "XLI": "Industrials", "XLE": "Energy",
              "XLB": "Materials", "XLV": "Health care", "XLP": "Consumer staples", "XLU": "Utilities",
              "XLRE": "Real estate", "XSD": "Semiconductors (equal weight)", "XME": "Metals and mining"}
SSGA_URL = "https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/navhist-us-en-{}.xlsx"
ICI_URL = "https://www.ici.org/mm_summary_data_2026.xls"


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


def market(start: str = "2024-01-01") -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(MARKET, start=start, progress=False, auto_adjust=True)["Close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[df["SPY"].notna()]
    now = pd.Timestamp.now(tz="America/New_York")
    if df.index[-1].date() == now.date() and now.hour < 17:
        df = df.iloc[:-1]
    return df


def ssga_flows() -> pd.DataFrame:
    """Daily NAV and shares outstanding for State Street SPDR funds (long format)."""
    rows = []
    for t in SSGA:
        r = requests.get(SSGA_URL.format(t.lower()), headers={"User-Agent": "Mozilla/5.0 (research-script)"}, timeout=60)
        x = pd.read_excel(io.BytesIO(r.content), header=None, engine="openpyxl")
        start = x.index[x[0].astype(str).str.strip() == "Date"][0] + 1
        x = x.iloc[start:, :3].dropna()
        x.columns = ["date", "nav", "shares"]
        x["date"] = pd.to_datetime(x["date"], format="%d-%b-%Y", errors="coerce")
        x = x.dropna(subset=["date"]).assign(ticker=t)
        rows.append(x[x.date >= "2024-01-01"])
    out = pd.concat(rows)
    out[["nav", "shares"]] = out[["nav", "shares"]].astype(float)
    return out.sort_values(["ticker", "date"]).reset_index(drop=True)


def ici_mmf() -> pd.DataFrame:
    """ICI weekly money market fund assets, $m (total, institutional, retail), as far back as the file goes."""
    r = requests.get(ICI_URL, headers={"User-Agent": "Mozilla/5.0 (research-script)"}, timeout=60)
    x = pd.read_excel(io.BytesIO(r.content), header=None, engine="xlrd")
    x = x[pd.to_datetime(x[0].astype(str).str.strip(), format="%m/%d/%Y", errors="coerce").notna()]
    # 12 columns per segment (all, institutional, retail): classes and TNA for total, tax-exempt,
    # government (total, Treasury & repo, Treasury & agency) and prime. Segment totals sit in columns 2, 14, 26.
    out = pd.DataFrame({"total": x[2].astype(float).values, "institutional": x[14].astype(float).values,
                        "retail": x[26].astype(float).values},
                       index=pd.to_datetime(x[0].astype(str).str.strip(), format="%m/%d/%Y"))
    out = out.dropna().sort_index()                 # the title row carries the report date but no data
    if out.empty or not (out.institutional + out.retail - out.total).abs().max() < 2:
        raise ValueError("ICI layout changed: institutional + retail no longer add up to the total")
    return out


class Bundle:
    """Everything one run uses; saved to and read from rotation/data/."""

    FILES = ("prices", "cot", "fred", "market", "flows", "mmf")

    def __init__(self, **kw):
        self.__dict__.update(kw)


def load(refresh: bool = False) -> Bundle:
    DATA.mkdir(exist_ok=True)
    path = {k: DATA / f"{k}.csv" for k in Bundle.FILES}
    if refresh or not all(f.exists() for f in path.values()):
        b = Bundle(prices=prices(), cot=cot(), fred=pd.DataFrame(fred()), market=market(), flows=ssga_flows(),
                   mmf=ici_mmf())
        for k in Bundle.FILES:
            getattr(b, k).to_csv(path[k], index=(k != "flows"))
    else:
        b = Bundle(**{k: pd.read_csv(path[k], index_col=None if k == "flows" else 0, parse_dates=[0] if k != "flows"
                                     else ["date"]) for k in Bundle.FILES})
    b.fred_series = {k: b.fred[k].dropna() for k in b.fred}
    return b
