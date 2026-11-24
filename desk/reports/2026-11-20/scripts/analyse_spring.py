"""Run the pre-registered spring tests (gold_desk/spring.py, committed in 59b21e2 before this run) and
the Monday 23 Nov bounce. Writes reports/2026-11-20/spring.json and data/monday_*.csv.

Usage (from desk/): python reports/2026-11-20/scripts/analyse_spring.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

DESK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(DESK))
from gold_desk import data, store  # noqa: E402
from gold_desk.model import GRID_Q, Forecast  # noqa: E402
from gold_desk.spring import (SPRING_ANCHORS, big_moves, h4, h5, past_slope, spring_check,  # noqa: E402
                              spring_qualifies, spring_shift, state_space, stretch_panel, summarise_moves)

OUT = DESK / "reports" / "2026-11-20"
FRI, MON = pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-23")

gold = data.gold(data.load(refresh=False), "2026-11-20")
assert gold.index[-1] == FRI and abs(gold.iloc[-1] - 3515.4) < 0.05
records = store.read_records()
panel = stretch_panel(records, gold)

# ------------------------------------------------------------------ the pre-registered tests
t4, t5 = h4(panel), h5(panel)
checks = {n: spring_check(records, gold, panel, n) for n in SPRING_ANCHORS}
gate = {n: spring_qualifies(checks[n]) for n in SPRING_ANCHORS}

# ------------------------------------------------------------------ descriptive
ev = big_moves(gold)
moves = summarise_moves(ev, gold)
ss = state_space(gold)

# where Friday's stretch sits in history, and the shadow spring forecast from Friday's close
live = [r for r in records if r["source"] == "live"]
rec = live[-1]
assert rec["origin"] == "2026-11-20"
now = panel.set_index("origin").loc[FRI]
pos = int(now["pos"])
shadow = {}
for n in SPRING_ANCHORS:
    s_now = float(now[f"s{n}"])
    hist = panel[f"s{n}"].dropna()
    row = {"stretch": s_now, "rank_low": int((hist < s_now).sum()), "n": int(len(hist)),
           "pct": float((hist < s_now).mean()), "sma": float(gold.iloc[-n:].mean())}
    for h in (1, 5, 21):
        hh = 5 if h == 1 else h                                  # the 1-day shift scales the 1-week slope
        b = past_slope(panel, n, hh, pos)
        row[f"slope_{h}"] = b
        row[f"shift_{h}"] = spring_shift(b, s_now, float(now["sigma"]), h) if b is not None else None
    shadow[n] = row

# ------------------------------------------------------------------ Monday 23 Nov
TK = ["GC=F", "SI=F", "^GSPC", "^NDX", "DX-Y.NYB", "^TNX", "^VIX", "CL=F", "BTC-USD", "^GVZ"]
d = yf.download(TK, start="2026-11-16", end="2026-11-25", progress=False, auto_adjust=False)["Close"]
d.to_csv(OUT / "data" / "monday_daily.csv")
m5 = yf.download(["GC=F", "ES=F", "DX-Y.NYB"], start="2026-11-22", end="2026-11-24", interval="5m",
                 progress=False, auto_adjust=False)["Close"]
m5.index = pd.to_datetime(m5.index, utc=True).tz_convert("America/New_York").tz_localize(None)
m5.to_csv(OUT / "data" / "monday_5m.csv")
fri, mon = d.loc[FRI], d.loc[MON]
assert abs(fri["GC=F"] - 3515.4) < 0.05
chg = {t: float(np.log(mon[t] / fri[t])) for t in TK if t not in ("^TNX",)}
chg["^TNX"] = float(mon["^TNX"] - fri["^TNX"])

# where Monday landed in Friday's 1-day forecast, with and without the spring shift
g1 = np.asarray(rec["grid"]["1"])
pit_mon = float(np.interp(mon["GC=F"], g1, GRID_Q / 100, left=0.005, right=0.995))
pit_spring = {}
for n in SPRING_ANCHORS:
    sh = shadow[n]["shift_1"]
    if sh is not None:
        pit_spring[n] = float(np.interp(np.log(mon["GC=F"] / rec["spot"]) - sh, np.log(g1 / rec["spot"]), GRID_Q / 100,
                                        left=0.005, right=0.995))
fc = Forecast.from_record(rec)
sig1 = float(np.sqrt(fc.fit.var_next))

# Monday through the weekly driver betas (dollar, VIX, stocks, oil; real yields are not out until tomorrow)
DRV = json.load(open(DESK / "reports" / "2026-11-20-weekly" / "drivers.json"))
b = DRV["week"]
contrib = {"Dollar": b["b_r_dxy"] * chg["DX-Y.NYB"], "Stress (VIX)": b["b_d_vix"] * chg["^VIX"],
           "US stocks": b["b_r_spx"] * chg["^GSPC"], "Oil": b["b_r_oil"] * chg["CL=F"]}
explained = sum(contrib.values())

res = {
    "prereg_commit": "59b21e2",
    "h4": t4.to_dict("records"), "h5": t5.to_dict("records"),
    "h6": {str(n): checks[n].assign(first=checks[n]["first"].astype(str)).to_dict("records") for n in SPRING_ANCHORS},
    "h6_passed": {str(n): gate[n] for n in SPRING_ANCHORS},
    "moves": moves.to_dict("records"),
    "recent_moves": ev[ev["date"] >= "2025-01-01"].assign(date=lambda x: x["date"].astype(str)).to_dict("records"),
    "state_space": {k: v for k, v in ss.items() if k not in ("stretch", "value")},
    "ss_stretch_now": float(ss["stretch"].iloc[-1]), "ss_value_now": float(np.exp(ss["value"].iloc[-1])),
    "ss_stretch_pct": float((ss["stretch"] < ss["stretch"].iloc[-1]).mean()),
    "shadow": {str(n): v for n, v in shadow.items()},
    "sigma_now": float(now["sigma"]),
    "monday": {"close": float(mon["GC=F"]), "chg": chg, "pit_garch": pit_mon,
               "pit_spring": {str(k): v for k, v in pit_spring.items()}, "z": chg["GC=F"] / sig1,
               "contrib": contrib, "explained": explained, "unexplained": chg["GC=F"] - explained,
               "high": float(m5["GC=F"].loc["2026-11-22 18:00":"2026-11-23 17:00"].max()),
               "low": float(m5["GC=F"].loc["2026-11-22 18:00":"2026-11-23 17:00"].min())},
}
(OUT / "spring.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
ss["stretch"].to_frame("stretch").join(ss["value"].rename("value")).to_csv(OUT / "data" / "spring_state.csv")
panel.to_csv(OUT / "data" / "spring_panel.csv", index=False)

pd.set_option("display.width", 200)
print("H4\n", t4.round(4).to_string())
print("H5\n", t5.round(4).to_string())
for n in SPRING_ANCHORS:
    print(f"H6 anchor {n} (qualifies: {gate[n]})\n", checks[n].round(4).to_string())
print("moves\n", moves.round(3).to_string())
print("state space", {k: round(v, 4) for k, v in res["state_space"].items()}, "stretch now", res["ss_stretch_now"],
      "pct", res["ss_stretch_pct"], "value now", res["ss_value_now"])
print("shadow", json.dumps(res["shadow"], indent=1, default=float))
print("monday", json.dumps(res["monday"], indent=1, default=float))
