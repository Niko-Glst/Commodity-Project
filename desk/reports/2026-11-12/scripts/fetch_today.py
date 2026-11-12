import sys, yfinance as yf, pandas as pd
out = sys.argv[1]
tick = ["GC=F", "SI=F", "DX-Y.NYB", "^GSPC", "^VIX", "^TNX", "CL=F"]
d = yf.download(tick, start="2003-01-01", progress=False, auto_adjust=False)["Close"]
d.index = pd.to_datetime(d.index).tz_localize(None)
d.to_csv(f"{out}/daily.csv")
i = yf.download("GC=F", period="5d", interval="5m", progress=False, auto_adjust=False)
i.columns = [c[0] if isinstance(c, tuple) else c for c in i.columns]
i.index = i.index.tz_convert("America/New_York")
i.to_csv(f"{out}/gold_5m.csv")
print(d.loc["2026-10-28":].round(2).to_string())
print("intraday last:", i.index[-1], round(i["Close"].iloc[-1], 1), "rows", len(i))
