"""Nova Gold Weekly, edition 25 Nov 2026 (Thanksgiving week, data to the Wednesday close). Internal: Nova Capital
analysts and board. Reads week.json and checks.json from analyse_week.py and the data snapshot, renders 12 pages in
the desk's teal slide style (gold_desk/nova_style.py), then runs the render checks and appends them to checks.json.
No forecast is logged: the weekly record stays on Friday's close.

Usage (from desk/): python reports/2026-11-25/scripts/build_note.py   (DESK_NOTE_OUT renders elsewhere)
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

DESK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(DESK))
from gold_desk import nova_style as NS  # noqa: E402

OUTDIR = DESK / "reports" / "2026-11-25"
D = OUTDIR / "data"
CUT, FRI, PREV, YEND = pd.Timestamp("2026-11-25"), pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-13"), pd.Timestamp("2025-12-31")
W_ = json.loads((OUTDIR / "week.json").read_text(encoding="utf-8"))
CHECKS = json.loads((OUTDIR / "checks.json").read_text(encoding="utf-8"))
CHECKS = [c for c in CHECKS if not c.get("render")]
assert all(c["result"] == "PASS" for c in CHECKS), [c for c in CHECKS if c["result"] != "PASS"]
DRV = json.loads((DESK / "reports" / "2026-11-20-weekly" / "drivers.json").read_text(encoding="utf-8"))
SPR = json.loads((DESK / "reports" / "2026-11-20" / "spring.json").read_text(encoding="utf-8"))
daily = pd.read_csv(D / "daily.csv", index_col=0, parse_dates=True).loc[:CUT]
fred = pd.read_csv(D / "fred.csv", index_col=0, parse_dates=True).loc[:CUT]
gold = daily["GC=F"].dropna()
tr = pd.read_csv(D / "treasury_real_yield_2026.csv")
tr["Date"] = pd.to_datetime(tr["Date"], format="%m/%d/%Y")
real10 = tr.set_index("Date").sort_index()["10 YR"].astype(float).loc[:CUT].combine_first(fred["DFII10"].dropna())

G, NV, CY, SH, P20, FL = W_["gold"], W_["nova"], W_["cycles"], W_["shadow"], W_["pit20"], W_["flows"]
DY = {d["date"]: d for d in W_["days"]}
F_, M_, T_, WD = (DY[k] for k in ("2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25"))
MI, MMF, COT, VOL, INTR = W_["miners"], W_["mmf"], W_["cot"], W_["vol"], W_["intraday"]
PERF = W_["perf"]
G16 = {pd.Timestamp(k): v for k, v in NV["gold16"].items()}
ODDS, AL, AN, TECH, OZ = NV["odds"], NV["attr_last"], NV["attr_now"], NV["tech"], NV["oz"]
CYC = {r["peak"]: r for r in NV["cycles"]["rows"]}
MATCH = NV["matched"]

usd = lambda v: f"${v:,.0f}"  # noqa: E731
pc = lambda v, d=1: f"{v * 100:+.{d}f}%"  # noqa: E731
ap = lambda v, d=1: f"{abs(v) * 100:.{d}f}%"  # noqa: E731
bp = lambda v: f"{v:+.0f} bp"  # noqa: E731
lp = lambda v: f"{v * 100:+.1f}"  # noqa: E731   log points


def nth(q):
    n_ = int(round(q * 100))
    return f"{n_}{'th' if 10 <= n_ % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n_ % 10, 'th')}"


# ------------------------------------------------------------------ chart style
for f_ in ("segoeui.ttf", "segoeuib.ttf"):
    font_manager.fontManager.addfont(str(NS.FONT_DIR / f_))
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9.5, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": NS.INK,
                     "xtick.color": NS.MUTED, "ytick.color": NS.MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e3e3df", "grid.linewidth": 0.6,
                     "legend.frameon": False, "legend.fontsize": 8.5})
CH = OUTDIR / "_charts"
CH.mkdir(exist_ok=True)
GREY, RUST = "#9aa7b0", "#eb6834"
FIGTXT = {}


def save(fig, name):
    p = CH / f"{name}.png"
    FIGTXT[str(p)] = NS.figure_texts(fig)
    fig.savefig(p, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(p)


fmt_usd = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")

# chart of the week: December contract, Sunday open to Wednesday 17:00
i5 = pd.read_csv(D / "gold_5m_contracts.csv", index_col=0, parse_dates=True)["GCZ26.CMX"].dropna()
seg = i5.loc["2026-11-22 18:00":"2026-11-25 17:00"]
fig, ax = plt.subplots(figsize=(6.2, 3.0))
x = np.arange(len(seg))
ax.plot(x, seg.values, color=NS.GOLD, lw=1.3)
ax.axhline(G["fri"], color=GREY, lw=0.8, ls="--")
ax.text(2, G["fri"] - 5, f"Friday settlement ${G['fri']:,.0f}", fontsize=7.5, color=GREY, va="top")
for k in range(1, len(seg)):
    if seg.index[k].hour == 18 and seg.index[k - 1].hour != 18:
        ax.axvline(k, color="#e3e3df", lw=0.9)
for d in ("2026-11-23", "2026-11-24", "2026-11-25"):
    k = int(seg.index.searchsorted(pd.Timestamp(f"{d} 13:30")))
    ax.scatter([k], [DY[d]["GC=F"]], color=NS.BLUE, s=16, zorder=5)
kp = int(seg.index.searchsorted(pd.Timestamp("2026-11-25 08:30")))
ax.axvline(kp, color=RUST, lw=0.9, ls=":")
kl = int(np.argmin(seg.values))
ax.annotate(f"PCE, then low ${INTR['wed_low']:,.0f}", xy=(kl, INTR["wed_low"]), xytext=(-122, 2), textcoords="offset points",
            fontsize=7.5, color=RUST, arrowprops={"arrowstyle": "-", "color": RUST, "lw": 0.7})
ax.set_xticks([int(seg.index.searchsorted(pd.Timestamp(f"{d} 09:00"))) for d in ("2026-11-23", "2026-11-24", "2026-11-25")])
ax.set_xticklabels(["Monday", "Tuesday", "Wednesday"])
ax.set_xlim(0, len(seg) - 1)
ax.yaxis.set_major_formatter(fmt_usd)
c_cotw = save(fig, "cotw")

# Fed: gold and yields
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.2, 3.4), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
gs = gold.loc["2026-09-01":]
a1.plot(gs.index, gs.values, color=NS.GOLD, lw=1.4)
a1.set_ylabel("Gold, $/oz", fontsize=8)
a1.yaxis.set_major_formatter(fmt_usd)
rs, d2 = real10.loc["2026-09-01":], fred["DGS2"].dropna().loc["2026-09-01":]
a2.plot(rs.index, rs.values, color=NS.BLUE, lw=1.4, label="10-yr TIPS yield")
a2.plot(d2.index, d2.values, color=GREY, lw=1.2, label="2-yr Treasury yield (to 24 Nov)")
a2.set_ylabel("%", fontsize=8)
a2.legend(loc="center left", ncol=2, fontsize=7.5)
a2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
c_fed = save(fig, "fed")

# performance bars
BT = [("Gold", "GC=F"), ("Silver", "SI=F"), ("GDX", "GDX"), ("GDXJ", "GDXJ"), ("S&P 500", "^GSPC"), ("Nasdaq-100", "^NDX"),
      ("Dollar", "DX-Y.NYB"), ("Copper", "HG=F"), ("Brent", "BZ=F"), ("Bitcoin", "BTC-USD")]
PR = {r["ticker"]: r for r in PERF}
fig, ax = plt.subplots(figsize=(9.6, 2.2))
vals = [PR[t]["wtd"] * 100 for _, t in BT]
ax.bar(range(len(BT)), vals, color=[NS.GOLD if t == "GC=F" else NS.BLUE for _, t in BT], width=0.6)
for i_, v in enumerate(vals):
    ax.text(i_, v + (0.3 if v >= 0 else -0.3), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8, color=NS.INK)
ax.set_xticks(range(len(BT)))
ax.set_xticklabels([n for n, _ in BT], fontsize=8.5)
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_ylim(min(vals) - 1.6, max(vals) + 1.6)
ax.set_ylabel("%", fontsize=8)
c_bars = save(fig, "bars")

# driver model: this week (gold at 16:00), market factors only, unexplained first
cn = AN["contrib"]
parts = [("Unexplained", AN["residual"], "#b5b3ad"), ("Rates and\ninflation", cn["d_real"] + cn["d_be"], "#2a78d6"),
         ("Dollar", cn["r_dxy"], "#eb6834"), ("Stress\n(VIX)", cn["d_vix"], "#1baf7a"), ("US stocks", cn["r_spx"], "#eda100"),
         ("Oil", cn["r_oil"], "#6250d6")]
fig, ax = plt.subplots(figsize=(6.0, 2.8))
cum = 0.0
for i_, (lab, v, col) in enumerate(parts):
    v *= 100
    ax.bar(i_, v, bottom=cum if v >= 0 else cum + v, color=col, width=0.62)
    ax.text(i_, cum + v + (0.06 if v >= 0 else -0.06), f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
    cum += v
ax.bar(len(parts), AN["r_gold16"] * 100, color=NS.INK, width=0.62)
ax.text(len(parts), AN["r_gold16"] * 100 + 0.06, f"{AN['r_gold16'] * 100:+.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xticks(range(len(parts) + 1))
ax.set_xticklabels([p[0] for p in parts] + ["Gold,\nFri-Wed"], fontsize=8)
ax.set_ylabel("log points", fontsize=8)
c_attr = save(fig, "attr")

# cycles: drawdown paths (monthly averages)
fig, ax = plt.subplots(figsize=(5.9, 3.1))
labs = []
for k, v in CY["paths"].items():
    v = np.asarray(v[:49]) * 100
    ax.plot(range(len(v)), v, color="#b5b3ad", lw=1.0)
    labs.append([float(np.clip(v[-1], -58, 38)), len(v) - 1, k[:7]])
labs.sort()
for j in range(1, len(labs)):
    labs[j][0] = max(labs[j][0], labs[j - 1][0] + 4)
for yv, xv, k in labs:
    ax.text(xv, yv, f" {k}", fontsize=7, color=NS.MUTED, va="center")
v26 = np.asarray(CY["path26"]) * 100
ax.plot(range(len(v26)), v26, color=NS.GOLD, lw=2.6, label="2026 (November: month to date)")
ax.axvline(9, color=RUST, lw=0.8, ls=":")
ax.text(9, 0.98, " month 9", transform=ax.get_xaxis_transform(), color=RUST, fontsize=7.5, va="top")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xlabel("Months after the peak month", fontsize=8)
ax.set_ylabel("% from the peak month's average", fontsize=8)
ax.set_xlim(0, 55)
ax.set_ylim(-60, 40)
ax.legend(loc="lower left", fontsize=7.5)
c_cyc = save(fig, "cycles")

# ETF weekly flows, the partial week hatched
wkf = pd.DataFrame({"GLD": pd.Series(FL["GLD"]["weekly"]), "GLDM": pd.Series(FL["GLDM"]["weekly"])}) / 1e9
wkf.index = pd.to_datetime(wkf.index)
wkf = wkf.iloc[-13:]
fig, ax = plt.subplots(figsize=(6.0, 2.5))
xx = np.arange(len(wkf))
for i_ in xx:
    part = i_ == len(wkf) - 1
    ax.bar(i_ - 0.2, wkf["GLD"].iloc[i_], width=0.4, color=NS.BLUE, alpha=0.45 if part else 1, hatch="///" if part else None,
           edgecolor=NS.BLUE, label="GLD" if i_ == 0 else None)
    ax.bar(i_ + 0.2, wkf["GLDM"].iloc[i_], width=0.4, color=NS.GOLD, alpha=0.45 if part else 1, hatch="///" if part else None,
           edgecolor=NS.GOLD, label="GLDM" if i_ == 0 else None)
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xticks(xx)
ax.set_xticklabels([d.strftime("%d/%m") for d in wkf.index[:-1]] + ["23-25\nNov"], fontsize=7)
ax.set_ylabel("US$ bn", fontsize=8)
ax.legend(loc="lower left", ncol=2, fontsize=7.5)
c_etf = save(fig, "etf")
big_wk = wkf["GLD"].idxmin()

# miners vs gold vs stocks, all at 16:00 ET, Mon 16 Nov = 100
d16 = sorted(G16)
ix = pd.DataFrame({"Gold (16:00 ET)": [G16[d] for d in d16], "GDX": daily.loc[d16, "GDX"].values,
                   "GDXJ": daily.loc[d16, "GDXJ"].values, "S&P 500": daily.loc[d16, "^GSPC"].values}, index=d16)
ix = ix / ix.iloc[0] * 100
fig, ax = plt.subplots(figsize=(6.0, 2.5))
for col, cc, lw in (("Gold (16:00 ET)", NS.GOLD, 2.0), ("GDX", NS.BLUE, 1.4), ("GDXJ", "#6250d6", 1.4), ("S&P 500", GREY, 1.4)):
    ax.plot(ix.index, ix[col], color=cc, lw=lw, marker="o", ms=2.5, label=col)
ax.axhline(100, color="#c3c2b7", lw=0.8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.set_ylabel("Mon 16 Nov = 100", fontsize=8)
ax.legend(loc="lower left", ncol=2, fontsize=7.5)
c_min = save(fig, "miners")

# ------------------------------------------------------------------ derived text values
rr_chg = (WD["real10"] - F_["real10"]) * 100
_d2 = fred["DGS2"].dropna()
d2_lw = (float(_d2.loc[:FRI].iloc[-1]) - float(_d2.loc[:PREV].iloc[-1])) * 100
m_chg, t_chg, w_chg = M_["GC=F"] / F_["GC=F"] - 1, T_["GC=F"] / M_["GC=F"] - 1, WD["GC=F"] / T_["GC=F"] - 1
spx_w = PR["^GSPC"]["wtd"]
last_simple = G["prev_week"]
x2, x4 = ODDS["x2"], ODDS["x4"]
same_dir = sum((m["gold_chg"] > 0) == (m["spx_chg"] > 0) for m in MATCH)
gusd = [m for m in MATCH if m["gold_up_stocks_down"]]
spx_last_share = AL["contrib"]["r_spx"] / AL["r_gold"]
unexpl_last = AL["residual"] / AL["r_gold"]
old_last = NV["attr_last_old"]
p26 = CYC["2026-02"]
STAR = "★" if NS.fonts_available() else "*"


def stars(n):
    return STAR * n


# ------------------------------------------------------------------ pages
OUT = Path(os.environ.get("DESK_NOTE_OUT", OUTDIR / "nova_gold_weekly_2026-11-25.pdf"))
dk = NS.Deck(OUT, "Nova Gold Weekly, 25 November 2026", "Nova Gold Weekly  |  25 November 2026",
             "Nova Gold Weekly  |  Internal: Nova Capital analysts and board  |  Data to the Wednesday 25 Nov close unless stated")
if not NS.has_glyph("NV-R", STAR):
    STAR = "*"

# 1 cover and what you need to know
dk.new_page("", "Chart: COMEX December futures, 5-minute bars, New York time; dots mark the 13:30 ET settlements. Gold prices in this report are settlements unless marked 16:00 ET.")
dk.cv.setFillColor(NS.C(NS.TEAL))
dk.cv.roundRect(20, 420, 920, 104, 14, stroke=0, fill=1)
dk.string(40, 500, "NOVA CAPITAL", font="NV-H", size=12, color=NS.KEYTITLE)
dk.string(920, 500, "Internal: Nova Capital analysts and board", size=8.5, color=NS.MINT, align="right")
dk.string(40, 466, "Nova Gold Weekly", font="NV-L", size=30, color=NS.MINT)
dk.string(40, 446, "Edition 25 November 2026: Thanksgiving week, data to the Wednesday close", size=11, color=NS.WHITE)
dk.string(40, 428, "Liquidation, then a whipsaw: gold ends the week near where it began", font="NV-H", size=12.5, color=NS.KEYTITLE)
dk.card(36, 412, 440, 268)
dk.heading(48, 394, 416, "What you need to know")
dk.bullets(48, 380, 416, [
    f"Gold settled Wednesday at <b>{usd(G['close'])}</b>, {pc(G['wtd'])} from Friday (settlements; {pc(NV['gold16_wtd'])} at 16:00 ET), "
    f"after {pc(m_chg)} Monday, {pc(t_chg)} Tuesday and {pc(w_chg)} Wednesday. It is {pc(G['ytd'])} this year and "
    f"{pc(CY['daily_dd'], 0)} from the daily record of 29 Jan.",
    "<b>Hawkish Fed, confirmed:</b> core PCE 3.3% a year, the highest since 2023. A December hike was priced at 94.4% "
    "after the release (CME FedWatch, relayed by CoinCentral, 16:01 UTC 25 Nov).",
    f"<b>Gold followed stocks:</b> at matched 16:00 ET prices gold and the S&amp;P 500 moved the same way on {same_dir} of "
    f"{len(MATCH)} days since 17 Nov. Wednesday was the exception: gold {pc(gusd[0]['gold_chg']) if gusd else ''}, stocks "
    f"{pc(gusd[0]['spx_chg']) if gusd else ''}.",
    f"<b>Flows:</b> GLD lost another ${abs(FL['GLD']['wtd']) / 1e6:,.0f}m from Monday to Wednesday; SPY took in "
    f"${FL['SPY']['wtd'] / 1e9:.1f}bn on Monday and Tuesday; miners rose {ap(MI['GDX']['wtd'])}.",
    "<b>Narratives:</b> forced selling and its unwind fit the swings best, but that is not proven; the hawkish Fed is the "
    "backdrop; the bull case (central banks) is real but slow.",
    f"<b>Cycles:</b> nine months after the peak month, gold is {ap(-CY['path26'][-1], 0)} below it on monthly averages, deeper "
    "than any of seven independent past cycles at that stage.",
], size=9.2)
y = dk.chart(c_cotw, 492, 412, 432, "PCE knocked gold to $3,430, then it recovered by the close",
             "COMEX December futures, 5-minute bars, New York time, Sun 22 to Wed 25 Nov", FIGTXT[c_cotw])

# 2 desk view
dk.new_page("Desk view", "Model: GARCH(1,1) with Student-t shocks on daily COMEX settlements, zero drift. Day odds: the 20 Nov fit, variance carried through the Mon to Wed settlements without re-estimation, 20,000 paths, seed 42. Matched-time comparisons use gold at 16:00 ET.", "Core")
dk.blue_block(36, 448, 452, 214, "THE DESK VIEW, AT WEDNESDAY'S CLOSE", [
    "<b>Direction: no call.</b> No drift rule, no positioning or flow signal and no spring toward value passed our "
    "pre-registered tests. The narratives explain moves after the fact; none has predicted them.",
    f"<b>Big days stay likely.</b> Daily sigma is {ODDS['daily_sigma'] * 100:.1f}%. A move of more than 2% is expected on "
    f"about {x2['share_of_days'] * 100:.0f}% of days to 9 Dec (1 in {1 / x2['share_of_days']:.0f}); the chance of at least one "
    f"such day in those {ODDS['days']} days is {x2['at_least_once'] * 100:.0f}%. More than 4%: {x4['share_of_days'] * 100:.0f}% of "
    f"days, {x4['at_least_once'] * 100:.0f}% for at least one.",
    f"<b>Regime: gold mostly moves with stocks.</b> Same direction on {same_dir} of {len(MATCH)} days at matched 16:00 ET "
    "prices; Wednesday was the first gold-up, stocks-down day in that window.",
    f"<b>Last week:</b> stocks explained {spx_last_share * 100:.0f}% of the fall ({lp(AL['contrib']['r_spx'])} of "
    f"{lp(AL['r_gold'])} log points), but the jump in the VIX added back {lp(AL['contrib']['d_vix'])}, so "
    f"{unexpl_last * 100:.0f}% stayed unexplained by market prices.",
], size=9.4)
dk.card(36, 222, 452, 64, border=NS.GOLD)
dk.string(48, 204, "What this means for Nova", font="NV-H", size=10.5, color=NS.BLUE)
dk.bullets(48, 196, 428, [
    f"A gold holder should plan for a 1-week range of about {usd(SH['q']['5']['5'])} to {usd(SH['q']['5']['95'])} "
    f"({(SH['q']['5']['5'] / G['close'] - 1) * 100:+.0f}% to {(SH['q']['5']['95'] / G['close'] - 1) * 100:+.0f}%, 90% of outcomes) and "
    "a 2% daily move roughly once a week: size positions for that, not for a direction."], bullet=False, size=9)
dk.card(504, 448, 420, 186)
dk.heading(516, 430, 396, "What we watch for a turn")
dk.bullets(516, 416, 396, [
    "<b>More gold-up, stocks-down days</b> at matched times: the safe-haven link returning.",
    "<b>GLD inflows for a full week:</b> a confirmation, not a signal (flows follow the price, H2).",
    "<b>A dovish hike on 9 Dec:</b> projections that signal the end of tightening would ease the real-yield cap.",
    f"<b>Range:</b> a {SH['touch_1w']['3430.0'] * 100:.0f}% chance of a close below $3,430 within a week and "
    f"{SH['touch_1w']['3700.0'] * 100:.0f}% above $3,700 (shadow refit): a break alone says little.",
], size=8.8)
dk.heading(504, 248, 420, "The model, Friday and Wednesday", size=10.5)
y = dk.table([["Desk model", "20 Nov (logged)", "25 Nov (shadow refit)"],
              ["Next-day volatility, annualised", f"{SH['vol_next_20nov'] * 100:.1f}%", f"{SH['vol_next'] * 100:.1f}%"],
              ["Tail thickness (t degrees of freedom)", "4.78", f"{SH['nu']:.2f}"],
              ["1-week 90% range", "$3,298 to $3,751", f"{usd(SH['q']['5']['5'])} to {usd(SH['q']['5']['95'])}"]],
             504, 234, [200, 105, 115], size=8.4, basis="settlement")
dk.heading(504, y - 14, 420, "The 20 Nov forecast so far (settlements)", size=10.5)
rows = [["Day", "Settlement", "Percentile", "Status"]]
for k_, lab in (("2026-11-23", "Mon 23 (day 1)"), ("2026-11-24", "Tue 24 (day 2)"), ("2026-11-25", "Wed 25 (day 3)")):
    p_ = P20[k_]
    rows.append([lab, usd(p_["close"]), f"{p_['pit'] * 100:.1f}", "scored: above the 90% range" if k_ == "2026-11-23" else "information only"])
dk.table(rows, 504, y - 28, [110, 80, 70, 160], size=8.4, basis="settlement")

# 3 narratives
dk.new_page("The narratives, against our data", "What is said: dated sources. What our data says: desk model and tests pre-registered on 21 Nov (H1 to H3, commit 0a7239c) and 23 Nov (H4 to H6, commit 59b21e2). Driver figures in log points.", "Core")
lw_old = DRV["week"]
dk.heading(36, 446, 888, "Bear case")
bear = [["Narrative", "What is said", "What our data says", "Verdict"],
        ["<b>The Fed stays hawkish</b>",
         "Almost all officials see further hikes as likely appropriate (minutes of the 27-28 Oct meeting, CNBC, 18 Nov). "
         "Governor Waller is open to a larger December move (Bloomberg, 10 Nov). Core PCE 3.3% a year (BEA via CNBC, 25 Nov).",
         f"The 10-yr TIPS yield moved {bp(rr_chg)} this week while gold swung 2-4% a day. Since 2022 gold's link to real yields "
         f"is about half what it was (H1: slope {DRV['h1']['beta_before']:.3f} to {DRV['h1']['beta_after']:.3f}). Rates and "
         f"inflation explained {lp(AL['contrib']['d_real'] + AL['contrib']['d_be'])} of last week's {lp(AL['r_gold'])} log points.",
         "The backdrop that caps rallies, not the trigger."],
        ["<b>Forced selling</b>",
         "Investors sold precious metals to cover losses on Wall Street (Jiji/Nation, 24 Nov); a broad short-covering wave "
         "on Monday (investingLive, 23 Nov).",
         f"{unexpl_last * 100:.0f}% of last week's move is unexplained: that only says the model has no explanation. Supporting: "
         "on 18-20 Nov gold, silver, bitcoin and stocks fell together while Treasuries rallied. Still to confirm: the 24 Nov "
         "CFTC report (managed money selling) and CME margin changes (none found for November).",
         "Most consistent with the data, not proven."],
        ["<b>The dollar is too strong</b>",
         f"The dollar near a 19-month high (Jiji/Nation, 24 Nov). Our data: Monday's close of {NV['dxy_mon']['close']:.2f} was the "
         f"highest since {pd.Timestamp(NV['dxy_mon']['highest_since']):%d %b %Y}.",
         f"Dollar contribution {lp(AL['contrib']['r_dxy'])} log points last week and {lp(AN['contrib']['r_dxy'])} this week.",
         "True, but minor for gold this month."],
        ["<b>ETF investors are leaving</b>",
         f"GLD lost ${abs(FL['GLD']['prev']) / 1e9:.2f}bn last week and ${abs(FL['GLD']['wtd']) / 1e6:,.0f}m Mon to Wed (State Street data).",
         f"Flows follow the price, they do not lead it (H2 confirmed, H3 failed). GLDM took in ${FL['GLDM']['ytd'] / 1e9:.1f}bn this year "
         f"while GLD lost ${abs(FL['GLD']['ytd']) / 1e9:.1f}bn: part of the exit is a switch to the cheaper fund.",
         "A symptom, not a cause."]]
y = dk.table(bear, 36, 438, [110, 290, 340, 148], size=7.7, basis="none")
dk.heading(36, y - 14, 888, "Bull case")
bull = [["Narrative", "What is said", "What our data says", "Verdict"],
        ["<b>Central banks keep buying</b>",
         "Central-bank demand 321 t in Q3, +42% on a year; reported purchases 120 t, led by China (63 t) and Poland (40 t) "
         "(World Gold Council, Gold Demand Trends Q3 2026).",
         "Quarterly data cannot enter a weekly model. Central banks bought through the peak and the fall: a slow floor under "
         "demand, not the weekly path.",
         "Real, but slow."],
        ["<b>The AI rout will stop the Fed</b>",
         "Less fear of aggressive Fed tightening as the AI selloff clouds the outlook (Kitco, 23 Nov).",
         f"The 2-yr yield moved {bp(d2_lw)} last week and the TIPS yield {bp(rr_chg)} this week, but December stayed priced at "
         "94.4% after PCE, and Q3 GDP was revised to 4.3% from an advance 3.4%.",
         "Open; the test is 9 Dec."],
        ["<b>Oversold: a bounce is due</b>",
         f"Daily momentum has not confirmed a durable recovery (Kitco, 23 Nov). Our 14-day RSI is {TECH['rsi14']:.0f}.",
         f"Our spring tests found no pull back toward value after big stretches (H4 to H6 failed; H5 p = {SPR['h5'][0]['p_one_sided']:.3f} "
         "missed the pre-registered 0.025, i.e. 0.05 split over two anchors). Monday's +3.9% faded by Wednesday.",
         "Not supported by 20 years of data."],
        ["<b>Positioning is washed out</b>",
         f"Speculators cut longs (CFTC: managed money {COT['mm_t'] - COT['mm_t_prev']:+.0f} t in the week to 17 Nov).",
         f"Net long still {COT['share'] * 100:.0f}% of open interest, the {nth(COT['share_pct'])} percentile since 2006: mid-range. "
         "Positioning does not predict the next month (H3).",
         "Not yet."],
        ["<b>The banks still see higher prices</b>",
         "Goldman cut its end-2026 forecast to $4,150; UBS sees $5,000 by end-2027; a Reuters poll's 2027 median is $4,650 "
         "(via Yahoo Finance, one source).",
         "Targets follow the price with a lag. The desk model has no drift; no target-based signal has been tested.",
         "Opinion, not evidence."]]
dk.table(bull, 36, y - 22, [110, 290, 340, 148], size=7.7, basis="none")

# 4 Fed and macro
dk.new_page("The hawkish Fed in numbers", "PCE: BEA via CNBC, Morningstar, Advisor Perspectives. GDP: BEA. Durable goods and claims: TMGM, The Edge. Beige Book: Minneapolis Fed, investingLive. FedWatch: CME, relayed by CoinCentral. Yields: Treasury par real curve (TIPS), FRED.", "Core")
dk.card(36, 448, 470, 300)
dk.heading(48, 430, 446, "This week's US data")
eco = [["Date", "What", "Prior", "Consensus", "Actual"],
       ["Wed 25", "Core PCE, m/m (Oct)", "0.3%", "0.3%", "0.3%"],
       ["Wed 25", "Core PCE, y/y (Oct)", "3.1%", "3.2%", "3.3%"],
       ["Wed 25", "PCE, y/y (Oct)", "–", "3.8%", "3.8%"],
       ["Wed 25", "GDP, 2nd estimate (Q3), annualised", "3.4% (advance)", "3.4-3.5%", "4.3%"],
       ["Wed 25", "Durable goods orders, m/m (Oct)", "2.0% (revised)", "0.4-0.6%", "0.2%"],
       ["Wed 25", "Initial jobless claims (week to 21 Nov)", "203k", "200k", "189k"],
       ["Wed 25", "Continuing claims", "1.763m", "–", "1.697m"],
       ["Mon 23", "Flash PMI, services (Nov)", "56.1", "–", "54.7"]]
y = dk.table(eco, 48, 418, [46, 186, 76, 64, 50], size=8.4)
dk.bullets(48, y - 10, 446, [
    "<b>Beige Book:</b> 8 of 12 districts grew, 4 were flat; wages rose at a moderate pace (up from modest); prices rose moderately.",
    "<b>For the Fed:</b> hotter core inflation, faster growth and low layoffs point to a hike on 9 Dec (94.4% priced after PCE); "
    "softer PMIs and the equity rout are the counterweight.",
    f"<b>Which real rate:</b> the 10-yr TIPS yield is {WD['real10']:.2f}% (market real yield). The +{p26['trailing_rr']:.1f}% on the "
    "cycles page is a different measure: the 10-yr nominal yield minus trailing CPI inflation at the February peak.",
], size=8.8)
y = dk.chart(c_fed, 522, 448, 402, "Real yields eased this week; gold did not follow them",
             "COMEX gold (settlement, $/oz); 10-yr TIPS yield and 2-yr Treasury yield, %", FIGTXT[c_fed])
dk.bullets(522, y - 6, 402, [
    f"The TIPS yield went from {F_['real10']:.2f}% to {WD['real10']:.2f}% ({bp(rr_chg)}), lower even after a hot PCE: the "
    "hike looks priced.", "Gold's fall since October came with TIPS yields near 2.8-2.9%, but its daily swings followed stocks."], size=8.6)

# 5 week in review and week ahead
dk.new_page("The week in review and the week ahead", "Closes from Yahoo Finance (gold: COMEX December settlement). Matched-time table: gold at 16:00 ET from 5-minute December futures against the S&P 500 close. News: CNBC, CNN, Nvidia (8-K, 23 Nov), Yahoo Finance and Seeking Alpha (S&P CreditWatch), Kitco, Jiji/Nation, investingLive.", "Core")
rows = [["Settlements and closes", "Fri 20", "Mon 23", "Tue 24", "Wed 25", "Fri to Wed"]]
SPEC = [("Gold, COMEX Dec", "GC=F", "${:,.1f}", "pct"), ("Silver", "SI=F", "{:.2f}", "pct"), ("S&P 500", "^GSPC", "{:,.0f}", "pct"),
        ("Dollar index", "DX-Y.NYB", "{:.2f}", "pct"), ("US 10-yr yield", "^TNX", "{:.2f}%", "bp"),
        ("10-yr TIPS yield", "real10", "{:.2f}%", "bp"), ("VIX", "^VIX", "{:.1f}", "pct")]
for name, t, f_, u in SPEC:
    vv = [d[t] for d in (F_, M_, T_, WD)]
    rows.append([name] + [f_.format(v) for v in vv] + [pc(vv[-1] / vv[0] - 1) if u == "pct" else bp((vv[-1] - vv[0]) * 100)])
y = dk.table(rows, 36, 448, [118, 64, 64, 64, 64, 72], size=8.2, basis="settlement")
dk.bullets(36, y - 8, 446, [
    f"<b>Monday:</b> gold {pc(m_chg)} on short covering (Kitco, investingLive); stocks {pc(M_['^GSPC'] / F_['^GSPC'] - 1)}. Nvidia's "
    "board reinstated Jensen Huang as CEO (Nvidia 8-K; CNN: shares up 30%).",
    f"<b>Tuesday:</b> gold {pc(t_chg)} as traders priced the December hike and sold metals to cover losses (Jiji/Nation, CNBC).",
    f"<b>Wednesday:</b> hot core PCE; gold fell to {usd(INTR['wed_low'])} at 10:15 ET, settled {usd(WD['GC=F'])} and reached "
    f"{usd(INTR['wed_1655'])} by 17:00. S&amp;P Global put Nvidia's AA rating on CreditWatch negative (Yahoo Finance, Seeking Alpha).",
], size=8.5)
rows = [["Matched 16:00 ET", "Gold", "S&P 500", "Same way?"]]
for m in MATCH:
    rows.append([f"{pd.Timestamp(m['date']):%a %d %b}", pc(m["gold_chg"]), pc(m["spx_chg"]),
                 "no: gold up, stocks down" if m["gold_up_stocks_down"] else ("yes" if (m["gold_chg"] > 0) == (m["spx_chg"] > 0) else "no")])
y2 = dk.table(rows, 500, 448, [110, 80, 80, 154], size=8.2, basis="16:00")
cal = [["Week ahead", "What", "Why it matters"],
       ["Fri 27", "Half day; the weekly forecast is logged at the close", "First regular origin since 20 Nov"],
       ["From Thu 26", "Continuous futures on February", f"Feb {usd(G['roll_gap'])} above Dec: scores adjust"],
       ["Mon 30", "CFTC report for 24 Nov (holiday delay)", "Managed money in the crash days"],
       ["Tue 1 Dec", "ISM manufacturing (Nov), date to confirm", "Growth scare or not"],
       ["Fri 4 Dec", "Payrolls (Nov), date to confirm", "Last big print before the FOMC"],
       ["8-9 Dec", "FOMC: 25 bp hike priced at 94.4%", "Projections for 2027"]]
dk.table(cal, 500, y2 - 14, [70, 196, 158], size=8.2)

# 6 ranges and scorecard
dk.new_page("Ranges and the scorecard", "Day percentiles: 20,000 paths rebuilt from the stored 20 Nov fit (they reproduce the stored grids to within $0.01). Shadow refit at Wednesday's close, not stored. Ranges and scores use settlements. Binomial figure indicative: pairs share origins and overlap, so they are not independent.", "Core")
dk.card(36, 448, 452, 300)
dk.heading(48, 430, 428, "The 20 Nov forecast, day by day")
rows = [["Day", "Settlement", "90% range that day", "Percentile", "Status"]]
for k_, lab in (("2026-11-23", "Mon 23"), ("2026-11-24", "Tue 24"), ("2026-11-25", "Wed 25")):
    p_ = P20[k_]
    rows.append([lab, usd(p_["close"]), f"{usd(p_['q5'])} to {usd(p_['q95'])}", f"{p_['pit'] * 100:.1f}", "scored (1 day)" if k_ == "2026-11-23" else "information"])
y = dk.table(rows, 48, 418, [50, 70, 130, 64, 114], size=8.4, basis="settlement")
dk.bullets(48, y - 10, 428, [
    f"Monday closed above the 1-day range: the {P20['2026-11-23']['pit'] * 100:.1f}th percentile on the settlement of "
    f"{usd(M_['GC=F'])}. The Monday update of our 20 Nov note (published on the evening of 23 Nov) used a preliminary $3,632 and "
    "showed 96.8.",
    f"Live record: 4 of 6 scored ranges held. Two misses in six 90% ranges has about a {NV['binom_2of6'] * 100:.0f}% chance if the "
    "model is right (indicative). Two data points cannot tell a biased centre from bad luck.",
    "From 20 or more live scores we add a calibration plot (histogram of percentiles).",
    f"<b>Futures roll:</b> from 26 Nov the continuous series is the February contract ({usd(G['roll_gap'])} above December). "
    "Scores due 30 Nov and 1 Dec will convert February outcomes back to December at the 25 Nov ratio, so forecast and outcome "
    "use the same contract, once the roll date is confirmed on the 27 Nov settlement (gold_desk/rolls.json; unconfirmed rolls are "
    "not applied). The model's own inputs do not yet strip the roll jump.",
], size=8.6)
dk.card(504, 448, 420, 300)
dk.heading(516, 430, 396, "Shadow refit at Wednesday's close")
rows = [["Horizon", "5%", "25%", "Median", "75%", "95%"]]
for h, lab in (("5", "1 week"), ("21", "1 month")):
    qq = SH["q"][h]
    rows.append([lab] + [usd(qq[q]) for q in ("5", "25", "50", "75", "95")])
y = dk.table(rows, 516, 418, [62, 66, 66, 66, 66, 66], size=8.4, basis="settlement")
rows = [["Level", "Close through it within a week"]]
for lv, note in (("3250.0", "$3,250"), ("3430.0", "$3,430 (week's intraday low)"), ("3700.0", "$3,700"), ("3886.3", "$3,886 (13 Nov close)")):
    rows.append([note, f"{SH['touch_1w'][lv] * 100:.0f}%"])
y = dk.table(rows, 516, y - 12, [220, 176], size=8.4, basis="settlement")
rows = [["Daily move to 9 Dec", "Share of days", "At least once"],
        ["More than 2%", f"{x2['share_of_days'] * 100:.0f}% (1 in {1 / x2['share_of_days']:.0f})", f"{x2['at_least_once'] * 100:.0f}%"],
        ["More than 4%", f"{x4['share_of_days'] * 100:.0f}% (1 in {1 / x4['share_of_days']:.0f})", f"{x4['at_least_once'] * 100:.0f}%"]]
dk.table(rows, 516, y - 12, [150, 130, 116], size=8.4)

# 7 performance
dk.new_page("Market performance", "Closes on Wed 25 Nov (US 2-yr yield: FRED, 24 Nov). One month: 21 trading days. z-score: Fri to Wed move against the past 52 weekly moves, scaled to three days. Yields in basis points.", "Core")
UNITS = {"GC=F": "$/oz", "SI=F": "$/oz", "GDX": "$ per share", "GDXJ": "$ per share", "HG=F": "$/lb", "BZ=F": "$/bbl",
         "DX-Y.NYB": "index", "^GSPC": "index", "^NDX": "index", "^STOXX50E": "index", "^N225": "index", "EEM": "$ per share",
         "BTC-USD": "$", "^TNX": "%", "real10": "%", "DGS2": "%"}
rows = [["Asset", "Unit", "Wed close", "Fri to Wed", "z-score", "One month", "Year to date"]]
sty = []
for i_, r_ in enumerate(PERF, start=1):
    t = r_["ticker"]
    z = NV["z"][t]
    if r_.get("unit") == "bp":
        rows.append([r_["asset"], UNITS[t], f"{r_['close']:.2f}", bp(r_["wtd"]), f"{z:+.2f}", bp(r_["m1"]), bp(r_["ytd"])])
    else:
        cl = f"{r_['close']:,.0f}" if r_["close"] > 500 else f"{r_['close']:,.2f}"
        rows.append([r_["asset"], UNITS[t], cl, pc(r_["wtd"]), f"{z:+.2f}", pc(r_["m1"]), pc(r_["ytd"])])
    if abs(z) >= 2:
        sty.append(("BACKGROUND", (4, i_), (4, i_), NS.C("#f6ecd2")))
UNITS_OK = all(r[1] for r in rows[1:])
y = dk.table(rows, 36, 448, [190, 100, 110, 110, 90, 110, 110], size=8.4, styles=sty, basis="settlement")
dk.chart(c_bars, 36, y - 10, 888, "Stocks and miners led the rebound; gold barely moved",
         "Change from Fri 20 to Wed 25 Nov, % (closes; gold: settlement)", FIGTXT[c_bars], h=104)

# 8 driver model
dk.new_page("What moved gold: the driver model", f"Contributions in log points. Betas: rolling 156-week regressions on weekly changes in the TIPS yield, breakeven, dollar, VIX (log), S&amp;P 500 and WTI oil; each week uses only the 156 weeks before it. This week: betas to 20 Nov ({AN['window'][0]} to {AN['window'][1]}), gold at 16:00 ET, TIPS yield for 25 Nov from the Treasury curve; the intercept is left in 'unexplained'.", "Core")
y = dk.chart(c_attr, 36, 448, 452, "Stocks did most of the work this week; little is left unexplained",
             "Fri 20 to Wed 25 Nov, gold at 16:00 ET, log points, market factors only", FIGTXT[c_attr])
rows = [["Log points", "Last week (to 20 Nov)", "This week (to 25 Nov)"]]
for lab, k in (("Rates and inflation", ("d_real", "d_be")), ("Dollar", ("r_dxy",)), ("Stress (VIX)", ("d_vix",)),
               ("US stocks", ("r_spx",)), ("Oil", ("r_oil",))):
    rows.append([lab, lp(sum(AL["contrib"][x_] for x_ in k)), lp(sum(AN["contrib"][x_] for x_ in k))])
rows += [["Unexplained", lp(AL["residual"]), lp(AN["residual"])], ["<b>Gold</b>", lp(AL["r_gold"]), lp(AN["r_gold16"])],
         ["Contemporaneous GLD flows (not a driver)", lp(lw_old["flow"]), lp(AN["flow_contemporaneous"])]]
dk.table(rows, 504, 448, [190, 115, 115], size=8.4)
dk.bullets(504, 270, 420, [
    f"<b>Out of sample, honestly:</b> each week's split uses betas from the 156 weeks before it only, so the share explained is a "
    f"true out-of-sample figure: {NV['explained_oos'] * 100:.0f}% of weekly variance since 2009 and "
    f"{NV['explained_2026'] * 100:.0f}% in 2026 (below zero: worse than the average week).",
    "<b>Why no flows or positioning:</b> both follow the price (H2; managed money is trend-following), so as regressors they "
    "bias the other betas. Flows are shown as a contemporaneous line only.",
    f"<b>Reconciliation:</b> with flows and positioning (our 20 Nov notes) last week read stocks {lp(old_last['spx'])}, flows "
    f"{lp(old_last['flow'])}, positioning {lp(old_last['d_mm'])}, unexplained {lp(old_last['residual'])}. On market factors only: "
    f"stocks {lp(AL['contrib']['r_spx'])}, unexplained {lp(AL['residual'])}.",
    f"Gold {lp(AN['r_gold16'])} log points at 16:00 ET this week; on settlements {lp(AN['r_gold_settle'])}. Last week "
    f"{lp(AL['r_gold'])} log points is {pc(last_simple)} as a simple return.",
], size=8.5)

# 9 cycles (appendix)
dk.new_page("Appendix: gold's past cycles", "Monthly averages (WGC/LBMA via datahub; Nov 2026 = COMEX month to date), which understate daily peaks and troughs. Bear markets by the 20/20 rule from 1974. Trailing real rate: 10-yr Treasury minus CPI over the past 12 months (Oct 2025 CPI interpolated; it enters no peak value). TIPS yield from 2003. Free gold trading began with the two-tier market of March 1968; US private ownership only in 1975. Definition of 'rise before' changed from the 19 Nov note (see changelog).", "Appendix")
y = dk.chart(c_cyc, 36, 448, 430, "2026 is deeper at month 9 than any of the seven independent cycles",
             "% from the peak month's average, by months after the peak; monthly averages", FIGTXT[c_cyc])
rows = [["Peak", "Rise before (trough to peak)", "Fall to low", "Months to low", "Years to regain", "Trailing real rate", "TIPS 10-yr", "At month 9"]]
for r_ in NV["cycles"]["rows"]:
    is26 = r_["peak"] == "2026-02"
    rows.append([f"<b>{r_['peak']}</b>" if is26 else r_["peak"], f"{r_['rise'] * 100:+.0f}% (from {r_['from']})",
                 f"{r_['fall'] * 100:.0f}%" + (" so far" if is26 else ""), f"{r_['months_to_low']}" + (" so far" if is26 else ""),
                 f"{r_['years_to_regain']:.1f}" if r_["years_to_regain"] else "–", f"{r_['trailing_rr']:+.1f}%",
                 f"{r_['tips']:+.2f}%" if r_["tips"] is not None else "–", f"{r_['at9'] * 100:.0f}%" if r_["at9"] is not None else "–"])
y2 = dk.table(rows, 478, 448, [44, 92, 46, 40, 40, 50, 46, 44], size=7.2,
              styles=[("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), NS.C("#f6ecd2"))])
f7 = NV["cycles"]["falls7"]
dk.bullets(36, min(y, y2) - 8, 888, [
    f"<b>Seven independent cycles:</b> 1980-01 and 1980-09 are a double top of one secular peak, so the statistics treat them as one "
    f"(from the January 1980 top: {NV['cycles']['rows'][1]['fall'] * 100:.0f}% to the May 1980 low, {f7[1] * 100:.0f}% to the June 1982 low). Over the seven, "
    f"falls ran from {max(f7) * 100:.0f}% to {min(f7) * 100:.0f}% (median {NV['cycles']['median_fall7'] * 100:.0f}%), "
    f"{min(NV['cycles']['months7'])} to {max(NV['cycles']['months7'])} months after the peak. At month 9, 2026 ({CY['path26'][-1] * 100:.0f}%) is "
    "below all seven, narrowly below 1974 and 1983 (both -22%); the second 1980 top was at -32% nine months on. The 2026 daily record "
    "was 29 Jan; the peak monthly average was February.",
    f"<b>Real rates:</b> on the trailing measure, the peaks of 1974, 1980, 2008 and 2011 came with negative real rates and 2026 with "
    f"+{p26['trailing_rr']:.1f}%. On TIPS yields, 2008 was +{CYC['2008-03']['tips']:.1f}%, 2011 {CYC['2011-09']['tips']:+.1f}% and 2026 "
    f"+{p26['tips']:.1f}%: the 'negative real rates at big peaks' pattern holds only on the trailing measure.",
], size=8.4)

# 10 flows (appendix)
gl, gm = FL["GLD"], FL["GLDM"]
dk.new_page("Appendix: ETF, equity and cash flows", "State Street NAV history: flows = change in shares x NAV. Tonnes: ounces per share estimated as NAV / COMEX December at 10:00 ET (the NAV's pricing time), median of 16-25 Nov; the official SPDR holdings file was not machine-readable. Equity flows to 24 Nov. Money funds: ICI, week to 24 Nov. Miners chart: closes, gold at 16:00 ET.", "Appendix")
rows = [["Fund", "Mon 23", "Tue 24", "Wed 25", "Mon to Wed", "Last week", "Year to date", "Tonnes (est.)"]]
for t in ("GLD", "GLDM"):
    f_ = FL[t]
    dd = [f_["days"].get(k, 0.0) / 1e6 for k in ("2026-11-23", "2026-11-24", "2026-11-25")]
    rows.append([t] + [f"{v:+,.0f}" for v in dd] + [f"{f_['wtd'] / 1e6:+,.0f}", f"{f_['prev'] / 1e6:+,.0f}", f"{f_['ytd'] / 1e9:+.1f}bn",
                                                       f"{OZ[t]['tonnes']:,.0f} ({OZ[t]['tonnes'] - OZ[t]['tonnes_fri']:+.1f})"])
y = dk.table(rows, 36, 448, [42, 50, 50, 50, 64, 62, 66, 72], size=8.2)
y = dk.chart(c_etf, 36, y - 10, 456, f"GLD's biggest outflow this autumn came in the week to {big_wk:%d %b}, not the crash week",
             "Weekly flows, GLD and GLDM, US$ bn; the last bar covers 23-25 Nov only (hatched)", FIGTXT[c_etf], h=150)
rows = [["Fund", "What it holds", "Mon 23 to Tue 24", "Last week", "Year to date"]]
for t, what in (("SPY", "S&P 500"), ("XLK", "Technology"), ("XLP", "Consumer staples"), ("XLU", "Utilities"), ("BIL", "1-3 month T-bills")):
    f_ = FL[t]
    rows.append([t, what, f"{f_['wtd'] / 1e6:+,.0f}", f"{f_['prev'] / 1e6:+,.0f}", f"{f_['ytd'] / 1e9:+.1f}bn"])
y2 = dk.table(rows, 508, 448, [40, 110, 92, 82, 92], size=8.2)
dk.string(508, y2 - 10, f"US$ millions. Money funds ${MMF['total_bn'] / 1000:.2f}tn on {pd.Timestamp(MMF['date']):%d %b}, up ${MMF['chg_bn']:.1f}bn on the week.", size=7.8, color=NS.MUTED)
dk.chart(c_min, 508, y2 - 22, 416, "Miners tracked stocks, not gold",
         f"Mon 16 Nov = 100; GDX {pc(NV['miners16']['GDX'])}, gold {pc(NV['gold16_wtd'])} at 16:00 ET, Fri to Wed", FIGTXT[c_min], h=150)

# 11 positioning, volatility, physical market, technicals (appendix)
dk.new_page("Appendix: positioning, volatility, physical market, technicals", "CFTC disaggregated, futures only, contracts x 100 oz. GVZ: CBOE gold volatility index. Technical levels from our own COMEX data; stars: 1 = this week's extreme, 2 = 3-month extreme or 55-day average, 3 = 12-month extreme or 200-day average.", "Appendix")
dk.heading(36, 446, 430, "COMEX positioning (latest report 17 Nov)")
y = dk.table([["Measure", "17 Nov", "10 Nov"], ["Managed money net long", f"{COT['mm_t']:,.0f} t", f"{COT['mm_t_prev']:,.0f} t"],
              ["Net long, share of open interest", f"{COT['share'] * 100:.0f}%", f"{COT['share_prev'] * 100:.0f}%"],
              ["Percentile since 2006", nth(COT["share_pct"]), "–"]], 36, 434, [220, 100, 110], size=8.4)
dk.string(36, y - 10, "The 24 Nov report, the first to cover the crash days, is delayed by Thanksgiving.", size=8, color=NS.MUTED)
dk.heading(36, y - 34, 430, "Volatility")
y = dk.table([["Measure", "Level", "Note"], ["GVZ, 30-day implied", f"{VOL['gvz']:.1f}", f"Fri 20 Nov: {VOL['gvz_fri']:.1f}"],
              ["Realised, 21 days", f"{VOL['rv21'] * 100:.1f}%", "Settlements"],
              ["Model, next day (20 Nov fit carried)", f"{ODDS['vol_next'] * 100:.1f}%", f"Shadow refit {SH['vol_next'] * 100:.1f}%"],
              ["VIX", f"{VOL['vix']:.1f}", f"Fri 20 Nov: {F_['^VIX']:.1f}"]], 36, y - 46, [200, 90, 140], size=8.4)
dk.heading(36, y - 26, 430, "Physical market")
dk.table([["Measure", "Status"], ["Shanghai premium over London", "Not yet wired: source SGE Au99.99 benchmark vs LBMA PM"],
          ["COMEX vs London (EFP)", "Not yet wired: source CME/LBMA exchange-for-physical quotes"],
          ["Central banks", "Q3 2026: 321 t, +42% on a year; China 63 t, Poland 40 t reported (WGC)"]], 36, y - 38, [150, 280], size=8.2)
dk.heading(494, 446, 430, "Technicals (our data)")
T = TECH
lv_rows = [["Level", "Type", "Rank", "Basis"],
           [usd(T["sma200"]), "Resistance", stars(3), "200-day average"],
           [usd(T["high_3m"]), "Resistance", stars(2), "3-month high close"],
           [usd(T["sma55"]), "Resistance", stars(2), "55-day average"],
           [usd(T["wk_high"]), "Resistance", stars(1), "This week's intraday high (23 Nov)"],
           [usd(T["low_12m"]), "Support", stars(3), f"12-month low close ({pd.Timestamp(T['low_12m_date']):%d %b})"],
           [usd(T["wk_low"]), "Support", stars(1), "This week's intraday low (25 Nov)"],
           [usd(T["last_below_wk_low_px"]), "Support", "–", f"Last close below $3,430: {pd.Timestamp(T['last_below_wk_low']):%d %b %Y}"]]
y = dk.table(lv_rows, 494, 434, [70, 70, 50, 240], size=8.4)
dk.bullets(494, y - 10, 430, [
    f"Momentum: 14-day RSI {T['rsi14']:.0f}, 9-week RSI {T['rsi9w']:.0f} (below 30 reads as oversold; our spring tests found no "
    "reliable bounce after such readings).",
    f"Gold is {abs(G['close'] / T['sma55'] - 1) * 100:.0f}% below its 55-day and {abs(G['close'] / T['sma200'] - 1) * 100:.0f}% below its "
    "200-day average: both falling, the trend is down."], size=8.6)

# 12 method, glossary, sources (appendix)
dk.new_page("Appendix: method, glossary and sources", "", "Appendix")
dk.heading(36, 446, 440, "Method")
dk.bullets(36, 432, 440, [
    "<b>Prices:</b> COMEX December settlements to Wed 25 Nov (checked against the contract itself); the 26 Nov Thanksgiving bar is "
    "dropped. Gold-vs-equity comparisons for the current week use gold at 16:00 ET from 5-minute futures; history (betas, ranges, "
    "scores) uses settlements, because 5-minute data only reach back about 60 days.",
    "<b>Model:</b> GARCH(1,1), Student-t, zero drift, 20,000 paths. The 20 Nov live forecast is rebuilt from its stored fit; only the "
    "1-day outcome is a score. The Wednesday refit is a shadow: store/live.jsonl is unchanged (hash in checks.json).",
    "<b>Pre-registration:</b> tests H1 to H6 were fixed in code before they ran (commits 0a7239c, 59b21e2). They were registered on "
    "historical data we had partly seen, so they guard against tuning after the fact but are not a true out-of-sample test.",
    "<b>Rolls:</b> a forecast is scored on the contract it was made on (gold_desk/rolls.py, confirmed rolls only). Known limits: rolls "
    "in the 2006-2026 backfill are not adjusted, and the fit's daily returns still include each roll jump (about +0.8% on 26 Nov).",
    f"<b>Checks:</b> {len(CHECKS)} data checks plus render checks (no dashes, one key block, chart titles, units, fonts embedded, "
    "one price basis per table), all in checks.json.",
], size=8.2)
dk.heading(494, 446, 430, "Glossary")
dk.bullets(494, 432, 430, [
    "<b>GARCH:</b> a volatility model in which big moves raise the expected size of the next moves, which then fade.",
    "<b>Student-t:</b> a bell curve with fatter tails, so extreme days are more likely than in a normal curve.",
    "<b>Percentile score:</b> where the actual price fell in the forecast distribution (50 = middle; below 5 or above 95 = a miss).",
    "<b>90% range:</b> the band that should hold the outcome 9 times in 10.",
    "<b>Shadow refit:</b> the model re-estimated on newer data for information only; it is not logged or scored.",
    "<b>Pre-registration:</b> writing a test's rule and pass mark into code before seeing its result.",
    "<b>Managed money:</b> hedge funds and commodity trading advisers in the CFTC report; mostly trend-following.",
    "<b>z-score:</b> a move divided by its usual size; beyond plus or minus 2 is unusual.",
    "<b>Log points:</b> 100 x the log of the price ratio; they add up across factors (-10.0 log points = -9.5%).",
], size=8.2)
dk.heading(36, 150, 888, "Sources")
dk.bullets(36, 136, 888, [
    "CNBC (Fed minutes, PCE, gold 24 Nov); Bloomberg (Waller, 10 Nov); BEA (GDP); Morningstar, Advisor Perspectives (PCE); TMGM, The Edge "
    "(durable goods, claims); Minneapolis Fed, investingLive (Beige Book); CME FedWatch relayed by CoinCentral; Nvidia press release and "
    "SEC 8-K (23 Nov), CNN; Yahoo Finance and Seeking Alpha (S&amp;P CreditWatch, 25 Nov); Kitco and investingLive (23 Nov); Jiji/Nation "
    "(24 Nov); World Gold Council (Gold Demand Trends Q3 2026); Yahoo Finance (bank forecasts, one source); data: Yahoo Finance, FRED, "
    "US Treasury, CFTC, State Street, ICI."], bullet=False, size=8)
dk.save()

# ------------------------------------------------------------------ render checks, appended to checks.json
render = []


def rcheck(name, ok, detail):
    render.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail, "render": True})


dashes = NS.find_dashes(dk.texts)
rcheck("No em dash or en dash used as a dash in any page or chart text", not dashes, f"offending: {dashes[:3] or 'none'}; strings checked: {len(dk.texts)}")
rcheck("Exactly one key block (the desk view)", dk.blue_blocks == 1, f"blue blocks: {dk.blue_blocks}")
rcheck("Every chart has a takeaway title and a subtitle", all(c["title"] and c["subtitle"] for c in dk.charts) and len(dk.charts) == 7,
       f"charts: {len(dk.charts)}")
rcheck("Units column filled for every row of the performance table", UNITS_OK, "all rows have a unit")
ok_f, det_f = NS.fonts_embedded(OUT)
rcheck("All fonts embedded in the PDF", ok_f, det_f)
rcheck("No table mixes settlement and 16:00 ET gold prices", all(t["basis"] in ("settlement", "16:00", "none") for t in dk.tables),
       f"tables: {len(dk.tables)}; 16:00 tables: {sum(t['basis'] == '16:00' for t in dk.tables)}")
rcheck("12 pages or fewer", dk.page <= 12, f"pages: {dk.page}")
if OUT.parent == OUTDIR:
    (OUTDIR / "checks.json").write_text(json.dumps(CHECKS + render, indent=1), encoding="utf-8")
print("\n".join(f"{c['result']}  {c['check']}: {c['detail']}" for c in render))
print("wrote", OUT, "pages", dk.page)
