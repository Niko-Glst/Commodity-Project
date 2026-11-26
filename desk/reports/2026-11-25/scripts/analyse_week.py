"""Numbers for the holiday-week note, to the Wednesday 25 Nov 2026 close. Writes week.json and checks.json.

No forecast is logged: the shadow refit calls model.fit and model.simulate directly (never `python -m gold_desk
forecast`), and checks.json records a sha256 of store/live.jsonl before and after this script. Every series is cut
at 25 Nov: the snapshot has a 26 Nov Thanksgiving Globex bar with no settlement.

Usage (from desk/): python reports/2026-11-25/scripts/analyse_week.py
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DESK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(DESK))
from gold_desk import drivers as DR  # noqa: E402
from gold_desk.model import GRID_Q, H_MAX, N_PATHS, SEED, Fit, fit, simulate  # noqa: E402

N = DESK / "reports" / "2026-11-25"
D = N / "data"
CUT, FRI, PREV, YEND = pd.Timestamp("2026-11-25"), pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-13"), pd.Timestamp("2025-12-31")
DAYS = [pd.Timestamp("2026-11-23"), pd.Timestamp("2026-11-24"), CUT]
OZ_PER_T = 32150.7466
LIVE = DESK / "store" / "live.jsonl"
SHA_BEFORE = hashlib.sha256(LIVE.read_bytes()).hexdigest()
checks = []


def check(name, ok, detail):
    checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})


# ------------------------------------------------------------------ prices, cut at Wednesday
daily = pd.read_csv(D / "daily.csv", index_col=0, parse_dates=True).loc[:CUT]
fred = pd.read_csv(D / "fred.csv", index_col=0, parse_dates=True).loc[:CUT]
USED = ["GC=F", "SI=F", "^GSPC", "^NDX", "DX-Y.NYB", "^TNX", "^VIX", "GDX", "GDXJ", "GLD", "IAU", "HG=F", "BZ=F",
        "^STOXX50E", "^N225", "EEM", "BTC-USD", "CL=F", "^GVZ"]
missing = [t for t in USED if pd.isna(daily.loc[CUT, t])] if daily.index[-1] == CUT else USED
check("Every series used has a value on Wed 25 Nov and nothing later (Thanksgiving bar dropped)", not missing,
      f"last date {daily.index[-1].date()}; missing on 25 Nov: {missing or 'none'}")
gold = daily["GC=F"].dropna()
con = pd.read_csv(D / "gold_contracts_daily.csv", index_col=0, parse_dates=True)
same = np.allclose(gold.loc[FRI:CUT].values, con.loc[FRI:CUT, "GCZ26.CMX"].values, atol=0.05)
check("GC=F is the December contract from 20 to 25 Nov (no roll inside the window)", bool(same),
      f"GC=F {gold.loc[FRI:CUT].round(1).tolist()} vs GCZ26 {con.loc[FRI:CUT, 'GCZ26.CMX'].round(1).tolist()}")
roll_gap = float(con.loc[CUT, "GCG27.CMX"] - con.loc[CUT, "GCZ26.CMX"])

tr = pd.read_csv(D / "treasury_real_yield_2026.csv")
tr["Date"] = pd.to_datetime(tr["Date"], format="%m/%d/%Y")
real10 = tr.set_index("Date").sort_index()["10 YR"].astype(float).loc[:CUT]
common = fred["DFII10"].dropna().loc["2026-10-01":].index.intersection(real10.index)
gap = float((fred["DFII10"].reindex(common) - real10.reindex(common)).abs().max())
check("Treasury 10-yr real yield matches FRED DFII10 on every common day since 1 Oct", gap < 0.015, f"max gap {gap:.3f} pp over {len(common)} days")
real10 = real10.combine_first(fred["DFII10"].dropna())          # FRED for history, Treasury for days H.15 has not published yet


def at(s, d):
    s = s.dropna()
    return float(s.loc[:d].iloc[-1])


# day-by-day table
COLS = [("Gold (COMEX Dec)", "GC=F"), ("Silver", "SI=F"), ("S&P 500", "^GSPC"), ("Nasdaq-100", "^NDX"),
        ("Dollar index", "DX-Y.NYB"), ("US 10-yr yield", "^TNX"), ("VIX", "^VIX"), ("Gold miners (GDX)", "GDX"),
        ("Junior miners (GDXJ)", "GDXJ"), ("GLD", "GLD"), ("IAU", "IAU")]
days = []
for d in [FRI] + DAYS:
    row = {"date": str(d.date())}
    for name, t in COLS:
        row[t] = at(daily[t], d)
    row["real10"] = float(real10.loc[d])
    days.append(row)

# performance: Friday to Wednesday, one month, year to date
ASSETS = [("Gold", "GC=F"), ("Silver", "SI=F"), ("Gold miners (GDX)", "GDX"), ("Junior miners (GDXJ)", "GDXJ"),
          ("Copper", "HG=F"), ("Oil (Brent)", "BZ=F"), ("Dollar (DXY)", "DX-Y.NYB"), ("S&P 500", "^GSPC"),
          ("Nasdaq-100", "^NDX"), ("EuroStoxx 50", "^STOXX50E"), ("Nikkei 225", "^N225"), ("MSCI EM (EEM)", "EEM"),
          ("Bitcoin", "BTC-USD")]
perf = []
m1 = gold.index[-22]
for name, t in ASSETS:
    s = daily[t].dropna()
    last = float(s.iloc[-1])
    perf.append({"asset": name, "ticker": t, "close": last, "wtd": last / at(s, FRI) - 1, "m1": last / at(s, m1) - 1,
                 "ytd": last / at(s, YEND) - 1})
for name, t, s in (("US 10-yr yield", "^TNX", daily["^TNX"]), ("US 10-yr real yield", "real10", real10),
                   ("US 2-yr yield (to 24 Nov)", "DGS2", fred["DGS2"])):
    s = s.dropna()
    perf.append({"asset": name, "ticker": t, "close": float(s.iloc[-1]), "wtd": (float(s.iloc[-1]) - at(s, FRI)) * 100,
                 "m1": (float(s.iloc[-1]) - at(s, m1)) * 100, "ytd": (float(s.iloc[-1]) - at(s, YEND)) * 100, "unit": "bp"})

# miners against gold
r = np.log(daily[["GC=F", "GDX", "GDXJ"]].dropna()).diff().dropna().iloc[-252:]
miners = {}
for t in ("GDX", "GDXJ"):
    b = float(np.polyfit(r["GC=F"], r[t], 1)[0])
    s = daily[t].dropna()
    miners[t] = {"beta_1y": b, "wtd": float(s.iloc[-1] / at(s, FRI) - 1), "ytd": float(s.iloc[-1] / at(s, YEND) - 1),
                 "from_high": float(s.iloc[-1] / s.loc["2026-01-01":].max() - 1)}
g_wtd, g_ytd = float(gold.iloc[-1] / gold.loc[FRI] - 1), float(gold.iloc[-1] / gold.loc[YEND] - 1)


# ------------------------------------------------------------------ fund flows (State Street NAV history)
def nav(t):
    g = pd.read_excel(D / f"ssga_navhist_{t}.xlsx", header=None, engine="openpyxl")
    s0 = g.index[g[0].astype(str).str.strip() == "Date"][0] + 1
    g = g.iloc[s0:, :3]
    g.columns = ["date", "nav", "shares"]
    g["date"] = pd.to_datetime(g["date"], format="%d-%b-%Y", errors="coerce")
    g[["nav", "shares"]] = g[["nav", "shares"]].apply(pd.to_numeric, errors="coerce")
    g = g.dropna().set_index("date").sort_index().loc[:CUT]
    g["flow"] = g.shares.diff() * g.nav
    g["aum"] = g.shares * g.nav
    return g


i5 = pd.read_csv(D / "gold_5m_contracts.csv", index_col=0, parse_dates=True)["GCZ26.CMX"].dropna()
flows = {}
NAVS = {}
for t in ("GLD", "GLDM", "SPY", "XLK", "XLU", "XLP", "BIL"):
    g = nav(t)
    NAVS[t] = g
    wk = g.loc[DAYS[0]:CUT, "flow"]
    weekly = g["flow"].resample("W-FRI").sum().loc["2026-09-01":]
    flows[t] = {"last": str(g.index[-1].date()), "days": {str(k.date()): float(v) for k, v in wk.items()},
                "wtd": float(wk.sum()), "prev": float(g.loc["2026-11-16":FRI, "flow"].sum()),
                "ytd": float(g.loc["2026-01-01":, "flow"].sum()), "aum": float(g["aum"].iloc[-1]),
                "weekly": {str(k.date()): float(v) for k, v in weekly.items()}}
# GLD tonnes: shares x ounces per share (60-day median of NAV / COMEX price)
for t in ("GLD", "GLDM"):
    g = NAVS[t]
    oz = (g.nav / gold.reindex(g.index, method="ffill")).rolling(60, min_periods=20).median()
    tonnes = g.shares * oz / OZ_PER_T
    flows[t]["tonnes"] = float(tonnes.iloc[-1])
    flows[t]["tonnes_wtd"] = float(tonnes.iloc[-1] - tonnes.loc[:FRI].iloc[-1])
    flows[t]["tonnes_ytd"] = float(tonnes.iloc[-1] - tonnes.loc[:YEND].iloc[-1])
    # The NAV is struck at the LBMA PM price (10:00 New York), COMEX settles at 13:30. In a year of 4% days that
    # gap blurs even weekly NAV changes (on 25 Nov the NAV caught the post-PCE low), so the integrity check uses
    # the fund's market close, which trades with COMEX, and reports the NAV figure as information.
    if t in daily:
        lv = pd.concat([daily[t].rename("px"), g.nav.rename("nav"), gold.rename("gc")], axis=1, join="inner").loc["2025-01-01":CUT]
        wc = np.log(lv.resample("W-FRI").last()).diff().dropna().corr()
        check(f"{t} market price moves with COMEX gold (weekly correlation since 2025 above 0.95)", float(wc.loc["px", "gc"]) > 0.95,
              f"price {float(wc.loc['px', 'gc']):.3f}; NAV {float(wc.loc['nav', 'gc']):.3f} (NAV struck at 10:00 New York)")
    flows[t]["nav_wed_chg"] = float(g.nav.loc[CUT] / g.nav.loc[:CUT].iloc[-2] - 1)
    if t == "GLD":                                 # the NAV follows the December contract at 10:00 New York
        b10 = {d: float(i5.loc[:f"{d.date()} 10:00"].iloc[-1]) for d in [FRI] + DAYS}
        gaps = []
        for p_, d in zip([FRI] + DAYS[:-1], DAYS):
            gaps.append(abs((g.nav.loc[d] / g.nav.loc[p_] - 1) - (b10[d] / b10[p_] - 1)) * 100)
        check("GLD daily NAV change matches the 10:00 ET December bar on 23-25 Nov (within 0.5 pp)", max(gaps) < 0.5,
              f"gaps {[round(float(x), 2) for x in gaps]} pp")

ici = pd.read_excel(D / "ici_mm_summary_2026.xls", header=None, engine="xlrd")
ici = ici[pd.to_datetime(ici[0].astype(str).str.strip(), format="%m/%d/%Y", errors="coerce").notna()]
mmf = pd.DataFrame({"total": ici[2].astype(float).values, "inst": ici[14].astype(float).values,
                    "retail": ici[26].astype(float).values},
                   index=pd.to_datetime(ici[0].astype(str).str.strip(), format="%m/%d/%Y")).dropna().sort_index()
check("ICI money funds: institutional + retail = total", float((mmf.inst + mmf.retail - mmf.total).abs().max()) < 2,
      f"max gap {float((mmf.inst + mmf.retail - mmf.total).abs().max()):.1f} $m")
mm = {"date": str(mmf.index[-1].date()), "total_bn": float(mmf.total.iloc[-1] / 1000),
      "chg_bn": float((mmf.total.iloc[-1] - mmf.total.iloc[-2]) / 1000),
      "chg4_bn": float((mmf.total.iloc[-1] - mmf.total.iloc[-5]) / 1000),
      "inst_chg_bn": float((mmf.inst.iloc[-1] - mmf.inst.iloc[-2]) / 1000),
      "retail_chg_bn": float((mmf.retail.iloc[-1] - mmf.retail.iloc[-2]) / 1000),
      "first": str(mmf.index[0].date()), "since_first_bn": float((mmf.total.iloc[-1] - mmf.total.iloc[0]) / 1000)}

# ------------------------------------------------------------------ the model: the 20 Nov forecast and a shadow refit
recs = [json.loads(line) for line in LIVE.read_text(encoding="utf-8").splitlines() if line.strip()]
rec = [x for x in recs if x["origin"] == "2026-11-20"][0]
f20 = Fit(**rec["fit"])
p20 = rec["spot"] * np.exp(simulate(f20, horizon=H_MAX, n_paths=N_PATHS, seed=SEED)[:, 1:])
rebuilt = {h: float(np.abs(np.percentile(p20[:, h - 1], GRID_Q) - np.asarray(rec["grid"][str(h)])).max()) for h in (1, 5)}
check("Rebuilt 20 Nov paths reproduce the stored 1-day and 1-week quantile grids", max(rebuilt.values()) < 0.02,
      f"max gap ${max(rebuilt.values()):.3f}")
pit20 = {}
for k, d in enumerate(DAYS, start=1):
    px = float(gold.loc[d])
    pit20[str(d.date())] = {"day": k, "close": px, "pit": float((p20[:, k - 1] < px).mean()),
                            "q5": float(np.percentile(p20[:, k - 1], 5)), "q95": float(np.percentile(p20[:, k - 1], 95))}

f_w = fit(gold)
paths_w = simulate(f_w, horizon=H_MAX, n_paths=N_PATHS, seed=SEED)
px_w = float(gold.iloc[-1]) * np.exp(paths_w[:, 1:])
shadow = {"vol_next": f_w.vol_next, "vol_long_run": f_w.vol_long_run, "nu": f_w.nu, "half_life": f_w.half_life,
          "vol_next_20nov": f20.vol_next,
          "q": {str(h): {str(q): float(np.percentile(px_w[:, h - 1], q)) for q in (1, 5, 25, 50, 75, 95, 99)} for h in (1, 5, 21)},
          "touch_1w": {str(lv): float(((px_w[:, :5].min(axis=1) <= lv) if lv < gold.iloc[-1] else (px_w[:, :5].max(axis=1) >= lv)).mean())
                       for lv in (3250.0, 3430.0, 3700.0, 3886.3)}}

# ------------------------------------------------------------------ partial-week attribution (Fri 20 -> Wed 25)
frame = pd.DataFrame({"gold": daily["GC=F"], "dxy": daily["DX-Y.NYB"], "vix": daily["^VIX"], "spx": daily["^GSPC"],
                      "oil": daily["CL=F"]}).join(fred[["DFII10", "T10YIE"]].rename(columns={"DFII10": "real", "T10YIE": "be"}), how="outer")
frame = frame[frame.index >= "2003-01-01"].sort_index().loc[:CUT]
real_fill = pd.isna(frame.loc[CUT, "real"])
if real_fill:                                      # H.15 lags; Treasury's par real curve is the series behind DFII10
    frame.loc[CUT, "real"] = float(real10.loc[CUT])
pw = DR.weekly_panel(frame, NAVS["GLD"][["nav", "shares"]])
FAC = ["d_real", "d_be", "r_dxy", "d_vix", "r_spx", "r_oil", "flow"]       # positioning left out: no COT report for 23-25 Nov
past = pw.loc[:FRI, ["r_gold"] + FAC].dropna().iloc[-156:]
X = np.column_stack([np.ones(len(past)), past[FAC].values])
beta = np.linalg.lstsq(X, past["r_gold"].values, rcond=None)[0]
xw = pw.iloc[-1]
check("The partial week in the panel runs from Fri 20 to Wed 25 Nov", abs(xw["r_gold"] - np.log(gold.loc[CUT] / gold.loc[FRI])) < 1e-9,
      f"r_gold {xw['r_gold']:.5f}")
contrib = {f: float(b * xw[f]) for f, b in zip(FAC, beta[1:])}
attr = {"r_gold": float(xw["r_gold"]), "contrib": contrib, "betas": {f: float(b) for f, b in zip(FAC, beta[1:])},
        "alpha_weekly": float(beta[0]), "residual": float(xw["r_gold"] - sum(contrib.values())),
        "x": {f: float(xw[f]) for f in FAC}, "window": [str(past.index[0].date()), str(past.index[-1].date())],
        "real_from_treasury": bool(real_fill)}

# ------------------------------------------------------------------ cycles (monthly averages, from the 19 Nov note)
cyc = json.loads((DESK / "reports" / "2026-11-19-cycles" / "cycles.json").read_text(encoding="utf-8"))
peaks = cyc["peaks"]
p26 = [p for p in peaks if p["peak"] == "2026-02"][0]
nov_mtd = float(gold.loc["2026-11-01":CUT].mean())
path26 = list(cyc["paths"]["2026-02"])
check("2026 cycle path runs Feb to Nov (10 months)", len(path26) == 10, f"{len(path26)} months")
path26[-1] = nov_mtd / p26["peak_avg"] - 1
cycles = {"peaks": peaks, "paths": {k: v for k, v in cyc["paths"].items() if k != "2026-02"}, "path26": path26,
          "nov_mtd": nov_mtd, "peak26_avg": p26["peak_avg"], "nov_avg_19nov": cyc["nov_avg"],
          "at9": {k: (v[9] if len(v) > 9 else None) for k, v in cyc["paths"].items() if k != "2026-02"},
          "real_1980_today": cyc["real_1980_peak_today"], "real_2011_today": cyc["real_2011_peak_today"],
          "daily_peak": float(gold.loc["2026-01-01":].max()), "daily_peak_date": str(gold.loc["2026-01-01":].idxmax().date()),
          "daily_dd": float(gold.iloc[-1] / gold.loc["2026-01-01":].max() - 1)}

# ------------------------------------------------------------------ positioning and volatility
c = pd.read_csv(D / "cftc_gold_full.csv")
c["date"] = pd.to_datetime(c.report_date_as_yyyy_mm_dd)
num = lambda col: pd.to_numeric(c[col], errors="coerce")  # noqa: E731
mm_n = (num("m_money_positions_long_all") - num("m_money_positions_short_all")) * 100 / OZ_PER_T
share = (num("m_money_positions_long_all") - num("m_money_positions_short_all")) / num("open_interest_all")
cot = {"date": str(c["date"].iloc[-1].date()), "mm_t": float(mm_n.iloc[-1]), "mm_t_prev": float(mm_n.iloc[-2]),
       "share": float(share.iloc[-1]), "share_prev": float(share.iloc[-2]), "share_pct": float((share < share.iloc[-1]).mean())}
rr = np.log(gold).diff().dropna()
gvz = daily["^GVZ"].dropna()
vol = {"gvz": float(gvz.iloc[-1]), "gvz_fri": at(gvz, FRI), "rv21": float(rr.iloc[-21:].std() * np.sqrt(252)),
       "vix": float(daily["^VIX"].dropna().iloc[-1])}

# ------------------------------------------------------------------ intraday (December contract, 5-minute)
wed = i5.loc["2026-11-25 00:00":"2026-11-25 17:00"]
intraday = {"wed_pre_pce": float(i5.loc[:"2026-11-25 08:25"].iloc[-1]), "wed_low": float(wed.min()),
            "wed_low_time": wed.idxmin().strftime("%H:%M"), "wed_1655": float(i5.loc[:"2026-11-25 16:55"].iloc[-1]),
            "wed_settle": float(gold.loc[CUT])}
check("5-minute December bars agree with the daily settlements on Mon and Tue at 13:30 ET",
      all(abs(float(i5.loc[:f"{d.date()} 13:30"].iloc[-1]) - float(gold.loc[d])) < 3 for d in DAYS[:2]),
      str([round(float(i5.loc[:f"{d.date()} 13:30"].iloc[-1]), 1) for d in DAYS[:2]]))

out = {"cut": str(CUT.date()), "gold": {"fri": float(gold.loc[FRI]), "close": float(gold.iloc[-1]), "wtd": g_wtd, "ytd": g_ytd,
       "prev_week": float(gold.loc[FRI] / gold.loc[PREV] - 1), "roll_gap": roll_gap},
       "days": days, "perf": perf, "miners": miners, "flows": flows, "mmf": mm, "pit20": pit20, "rebuilt_gap": rebuilt,
       "shadow": shadow, "attr": attr, "cycles": cycles, "cot": cot, "vol": vol, "intraday": intraday}
(N / "week.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
sha_after = hashlib.sha256(LIVE.read_bytes()).hexdigest()
check("store/live.jsonl unchanged by this script (no forecast logged)", sha_after == SHA_BEFORE, f"sha256 {sha_after[:16]}")
(N / "checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
print("\n".join(f"{c_['result']}  {c_['check']}: {c_['detail']}" for c_ in checks))
print(json.dumps({k: out[k] for k in ("gold", "pit20", "attr", "intraday", "mmf", "vol", "cot")}, indent=1, default=float)[:4000])
print({t: (round(v["wtd"] / 1e6), round(v["prev"] / 1e6), round(v["ytd"] / 1e9, 2), v["last"]) for t, v in flows.items()})
print("miners", miners, "gold wtd", g_wtd, "ytd", g_ytd)
print("shadow", {k: v for k, v in shadow.items() if k != "q"}, shadow["q"]["5"])
print("cycles at 9", cycles["at9"], "2026 now", path26[-1], "nov_mtd", nov_mtd)
