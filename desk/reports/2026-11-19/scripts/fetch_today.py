"""Snapshot for the 19 Nov summary note: daily closes, 5-minute gold, FRED rates and spreads, CFTC gold positioning."""
import io
import sys

import pandas as pd
import requests
import yfinance as yf

out = sys.argv[1]
H = {"User-Agent": "research-script/1.0"}
tick = ["GC=F", "SI=F", "HG=F", "CL=F", "DX-Y.NYB", "^GSPC", "ES=F", "^VIX", "^TNX", "^GVZ", "BTC-USD"]
d = yf.download(tick, start="2003-01-01", progress=False, auto_adjust=False)["Close"]
d.index = pd.to_datetime(d.index).tz_localize(None)
d.to_csv(f"{out}/daily.csv")
i = yf.download("GC=F", period="5d", interval="5m", progress=False, auto_adjust=False)
i.columns = [c[0] if isinstance(c, tuple) else c for c in i.columns]
i.index = i.index.tz_convert("America/New_York")
i.to_csv(f"{out}/gold_5m.csv")
fred = {}
for sid in ["DFII10", "DGS2", "DGS10", "T10YIE", "BAMLH0A0HYM2"]:
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", headers=H, timeout=60)
    s = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True).iloc[:, 0]
    fred[sid] = pd.to_numeric(s, errors="coerce")
pd.DataFrame(fred).to_csv(f"{out}/fred.csv")
url = ("https://publicreporting.cftc.gov/resource/72hh-3qpy.json?$where=cftc_contract_market_code='088691' AND "
       "report_date_as_yyyy_mm_dd >= '2024-01-01'&$select=report_date_as_yyyy_mm_dd,m_money_positions_long_all,"
       "m_money_positions_short_all,open_interest_all&$order=report_date_as_yyyy_mm_dd&$limit=5000")
c = pd.DataFrame(requests.get(url, headers=H, timeout=60).json())
c.to_csv(f"{out}/cftc_gold.csv", index=False)
print(d.loc["2026-11-10":].round(2).to_string())
print("intraday last:", i.index[-1], round(i["Close"].iloc[-1], 1), "low", round(i["Low"].loc[i.index >= i.index[-1].normalize() - pd.Timedelta(hours=6)].min(), 1))
print(pd.DataFrame(fred).dropna(how="all").tail(4).to_string())
print(c.tail(2).to_string())
