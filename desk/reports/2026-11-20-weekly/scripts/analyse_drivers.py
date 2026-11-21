"""Run the pre-registered driver tests (gold_desk.drivers, rules committed in 0a7239c) and the attribution.

Usage (from desk/): python reports/2026-11-20-weekly/scripts/analyse_drivers.py reports/2026-11-20-weekly
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

N = Path(sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from gold_desk import drivers as DR  # noqa: E402

D = N / "data"
daily = pd.read_csv(D / "daily.csv", index_col=0, parse_dates=True)
fred = pd.read_csv(D / "fred.csv", index_col=0, parse_dates=True)
frame = pd.DataFrame({"gold": daily["GC=F"], "dxy": daily["DX-Y.NYB"], "vix": daily["^VIX"], "spx": daily["^GSPC"],
                      "oil": daily["CL=F"]}).join(fred[["DFII10", "T10YIE"]].rename(columns={"DFII10": "real", "T10YIE": "be"}),
                                                  how="outer")
frame = frame[frame.index >= "2003-01-01"].sort_index()
g = pd.read_excel(D / "ssga_navhist_GLD.xlsx", header=None, engine="openpyxl")
s0 = g.index[g[0].astype(str).str.strip() == "Date"][0] + 1
g = g.iloc[s0:, :3]
g.columns = ["date", "nav", "shares"]
g["date"] = pd.to_datetime(g["date"], format="%d-%b-%Y", errors="coerce")
g[["nav", "shares"]] = g[["nav", "shares"]].apply(pd.to_numeric, errors="coerce")
g = g.dropna().set_index("date").sort_index()
c = pd.read_csv(D / "cftc_gold_full.csv")
cot = pd.DataFrame({"mm_net": (c.m_money_positions_long_all.astype(float) - c.m_money_positions_short_all.astype(float)).values,
                    "oi": c.open_interest_all.astype(float).values}, index=pd.to_datetime(c.report_date_as_yyyy_mm_dd).values)
p = DR.weekly_panel(frame, g, cot)
p = p[p.index <= "2026-11-20"]
attr = DR.attribution(p)
h1, h2, h3 = DR.decoupling(p), DR.procyclical_flows(p), DR.h3(p)
ev = DR.stress_selloffs(p)
allw = {h: float(np.expm1((np.log(p["gold"]).shift(-h) - np.log(p["gold"])).dropna()).mean()) for h in (4, 13, 26)}
fac = [k for k in DR.FACTORS if f"c_{k}" in attr]
y26 = attr.loc["2026-01-01":]
since_peak = attr.loc["2026-01-30":]
week = attr.iloc[-1]
mon = attr.loc["2026-01-01":].groupby(attr.loc["2026-01-01":].index.to_period("M")).sum()
# rolling 52-week betas on real yield and dollar for the "changing links" chart (univariate, descriptive)
d = p[["r_gold", "d_real", "r_dxy"]].dropna()
roll = pd.DataFrame({"beta_real": d["r_gold"].rolling(52).cov(d["d_real"]) / d["d_real"].rolling(52).var(),
                     "corr_real": d["r_gold"].rolling(52).corr(d["d_real"]),
                     "corr_dxy": d["r_gold"].rolling(52).corr(d["r_dxy"])}).dropna()
out = {"panel_first": str(p.index[0].date()), "last_week": str(p.index[-1].date()),
       "attr_first": str(attr.index[0].date()), "explained_oos": DR.explained_share(attr),
       "explained_2026": DR.explained_share(y26),
       "week": {"r_gold": float(week["r_gold"]), "alpha": float(week["alpha"]), "residual": float(week["residual"]),
                **{f: float(week[f"c_{f}"]) for f in fac}, **{f"b_{f}": float(week[f"b_{f}"]) for f in fac}},
       "ytd": {"r_gold": float(y26["r_gold"].sum()), "alpha": float(y26["alpha"].sum()), "residual": float(y26["residual"].sum()),
               **{f: float(y26[f"c_{f}"].sum()) for f in fac}},
       "since_peak": {"r_gold": float(since_peak["r_gold"].sum()), "alpha": float(since_peak["alpha"].sum()),
                      "residual": float(since_peak["residual"].sum()), **{f: float(since_peak[f"c_{f}"].sum()) for f in fac}},
       "monthly": {str(k): {"r_gold": float(v["r_gold"]), "residual": float(v["residual"]), "alpha": float(v["alpha"]),
                            **{f: float(v[f"c_{f}"]) for f in fac}} for k, v in mon.iterrows()},
       "last12": [{"week": str(i.date()), "r_gold": float(r["r_gold"]), "residual": float(r["residual"]), "alpha": float(r["alpha"]),
                   **{f: float(r[f"c_{f}"]) for f in fac}} for i, r in attr.iloc[-12:].iterrows()],
       "h1": h1, "h2": h2, "h3": json.loads(h3.to_json(orient="records")),
       "events": json.loads(ev.to_json(orient="records", date_format="iso")), "events_all_weeks": allw,
       "rolling": {"dates": [str(x.date()) for x in roll.index], **{k: roll[k].round(4).tolist() for k in roll}},
       "factors": {k: DR.FACTORS[k] for k in fac}}
(N / "drivers.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
pd.set_option("display.width", 200)
print("attribution from", out["attr_first"], "explained OOS", round(out["explained_oos"], 3), "2026", round(out["explained_2026"], 3))
print("H1", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in h1.items()})
print("H2", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in h2.items()})
print(h3.round(4).to_string(index=False))
print("week", {k: round(v, 4) for k, v in out["week"].items() if not k.startswith("b_")})
print("ytd", {k: round(v, 4) for k, v in out["ytd"].items()})
print("since peak", {k: round(v, 4) for k, v in out["since_peak"].items()})
print(ev.round(3).to_string(index=False)); print("all weeks", {k: round(v, 4) for k, v in allw.items()})
