"""Snapshot for the 18 Nov flash note: daily closes since 2003 and 5-minute GC=F bars (Yahoo Finance)."""
import sys

import pandas as pd
import yfinance as yf

out = sys.argv[1]
tick = ["GC=F", "SI=F", "DX-Y.NYB", "^GSPC", "ES=F", "^VIX", "^TNX", "CL=F", "^GVZ"]
d = yf.download(tick, start="2003-01-01", progress=False, auto_adjust=False)["Close"]
d.index = pd.to_datetime(d.index).tz_localize(None)
d.to_csv(f"{out}/daily.csv")
i = yf.download("GC=F", period="5d", interval="5m", progress=False, auto_adjust=False)
i.columns = [c[0] if isinstance(c, tuple) else c for c in i.columns]
i.index = i.index.tz_convert("America/New_York")
i.to_csv(f"{out}/gold_5m.csv")
print(d.loc["2026-11-05":].round(2).to_string())
print("intraday last:", i.index[-1], round(i["Close"].iloc[-1], 1), "rows", len(i))
