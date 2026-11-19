"""Snapshot for the gold-cycles note: monthly gold since 1833 (datahub, World Gold Council / LBMA), daily COMEX
futures since 2000 (from the 19 Nov summary snapshot), US CPI and 10-year yields (FRED).

Usage (from desk/): python reports/2026-11-19-cycles/scripts/fetch_history.py reports/2026-11-19-cycles/data
"""
import io
import sys
from pathlib import Path

import pandas as pd
import requests

out = Path(sys.argv[1])
H = {"User-Agent": "Mozilla/5.0 (research-script)"}
r = requests.get("https://datahub.io/core/gold-prices/r/monthly.csv", headers=H, timeout=60)
pd.read_csv(io.StringIO(r.text)).to_csv(out / "gold_monthly_datahub.csv", index=False)
fred = {}
for sid in ("CPIAUCSL", "GS10", "DFII10"):
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=H, timeout=60)
    fred[sid] = pd.to_numeric(pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True).iloc[:, 0], errors="coerce")
pd.DataFrame({k: v for k, v in fred.items() if k != "DFII10"}).to_csv(out / "fred_monthly.csv")
fred["DFII10"].dropna().to_csv(out / "fred_dfii10_daily.csv")
daily = pd.read_csv(out.parent.parent / "2026-11-19" / "data" / "daily.csv", index_col=0, parse_dates=True)
daily[["GC=F"]].dropna().to_csv(out / "gc_daily.csv")
print("datahub rows", len(pd.read_csv(out / "gold_monthly_datahub.csv")), "| GC=F last", daily["GC=F"].dropna().index[-1].date())
