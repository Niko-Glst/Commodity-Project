"""20 Nov full report: latest move, model, macro, flows, history, validation tests, and number checks.

Usage (from desk/): python reports/2026-11-20/scripts/analyse_report.py reports/2026-11-20
Writes results.json (every number in the report) and checks.json (cross-checks with PASS/FAIL).
"""
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

N = Path(sys.argv[1])
DESK = Path(__file__).resolve().parents[3]
REPO = DESK.parent
sys.path.insert(0, str(DESK))
from gold_desk import store  # noqa: E402
from gold_desk.backtest import coverage, iv_targets, score  # noqa: E402
from gold_desk.model import GRID_Q, Fit, fit, simulate  # noqa: E402

D = N / "data"
checks = []


def check(name, ok, detail):
    checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})


def d_(ts):
    return f"{pd.Timestamp(ts).day} {pd.Timestamp(ts):%b %Y}"


# ------------------------------------------------------------------ prices
daily = pd.read_csv(D / "daily.csv", index_col=0, parse_dates=True)
intra = pd.read_csv(D / "gold_5m.csv", index_col=0)
intra.index = pd.to_datetime(intra.index, utc=True).tz_convert("America/New_York").tz_localize(None)
g = daily["GC=F"].dropna()
TODAY = g.index[-1]
now, asof = float(intra["Close"].iloc[-1]), intra.index[-1]
check("Latest gold price: 5-minute bar vs daily bar", abs(now / g.iloc[-1] - 1) < 0.002,
      f"5-min {now:,.1f} at {asof:%H:%M} ET vs daily row {g.iloc[-1]:,.1f}")
g.iloc[-1] = now
hist = g.iloc[:-1]                                    # finished closes, to Thursday 19 Nov
y_close = float(hist.iloc[-1])
wk_close = float(hist.loc[:"2026-11-13"].iloc[-1])
weekly = g.groupby(g.index.to_period("W-FRI")).last()
week_ret = float(weekly.iloc[-1] / weekly.iloc[-2] - 1)
check("Weekly change computed two ways", abs(week_ret - (now / wk_close - 1)) < 1e-9,
      f"weekly closes {week_ret:+.2%}; direct {now / wk_close - 1:+.2%}")
worse_weeks = weekly.pct_change().iloc[:-1]
n_worse_weeks = int((worse_weeks <= week_ret).sum())
dret = g.pct_change()
n_worse_days = int((dret.iloc[:-1] <= dret.iloc[-1]).sum())
last_worse_day = dret.iloc[:-1][dret.iloc[:-1] <= dret.iloc[-1]].index.max()
peak_close, peak_date = float(g.max()), g.idxmax()
check("Record close", abs(peak_close - 5318.4) < 0.5 and f"{peak_date:%Y-%m-%d}" == "2026-01-29",
      f"max GC=F close {peak_close:,.1f} on {peak_date:%d %b %Y}")
low_since = hist[hist <= now].index.max()
session = intra.loc[f"{hist.index[-1]:%Y-%m-%d} 18:00":]
week_days = g.loc["2026-11-13":]

cross = {}
for t in ["GC=F", "SI=F", "HG=F", "CL=F", "DX-Y.NYB", "^TNX", "^GSPC", "^VIX", "^VIX3M", "^GVZ", "BTC-USD", "GLD"]:
    s = daily[t].dropna().copy()
    if t == "GC=F":
        s.iloc[-1] = now
    lvl = t in ("^TNX", "^VIX", "^VIX3M", "^GVZ")
    f_ = (lambda a, b: float(b - a)) if lvl else (lambda a, b: float(b / a - 1))
    cross[t] = {"now": float(s.iloc[-1]), "date": str(s.index[-1].date()),
                "today": f_(s.iloc[-2], s.iloc[-1]), "week": f_(s.loc[:"2026-11-13"].iloc[-1], s.iloc[-1]),
                "since_oct6": f_(s.loc[:"2026-10-06"].iloc[-1], s.iloc[-1]),
                "since_peak": f_(s.loc[:"2026-01-29"].iloc[-1], s.iloc[-1])}
vix_ratio = cross["^VIX"]["now"] / cross["^VIX3M"]["now"]

# ------------------------------------------------------------------ model
f0 = fit(hist)
sig, nu = np.sqrt(f0.var_next), f0.nu
sc = np.sqrt(nu / (nu - 2))
z_today = float(np.log(now / y_close) / sig)
p_today = float(stats.t.cdf(z_today * sc, nu))
q0 = lambda pr: y_close * np.exp(stats.t.ppf(pr, nu) / sc * sig)  # noqa: E731
live = store.read_records()
rec13 = [r for r in live if r["origin"] == "2026-11-13" and r["source"] == "live"][0]
grid5 = np.array(rec13["grid"]["5"])
pit_grid = float(np.interp(now, grid5, GRID_Q / 100, left=0.0, right=1.0))
p13 = rec13["spot"] * np.exp(simulate(Fit(**rec13["fit"]), horizon=21)[:, 1:])
pit_sim = float((p13[:, 4] <= now).mean())
check("13 Nov forecast: stored grid vs re-simulated paths", abs(np.percentile(p13[:, 4], 1) - grid5[0]) < 2,
      f"1st percentile, week ahead: stored {grid5[0]:,.1f}, re-simulated {np.percentile(p13[:, 4], 1):,.1f}; "
      f"today's price below both (grid PIT {pit_grid:.3f}, simulated PIT {pit_sim:.4f})")
flash18 = json.load(open(DESK / "reports" / "2026-11-18" / "today.json"))
sum19 = json.load(open(DESK / "reports" / "2026-11-19" / "today.json"))
f1 = fit(g)
paths = now * np.exp(simulate(f1, horizon=21)[:, 1:])
LEV = (3200, 3300, 3400, 3600, 3800, 4000)
touch = {lv: float((paths.min(1) <= lv).mean() if lv < now else (paths.max(1) >= lv).mean()) for lv in LEV}
touch_w = {lv: float((paths[:, :5].min(1) <= lv).mean() if lv < now else (paths[:, :5].max(1) >= lv).mean()) for lv in LEV}
fan = {p: np.percentile(paths, p, axis=0).tolist() for p in (5, 25, 50, 75, 95)}
r = np.log(hist).diff().dropna()
from arch import arch_model  # noqa: E402
res = arch_model(r * 100, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(disp="off", show_warning=False)
zres = ((r * 100 - res.params["mu"]) / res.conditional_volatility).dropna()
emp_tail = float((zres <= z_today).mean())
t_tail = float(stats.t.cdf(z_today * sc, nu))
cond = res.conditional_volatility / 100 * np.sqrt(252)
vol_pct = float((cond < f1.vol_next).mean())
ivt = iv_targets(g, daily["^GVZ"].dropna()).iloc[-1]
recs = store.read_records()
scores = score(recs, hist)
cov = coverage(scores, scores["origin"].max())
old_cov = json.load(open(DESK / "reports" / "2026-11-13" / "summary.json"))["coverage"]
c_new = cov[(cov.window == "All history") & (cov.h == 5)].iloc[0]
c_old = [c for c in old_cov if c["window"] == "All history" and c["h"] == 5][0]
check("Track record recomputed from the forecast store", abs(c_new.inside90 - c_old["inside90"]) < 0.01,
      f"1-week 90% coverage, all history: {c_new.inside90:.1%} now (n={int(c_new.n)}) vs {c_old['inside90']:.1%} on 13 Nov")

# ------------------------------------------------------------------ macro (FRED)
fr = pd.read_csv(D / "fred.csv", index_col=0, parse_dates=True)
cpi = np.exp(np.log(fr["CPIAUCSL"].dropna()).reindex(pd.date_range("1947-01-01", fr["CPIAUCSL"].dropna().index[-1], freq="MS")).interpolate(limit_area="inside"))
core = np.exp(np.log(fr["CPILFESL"].dropna()).reindex(pd.date_range("1957-01-01", fr["CPILFESL"].dropna().index[-1], freq="MS")).interpolate(limit_area="inside"))
missing = [f"{d:%b %Y}" for d in pd.date_range("2024-01-01", fr["CPIAUCSL"].dropna().index[-1], freq="MS")
           if d not in fr["CPIAUCSL"].dropna().index]
cpi_yoy = float(cpi.iloc[-1] / cpi.iloc[-13] - 1)
naive13 = float(fr["CPIAUCSL"].dropna().iloc[-1] / fr["CPIAUCSL"].dropna().iloc[-13] - 1)
check("CPI: gaps in the FRED series handled", len(missing) <= 1,
      f"missing months since 2024: {', '.join(missing) or 'none'} (interpolated). 12-month CPI {cpi_yoy:.2%}; "
      f"skipping the gap would give a 13-month change of {naive13:.2%}")


MONTHLY = {"CPIAUCSL", "CPILFESL", "UNRATE", "PAYEMS"}


def known(when):
    """Monthly data are dated the 1st of the month they describe and published about six weeks later:
    as of `when`, only months dated at least 45 days earlier were known."""
    return None if when is None else f"{pd.Timestamp(when) - pd.Timedelta(days=45):%Y-%m-%d}"


def lvl(sid, when=None):
    s = fr[sid].dropna()
    cut = known(when) if sid in MONTHLY else when
    return float(s.loc[:cut].iloc[-1]) if cut else float(s.iloc[-1])


PUBLISHED = fr["CPIAUCSL"].dropna().index      # interpolated months were never published: never "known"


def last_pub(when):
    return None if when is None else PUBLISHED[PUBLISHED <= known(when)].max()


def yoy(x, when=None):
    x = x.loc[:last_pub(when)] if when else x.loc[:PUBLISHED.max()]
    return float(x.iloc[-1] / x.iloc[-13] - 1)


def ann3(x, when=None):
    x = x.loc[:last_pub(when)] if when else x.loc[:PUBLISHED.max()]
    return float((x.iloc[-1] / x.iloc[-4]) ** 4 - 1)


pay = fr["PAYEMS"].dropna()
nl = ((fr["WALCL"] - fr["WTREGEN"]) / 1e3 - fr["RRPONTSYD"].ffill()).dropna()
macro_rows = []
for label, fn, unit in [
    ("Fed funds target (upper)", lambda w: lvl("DFEDTARU", w), "pct"),
    ("2-year Treasury yield", lambda w: lvl("DGS2", w), "pct"),
    ("10-year Treasury yield", lambda w: lvl("DGS10", w), "pct"),
    ("10-year real yield (TIPS)", lambda w: lvl("DFII10", w), "pct"),
    ("10-year breakeven inflation", lambda w: lvl("T10YIE", w), "pct"),
    ("5y5y forward inflation", lambda w: lvl("T5YIFR", w), "pct"),
    ("CPI inflation, 12 months", lambda w: 100 * yoy(cpi, w), "pct"),
    ("Core CPI inflation, 12 months", lambda w: 100 * yoy(core, w), "pct"),
    ("CPI inflation, 3 months annualised", lambda w: 100 * ann3(cpi, w), "pct"),
    ("Unemployment rate", lambda w: lvl("UNRATE", w), "pct"),
    ("Payrolls, 3-month average change (000)", lambda w: float(pay.loc[:known(w)].diff().iloc[-3:].mean()) if w else float(pay.diff().iloc[-3:].mean()), "k"),
    ("Initial jobless claims, 4-week average (000)", lambda w: float(fr["ICSA"].dropna().loc[:w].iloc[-4:].mean() / 1e3) if w else float(fr["ICSA"].dropna().iloc[-4:].mean() / 1e3), "k"),
    ("High-yield credit spread", lambda w: lvl("BAMLH0A0HYM2", w), "pct"),
    ("Investment-grade credit spread", lambda w: lvl("BAMLC0A0CM", w), "pct"),
    ("Broad trade-weighted dollar", lambda w: lvl("DTWEXBGS", w), "idx"),
    ("Net liquidity: Fed assets - TGA - RRP ($bn)", lambda w: float(nl.loc[:w].iloc[-1]) if w else float(nl.iloc[-1]), "bn"),
]:
    macro_rows.append({"measure": label, "unit": unit, "now": fn(None), "oct6": fn("2026-10-06"), "year_ago": fn("2025-11-20")})
dates_macro = {k: str(fr[k].dropna().index[-1].date()) for k in fr}

common = fr[["DFII10", "T10YIE", "DGS10"]].dropna().iloc[-1]
check("Real yield + breakeven = nominal 10-year (Fisher identity)",
      abs(common.DFII10 + common.T10YIE - common.DGS10) <= 0.12,
      f"{fr[['DFII10', 'T10YIE', 'DGS10']].dropna().index[-1]:%d %b}: {common.DFII10:.2f} + {common.T10YIE:.2f} = "
      f"{common.DFII10 + common.T10YIE:.2f} vs {common.DGS10:.2f}")
tnx = daily["^TNX"].dropna()
dgs = fr["DGS10"].dropna()
both = pd.concat([tnx, dgs], axis=1, join="inner").dropna().iloc[-5:]
check("10-year yield: FRED vs Yahoo", (both.iloc[:, 0] - both.iloc[:, 1]).abs().max() <= 0.06,
      f"largest gap over the last 5 common days {(both.iloc[:, 0] - both.iloc[:, 1]).abs().max():.3f} pt")
dxy_chg = cross["DX-Y.NYB"]["since_oct6"]
broad = fr["DTWEXBGS"].dropna()
broad_chg = float(broad.iloc[-1] / broad.loc[:"2026-10-06"].iloc[-1] - 1)
check("Dollar strength: DXY vs broad trade-weighted dollar", np.sign(dxy_chg) == np.sign(broad_chg),
      f"since 6 Oct: DXY {dxy_chg:+.1%}, broad dollar {broad_chg:+.1%} (to {broad.index[-1]:%d %b})")
real = fr["DFII10"].dropna()
real_pre = real.loc[:"2025-12-31"]
real_info = {"now": float(real.iloc[-1]), "date": str(real.index[-1].date()),
             "wk_bp": 100 * float(real.iloc[-1] - real.loc[:"2026-11-11"].iloc[-1]),
             "since_feb_bp": 100 * float(real.iloc[-1] - real.loc["2026-02"].mean()),
             "last_higher_pre2026": str(real_pre[real_pre >= real.iloc[-1]].index.max().date())}

# ------------------------------------------------------------------ flows and positioning
ici = pd.read_excel(D / "ici_mm_summary_2026.xls", header=None, engine="xlrd")
ici = ici[pd.to_datetime(ici[0].astype(str).str.strip(), format="%m/%d/%Y", errors="coerce").notna()]
mmf = pd.DataFrame({"total": ici[2].astype(float).values, "inst": ici[14].astype(float).values,
                    "retail": ici[26].astype(float).values},
                   index=pd.to_datetime(ici[0].astype(str).str.strip(), format="%m/%d/%Y")).dropna().sort_index()
check("ICI money funds: institutional + retail = total", float((mmf.inst + mmf.retail - mmf.total).abs().max()) < 2,
      f"{len(mmf)} weeks to {mmf.index[-1]:%d %b}; largest gap {float((mmf.inst + mmf.retail - mmf.total).abs().max()):.0f} $m")
mchg = mmf.total.diff().dropna()
mmf_info = {"date": str(mmf.index[-1].date()), "total_tn": mmf.total.iloc[-1] / 1e6, "chg_bn": mchg.iloc[-1] / 1e3,
            "z": float((mchg.iloc[-1] - mchg.iloc[:-1].mean()) / mchg.iloc[:-1].std()), "n": len(mchg) - 1,
            "chg4w_bn": float(mmf.total.iloc[-1] - mmf.total.iloc[-5]) / 1e3, "max_tn": mmf.total.max() / 1e6,
            "max_date": str(mmf.total.idxmax().date())}

flows = {}
for t in ["GLD", "SPY", "XLK", "XLU", "XLP", "BIL"]:
    x = pd.read_excel(D / f"ssga_navhist_{t}.xlsx", header=None, engine="openpyxl")
    start = x.index[x[0].astype(str).str.strip() == "Date"][0] + 1
    x = x.iloc[start:, :3].dropna()
    x.columns = ["date", "nav", "shares"]
    x["date"] = pd.to_datetime(x["date"], format="%d-%b-%Y", errors="coerce")
    x["nav"] = pd.to_numeric(x["nav"], errors="coerce")          # a few old rows carry '-' for missing values
    x["shares"] = pd.to_numeric(x["shares"], errors="coerce")
    x = x.dropna().sort_values("date").set_index("date")
    x["flow"] = x.shares.diff() * x.nav
    x["aum"] = x.shares * x.nav
    wk = x.flow.resample("W-FRI").sum()
    info = {"last": str(x.index[-1].date()), "aum_bn": x.aum.iloc[-1] / 1e9, "nav": x.nav.iloc[-1]}
    for lab, st_ in (("since_peak", "2026-01-29"), ("since_oct6", "2026-10-06"), ("nov", "2026-10-30"), ("week", "2026-11-13")):
        fl = x.loc[x.index > st_, "flow"].sum()
        info[f"{lab}_bn"] = fl / 1e9
        info[f"{lab}_pct"] = fl / x.loc[:st_, "aum"].iloc[-1]
    hist_w = wk.iloc[-53:-1]
    info["z_week"] = float((wk.iloc[-1] - hist_w.mean()) / hist_w.std())
    info["week_partial_to"] = str(x.index[-1].date())
    flows[t] = info
    if t == "GLD":
        gld_y = daily["GLD"].dropna()
        j = pd.concat([x.nav, gld_y], axis=1, join="inner").dropna().iloc[-60:]
        dev = float((j.iloc[:, 0] / j.iloc[:, 1] - 1).abs().median())
        check("GLD: State Street NAV vs Yahoo market price", dev < 0.005,
              f"median gap {dev:.2%} over the last {len(j)} common days")
        a0, a1 = x.loc[:"2026-10-06"].iloc[-1], x.iloc[-1]
        bridge = (a1.aum - a0.aum) - x.loc[x.index > "2026-10-06", "flow"].sum()
        perf = (a1.nav / a0.nav - 1) * a0.aum
        check("GLD: asset bridge (change in assets = flows + price effect)", abs(bridge - perf) / a0.aum < 0.02,
              f"price effect from NAV {perf / 1e9:+.2f}bn vs assets minus flows {bridge / 1e9:+.2f}bn")

cf = pd.read_csv(D / "cftc_gold.csv")
cf["date"] = pd.to_datetime(cf.report_date_as_yyyy_mm_dd)
cf["net"] = cf.m_money_positions_long_all.astype(float) - cf.m_money_positions_short_all.astype(float)
cf["pct_oi"] = cf.net / cf.open_interest_all.astype(float)
cftc = {"date": str(cf.date.iloc[-1].date()), "net": float(cf.net.iloc[-1]), "chg_1w": float(cf.net.iloc[-1] - cf.net.iloc[-2]),
        "chg_4w": float(cf.net.iloc[-1] - cf.net.iloc[-5]), "pct_oi": float(cf.pct_oi.iloc[-1]),
        "pctile_since_2006": float((cf.pct_oi < cf.pct_oi.iloc[-1]).mean()),
        "at_peak": float(cf.loc[cf.date <= "2026-01-27", "net"].iloc[-1]),
        "max_2026": float(cf.loc[cf.date >= "2026-01-01", "net"].max())}

# ------------------------------------------------------------------ history (monthly averages)
dh = pd.read_csv(D / "gold_monthly_datahub.csv")
dh = pd.Series(dh.Price.values, index=pd.PeriodIndex(dh.Date, freq="M"))
gm = g.groupby(g.index.to_period("M")).mean()
ov = pd.concat([dh, gm], axis=1, join="inner").dropna().loc["2001-01":]
ratio = ov.iloc[:, 0] / ov.iloc[:, 1]
check("Long history: datahub monthly averages vs COMEX futures", abs(ratio.median() - 1) < 0.01 and (ratio - 1).abs().max() < 0.02,
      f"{len(ov)} overlapping months; median ratio {ratio.median():.4f}, largest gap {(ratio - 1).abs().max():.1%}")
m = pd.concat([dh.loc["1970-01":"2026-10"], gm.loc["2026-11":]])
cyc = json.load(open(DESK / "reports" / "2026-11-19-cycles" / "cycles.json"))
p26 = m.loc["2026-02"]
path26 = (m.loc["2026-02":] / p26 - 1).tolist()
cpi_m = cpi.copy()
cpi_m.index = cpi_m.index.to_period("M")
rec80 = 850 * cpi.iloc[-1] / cpi.loc["1980-01-01"]
rec11 = 1895 * cpi.iloc[-1] / cpi.loc["2011-09-01"]
real_now_vs80 = now / rec80 - 1
hist_peaks = {p["peak"]: p for p in cyc["peaks"]}
month9 = {pk: cyc["paths"][pk][9] for pk in ("1974-12", "1980-01", "1980-09", "1983-02", "2008-03", "2011-09")}

# ------------------------------------------------------------------ validation tests already run, plus the breakeven re-run
summ13 = json.load(open(DESK / "reports" / "2026-11-13" / "summary.json"))
win = json.load(open(DESK / "reports" / "2026-11-13" / "window_check.json"))
ivc = json.load(open(DESK / "reports" / "2026-11-13" / "iv_check.json"))
cop = json.load(open(REPO / "copper" / "reports" / "2026-11-18" / "results.json"))
rot = json.load(open(REPO / "rotation" / "reports" / "2026-11-18" / "results.json"))
check("Earlier test results reloaded unchanged", abs(cop["preregistered"][0]["r2_os"] + 0.0082) < 1e-3 and
      abs(rot["profit_taking"]["spearman"] + 0.499) < 1e-3,
      "copper R² (4 weeks) and profit-taking correlation match the committed results files")

mo = pd.DataFrame({"real": fr["DFII10"].dropna().resample("ME").last(), "be": fr["T10YIE"].dropna().resample("ME").last()}).dropna()
core_yoy_m = (core.pct_change(12, fill_method=None) * 100)
core_yoy_m.index = core_yoy_m.index + pd.offsets.MonthEnd(0)
mo["core_pub"] = core_yoy_m.shift(1).reindex(mo.index)          # month t-1 CPI is published by the end of month t
mo["c1"], mo["c2"] = mo.be - mo.core_pub, mo.real - mo.be
H3 = 3
mo["y1"], mo["y2"] = mo.be.shift(-H3) - mo.be, mo.c2.shift(-H3) - mo.c2


def oos_rw(x, y, burn=60):
    out_ = []
    for w in range(len(x)):
        j = np.arange(0, w - H3 + 1)
        j = j[~np.isnan(x[j]) & ~np.isnan(y[j])]
        if len(j) < burn or np.isnan(x[w]) or np.isnan(y[w]):
            continue
        b = np.cov(x[j], y[j], ddof=0)[0, 1] / np.var(x[j])
        out_.append((y[w], y[j].mean() - b * x[j].mean() + b * x[w]))
    o = np.array(out_)
    em, eb = o[:, 0] - o[:, 1], o[:, 0]
    f = eb ** 2 - (em ** 2 - o[:, 1] ** 2)
    fc = f - f.mean()
    v = fc @ fc / len(fc) + sum(2 * (1 - k / H3) * (fc[k:] @ fc[:-k]) / len(fc) for k in range(1, H3))
    t = f.mean() / np.sqrt(v / len(f))
    h = len(o) // 2
    r2 = lambda a, b: float(1 - (a ** 2).sum() / (b ** 2).sum())  # noqa: E731
    return {"n": len(o), "r2": r2(em, eb), "p": float(stats.norm.sf(t)), "r2_a": r2(em[:h], eb[:h]), "r2_b": r2(em[h:], eb[h:])}


be_test = {"gap": oos_rw(mo.c1.values, mo.y1.values), "spread": oos_rw(mo.c2.values, mo.y2.values)}
drift = summ13["drift_check"]["rows"]
tests = [
    {"test": "Drift in the forecast (2 Nov)", "question": "Does adding drift improve the 1-month forecast?",
     "result": f"Best candidate p = {[r for r in drift if r['h'] == 21][0]['p']:.3f}; rule p < 0.05", "verdict": "No: zero drift stays"},
    {"test": "Rolling estimation window (16 Nov)", "question": "Is a 10- or 5-year window better than all data since 2003?",
     "result": f"1-month p = {[w for w in win if w['window'] == '10 years' and w['h'] == 21][0]['p']:.2f} (10y), "
               f"{[w for w in win if w['window'] == '5 years' and w['h'] == 21][0]['p']:.2f} (5y); rule p < 0.025", "verdict": "No"},
    {"test": "GVZ implied volatility (17 Nov)", "question": "Does the options market improve the ranges?",
     "result": f"Blend 1-week p = {[i for i in ivc if i['candidate'].startswith('Blend') and i['h'] == 5][0]['p']:.4f}, "
               f"1-month p = {[i for i in ivc if i['candidate'].startswith('Blend') and i['h'] == 21][0]['p']:.2f}",
     "verdict": "No for 1 month; a 1-week lead for live testing"},
    {"test": "Copper as a leading indicator (19 Nov)", "question": "Does copper forecast the Nasdaq's next 4 weeks?",
     "result": "R² " + ", ".join(f"{c['r2_os']:+.1%}" for c in cop["preregistered"]) + "; all p > 0.2", "verdict": "No"},
    {"test": "Profit-taking across assets (19 Nov)", "question": "Did last year's winners fall hardest?",
     "result": f"Rank correlation {rot['profit_taking']['spearman']:+.2f} (p {rot['profit_taking']['p']:.3f}); "
               f"controlling for volatility t = {[x for x in rot['robustness'] if x['start'] == '2026-10-06' and x['universe'] == 'All 28'][0]['t_mom_vol']:+.1f}",
     "verdict": "Mostly volatility; a momentum unwind within stocks"},
    {"test": "Breakeven gap to inflation (re-run 20 Nov)", "question": "Does a low breakeven vs core CPI predict it rising?",
     "result": f"R² {be_test['gap']['r2']:+.1%}, p {be_test['gap']['p']:.2f}", "verdict": "No"},
    {"test": "Real yield minus breakeven (re-run 20 Nov)", "question": "Does the spread revert within 3 months?",
     "result": f"R² {be_test['spread']['r2']:+.1%}, p {be_test['spread']['p']:.2f}", "verdict": "No"},
    {"test": "Gold cycles since 1974 (19 Nov)", "question": "Is there a regular rhythm between peaks?",
     "result": "Gaps between bear-market peaks: " + ", ".join(f"{x:.1f}" for x in cyc["gaps_years"]) + " years",
     "verdict": "No regular cycle"},
]

out = {
    "asof": f"{asof:%H:%M}", "today": str(TODAY.date()), "now": now, "y_close": y_close, "y_date": str(hist.index[-1].date()),
    "wk_close": wk_close, "r_today": now / y_close - 1, "r_week": week_ret, "n_worse_weeks_since_2000": n_worse_weeks,
    "n_worse_days_since_2000": n_worse_days, "last_worse_day": str(last_worse_day.date()),
    "peak_close": peak_close, "peak_date": str(peak_date.date()), "from_peak": now / peak_close - 1,
    "low_since": str(low_since.date()), "session_low": float(session["Low"].min()), "session_low_t": f"{session['Low'].idxmin():%H:%M}",
    "session_high": float(session["High"].max()),
    "week_days": {str(k.date()): float(v) for k, v in week_days.items()},
    "cross": cross, "vix_ratio": vix_ratio,
    "model": {"sigma_day": float(sig), "vol_prev": f0.vol_next, "z_today": z_today, "p_today": p_today,
              "band90": [q0(0.05), q0(0.95)], "band98": [q0(0.01), q0(0.99)], "emp_tail": emp_tail, "t_tail": t_tail,
              "vol_now": f1.vol_next, "vol_pct": vol_pct, "vol_lr": f1.vol_long_run, "nu": f1.nu,
              "gvz": float(daily["^GVZ"].dropna().iloc[-1]), "gvz_corrected": float(ivt["iv_corrected"])},
    "f13": {"spot": rec13["spot"], "band90_week": [float(np.percentile(p13[:, 4], 5)), float(np.percentile(p13[:, 4], 95))],
            "q1_week": float(grid5[0]), "pit_sim": pit_sim, "pit_grid": pit_grid},
    "flash18": {"now": flash18["now"], "w5": flash18["fan"]["5"][4], "touch3600": flash18["touch_week"]["3600"]},
    "sum19": {"now": sum19["now"], "w5": sum19["fan"]["5"][4], "touch3500w": sum19["touch_week"]["3500"],
              "touch3600w": sum19["touch_week"]["3600"]},
    "fan": fan, "touch": touch, "touch_week": touch_w,
    "coverage": json.loads(cov.to_json(orient="records", date_format="iso")),
    "macro": macro_rows, "macro_dates": dates_macro, "real": real_info,
    "cpi_yoy": cpi_yoy, "cpi_missing": missing,
    "mmf": mmf_info, "flows": flows, "cftc": cftc,
    "history": {"path26": path26, "feb_avg": float(p26), "nov_avg": float(m.iloc[-1]), "month9": month9,
                "peaks": {k: hist_peaks[k] for k in ("1974-12", "1980-01", "2008-03", "2011-09")},
                "paths": {k: cyc["paths"][k][:37] for k in ("1974-12", "1980-01", "2008-03", "2011-09")},
                "rec80_today": float(rec80), "rec11_today": float(rec11), "now_vs_rec80": float(real_now_vs80),
                "gaps": cyc["gaps_years"], "n_bears": len(cyc["peaks"])},
    "tests": tests, "breakeven_test": be_test,
}
(N / "results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
(N / "checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("fan", "coverage", "history", "macro", "flows", "cross", "tests")},
                 indent=1, default=float)[:4000])
print(pd.DataFrame(macro_rows).round(2).to_string(index=False))
print(json.dumps(flows, indent=1, default=float)[:2500])
for c in checks:
    print(f"[{c['result']}] {c['check']}: {c['detail']}")
