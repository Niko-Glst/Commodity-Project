"""Snapshot for the 20 Nov full report. Every source is saved raw so each number can be rechecked.

Usage (from desk/): python reports/2026-11-20/scripts/fetch_report.py reports/2026-11-20/data
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

# 1. Yahoo: daily closes since 2003 and 5-minute gold for the last five sessions
tick = ["GC=F", "SI=F", "HG=F", "CL=F", "DX-Y.NYB", "^GSPC", "ES=F", "^VIX", "^VIX3M", "^TNX", "^GVZ", "BTC-USD", "GLD"]
d = yf.download(tick, start="2003-01-01", progress=False, auto_adjust=False)["Close"]
d.index = pd.to_datetime(d.index).tz_localize(None)
d.to_csv(out / "daily.csv")
i = yf.download("GC=F", period="5d", interval="5m", progress=False, auto_adjust=False)
i.columns = [c[0] if isinstance(c, tuple) else c for c in i.columns]
i.index = i.index.tz_convert("America/New_York")
i.to_csv(out / "gold_5m.csv")
log["yahoo_last_daily"] = str(d["GC=F"].dropna().index[-1].date())
log["gold_5m_last"] = str(i.index[-1])

# 2. FRED: rates, inflation, dollar, credit, labour, Fed balance sheet
FRED = ["DFII10", "T10YIE", "T5YIFR", "DGS2", "DGS10", "BAMLH0A0HYM2", "BAMLC0A0CM", "DTWEXBGS", "DCOILWTICO",
        "DFEDTARU", "CPIAUCSL", "CPILFESL", "UNRATE", "PAYEMS", "ICSA", "WALCL", "WTREGEN", "RRPONTSYD", "GS10"]
fr = {}
for sid in FRED:
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=H, timeout=60)
    s = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True).iloc[:, 0]
    fr[sid] = pd.to_numeric(s, errors="coerce")
    log[f"fred_{sid}"] = str(fr[sid].dropna().index[-1].date())
pd.DataFrame(fr).to_csv(out / "fred.csv")

# 3. CFTC: managed money in gold (disaggregated, futures only)
url = ("https://publicreporting.cftc.gov/resource/72hh-3qpy.json?$where=cftc_contract_market_code='088691' AND "
       "report_date_as_yyyy_mm_dd >= '2006-06-01'&$select=report_date_as_yyyy_mm_dd,m_money_positions_long_all,"
       "m_money_positions_short_all,open_interest_all&$order=report_date_as_yyyy_mm_dd&$limit=5000")
c = pd.DataFrame(requests.get(url, headers=H, timeout=60).json())
c.to_csv(out / "cftc_gold.csv", index=False)
log["cftc_last"] = str(c.report_date_as_yyyy_mm_dd.iloc[-1])[:10]

# 4. ICI weekly money market fund assets (2026 file)
r = requests.get("https://www.ici.org/mm_summary_data_2026.xls", headers=H, timeout=60)
(out / "ici_mm_summary_2026.xls").write_bytes(r.content)

# 5. State Street daily NAV and shares outstanding (flows = change in shares x NAV)
ssga = {}
for t in ["GLD", "SPY", "XLK", "XLU", "XLP", "BIL"]:
    r = requests.get(f"https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/navhist-us-en-{t.lower()}.xlsx",
                     headers=H, timeout=60)
    ok = r.status_code == 200 and r.content[:2] == b"PK"
    ssga[t] = ok
    if ok:
        (out / f"ssga_navhist_{t}.xlsx").write_bytes(r.content)
log["ssga_files"] = ssga

# 6. Monthly gold since 1833 (World Gold Council / LBMA via datahub)
r = requests.get("https://datahub.io/core/gold-prices/r/monthly.csv", headers=H, timeout=60)
(out / "gold_monthly_datahub.csv").write_text(r.text, encoding="utf-8")

(out / "fetch_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
print(json.dumps(log, indent=1))
print(d.loc["2026-11-12":, ["GC=F", "SI=F", "DX-Y.NYB", "^TNX", "^GVZ", "GLD"]].round(2).to_string())
print("intraday last", i.index[-1], round(float(i["Close"].iloc[-1]), 1))
