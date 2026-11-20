"""Snapshot for the full analysis of 20 Nov 2026. Every source is saved raw so each number can be rechecked.

Usage (from desk/): python reports/2026-11-20-full/scripts/fetch_full.py reports/2026-11-20-full/data
"""
import io
import json
import sys
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

out = Path(sys.argv[1])
H = {"User-Agent": "Mozilla/5.0 (research-script)"}
log = {}

# 1. Yahoo closes (not adjusted) since 1950 where available, and 5-minute gold
tick = ["GC=F", "SI=F", "HG=F", "CL=F", "DX-Y.NYB", "^GSPC", "ES=F", "^VIX", "^VIX3M", "^MOVE", "^TNX", "^GVZ", "BTC-USD", "GLD"]
d = yf.download(tick, start="1950-01-01", progress=False, auto_adjust=False)["Close"]
d.index = pd.to_datetime(d.index).tz_localize(None)
d.to_csv(out / "daily.csv")
i = yf.download("GC=F", period="5d", interval="5m", progress=False, auto_adjust=False)
i.columns = [c[0] if isinstance(c, tuple) else c for c in i.columns]
i.index = i.index.tz_convert("America/New_York")
i.to_csv(out / "gold_5m.csv")
log["gold_daily_last"] = str(d["GC=F"].dropna().index[-1].date())
log["gold_5m_last"] = str(i.index[-1])

# 2. Total-return ETFs (dividends reinvested) for sectors and asset classes, since the first sector SPDRs
etfs = ["SPY", "RSP", "QQQ", "IWM", "XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE",
        "SMH", "IGV", "BIL", "IEF", "TLT", "UUP", "GLD", "SLV", "CPER", "COPX", "USO", "EFA", "EEM", "MTUM", "USMV"]
e = yf.download(etfs, start="1998-12-01", progress=False, auto_adjust=True)["Close"]
e.index = pd.to_datetime(e.index).tz_localize(None)
e.to_csv(out / "etf_total_return.csv")
log["etf_last"] = str(e.dropna(how="all").index[-1].date())

# 3. FRED: rates, inflation, dollar, credit, labour, oil, Fed balance sheet
FRED = ["DFII10", "T10YIE", "T5YIFR", "DGS2", "DGS10", "BAMLH0A0HYM2", "BAMLC0A0CM", "DTWEXBGS", "DCOILWTICO",
        "DFEDTARU", "CPIAUCSL", "CPILFESL", "UNRATE", "PAYEMS", "ICSA", "WALCL", "WTREGEN", "RRPONTSYD", "GS10",
        "FEDFUNDS", "WTISPLC"]
fr = {}
for sid in FRED:
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=H, timeout=60)
    s = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True).iloc[:, 0]
    fr[sid] = pd.to_numeric(s, errors="coerce")
    log[f"fred_{sid}"] = str(fr[sid].dropna().index[-1].date())
pd.DataFrame(fr).to_csv(out / "fred.csv")

# 4. CFTC: managed money in gold
url = ("https://publicreporting.cftc.gov/resource/72hh-3qpy.json?$where=cftc_contract_market_code='088691' AND "
       "report_date_as_yyyy_mm_dd >= '2006-06-01'&$select=report_date_as_yyyy_mm_dd,m_money_positions_long_all,"
       "m_money_positions_short_all,open_interest_all&$order=report_date_as_yyyy_mm_dd&$limit=5000")
c = pd.DataFrame(requests.get(url, headers=H, timeout=60).json())
c.to_csv(out / "cftc_gold.csv", index=False)
log["cftc_last"] = str(c.report_date_as_yyyy_mm_dd.iloc[-1])[:10]

# 5. ICI weekly money market fund assets
r = requests.get("https://www.ici.org/mm_summary_data_2026.xls", headers=H, timeout=60)
(out / "ici_mm_summary_2026.xls").write_bytes(r.content)

# 6. State Street daily NAV and shares outstanding for every SPDR used
ssga = {}
for t in ["GLD", "SPY", "BIL", "XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE", "XSD", "XME"]:
    r = requests.get(f"https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/navhist-us-en-{t.lower()}.xlsx",
                     headers=H, timeout=60)
    ok = r.status_code == 200 and r.content[:2] == b"PK"
    ssga[t] = ok
    if ok:
        (out / f"ssga_navhist_{t}.xlsx").write_bytes(r.content)
log["ssga_files"] = ssga

# 7. Monthly gold since 1833 (World Gold Council / LBMA via datahub)
r = requests.get("https://datahub.io/core/gold-prices/r/monthly.csv", headers=H, timeout=60)
(out / "gold_monthly_datahub.csv").write_text(r.text, encoding="utf-8")

(out / "fetch_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
print(json.dumps(log, indent=1))
print("gold last:", d["GC=F"].dropna().iloc[-1], "| 5m last:", i.index[-1], round(float(i["Close"].iloc[-1]), 1))
