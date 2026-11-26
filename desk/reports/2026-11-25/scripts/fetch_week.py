"""Snapshot for the Thanksgiving-week note, to the Wednesday 25 Nov 2026 close.

Usage (from desk/): python reports/2026-11-25/scripts/fetch_week.py reports/2026-11-25/data
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
tick = ["GC=F", "SI=F", "HG=F", "CL=F", "BZ=F", "DX-Y.NYB", "^GSPC", "^NDX", "^STOXX50E", "000300.SS", "^BSESN",
        "^N225", "EFA", "EEM", "^TNX", "^VIX", "^VIX3M", "^MOVE", "^GVZ", "BTC-USD", "GLD", "IAU", "GDX", "GDXJ", "DBC",
        "EURUSD=X", "GBPUSD=X", "JPY=X", "CNY=X", "INR=X", "CHF=X"]
d = yf.download(tick, start="1999-01-01", progress=False, auto_adjust=False)["Close"]
d.index = pd.to_datetime(d.index).tz_localize(None)
d.to_csv(out / "daily.csv")
i = yf.download("GC=F", start="2026-11-16", end="2026-11-27", interval="5m", progress=False, auto_adjust=False)
i.columns = [c[0] if isinstance(c, tuple) else c for c in i.columns]
i.index = i.index.tz_convert("America/New_York")
i.to_csv(out / "gold_5m.csv")
log["daily_last"] = {t: str(d[t].dropna().index[-1].date()) for t in tick if d[t].notna().any()}
log["gold_5m"] = [str(i.index[0]), str(i.index[-1])]
fr = {}
for sid in ["DFII10", "T10YIE", "T5YIFR", "DGS2", "DGS10", "GS10", "CPIAUCSL", "CPILFESL", "GFDEBTN", "GFDEGDQ188S",
            "FYFSGDA188S", "WALCL", "DTWEXBGS", "DCOILBRENTEU", "FEDFUNDS", "DFEDTARU", "BAMLH0A0HYM2", "M2SL", "UNRATE"]:
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=H, timeout=60)
    s = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True).iloc[:, 0]
    fr[sid] = pd.to_numeric(s, errors="coerce")
    log[f"fred_{sid}"] = str(fr[sid].dropna().index[-1].date())
pd.DataFrame(fr).to_csv(out / "fred.csv")
url = ("https://publicreporting.cftc.gov/resource/72hh-3qpy.json?$where=cftc_contract_market_code='088691' AND "
       "report_date_as_yyyy_mm_dd >= '2006-06-01'&$order=report_date_as_yyyy_mm_dd&$limit=5000")
c = pd.DataFrame(requests.get(url, headers=H, timeout=60).json())
c.to_csv(out / "cftc_gold_full.csv", index=False)
log["cftc_last"] = str(c.report_date_as_yyyy_mm_dd.iloc[-1])[:10]
for t in ["GLD", "GLDM", "SPY", "XLK", "XLU", "XLP", "BIL"]:
    r = requests.get(f"https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/navhist-us-en-{t.lower()}.xlsx",
                     headers=H, timeout=60)
    if r.status_code == 200 and r.content[:2] == b"PK":
        (out / f"ssga_navhist_{t}.xlsx").write_bytes(r.content)
        log[f"ssga_{t}"] = "ok"
r = requests.get("https://www.ici.org/mm_summary_data_2026.xls", headers=H, timeout=60)
(out / "ici_mm_summary_2026.xls").write_bytes(r.content)
r = requests.get("https://datahub.io/core/gold-prices/r/monthly.csv", headers=H, timeout=60)
(out / "gold_monthly_datahub.csv").write_text(r.text, encoding="utf-8")
# per-contract COMEX gold (the continuous GC=F rolls Dec -> Feb in this window) and Treasury par real yields
pc_ = yf.download(["GCZ26.CMX", "GCG27.CMX"], start="2026-10-01", end="2026-11-27", progress=False, auto_adjust=False)["Close"]
pc_.index = pd.to_datetime(pc_.index).tz_localize(None)
pc_.to_csv(out / "gold_contracts_daily.csv")
log["contracts_daily_last"] = str(pc_.dropna(how="all").index[-1].date())
c5 = {}
for t in ["GCZ26.CMX", "GCG27.CMX", "GC=F"]:
    x = yf.download(t, start="2026-11-20", end="2026-11-27", interval="5m", progress=False, auto_adjust=False)
    s = x["Close"].iloc[:, 0] if isinstance(x.columns, pd.MultiIndex) else x["Close"]
    s.index = pd.to_datetime(s.index, utc=True).tz_convert("America/New_York").tz_localize(None)
    c5[t] = s
c5 = pd.DataFrame(c5)
c5.to_csv(out / "gold_5m_contracts.csv")
log["contracts_5m"] = [str(c5.index[0]), str(c5.index[-1])]
r = requests.get("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all"
                 "?type=daily_treasury_real_yield_curve&field_tdr_date_value=2026&page&_format=csv", headers=H, timeout=60)
(out / "treasury_real_yield_2026.csv").write_text(r.text, encoding="utf-8")
log["treasury_real_yield_first_row"] = r.text.splitlines()[1][:10] if r.status_code == 200 else f"HTTP {r.status_code}"
(out / "fetch_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in log.items() if k != "daily_last"}, indent=1))
print("missing tickers:", [t for t in tick if t not in log["daily_last"]])
print(d.loc["2026-11-18":, ["GC=F", "SI=F", "DX-Y.NYB", "^GSPC", "^TNX", "^VIX", "BTC-USD"]].round(2).to_string())
