"""Gold Desk weekly note, week to Friday 20 Nov 2026 with news to Sunday 22 Nov (landscape slides in the
weekly-monitor layout of reference/, own branding). Adds the live desk forecast, the scorecard and the
weekend to the Friday data of reports/2026-11-20-weekly/. Writes desk_week.json and gold_desk_2026-11-20.pdf.

Usage (from desk/): python reports/2026-11-20/scripts/build_desk_weekly.py
"""
import json
import os
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas as rl_canvas  # noqa: E402
from reportlab.platypus import Paragraph, Table, TableStyle  # noqa: E402

DESK = Path(__file__).resolve().parents[3]
N = DESK / "reports" / "2026-11-20-weekly"      # Friday data and driver results (built 21 Nov)
OUTDIR = DESK / "reports" / "2026-11-20"        # this note: summary.json, weekend data, PDF
D = N / "data"
sys.path.insert(0, str(DESK))
from gold_desk.model import fit  # noqa: E402

OZ_PER_T = 32150.7466
FRI, PREV, YEND = pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-13"), pd.Timestamp("2025-12-31")
TEAL, TEAL2, INK, INK2, MUTED, GRID = "#0b3a44", "#2f5d62", "#111111", "#4a4a48", "#8a8a86", "#e3e3df"
BOX = "#f1f1f0"
BLUE, ORANGE, AQUA, YELLOW, VIOLET, PINK = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6", "#e87ba4"
NEUTRAL, RED, GREEN = "#b5b3ad", "#c62828", "#2e7d32"

daily = pd.read_csv(D / "daily.csv", index_col=0, parse_dates=True)
fred = pd.read_csv(D / "fred.csv", index_col=0, parse_dates=True)
DRV = json.load(open(N / "drivers.json"))
gold = daily["GC=F"].dropna()
gold = gold[gold.index <= FRI]


def s_(t):
    x = (fred[t] if t in fred else daily[t]).dropna()
    return x[x.index <= FRI]


# ------------------------------------------------------------------ numbers
ASSETS = [("Gold", "GC=F"), ("Silver", "SI=F"), ("Commodities (DBC)", "DBC"), ("Oil (Brent)", "BZ=F"),
          ("Dollar (DXY)", "DX-Y.NYB"), ("S&P 500", "^GSPC"), ("Nasdaq-100", "^NDX"), ("EuroStoxx 50", "^STOXX50E"),
          ("Sensex", "^BSESN"), ("Nikkei 225", "^N225"), ("MSCI EAFE (EFA)", "EFA"),
          ("MSCI EM (EEM)", "EEM"), ("Bitcoin", "BTC-USD")]
YIELDS = [("US 2Y", "DGS2"), ("US 10Y", "^TNX")]
gw = np.log(gold.resample("W-FRI").last()).diff()
perf = []
for name, t in ASSETS + YIELDS:
    x = s_(t)
    lvl = name in ("US 2Y", "US 10Y")
    wk = x.resample("W-FRI").last().dropna()
    wr = wk.diff() * 100 if lvl else np.log(wk).diff()
    hist = wr.iloc[-53:-1]
    last, prev, ye = x.iloc[-1], x.loc[:PREV].iloc[-1], x.loc[:YEND].iloc[-1]
    ww = (last - prev) * 100 if lvl else last / prev - 1
    ytd = (last - ye) * 100 if lvl else last / ye - 1
    both = pd.concat([gw, wr], axis=1, join="inner").dropna()
    corr = both.iloc[-52:].corr().iloc[0, 1]
    corr_prev = both.iloc[-53:-1].corr().iloc[0, 1]
    perf.append({"asset": name, "ticker": t, "unit": "bp" if lvl else "pct", "close": float(last),
                 "date": str(x.index[-1].date()), "ww": float(ww), "ytd": float(ytd),
                 "z": float((wr.iloc[-1] - hist.mean()) / hist.std()), "corr": float(corr), "dcorr": float(corr - corr_prev)})
P = {r["asset"]: r for r in perf}


def rsi(x, n=9):
    d = x.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    au = up.ewm(alpha=1 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    return float(100 - 100 / (1 + au.iloc[-1] / ad.iloc[-1]))


TECH = [("Gold", "GC=F", "${:,.0f}"), ("Silver", "SI=F", "{:.2f}"), ("DXY", "DX-Y.NYB", "{:.2f}"),
        ("US 10yr yield", "^TNX", "{:.2f}%"), ("US 2yr yield", "DGS2", "{:.2f}%"), ("S&P 500", "^GSPC", "{:,.0f}"),
        ("Nasdaq-100", "^NDX", "{:,.0f}"), ("EuroStoxx 50", "^STOXX50E", "{:,.0f}"), ("Nikkei 225", "^N225", "{:,.0f}"),
        ("Brent crude", "BZ=F", "${:.2f}"), ("Bitcoin", "BTC-USD", "{:,.0f}")]
tech = []
for name, t, f in TECH:
    x = s_(t)
    y = x.loc["2026-01-01":]
    tech.append({"name": name, "fmt": f, "last": float(x.iloc[-1]), "hi": float(y.max()), "lo": float(y.min()),
                 "sma55": float(x.iloc[-55:].mean()), "sma200": float(x.iloc[-200:].mean()),
                 "rsi": rsi(x.resample("W-FRI").last().dropna())})

# CFTC in tonnes
c = pd.read_csv(D / "cftc_gold_full.csv")
c["date"] = pd.to_datetime(c.report_date_as_yyyy_mm_dd)
num = lambda col: pd.to_numeric(c[col], errors="coerce") if col in c else pd.Series(np.nan, index=c.index)  # noqa: E731
T = lambda col: num(col) * 100 / OZ_PER_T  # noqa: E731
cot = pd.DataFrame({"date": c["date"], "mm_l": T("m_money_positions_long_all"), "mm_s": T("m_money_positions_short_all"),
                    "ot_l": T("other_rept_positions_long"), "ot_s": T("other_rept_positions_short"),
                    "nr_l": T("nonrept_positions_long_all"), "nr_s": T("nonrept_positions_short_all"),
                    "mm_sp": T("m_money_positions_spread"), "ot_sp": T("other_rept_positions_spread"),
                    "oi": num("open_interest_all")}).set_index("date")
cot["mm_n"], cot["ot_n"], cot["nr_n"] = cot.mm_l - cot.mm_s, cot.ot_l - cot.ot_s, cot.nr_l - cot.nr_s
px_at = gold.reindex(cot.index, method="ffill")
for k in ("mm", "ot", "nr"):
    cot[f"{k}_bn"] = cot[f"{k}_n"] * OZ_PER_T * px_at / 1e9
cot["mm_share"] = (num("m_money_positions_long_all") - num("m_money_positions_short_all")).values / cot["oi"].values
share = cot["mm_share"]
c_last, c_prev = cot.iloc[-1], cot.iloc[-2]

# GLD flows and tonnes (estimated from NAV and the COMEX price)
g = pd.read_excel(D / "ssga_navhist_GLD.xlsx", header=None, engine="openpyxl")
s0 = g.index[g[0].astype(str).str.strip() == "Date"][0] + 1
g = g.iloc[s0:, :3]
g.columns = ["date", "nav", "shares"]
g["date"] = pd.to_datetime(g["date"], format="%d-%b-%Y", errors="coerce")
g[["nav", "shares"]] = g[["nav", "shares"]].apply(pd.to_numeric, errors="coerce")
g = g.dropna().set_index("date").sort_index()
g["flow"] = g.shares.diff() * g.nav
g["aum"] = g.shares * g.nav
oz_share = (g.nav / gold.reindex(g.index, method="ffill")).rolling(60, min_periods=20).median()
g["tonnes"] = g.shares * oz_share / OZ_PER_T
gw_flow = g.flow.resample("W-FRI").sum()
gw_t = g.tonnes.resample("W-FRI").last()
gld_rows = [{"week": str(i.date()), "flow_m": float(gw_flow.loc[i] / 1e6), "tonnes": float(gw_t.loc[i]),
             "dt": float(gw_t.loc[i] - gw_t.shift(1).loc[i])} for i in gw_flow.index[-9:]]
gld_ytd = {"flow_bn": float(g.loc["2026-01-01":, "flow"].sum() / 1e9),
           "dt": float(g.tonnes.iloc[-1] - g.tonnes.loc[:YEND].iloc[-1]), "tonnes": float(g.tonnes.iloc[-1]),
           "aum_bn": float(g.aum.iloc[-1] / 1e9), "last": str(g.index[-1].date())}

# sessions (5-minute bars, New York time)
i5 = pd.read_csv(D / "gold_5m.csv", index_col=0)
i5.index = pd.to_datetime(i5.index, utc=True).tz_convert("America/New_York").tz_localize(None)
r5 = np.log(i5["Close"]).diff().dropna()
hr = r5.index.hour + r5.index.minute / 60
sess = np.where((hr >= 18) | (hr < 3), "Asia", np.where(hr < 8, "Europe", "US"))
tot, ss = r5.sum(), (r5 ** 2).sum()
sessions = []
for nm, win in (("Asia", "18:00-03:00"), ("Europe", "03:00-08:00"), ("US", "08:00-17:00")):
    x = r5[sess == nm]
    sessions.append({"session": nm, "window": win, "ret": float(np.expm1(x.sum())), "share": float(x.sum() / tot),
                     "vol": float(x.std() * np.sqrt(276 * 252)), "var_share": float((x ** 2).sum() / ss)})

# volatility
r = np.log(gold).diff().dropna()
gvz = s_("^GVZ")
f_now = fit(gold)
lr = f_now.omega / (1 - f_now.persistence)
vol21 = float(np.sqrt(np.mean([lr + f_now.persistence ** k * (f_now.var_next - lr) for k in range(21)]) * 252))
vol = {"gvz": float(gvz.iloc[-1]), "gvz_1m": float(gvz.iloc[-1] - gvz.loc[:FRI - pd.Timedelta(days=30)].iloc[-1]),
       "gvz_pct": float((gvz.loc[FRI - pd.Timedelta(days=365):] < gvz.iloc[-1]).mean()),
       "rv30": float(r.iloc[-21:].std() * np.sqrt(252)), "rv90": float(r.iloc[-63:].std() * np.sqrt(252)),
       "rv30_1m": float(r.iloc[-21:].std() * np.sqrt(252) - r.iloc[-42:-21].std() * np.sqrt(252)),
       "garch_next": f_now.vol_next, "garch_21": vol21, "vix": float(s_("^VIX").iloc[-1]), "vix3m": float(s_("^VIX3M").iloc[-1])}

wk_days = gold.loc[PREV:]
week = {"close": float(gold.iloc[-1]), "ww": float(gold.iloc[-1] / gold.loc[PREV] - 1),
        "ytd": float(gold.iloc[-1] / gold.loc[:YEND].iloc[-1] - 1), "from_peak": float(gold.iloc[-1] / gold.max() - 1),
        "peak": float(gold.max()), "peak_date": str(gold.idxmax().date()),
        "worse_weeks": int((gold.resample("W-FRI").last().pct_change().iloc[:-1] <= gold.iloc[-1] / gold.loc[PREV] - 1).sum()),
        "days": {str(k.date()): float(v) for k, v in wk_days.items()}}
OUT = {"week": week, "perf": perf, "tech": tech, "sessions": sessions, "vol": vol, "gld": gld_rows, "gld_ytd": gld_ytd,
       "cftc": {"date": str(cot.index[-1].date()), "mm_n": float(c_last.mm_n), "mm_n_prev": float(c_prev.mm_n),
                "ot_n": float(c_last.ot_n), "ot_n_prev": float(c_prev.ot_n), "nr_n": float(c_last.nr_n),
                "share": float(share.iloc[-1]), "share_prev": float(share.iloc[-2]),
                "share_z52": float((share.iloc[-1] - share.iloc[-53:-1].mean()) / share.iloc[-53:-1].std()),
                "share_pct": float((share < share.iloc[-1]).mean())}}
(OUTDIR / "desk_week.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")

# ------------------------------------------------------------------ charts
for fp in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
                     "legend.frameon": False, "legend.fontsize": 8.5})
CH = OUTDIR / "_charts"
CH.mkdir(exist_ok=True)


def save(fig, name):
    p = CH / f"{name}.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(p)


GROUPS = [("Rates and inflation", ["d_real", "d_be"], BLUE), ("Dollar", ["r_dxy"], ORANGE),
          ("Stress (VIX)", ["d_vix"], AQUA), ("US stocks", ["r_spx"], YELLOW), ("Oil", ["r_oil"], VIOLET),
          ("Positioning and flows", ["d_mm", "flow"], PINK), ("Trend (past 3 years)", ["alpha"], "#3c3c3a"),
          ("Unexplained", ["residual"], NEUTRAL)]


def grouped(rec):
    return {g_: sum(rec.get(k, 0.0) for k in ks) * 100 for g_, ks, _ in GROUPS}


# cover image: gold since 2025
fig, ax = plt.subplots(figsize=(6.4, 6.0))
gg = gold.loc["2025-01-01":]
ax.fill_between(gg.index, gg.min() * 0.92, gg.values, color="#1f6f78", alpha=0.55, lw=0)
ax.plot(gg.index, gg.values, color="#e9c46a", lw=2.2)
ax.axis("off")
fig.patch.set_facecolor(TEAL)
c_cover = str(CH / "cover.png")
fig.savefig(c_cover, dpi=200, bbox_inches="tight", facecolor=TEAL)
plt.close(fig)

# chart of the week: this week's attribution
wk_g = grouped(DRV["week"])
fig, ax = plt.subplots(figsize=(6.2, 2.9))
labels = list(wk_g)
vals = [wk_g[k] for k in labels]
cum = 0
for i_, (lab, v) in enumerate(zip(labels, vals)):
    col = [c_ for g_, _, c_ in GROUPS if g_ == lab][0]
    ax.bar(i_, v, bottom=cum if v >= 0 else cum + v, color=col, width=0.62)
    ax.text(i_, (cum + v) + (0.25 if v >= 0 else -0.25), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top",
            fontsize=8, color=INK)
    cum += v
ax.bar(len(labels), cum, color="#3c3c3a", width=0.62)
ax.text(len(labels), cum - 0.25, f"{cum:+.1f}", ha="center", va="top", fontsize=8.5, fontweight="bold")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xticks(range(len(labels) + 1))
ax.set_xticklabels([l_.replace(" and ", " &\n").replace(" (", "\n(") for l_ in labels] + ["Gold,\nthe week"], fontsize=7.4)
ax.set_ylabel("Contribution, % points (log)")
c_cotw = save(fig, "cotw")

# asset bars W/W and YTD (percent) and yields (bp), two panels, one axis each
pa = [r for r in perf if r["unit"] == "pct"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.2, 2.3), gridspec_kw={"width_ratios": [5.2, 1]})
x = np.arange(len(pa))
a1.bar(x - 0.2, [r["ww"] * 100 for r in pa], width=0.4, color="#1c5cab", label="Week on week, %")
a1.bar(x + 0.2, [r["ytd"] * 100 for r in pa], width=0.4, color=ORANGE, label="Year to date, %")
for xi, r_ in zip(x, pa):
    for off, v in ((-0.2, r_["ww"] * 100), (0.2, r_["ytd"] * 100)):
        a1.text(xi + off, v + (0.8 if v >= 0 else -0.8), f"{v:.1f}", ha="center", va="bottom" if v >= 0 else "top",
                fontsize=6.6, color=INK2)
a1.set_xticks(x)
a1.set_xticklabels([r["asset"] for r in pa], rotation=28, ha="right", fontsize=7.4)
a1.get_xticklabels()[0].set_color("#b8860b")
a1.axhline(0, color="#c3c2b7", lw=0.8)
a1.legend(loc="upper left", ncol=2)
py = [r for r in perf if r["unit"] == "bp"]
xy = np.arange(len(py))
a2.bar(xy - 0.2, [r["ww"] for r in py], width=0.4, color="#1c5cab")
a2.bar(xy + 0.2, [r["ytd"] for r in py], width=0.4, color=ORANGE)
for xi, r_ in zip(xy, py):
    for off, v in ((-0.2, r_["ww"]), (0.2, r_["ytd"])):
        a2.text(xi + off, v + (2 if v >= 0 else -2), f"{v:.0f}", ha="center", va="bottom" if v >= 0 else "top",
                fontsize=6.6, color=INK2)
a2.set_xticks(xy)
a2.set_xticklabels([r["asset"] for r in py], fontsize=7.8)
a2.set_title("Yields, bp", fontsize=8.5, color=INK2)
a2.axhline(0, color="#c3c2b7", lw=0.8)
c_bars = save(fig, "bars")

# positioning w/w
fig, axs = plt.subplots(3, 1, figsize=(6.0, 4.6))
pairs = [("GLD holdings change, tonnes", [("GLD", gld_rows[-2]["dt"], gld_rows[-1]["dt"])]),
         ("COMEX net longs, tonnes", [("Money managers", c_prev.mm_n, c_last.mm_n), ("Other reportables", c_prev.ot_n, c_last.ot_n)]),
         ("Managed-money net long, % of open interest", [("Share", share.iloc[-2] * 100, share.iloc[-1] * 100)])]
for ax, (ttl, rows_) in zip(axs, pairs):
    yy = np.arange(len(rows_))
    ax.barh(yy + 0.18, [r_[1] for r_ in rows_], height=0.34, color="#9aa7b0", label=f"Week to {cot.index[-2].day} Nov" if "COMEX" in ttl or "%" in ttl else "Previous week")
    ax.barh(yy - 0.18, [r_[2] for r_ in rows_], height=0.34, color=VIOLET, label=f"Week to {cot.index[-1].day} Nov" if "COMEX" in ttl or "%" in ttl else "This week")
    for yi, r_ in zip(yy, rows_):
        for off, v in ((0.18, r_[1]), (-0.18, r_[2])):
            ax.text(v, yi + off, f" {v:,.1f}", va="center", fontsize=7.4, color=INK2, ha="left" if v >= 0 else "right")
    ax.set_yticks(yy)
    ax.set_yticklabels([r_[0] for r_ in rows_], fontsize=8)
    ax.set_title(ttl, fontsize=8.6, color=INK2, loc="left")
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    ax.axvline(0, color="#c3c2b7", lw=0.8)
    ax.legend(loc="lower left", bbox_to_anchor=(0.55, 1.0), ncol=2, fontsize=7)
fig.tight_layout()
c_pos = save(fig, "positioning")

# sessions chart
fig, ax = plt.subplots(figsize=(12.6, 3.7))
ix = np.arange(len(i5))
hh = i5.index.hour + i5.index.minute / 60
lab = np.where((hh >= 18) | (hh < 3), "Asia", np.where(hh < 8, "Europe", "US"))
colmap = {"Asia": AQUA, "Europe": BLUE, "US": VIOLET}
for k in range(1, len(i5)):
    ax.plot(ix[k - 1:k + 1], i5["Close"].values[k - 1:k + 1], color=colmap[lab[k]], lw=1.1)
days = [k for k in range(len(i5)) if k == 0 or i5.index[k].date() != i5.index[k - 1].date()]
ax.set_xticks(days)
ax.set_xticklabels([i5.index[k].strftime("%a %d %b") for k in days], fontsize=8)
ax.set_xlim(0, len(i5) - 1)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
from matplotlib.lines import Line2D  # noqa: E402
ax.legend([Line2D([], [], color=colmap[k], lw=2) for k in colmap], list(colmap), loc="upper right", ncol=3)
c_sess = save(fig, "sessions")

# attribution, last 12 weeks
L12 = DRV["last12"]
fig, ax = plt.subplots(figsize=(12.4, 2.9))
xs = np.arange(len(L12))
posb, negb = np.zeros(len(L12)), np.zeros(len(L12))
for g_, ks, col in GROUPS:
    v = np.array([sum(r_.get(k, 0.0) for k in ks) * 100 for r_ in L12])
    ax.bar(xs, np.where(v > 0, v, 0), bottom=posb, color=col, width=0.62, label=g_)
    ax.bar(xs, np.where(v < 0, v, 0), bottom=negb, color=col, width=0.62)
    posb += np.where(v > 0, v, 0)
    negb += np.where(v < 0, v, 0)
gr = [r_["r_gold"] * 100 for r_ in L12]
ax.plot(xs, gr, color="#b8860b", lw=1.6, marker="o", ms=4, label="Gold return")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xticks(xs)
ax.set_xticklabels([pd.Timestamp(r_["week"]).strftime("%d/%m") for r_ in L12], fontsize=8)
ax.set_ylabel("% points (log)")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=9, fontsize=7.6)
c_attr = save(fig, "attribution")

# COMEX positioning since 2024 (tonnes), price panel below (one axis each)
cc = cot.loc["2024-01-01":]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.2, 4.3), sharex=True, gridspec_kw={"height_ratios": [1.7, 1]})
a1.bar(cc.index, cc.mm_n, width=5, color=VIOLET, label="Money manager net long")
a1.bar(cc.index, cc.ot_n, width=5, bottom=cc.mm_n.clip(lower=0), color="#1f5c8a", label="Other reportables net long")
a1.set_ylabel("Tonnes")
a1.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
gp = gold.loc["2024-01-01":]
a2.plot(gp.index, gp.values, color="#b8860b", lw=1.4)
a2.set_ylabel("COMEX gold, $/oz")
a2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
a2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
c_comex = save(fig, "comex")

# GVZ vs realised volatility
rv = (r.rolling(21).std() * np.sqrt(252) * 100).loc["2025-01-01":]
fig, ax = plt.subplots(figsize=(6.2, 3.0))
ax.plot(gvz.loc["2025-01-01":].index, gvz.loc["2025-01-01":].values, color=BLUE, lw=1.4, label="GVZ (implied, 30 days)")
ax.plot(rv.index, rv.values, color=ORANGE, lw=1.4, label="Realised, past 21 days")
ax.set_ylabel("%")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.legend(loc="upper left")
c_vol = save(fig, "vol")

# ------------------------------------------------------------------ slides
W, H = 960, 540
FONTS = {"L": "C:/Windows/Fonts/segoeuil.ttf", "R": "C:/Windows/Fonts/segoeui.ttf", "B": "C:/Windows/Fonts/segoeuib.ttf",
         "S": "C:/Windows/Fonts/seguisb.ttf"}
for k, f_ in FONTS.items():
    pdfmetrics.registerFont(TTFont(f"SUI-{k}", f_ if os.path.exists(f_) else FONTS["R"]))
C = colors.HexColor
st = lambda name, **kw: ParagraphStyle(name, **{"fontName": "SUI-R", "fontSize": 10, "leading": 13.2, "textColor": C(INK), **kw})  # noqa: E731
BUL = st("bul", leftIndent=10, bulletIndent=0, spaceAfter=5, fontSize=9.6, leading=12.6)
CELL = st("cell", fontSize=8, leading=10)
CELLB = st("cellb", fontName="SUI-B", fontSize=8, leading=10)
out_pdf = OUTDIR / "gold_desk_2026-11-20.pdf"
cv = rl_canvas.Canvas(str(out_pdf), pagesize=(W, H))
cv.setTitle("Gold Desk Weekly, week to 20 November 2026")
cv.setAuthor("Nikolay Gelshtein")
page = [0]


def new_slide(title, source=""):
    if page[0]:
        cv.showPage()
    page[0] += 1
    cv.setFillColor(colors.white)
    cv.rect(0, 0, W, H, stroke=0, fill=1)
    if title:
        cv.setFillColor(C("#c9a227"))
        cv.rect(36, H - 62, 7, 30, stroke=0, fill=1)
        cv.setFillColor(C(INK))
        cv.setFont("SUI-L", 30)
        cv.drawString(52, H - 58, title)
    cv.setStrokeColor(C(TEAL2))
    cv.setLineWidth(4)
    cv.line(36, 30, W - 36, 30)
    cv.setFillColor(C(MUTED))
    cv.setFont("SUI-R", 6.8)
    if source:
        cv.drawRightString(W - 36, 18, source)
    cv.drawString(36, 18, "Gold Desk Weekly  |  week to Fri 20 Nov 2026, news to Sun 22 Nov")
    cv.setFont("SUI-B", 8)
    cv.setFillColor(C(INK))
    cv.drawRightString(W - 36, 36, str(page[0]))


def bar_header(x, y, w, text, h=22):
    cv.setFillColor(C(TEAL2))
    cv.roundRect(x, y, w, h, 5, stroke=0, fill=1)
    cv.setFillColor(colors.white)
    cv.setFont("SUI-L", 14)
    cv.drawCentredString(x + w / 2, y + 6, text)


def text_block(x, y_top, w, items, bullets=True, bg=None, pad=8, h=None):
    paras = [Paragraph(t_, BUL, bulletText="\u2022") if bullets else Paragraph(t_, st("p", fontSize=9.6, leading=12.6, spaceAfter=5)) for t_ in items]
    hh = sum(p_.wrap(w - 2 * pad, 1000)[1] + 5 for p_ in paras)
    if bg:
        cv.setFillColor(C(bg))
        cv.roundRect(x, y_top - (h or hh + 2 * pad), w, h or hh + 2 * pad, 8, stroke=0, fill=1)
    y = y_top - pad
    for p_ in paras:
        _, ph = p_.wrap(w - 2 * pad, 1000)
        p_.drawOn(cv, x + pad, y - ph)
        y -= ph + 5
    return y


def image(path, x, y_top, w=None, h=None):
    iw, ih = ImageReader(path).getSize()
    if w and not h:
        h = w * ih / iw
    elif h and not w:
        w = h * iw / ih
    cv.drawImage(path, x, y_top - h, w, h)
    return y_top - h


def table(rows, x, y_top, widths, header_bg=TEAL2, size=8, zebra=True, styles=()):
    cs = st("c", fontSize=size, leading=size + 2.2)
    cb = st("cb", fontName="SUI-B", fontSize=size, leading=size + 2.2, textColor=colors.white)
    cf = st("cf", fontName="SUI-B", fontSize=size, leading=size + 2.2)
    esc = lambda v: str(v).replace("&amp;", "&").replace("&", "&amp;")  # noqa: E731
    data = [[Paragraph(esc(v), cb) for v in rows[0]]] + [[Paragraph(esc(v), cf if j == 0 else cs) for j, v in enumerate(r_)] for r_ in rows[1:]]
    t = Table(data, colWidths=widths)
    sty = [("BACKGROUND", (0, 0), (-1, 0), C(header_bg)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
           ("LINEBELOW", (0, 1), (-1, -1), 0.3, C(GRID))]
    if zebra:
        sty += [("BACKGROUND", (0, i_), (-1, i_), C("#f6f5f2")) for i_ in range(2, len(rows), 2)]
    t.setStyle(TableStyle(sty + list(styles)))
    _, th = t.wrapOn(cv, W, H)
    t.drawOn(cv, x, y_top - th)
    return y_top - th


pc = lambda v, d=1: f"{v * 100:+.{d}f}%"  # noqa: E731


def nth(q):
    n_ = int(round(q * 100))
    return f"{n_}{'th' if 10 <= n_ % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n_ % 10, 'th')}"

wk = week
gp_ = P["Gold"]

# ================================================================== desk forecast, scorecard, weekend
from scipy import stats  # noqa: E402

from gold_desk import store  # noqa: E402
from gold_desk.backtest import score  # noqa: E402
from gold_desk.model import GRID_Q, Forecast, touch_probabilities  # noqa: E402

S = json.load(open(OUTDIR / "summary.json"))
S_PREV = json.load(open(DESK / "reports" / "2026-11-13" / "summary.json"))
LIVE = [r_ for r_ in store.read_records() if r_["source"] == "live"]
REC = LIVE[-1]
assert REC["origin"] == S["origin"] == "2026-11-20" and abs(REC["spot"] - gold.iloc[-1]) < 0.01
REC_PREV = [r_ for r_ in LIVE if r_["origin"] == "2026-11-13"][0]
FC = Forecast.from_record(REC)
MD, MP = S["model"], S_PREV["model"]
LF = S["last_forecast"]
# COMEX has no settlement on Thanksgiving (26 Nov): count trading days around it
BD = pd.offsets.CustomBusinessDay(holidays=["2026-11-26", "2026-12-25", "2027-01-01"])


def hdate(o, h):
    return pd.Timestamp(o) + h * BD


GQ = [int(q) for q in GRID_Q]
gq = lambda rec, h, q: float(rec["grid"][str(h)][GQ.index(q)])  # noqa: E731
HLAB = {1: "1 day", 5: "1 week", 10: "2 weeks", 21: "1 month"}

# scorecard: every live forecast made before this one
scored = score([r_ for r_ in LIVE if r_["origin"] < S["origin"]], gold)
scd = {(str(pd.Timestamp(r_.origin).date()), int(r_.h)): r_ for r_ in scored.itertuples()}
card = []
for rec in LIVE[:-1]:
    for h in (1, 5, 10, 21):
        row = {"origin": rec["origin"], "h": h, "target": str(hdate(rec["origin"], h).date()),
               "q5": gq(rec, h, 5), "q95": gq(rec, h, 95)}
        if (rec["origin"], h) in scd:
            r_ = scd[(rec["origin"], h)]
            row.update(realised=float(r_.realised), pit=float(r_.pit), inside=bool(r_.inside90))
            k = gold.index.get_loc(pd.Timestamp(rec["origin"]))
            assert str(gold.index[k + h].date()) == row["target"], row
            assert abs(gold.iloc[k + h] - row["realised"]) < 0.01, row
        card.append(row)
n_sc = sum("pit" in c_ for c_ in card)
n_in = sum(c_.get("inside", False) for c_ in card)
assert abs(LF["pit"] - [c_ for c_ in card if c_["origin"] == "2026-11-13" and c_["h"] == 5][0]["pit"]) < 1e-9

# touch probabilities from Friday's close (closes only), levels quoted in the press plus round numbers
LEVELS = [3250.0, 3430.0, 3700.0, 3886.3, 4000.0]
t1w = touch_probabilities(FC.fit, FC.spot, LEVELS, horizon=5)
t1m = touch_probabilities(FC.fit, FC.spot, LEVELS, horizon=21)
nu_p = MP["nu"]
p_tail = float(stats.t.cdf(-LF["worst_day_x_sigma"] * np.sqrt(nu_p / (nu_p - 2)), nu_p))

# the weekend: 5-minute futures from Friday's close to Sunday 23:55 ET (Yahoo, New York time)
w5 = pd.read_csv(OUTDIR / "data" / "weekend_5m.csv", index_col=0, parse_dates=True)
fri5 = w5.loc[:"2026-11-20 16:55"].ffill().iloc[-1]
sun5 = w5.loc["2026-11-22 18:00":"2026-11-22 23:59"]
sun_last = sun5.ffill().iloc[-1]
assert abs(fri5["GC=F"] - gold.iloc[-1]) < 0.5
WKD = [("Gold (COMEX)", "GC=F"), ("Silver", "SI=F"), ("S&P 500 futures", "ES=F"), ("Bitcoin", "BTC-USD"),
       ("Dollar index", "DX-Y.NYB"), ("10-yr T-note futures, price", "ZN=F")]
wkd = [{"name": n_, "ticker": t_, "fri": float(fri5[t_]), "sun": float(sun_last[t_]), "chg": float(sun_last[t_] / fri5[t_] - 1)}
       for n_, t_ in WKD]
gsun = sun5["GC=F"].dropna()
weekend = {"gold_open": float(gsun.iloc[0]), "gold_open_time": str(gsun.index[0]), "gold_last": float(gsun.iloc[-1]),
           "gold_last_time": str(gsun.index[-1]), "gold_hi": float(gsun.max()), "gold_lo": float(gsun.min()), "assets": wkd}
WG = {a["ticker"]: a for a in wkd}
sun_pct = float(np.interp(weekend["gold_last"], REC["grid"]["5"], GQ)) / 100

wk_drv = DRV["week"]
unexpl = wk_drv["residual"] / wk_drv["r_gold"]
OUT["desk"] = {"model": MD, "model_prev": MP, "forward": S["forward"], "rolling": S["rolling"],
               "touch_1w": {str(k): v for k, v in t1w.items()}, "touch_1m": {str(k): v for k, v in t1m.items()},
               "scorecard": card, "weekend": weekend, "sunday_pct_in_1w": sun_pct, "friday_tail_p": p_tail,
               "unexplained_share": unexpl}
(OUTDIR / "desk_week.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")

fmt_usd = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")

# chart of the week: last week's range and where gold landed
fig, ax = plt.subplots(figsize=(6.2, 3.3))
H10 = 10
dts = [PREV] + [hdate(PREV, h) for h in range(1, H10 + 1)]
bnd = lambda q: [REC_PREV["spot"]] + REC_PREV["fan"][str(q)][:H10]  # noqa: E731
ax.fill_between(dts, bnd(1), bnd(99), color=BLUE, alpha=0.10, lw=0, label="13 Nov forecast: 98% range")
ax.fill_between(dts, bnd(5), bnd(95), color=BLUE, alpha=0.26, lw=0, label="13 Nov forecast: 90% range")
ax.plot(dts, bnd(50), color=BLUE, lw=0.9, ls="--")
hist_ = gold.loc["2026-10-20":]
ax.plot(hist_.index, hist_.values, color="#b8860b", lw=1.8, marker="o", ms=2.4, label="COMEX gold, daily close")
sun_t = pd.Timestamp("2026-11-22 23:55")
ax.plot([FRI, sun_t], [gold.iloc[-1], weekend["gold_last"]], color=ORANGE, lw=1.1, ls=":")
ax.scatter([sun_t], [weekend["gold_last"]], color=ORANGE, s=22, zorder=5, label="Sunday 22 Nov, 23:55 ET")
ax.annotate(f"Fri ${gold.iloc[-1]:,.0f}\n{LF['pit'] * 100:.1f}th percentile", xy=(FRI, gold.iloc[-1]), xytext=(-92, -4),
            textcoords="offset points", fontsize=7.4, color=INK, va="center",
            arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.7})
ax.yaxis.set_major_formatter(fmt_usd)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.set_ylabel("$/oz")
ax.legend(loc="lower left", fontsize=7)
c_cotw2 = save(fig, "cotw_fan")

# weekend: gold on Friday and Sunday evening, 5-minute bars
gf = w5["GC=F"].dropna()
f_seg, s_seg = gf.loc["2026-11-20 08:00":"2026-11-20 16:55"], gf.loc["2026-11-22 18:00":"2026-11-22 23:59"]
fig, ax = plt.subplots(figsize=(6.0, 2.15))
xf = np.arange(len(f_seg))
xs2 = np.arange(len(s_seg)) + len(f_seg) + 8
ax.axvspan(len(f_seg) + 0.5, len(f_seg) + 7.5, color=BOX, lw=0)
ax.text(len(f_seg) + 4, gold.iloc[-1] + 4, "weekend", rotation=90, ha="center", va="bottom", fontsize=7, color=MUTED)
ax.plot(xf, f_seg.values, color="#b8860b", lw=1.3)
ax.plot(xs2, s_seg.values, color="#b8860b", lw=1.3)
ax.axhline(gold.iloc[-1], color=MUTED, lw=0.8, ls="--")
ax.text(xs2[-1], gold.iloc[-1] - 4, f"Friday close ${gold.iloc[-1]:,.0f}", ha="right", va="top", fontsize=7, color=MUTED)
tk = list(xf[::36]) + list(xs2[::36])
tl = [t_.strftime("Fri %H:%M") for t_ in f_seg.index[::36]] + [t_.strftime("Sun %H:%M") for t_ in s_seg.index[::36]]
ax.set_xticks(tk)
ax.set_xticklabels(tl, fontsize=6.6)
ax.yaxis.set_major_formatter(fmt_usd)
c_wk_line = save(fig, "weekend_line")

fig, ax = plt.subplots(figsize=(6.0, 2.2))
y_ = np.arange(len(wkd))[::-1]
vals = [a["chg"] * 100 for a in wkd]
ax.barh(y_, vals, color=["#b8860b" if a["ticker"] == "GC=F" else "#1c5cab" for a in wkd], height=0.6)
for yi, v in zip(y_, vals):
    ax.text(v + (0.06 if v >= 0 else -0.06), yi, f"{v:+.2f}%" if abs(v) < 1 else f"{v:+.1f}%", va="center",
            ha="left" if v >= 0 else "right", fontsize=7.4, color=INK2)
ax.set_yticks(y_)
ax.set_yticklabels([a["name"] for a in wkd], fontsize=7.8)
ax.axvline(0, color="#c3c2b7", lw=0.8)
ax.grid(axis="x", color=GRID)
ax.grid(axis="y", visible=False)
ax.set_xlim(min(vals) - 0.8, max(vals) + 0.9)
ax.set_xlabel("Change from Friday 16:55 to Sunday 23:55 ET, %", fontsize=7.6)
c_wk_bars = save(fig, "weekend_bars")

# ranges: Friday's forecast fan to one month
fig, ax = plt.subplots(figsize=(6.4, 3.4))
hh_ = gold.loc["2026-08-01":]
ax.plot(hh_.index, hh_.values, color="#b8860b", lw=1.5, label="COMEX gold, daily close")
dts2 = [FRI] + [hdate(FRI, h) for h in range(1, 22)]
b2 = lambda q: [REC["spot"]] + REC["fan"][str(q)]  # noqa: E731
ax.fill_between(dts2, b2(1), b2(99), color=BLUE, alpha=0.10, lw=0, label="98% range")
ax.fill_between(dts2, b2(5), b2(95), color=BLUE, alpha=0.22, lw=0, label="90% range")
ax.fill_between(dts2, b2(25), b2(75), color=BLUE, alpha=0.40, lw=0, label="50% range")
ax.plot(dts2, b2(50), color=BLUE, lw=0.9, ls="--")
for lv in (3430, 3700):
    ax.axhline(lv, color=MUTED, lw=0.7, ls=":")
    ax.text(hh_.index[0], lv, f"${lv:,}", va="bottom", fontsize=7, color=MUTED)
ax.axvline(pd.Timestamp("2026-12-09"), color=ORANGE, lw=0.9, ls="--")
ax.text(pd.Timestamp("2026-12-09"), ax.get_ylim()[1], " FOMC 9 Dec", va="top", fontsize=7, color=ORANGE)
ax.yaxis.set_major_formatter(fmt_usd)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.set_ylabel("$/oz")
ax.legend(loc="lower left", fontsize=7, ncol=2)
c_fan = save(fig, "fan")


def key_block(x, y_top, w, h, title, items):
    cv.setFillColor(C(TEAL))
    cv.roundRect(x, y_top - h, w, h, 10, stroke=0, fill=1)
    cv.setFillColor(C("#e9c46a"))
    cv.setFont("SUI-S", 11.5)
    cv.drawString(x + 16, y_top - 26, title)
    kb = st("kb", textColor=colors.white, fontSize=10.2, leading=13.8, leftIndent=11, bulletColor=colors.white)
    y = y_top - 40
    for t_ in items:
        p_ = Paragraph(t_, kb, bulletText="•")
        _, ph = p_.wrap(w - 32, 1000)
        p_.drawOn(cv, x + 16, y - ph)
        y -= ph + 8


usd = lambda v: f"${v:,.0f}"  # noqa: E731
fw = {r_["h"]: r_ for r_ in S["forward"]}
spx = P["S&P 500"]
fri_ret = gold.iloc[-1] / gold.iloc[-2] - 1
dr_ = gold.loc["2000-01-01":].pct_change().dropna()
big_falls = dr_[dr_ <= fri_ret + 1e-12]
big_years = [f"{y_}: {n_}" for y_, n_ in big_falls.groupby(big_falls.index.year).size().items()]
OUT["desk"]["big_falls"] = {str(k.date()): float(v) for k, v in big_falls.items()}
(OUTDIR / "desk_week.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")

# 1 cover
page[0] += 1
cv.setFillColor(colors.white)
cv.rect(0, 0, W, H, stroke=0, fill=1)
cv.setFillColor(C(TEAL))
cv.roundRect(20, 20, W - 40, H - 40, 18, stroke=0, fill=1)
image(c_cover, 470, H - 26, w=468, h=H - 52)
cv.setFillColor(C(TEAL))
cv.rect(20, 20, 452, H - 40, stroke=0, fill=1)
cv.setFillColor(C("#e9c46a"))
cv.setFont("SUI-S", 15)
cv.drawString(48, H - 70, "GOLD DESK")
cv.setFillColor(C("#7fd1b9"))
cv.setFont("SUI-L", 46)
cv.drawString(48, 226, "Weekly Gold")
cv.drawString(48, 174, "Desk Note")
cv.setFont("SUI-R", 15)
cv.drawString(48, 126, "Week to Friday 20 November 2026")
cv.setFont("SUI-R", 11)
cv.drawString(48, 104, "With the weekend and the Sunday open to 22 November, 23:55 ET")
cv.setFont("SUI-R", 8.5)
cv.drawString(48, 52, "All data as of the Friday 20 November close unless stated otherwise")

# 2 what you need to know
new_slide("What you need to know – a liquidation week, a Sunday bounce",
          "Chart of the week: desk forecast logged on 13 Nov (GARCH-t, zero drift, 20,000 paths) and COMEX closes; Sunday: 5-minute futures. Prices: Yahoo Finance.")
bar_header(36, 446, 440, "Highlights")
bar_header(484, 446, 440, "Chart of the week: last week's range and where gold landed")
text_block(36, 440, 440, [
    f"Gold had its worst week since at least 2000 in our data: <b>{pc(wk['ww'])}</b> to {usd(wk['close'])} (COMEX), "
    f"{pc(wk['from_peak'], 0)} from the {pd.Timestamp(wk['peak_date']):%d %b} record and {pc(wk['ytd'])} for the year.",
    f"A hawkish Fed met an AI-led stock rout: the S&amp;P 500 fell {abs(spx['ww']) * 100:.1f}%, the VIX closed at {vol['vix']:.1f}. "
    f"Gold fell with stocks while the 10-year yield dropped {abs(P['US 10Y']['ww']):.0f} bp: forced selling, not a new macro case.",
    f"The desk's 1-week forecast of 13 Nov missed: Friday's close was at the <b>{LF['pit'] * 100:.1f}th percentile</b>, "
    f"below the 90% range of {usd(LF['band90'][0])}-{usd(LF['band90'][1])}. Friday's {pc(fri_ret)} was "
    f"{LF['worst_day_x_sigma']:.1f} times the daily move the model expected.",
    f"<b>Sunday evening</b> gold reopened at {usd(weekend['gold_open'])} and stood at {usd(weekend['gold_last'])} by 23:55 ET "
    f"({pc(WG['GC=F']['chg'])}), with S&amp;P 500 futures {pc(WG['ES=F']['chg'])}: a relief bounce for all risk assets together.",
    f"Ranges are wider: next-day volatility {MD['vol_next'] * 100:.1f}% (13 Nov: {MP['vol_next'] * 100:.1f}%). "
    f"90% range for the coming week {usd(fw[5]['q5'])}-{usd(fw[5]['q95'])}.",
], bg=BOX, h=252)
image(c_cotw2, 490, 438, w=428)
iw_, ih_ = ImageReader(c_bars).getSize()
image(c_bars, 36 + (888 - 140 * iw_ / ih_) / 2, 180, h=140)

# 3 desk view
new_slide("Desk view", "Model: GARCH(1,1) with Student-t shocks on daily COMEX closes, zero drift, refitted on Friday's close. Tests: gold_desk/backtest.py and gold_desk/drivers.py.")
key_block(36, 470, 450, 238, "THE DESK VIEW, FROM FRIDAY'S CLOSE", [
    "<b>Direction: no call.</b> The desk runs a zero-drift model. No drift rule passed our pre-registered tests, and "
    "positioning and ETF flows failed as predictors (H3, 21 Nov). We do not forecast a rebound or a further fall.",
    f"<b>Volatility: high and slow to fade.</b> Next-day volatility is {MD['vol_next'] * 100:.1f}% against a long-run "
    f"{MD['vol_long_run'] * 100:.1f}%. With a half-life of {MD['half_life_days']:.0f} trading days, ranges stay wide "
    "through the 8-9 Dec FOMC.",
    f"<b>Regime: liquidation.</b> {unexpl * 100:.0f}% of the week's fall is not explained by rates, the dollar, stress, "
    "stocks, oil or flows. Gold traded as a source of cash, moving with stocks instead of against them.",
    f"<b>The week ahead:</b> PCE on Wednesday is the one scheduled test; Thanksgiving thins trading from Wednesday. "
    f"The 1-week 90% range is {usd(fw[5]['q5'])}-{usd(fw[5]['q95'])}; Sunday evening's {usd(weekend['gold_last'])} sits "
    f"near the {nth(sun_pct)} percentile of it.",
])
bar_header(500, 446, 424, "What we watch for a turn")
text_block(500, 440, 424, [
    "<b>Gold up on a day stocks fall:</b> the safe-haven link back, the clearest sign the forced selling is done.",
    "<b>GLD back to weekly inflows:</b> our H2 test says flows follow the price, so this would confirm a turn, not predict one.",
    "<b>A soft PCE print</b> (core below 0.3% m/m) that pulls real yields lower. December is priced; the surprise would "
    "move the path for 2027.",
    f"<b>A close below $3,430</b>, the support quoted in the press: the model gives it a {t1w[3430.0] * 100:.0f}% chance "
    "within a week, so a break alone says little.",
], bg=BOX, h=176)
bar_header(500, 252, 424, "What moved gold this week (driver model)")
image(c_cotw, 506, 246, w=412)
bar_header(36, 206, 450, "The model, then and now")
rows = [["Desk model", "13 Nov", "20 Nov"],
        ["Next-day volatility, annualised", f"{MP['vol_next'] * 100:.1f}%", f"{MD['vol_next'] * 100:.1f}%"],
        ["Long-run volatility", f"{MP['vol_long_run'] * 100:.1f}%", f"{MD['vol_long_run'] * 100:.1f}%"],
        ["Half-life of a volatility shock, days", f"{MP['half_life_days']:.0f}", f"{MD['half_life_days']:.0f}"],
        ["Tail thickness (t degrees of freedom)", f"{MP['nu']:.2f}", f"{MD['nu']:.2f}"],
        ["1-week 90% range", f"{usd(S_PREV['forward'][0]['q5'])}-{usd(S_PREV['forward'][0]['q95'])}",
         f"{usd(fw[5]['q5'])}-{usd(fw[5]['q95'])}"]]
table(rows, 36, 178, [240, 105, 105], size=8.6)

# 4 weekend
new_slide("The weekend and the Sunday open",
          "Sunday prices: Yahoo Finance 5-minute futures, New York time (DXY: ICE index). News: CNBC, Fortune, FinanceFeeds (Kitco survey, analyst levels, CME FedWatch).")
bar_header(36, 446, 470, "What happened between Friday's close and Sunday night")
text_block(36, 438, 470, [
    "<b>Fed:</b> we found no new remarks by Fed officials over the weekend; the latest signals remain the minutes of "
    "18 Nov and Waller's case for 50 bp. A 25 bp hike on 9 Dec is priced as near-certain (CME FedWatch; outlets "
    "report 93-99%).",
    "<b>Stocks:</b> the selloff was led by tech on fears that the AI boom is ending (CNBC, Fortune). Futures reopened "
    "higher on Sunday: S&amp;P 500 +1.1% at the open (CNBC), +2.1% by 21:16 ET (Fortune).",
    "<b>Sentiment:</b> Kitco's weekly survey (20 Nov): 9 of 15 Wall Street analysts expect lower prices, 4 higher; "
    "Main Street 46% lower, 36% higher (via FinanceFeeds).",
    "<b>Levels in the press:</b> support at $3,430-3,450 (Marc Chandler, Bannockburn Global Forex) and resistance at "
    "$3,597-3,699 (Kitco), both via FinanceFeeds.",
    f"<b>Sunday evening:</b> gold opened at {usd(weekend['gold_open'])}, traded between {usd(weekend['gold_lo'])} and "
    f"{usd(weekend['gold_hi'])} and stood at {usd(weekend['gold_last'])} at 23:55 ET. Gold, silver, stocks and bitcoin "
    "rose together, the mirror image of Friday; the dollar barely moved and Treasury futures slipped.",
], h=386)
bar_header(520, 446, 404, "COMEX gold, Friday and Sunday evening (5-minute)")
image(c_wk_line, 526, 440, w=392)
bar_header(520, 250, 404, "Friday close to Sunday night")
image(c_wk_bars, 526, 244, w=392)

# 5 all about gold
new_slide("All about Gold", "Sources: CFTC (report of 17 Nov), State Street (GLD), CME FedWatch via press, CNBC, Reuters, Quartz.")
bar_header(36, 446, 470, "The week in review")
text_block(36, 438, 470, [
    f"Gold fell on four of five days; Friday alone took {abs(fri_ret) * 100:.1f}% off as stocks slumped "
    f"{abs(s_('^GSPC').iloc[-1] / s_('^GSPC').iloc[-2] - 1) * 100:.1f}%.",
    f"GLD saw {gld_rows[-1]['flow_m']:+,.0f} $m of flows this week to {pd.Timestamp(gld_ytd['last']):%d %b} "
    f"({gld_rows[-1]['dt']:+.1f} t); holders stayed calmer than the price. Money managers trimmed their COMEX net long "
    f"to {c_last.mm_n:,.0f} t on {cot.index[-1]:%d %b} from {c_prev.mm_n:,.0f} t, before the worst of the week.",
    f"Implied volatility jumped: the GVZ closed at {vol['gvz']:.1f}, {vol['gvz_1m']:+.1f} points in a month.",
], h=168)
bar_header(36, 262, 470, "Into the new week")
text_block(36, 254, 470, [
    f"<b>Sunday's bounce:</b> {pc(WG['GC=F']['chg'])} by 23:55 ET, in step with stocks. After a liquidation week, a "
    "bounce that moves with stocks tells us little about gold's own demand.",
    "<b>US PCE inflation (Wed 25 Nov, 08:30 ET):</b> headline and core expected at 0.3% m/m. A hot print would harden "
    "the case for hikes beyond December.",
    "<b>Next CFTC report:</b> covers positions to Tue 24 Nov, the first to show how much of the speculative long was "
    "sold in the crash; Thanksgiving may delay its release.",
], h=200)
bar_header(520, 446, 404, "Gold market positioning, w/w change")
image(c_pos, 526, 440, w=392)

# 6 last week's data
new_slide("Last week's US data", "Actual vs consensus where a consensus was published; colours: green = better than expected for the economy, red = worse. Sources: Kitco, Reuters, Mitrade (single source, flagged *).")
bar_header(36, 446, 470, "Data releases, 16-20 Nov")
eco = [["Date", "What", "Consensus", "Actual"],
       ["Mon 16", "Empire State manufacturing (Nov)", "~17.6", "7.8"],
       ["Tue 17", "Retail sales, m/m (Oct)", "0.2%", "0.2%"],
       ["Tue 17", "Retail sales ex autos, m/m (Oct)", "0.4%", "0.6%"],
       ["Tue 17", "Industrial production, m/m (Oct)", "0.1%", "-0.4%"],
       ["Thu 19", "Initial jobless claims (week to 14 Nov)", "197k", "203k"],
       ["Thu 19", "Continuing claims (week to 7 Nov)", "\u2013", "1.763m"],
       ["Thu 19", "Philadelphia Fed outlook (Nov)*", "prior 20.9", "6.3"],
       ["Thu 19", "Leading indicators, m/m (Oct)*", "\u2013", "-0.3%"]]
colrs = {1: RED, 3: GREEN, 4: RED, 5: RED}
table(eco, 36, 418, [60, 250, 80, 80], size=9, styles=[("TEXTCOLOR", (3, k), (3, k), C(v)) for k, v in colrs.items()])
bar_header(520, 446, 404, "Recap of the week")
text_block(520, 418, 404, [
    "<b>Fed:</b> the minutes of the 27-28 Oct meeting showed almost all officials see further hikes as likely appropriate; "
    "two dissented for a hike. Waller backs 50 bp in December; Paulson said inflation could warrant another increase; "
    "Goolsbee did not rule out a larger move (CNBC, Reuters, Quartz).",
    "<b>Activity:</b> factory surveys weakened sharply (Empire, Philadelphia) and industrial output fell, while "
    "consumers kept spending. Layoffs stay low but continuing claims rose to their highest since late August.",
    "<b>Markets:</b> a sixth straight loss for US stocks by Friday, a VIX above 35 and falling Treasury yields: a growth "
    "scare on top of a rate scare.",
], bg=BOX, h=330)
# 7 sessions
new_slide("Market movement across global trading sessions", "5-minute COMEX gold futures, 16-20 Nov 2026, New York time. Monday's weekend gap is not included. Source: Yahoo Finance.")
image(c_sess, 36, 470, w=888)
rows = [["Session", "Time window (New York)", "Cumulative return", "% of total return", "Annualised volatility", "% of total variance"]]
for s in sessions:
    rows.append([s["session"], s["window"], pc(s["ret"], 2), f"{s['share'] * 100:.1f}%", f"{s['vol'] * 100:.1f}%", f"{s['var_share'] * 100:.1f}%"])
table(rows, 120, 190, [110, 150, 120, 120, 130, 120], header_bg="#c9a227", size=9)
cv.setFont("SUI-R", 8.5)
cv.setFillColor(C(INK2))
worst = min(sessions, key=lambda s: s["ret"])
mv = max(sessions, key=lambda s: s["var_share"])
cv.drawString(120, 92, f"Most of the week's fall came in the {worst['session']} session ({pc(worst['ret'], 1)}); "
                       f"the {mv['session']} session carried the most variance ({mv['var_share'] * 100:.0f}%), the Thursday-evening slide.")

# 8 week ahead
new_slide("The week ahead", "Consensus: Trading Economics, Investing.com, 1trader (via press, 20 Nov); sources differ where shown. PMI priors and Friday's early close: CNBC. Nowcast: Cleveland Fed.")
bar_header(36, 446, 520, "Consensus expectations")
cal = [["Date", "Where", "What", "Prior", "Consensus"],
       ["Mon 23", "US", "S&P Global flash PMI, manufacturing / services (Nov)", "54.5 / 56.1", "–"],
       ["Tue 24", "US", "Conference Board consumer confidence (Nov)*", "91.7", "92.0"],
       ["Wed 25", "US", "PCE price index, m/m (Oct)", "0.5%", "0.3%"],
       ["Wed 25", "US", "Core PCE, m/m (Oct)", "–", "0.3%"],
       ["Wed 25", "US", "Core PCE, y/y (Oct), Cleveland Fed nowcast", "–", "3.2%"],
       ["Wed 25", "US", "GDP, 2nd estimate (Q3), annualised", "3.4%", "3.4-3.5%"],
       ["Wed 25", "US", "Durable goods orders, m/m (Oct)", "1.8-1.9%", "0.0-0.5%"],
       ["Wed 25", "US", "Initial jobless claims (week to 21 Nov)", "203k", "–"],
       ["Wed 25", "US", "Personal spending (Oct); Fed Beige Book", "–", "–"],
       ["Thu 26", "US", "Thanksgiving: stock markets closed", "", ""],
       ["Fri 27", "US", "Stocks close at 1 p.m. ET; no major data", "", ""],
       ["8-9 Dec", "US", "FOMC: 25 bp hike priced as near-certain (CME FedWatch)", "", ""]]
table(cal, 36, 418, [60, 44, 270, 70, 76], size=8.6)
cv.setFont("SUI-R", 7)
cv.setFillColor(C(MUTED))
cv.drawString(36, 92, "*Day as given by one calendar provider.")
bar_header(570, 446, 354, "Things to look out for")
text_block(570, 418, 354, [
    "<b>PCE (Wed):</b> the Fed's preferred gauge. Core near 0.3% m/m keeps the hike path intact; a miss lower would "
    "ease pressure on real yields.",
    "<b>Beige Book (Wed):</b> how widely officials see inflation spreading, the theme of the minutes.",
    "<b>Liquidity:</b> Thanksgiving thins trading. After forced selling, both further drops and sharp rebounds come "
    f"easier in thin markets; the model's 1-week 90% range is {usd(fw[5]['q5'])}-{usd(fw[5]['q95'])} (p. 9).",
    "<b>The link with stocks:</b> if gold keeps moving with equities, the selling is still about cash, not about gold.",
], bg=BOX, h=300)

# 9 ranges
new_slide("Probabilistic ranges from Friday's close",
          "Desk model logged on 20 Nov (record 1,089 in store/live.jsonl). Dates count COMEX trading days and assume no settlement on Thanksgiving. Touch: share of paths with a close through the level.")
rows = [["Horizon", "Ends about", "1%", "5%", "25%", "Median", "75%", "95%", "99%"]]
for h in (5, 10, 21):
    f_ = fw[h]
    rows.append([HLAB[h], f"{hdate(FRI, h):%a %d %b}"] + [usd(f_[k]) for k in ("q1", "q5", "q25", "q50", "q75", "q95", "q99")])
table(rows, 36, 470, [92, 92] + [78] * 7, size=9)
bar_header(36, 372, 520, "The fan to one month, with press levels and the FOMC")
image(c_fan, 44, 344, w=504)
bar_header(570, 372, 354, "Chance of a close through a level")
rows = [["Level", "Note", "Within 1 week", "Within 1 month"]]
notes = {3250.0: "round number", 3430.0: "press support", 3700.0: "press resistance", 3886.3: "13 Nov close",
         4000.0: "round number"}
for lv in LEVELS:
    rows.append([usd(lv), notes[lv], f"{t1w[lv] * 100:.0f}%", f"{t1m[lv] * 100:.0f}%"])
y = table(rows, 570, 344, [70, 110, 87, 87], size=9)
ro = {r_["window"]: r_ for r_ in S["rolling"]}
text_block(570, y - 10, 354, [
    f"Shadow fits (not used): a 10-year window gives a 1-week 90% range of {usd(ro['10 years']['week90'][0])}-"
    f"{usd(ro['10 years']['week90'][1])}, a 5-year window {usd(ro['5 years']['week90'][0])}-{usd(ro['5 years']['week90'][1])}. "
    "Neither passed its test, so the full sample stays.",
    f"Sunday evening's {usd(weekend['gold_last'])} is near the {nth(sun_pct)} percentile of the 1-week range.",
], bullets=True)

# 10 scorecard
new_slide("Scorecard: the desk's live forecasts",
          "Percentile: where the realised COMEX close fell in the forecast distribution. Backfill: 1,088 weekly forecasts since 2006 made with data up to each origin only.")
bar_header(36, 446, 520, "Every live forecast so far")
rows = [["Made", "Horizon", "Target", "90% range", "Outcome", "Percentile", "Inside?"]]
sty = []
for i_, c_ in enumerate(card, start=1):
    if "pit" in c_:
        ok = c_["inside"]
        rows.append([f"{pd.Timestamp(c_['origin']):%d %b}", HLAB[c_["h"]], f"{pd.Timestamp(c_['target']):%a %d %b}",
                     f"{usd(c_['q5'])}-{usd(c_['q95'])}", usd(c_["realised"]), f"{c_['pit'] * 100:.1f}",
                     "yes" if ok else ("no, below" if c_["pit"] < 0.05 else "no, above")])
        sty.append(("TEXTCOLOR", (6, i_), (6, i_), C(GREEN if ok else RED)))
    else:
        rows.append([f"{pd.Timestamp(c_['origin']):%d %b}", HLAB[c_["h"]], f"{pd.Timestamp(c_['target']):%a %d %b}",
                     f"{usd(c_['q5'])}-{usd(c_['q95'])}", "pending", "", ""])
        sty.append(("TEXTCOLOR", (4, i_), (4, i_), C(MUTED)))
table(rows, 36, 418, [62, 66, 82, 128, 72, 64, 66], size=8.8, styles=sty)
bar_header(570, 446, 354, "Share of outcomes inside the 90% range")
cov = {(r_["window"], r_["h"]): r_ for r_ in S["coverage"]}
rows = [["Window", "1 day", "1 week", "2 weeks", "1 month"]]
for wn in ("All history", "Last 52 weeks", "Live only"):
    rows.append([wn] + [(f"{cov[(wn, h)]['inside90'] * 100:.0f}% ({cov[(wn, h)]['n']})" if cov[(wn, h)]["n"] else "–")
                        for h in (1, 5, 10, 21)])
y = table(rows, 570, 418, [96, 64, 64, 66, 64], size=8.4)
text_block(570, y - 10, 354, [
    f"Live so far: {n_in} of {n_sc} scored ranges held the outcome. A 90% range should miss about one time in ten, "
    "so one miss in five is no verdict; the backfill is the real test.",
    f"Friday's {pc(LF['worst_day_ret'])} was a {LF['worst_day_x_sigma']:.1f}-sigma day for the model of 13 Nov. With "
    f"its fat tails that has a {p_tail * 100:.2f}% chance per day, about once every {1 / p_tail:,.0f} trading days.",
    f"Daily falls of {abs(fri_ret) * 100:.1f}% or more since 2000: {len(big_falls)} ({', '.join(big_years)}). After such "
    f"a day the model widens at once: next-day volatility went from {MP['vol_next'] * 100:.1f}% to {MD['vol_next'] * 100:.1f}%.",
], bg=BOX, h=230)

# 11 performance table
new_slide("Market performance and positioning", "Weekly returns Friday to Friday; yields in bp. z-score: this week's move against the previous 52 weeks. Correlation: 52 weeks of weekly returns with gold.")
rows = [["Asset", "Friday close", "W/W", "YTD", "W/W z-score", "52w corr. with gold", "Corr. change"]]
sty = []
for i_, r_ in enumerate(perf, start=1):
    unit = r_["unit"]
    f_ = (lambda v: f"{v:+.0f} bp") if unit == "bp" else (lambda v: pc(v))
    close = f"{r_['close']:.2f}%" if unit == "bp" else (f"{r_['close']:,.0f}" if r_["close"] > 500 else f"{r_['close']:,.2f}")
    rows.append([r_["asset"], close, f_(r_["ww"]), f_(r_["ytd"]), f"{r_['z']:+.2f}", f"{r_['corr']:+.2f}", f"{r_['dcorr']:+.2f}"])
    for j, v in ((2, r_["ww"]), (3, r_["ytd"])):
        sty.append(("TEXTCOLOR", (j, i_), (j, i_), C(GREEN if v > 0 else RED)))
    if abs(r_["z"]) >= 2:
        sty.append(("BACKGROUND", (4, i_), (4, i_), C("#f8d7d3" if r_["z"] < 0 else "#d8eedd")))
table(rows, 36, 470, [170, 110, 100, 100, 100, 150, 110], size=8.8, header_bg="#5b3f86", styles=sty)
gc = OUT["cftc"]
cv.setFont("SUI-R", 8.5)
cv.setFillColor(C(INK2))
cv.drawString(36, 60, f"Gold positioning (CFTC, {pd.Timestamp(gc['date']):%d %b}): managed-money net long {gc['share'] * 100:.0f}% of open interest "
                      f"(prior {gc['share_prev'] * 100:.0f}%), 52-week z-score {gc['share_z52']:+.2f}, {nth(gc['share_pct'])} percentile since 2006.")

# 12 driver attribution
new_slide("Gold driver attribution (desk model)", "Model: weekly regression of gold on the listed drivers, betas re-estimated each week from the previous 156 weeks; pre-registered tests in gold_desk/drivers.py.")
image(c_attr, 36, 470, w=888)
rows = [["Week"] + [pd.Timestamp(r_["week"]).strftime("%d/%m/%y") for r_ in L12],
        ["Gold return"] + [f"{r_['r_gold'] * 100:+.2f}%" for r_ in L12],
        ["Explained by drivers"] + [f"{(r_['r_gold'] - r_['residual']) * 100:+.2f}%" for r_ in L12],
        ["Unexplained"] + [f"{r_['residual'] * 100:+.2f}%" for r_ in L12]]
table(rows, 36, 172, [116] + [64.3] * 12, size=7.6)
text_block(36, 104, 888, [
    f"Across all weeks since {pd.Timestamp(DRV['attr_first']):%Y}, the drivers explain {DRV['explained_oos'] * 100:.0f}% of weekly moves out of "
    f"sample; in 2026 only {DRV['explained_2026'] * 100:.0f}%. Gold's 2026 moves are driven by something the classic drivers miss: "
    "first a structural bid (the 'trend' bars), then its unwind.",
], bullets=False)
# 13 technicals
new_slide("Key technical data", "Daily closes to Fri 20 Nov (US 2-yr yield: FRED to 19 Nov). RSI: 9-week, weekly closes; red marks readings below 30 or above 70.")
rows = [["", "Last", "YTD high", "YTD low", "55-day SMA", "200-day SMA", "9-week RSI"]]
sty = []
for i_, t_ in enumerate(tech, start=1):
    f_ = t_["fmt"]
    rows.append([t_["name"], f_.format(t_["last"]), f_.format(t_["hi"]), f_.format(t_["lo"]), f_.format(t_["sma55"]),
                 f_.format(t_["sma200"]), f"{t_['rsi']:.1f}"])
    if t_["rsi"] < 30 or t_["rsi"] > 70:
        sty.append(("TEXTCOLOR", (6, i_), (6, i_), C(RED)))
table(rows, 70, 470, [150, 120, 120, 120, 120, 120, 120], header_bg=TEAL, size=10.5, styles=sty)

# 14 COMEX positioning tonnes
new_slide("COMEX positioning (tonnes)", "CFTC Commitments of Traders, disaggregated, futures only; contracts converted at 100 oz. Price: COMEX front month.")
image(c_comex, 36, 470, w=610)
text_block(660, 440, 264, [
    f"Money manager net long: <b>{c_last.mm_n:,.0f} t</b>",
    f"Other reportables net long: <b>{c_last.ot_n:,.0f} t</b>",
    f"Non-reportables net long: <b>{c_last.nr_n:,.0f} t</b>",
    f"Total net longs: <b>{c_last.mm_n + c_last.ot_n + c_last.nr_n:,.0f} t</b>",
    f"COMEX gold on {cot.index[-1]:%d %b}: <b>${px_at.iloc[-1]:,.0f}/oz</b>",
    f"Data as of {cot.index[-1]:%d %B %Y} (released Friday 20 Nov)",
])

# 15 COMEX table
new_slide("Weekly COMEX futures positioning data", "Tonnes (contracts x 100 oz). US$bn at the COMEX close on each report date. Source: CFTC.")
last10 = cot.iloc[-10:]
rows = [["Date", "MM long", "MM short", "MM net", "US$bn", "Net \u0394", "Other long", "Other short", "Other net", "US$bn", "Net \u0394"]]
for d_, r_ in last10.iterrows():
    k = cot.index.get_loc(d_)
    pm, po = cot.iloc[k - 1].mm_n, cot.iloc[k - 1].ot_n
    rows.append([d_.strftime("%d/%m/%y"), f"{r_.mm_l:.1f}", f"{r_.mm_s:.1f}", f"{r_.mm_n:.1f}", f"${r_.mm_bn:.1f}", f"{r_.mm_n - pm:+.1f}",
                 f"{r_.ot_l:.1f}", f"{r_.ot_s:.1f}", f"{r_.ot_n:.1f}", f"${r_.ot_bn:.1f}", f"{r_.ot_n - po:+.1f}"])
sty = [("TEXTCOLOR", (5, i_), (5, i_), C(RED if float(rows[i_][5]) < 0 else GREEN)) for i_ in range(1, len(rows))]
sty += [("TEXTCOLOR", (10, i_), (10, i_), C(RED if float(rows[i_][10]) < 0 else GREEN)) for i_ in range(1, len(rows))]
y = table(rows, 36, 470, [80] + [80.8] * 10, header_bg="#5b3f86", size=8.4, styles=sty)
rows = [["Date", "Non-rep. long", "Non-rep. short", "Non-rep. net", "US$bn", "Spreading MM", "Spreading other"]]
for d_, r_ in last10.iterrows():
    rows.append([d_.strftime("%d/%m/%y"), f"{r_.nr_l:.1f}", f"{r_.nr_s:.1f}", f"{r_.nr_n:.1f}", f"${r_.nr_bn:.1f}", f"{r_.mm_sp:.1f}", f"{r_.ot_sp:.1f}"])
table(rows, 36, y - 16, [80, 128, 128, 128, 128, 140, 156], header_bg="#5b3f86", size=8.4)

# 16 ETF flows
new_slide("Weekly ETF flows: SPDR Gold Shares (GLD)", "State Street NAV history; flows = change in shares x NAV; tonnes = shares x ounces per share (60-day median of NAV / COMEX price). Other funds not covered.")
rows = [["Week to", "Flows, US$m", "Holdings, tonnes (est.)", "Change, tonnes"]]
sty = []
for i_, r_ in enumerate(gld_rows, start=1):
    rows.append([pd.Timestamp(r_["week"]).strftime("%d %b %Y"), f"{r_['flow_m']:+,.0f}", f"{r_['tonnes']:,.1f}", f"{r_['dt']:+.1f}"])
    sty.append(("TEXTCOLOR", (1, i_), (1, i_), C(GREEN if r_["flow_m"] > 0 else RED)))
rows.append(["Year to date", f"{gld_ytd['flow_bn'] * 1000:+,.0f}", f"{gld_ytd['tonnes']:,.1f}", f"{gld_ytd['dt']:+.1f}"])
table(rows, 36, 470, [150, 130, 170, 130], size=9.4, styles=sty + [("FONTNAME", (0, len(rows) - 1), (-1, len(rows) - 1), "SUI-B")])
text_block(640, 470, 284, [
    f"GLD assets: <b>${gld_ytd['aum_bn']:,.0f}bn</b> on {pd.Timestamp(gld_ytd['last']):%d %b} (State Street publishes with a one-day lag).",
    "Global gold ETF holdings reached a record 4,256 t at the end of Q3 after 211 t of inflows in the quarter "
    "(World Gold Council, Gold Demand Trends Q3 2026).",
    "The desk's test of 21 Nov confirms that GLD flows follow the price: they rise after gains and fall after losses "
    f"(slope p = {DRV['h2']['p']:.4f}), but they do not predict the next month's move.",
], bg=BOX, h=230)

# 17 volatility
new_slide("Gold volatility overview", "GVZ: CBOE gold ETF volatility index. Realised volatility: daily COMEX returns. Model: desk GARCH(1,1) with Student-t shocks fitted to Friday's close.")
rows = [["Measure", "Level", "1-month change", "Note"],
        ["GVZ, 30-day implied", f"{vol['gvz']:.1f}", f"{vol['gvz_1m']:+.1f}", f"{nth(vol['gvz_pct'])} percentile of the past year"],
        ["Realised, 30 days", f"{vol['rv30'] * 100:.1f}%", f"{vol['rv30_1m'] * 100:+.1f}", ""],
        ["Realised, 90 days", f"{vol['rv90'] * 100:.1f}%", "", ""],
        ["Desk model, next day", f"{vol['garch_next'] * 100:.1f}%", "", "Annualised"],
        ["Desk model, next month", f"{vol['garch_21'] * 100:.1f}%", "", "Average over 21 trading days"],
        ["VIX / VIX3M", f"{vol['vix']:.1f} / {vol['vix3m']:.1f}", "", f"Ratio {vol['vix'] / vol['vix3m']:.2f}: above 1 = stress"]]
table(rows, 36, 470, [170, 110, 100, 200], size=9.4)
image(c_vol, 620, 470, w=304)

# 18 method
new_slide("Method, glossary and sources", "")
text_block(36, 470, 888, [
    "<b>Prices:</b> Yahoo Finance daily closes to Friday 20 Nov 2026 (COMEX gold and silver futures, indices, ETFs, FX); "
    "5-minute futures to Sunday 22 Nov 23:55 ET for the weekend page; yields and macro from FRED; positioning from the "
    "CFTC disaggregated report (17 Nov); ETF data from State Street.",
    f"<b>Desk model:</b> GARCH(1,1) with Student-t shocks on daily COMEX log returns, zero drift, refitted each Friday; "
    f"20,000 simulated paths start from the next-day variance. Each forecast is logged before the outcome is known "
    f"({S['n_records']:,} records, {S['n_live']} live). The percentile of the realised close in the forecast distribution "
    "is the score; a well-calibrated model puts 90% of outcomes inside the 90% range.",
    "<b>Driver attribution:</b> each week's gold log return regressed on weekly changes in the 10-year TIPS yield, the 10-year "
    "breakeven, the dollar index, the VIX (log), the S&amp;P 500, WTI oil, the managed-money net long share and GLD flows. "
    "Betas come from the previous 156 weeks only. 'Trend' is the intercept; 'Unexplained' is the residual.",
    f"<b>Tests (pre-registered 21 Nov, commit 0a7239c):</b> H1 decoupling from real yields: "
    f"{'confirmed' if DRV['h1']['confirmed'] else 'not confirmed'} (slope {DRV['h1']['beta_before']:.3f} in 2010-21, "
    f"{DRV['h1']['beta_after']:.3f} since Mar 2022, p = {DRV['h1']['p_one_sided']:.3f}). H2 procyclical ETF flows: "
    f"{'confirmed' if DRV['h2']['confirmed'] else 'not confirmed'} (p = {DRV['h2']['p']:.4f}). H3 positioning and flows as "
    "predictors of the next four weeks: none passed.",
    "<b>Glossary:</b> percentile = share of simulated outcomes below the realised close; touch = a daily close through the "
    "level at some point in the horizon; z-score = move divided by its usual size over 52 weeks; SMA = simple moving "
    "average; RSI = relative strength index; GVZ = implied volatility of gold options.",
    "<b>News:</b> CNBC (Fed minutes, Waller; Sunday futures, PMI priors, Friday's early close), Fortune (Sunday futures, "
    "the AI selloff), FinanceFeeds (Kitco survey, Chandler and Kitco levels, CME FedWatch), Reuters via Yoopya and "
    "Investing.com (Paulson, jobless claims), Quartz (Goolsbee), Kitco (Empire, retail sales, industrial production), "
    "Mitrade (Philadelphia Fed, leading indicators), World Gold Council (Q3 2026 demand).",
])
cv.save()
print("wrote", out_pdf, "pages", page[0])
