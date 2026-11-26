"""Gold Desk holiday-week note, to the Wednesday 25 Nov 2026 close (landscape slides in the weekly-monitor layout
of reference/, own branding). Reads week.json and checks.json from analyse_week.py and the data snapshot; no forecast
is logged (the weekly record stays on Friday's close).

Usage (from desk/): python reports/2026-11-25/scripts/build_note.py
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
OUTDIR = DESK / "reports" / "2026-11-25"
D = OUTDIR / "data"
CUT, FRI, PREV, YEND = pd.Timestamp("2026-11-25"), pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-13"), pd.Timestamp("2025-12-31")
TEAL, TEAL2, INK, INK2, MUTED, GRID = "#0b3a44", "#2f5d62", "#111111", "#4a4a48", "#8a8a86", "#e3e3df"
BOX = "#f1f1f0"
BLUE, ORANGE, AQUA, YELLOW, VIOLET, PINK = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6", "#e87ba4"
NEUTRAL, RED, GREEN, GOLDC = "#b5b3ad", "#c62828", "#2e7d32", "#b8860b"

W_ = json.loads((OUTDIR / "week.json").read_text(encoding="utf-8"))
CHECKS = json.loads((OUTDIR / "checks.json").read_text(encoding="utf-8"))
assert all(c["result"] == "PASS" for c in CHECKS), [c for c in CHECKS if c["result"] != "PASS"]
DRV = json.loads((DESK / "reports" / "2026-11-20-weekly" / "drivers.json").read_text(encoding="utf-8"))
SPR = json.loads((DESK / "reports" / "2026-11-20" / "spring.json").read_text(encoding="utf-8"))
daily = pd.read_csv(D / "daily.csv", index_col=0, parse_dates=True).loc[:CUT]
fred = pd.read_csv(D / "fred.csv", index_col=0, parse_dates=True).loc[:CUT]
gold = daily["GC=F"].dropna()
tr = pd.read_csv(D / "treasury_real_yield_2026.csv")
tr["Date"] = pd.to_datetime(tr["Date"], format="%m/%d/%Y")
real10 = tr.set_index("Date").sort_index()["10 YR"].astype(float).loc[:CUT].combine_first(fred["DFII10"].dropna())
G = W_["gold"]
DAYS = W_["days"]
DY = {d["date"]: d for d in DAYS}
F_, M_, T_, WD = (DY[k] for k in ("2026-11-20", "2026-11-23", "2026-11-24", "2026-11-25"))
FL = W_["flows"]
ATT = W_["attr"]
CY = W_["cycles"]
SH = W_["shadow"]
P20 = W_["pit20"]
INTR = W_["intraday"]
MI = W_["miners"]
MMF = W_["mmf"]
COT = W_["cot"]
VOL = W_["vol"]
PERF = {r["ticker"]: r for r in W_["perf"]}

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

W, H = 960, 540
FONTS = {"L": "C:/Windows/Fonts/segoeuil.ttf", "R": "C:/Windows/Fonts/segoeui.ttf", "B": "C:/Windows/Fonts/segoeuib.ttf",
         "S": "C:/Windows/Fonts/seguisb.ttf"}
for k, f_ in FONTS.items():
    pdfmetrics.registerFont(TTFont(f"SUI-{k}", f_ if os.path.exists(f_) else FONTS["R"]))
_it = "C:/Windows/Fonts/segoeuii.ttf"
pdfmetrics.registerFont(TTFont("SUI-I", _it if os.path.exists(_it) else FONTS["R"]))
pdfmetrics.registerFontFamily("SUI-R", normal="SUI-R", bold="SUI-B", italic="SUI-I", boldItalic="SUI-B")
C = colors.HexColor
st = lambda name, **kw: ParagraphStyle(name, **{"fontName": "SUI-R", "fontSize": 10, "leading": 13.2, "textColor": C(INK), **kw})  # noqa: E731
BUL = st("bul", leftIndent=10, bulletIndent=0, spaceAfter=5, fontSize=9.6, leading=12.6)
CELL = st("cell", fontSize=8, leading=10)
CELLB = st("cellb", fontName="SUI-B", fontSize=8, leading=10)
out_pdf = Path(os.environ.get("DESK_NOTE_OUT", OUTDIR / "gold_desk_2026-11-25.pdf"))   # override to render elsewhere
cv = rl_canvas.Canvas(str(out_pdf), pagesize=(W, H))
cv.setTitle("Gold Desk holiday-week note, to 25 November 2026")
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
    cv.drawString(36, 18, "Gold Desk Weekly  |  Thanksgiving week, to Wed 25 Nov 2026")
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


fmt_usd = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")
usd = lambda v: f"${v:,.0f}"  # noqa: E731
ap = lambda v, d=1: f"{abs(v) * 100:.{d}f}%"  # noqa: E731
bp = lambda v: f"{v:+.0f} bp"  # noqa: E731

# ------------------------------------------------------------------ charts
fig, ax = plt.subplots(figsize=(6.4, 6.0))
gg = gold.loc["2025-01-01":]
ax.fill_between(gg.index, gg.min() * 0.92, gg.values, color="#1f6f78", alpha=0.55, lw=0)
ax.plot(gg.index, gg.values, color="#e9c46a", lw=2.2)
ax.axis("off")
fig.patch.set_facecolor(TEAL)
c_cover = str(CH / "cover.png")
fig.savefig(c_cover, dpi=200, bbox_inches="tight", facecolor=TEAL)
plt.close(fig)

# chart of the week: the December contract from Sunday's open to Wednesday 17:00 ET
i5 = pd.read_csv(D / "gold_5m_contracts.csv", index_col=0, parse_dates=True)["GCZ26.CMX"].dropna()
seg = i5.loc["2026-11-22 18:00":"2026-11-25 17:00"]
fig, ax = plt.subplots(figsize=(6.2, 3.2))
x = np.arange(len(seg))
ax.plot(x, seg.values, color=GOLDC, lw=1.2)
ax.axhline(G["fri"], color=MUTED, lw=0.8, ls="--")
ax.text(x[0] + 2, G["fri"] - 5, f"Friday settlement ${G['fri']:,.0f}", fontsize=7, color=MUTED, va="top", ha="left")
for k in range(1, len(seg)):
    if seg.index[k].hour == 18 and seg.index[k - 1].hour != 18:
        ax.axvline(k, color=GRID, lw=0.9)
for d in ("2026-11-23", "2026-11-24", "2026-11-25"):
    k = int(seg.index.searchsorted(pd.Timestamp(f"{d} 13:30")))
    ax.scatter([k], [DY[d]["GC=F"]], color=TEAL2, s=16, zorder=5)
kp = int(seg.index.searchsorted(pd.Timestamp("2026-11-25 08:30")))
ax.axvline(kp, color=ORANGE, lw=0.9, ls=":")
kl = int(np.argmin(seg.values))
ax.annotate(f"PCE, then low ${INTR['wed_low']:,.0f}", xy=(kl, INTR["wed_low"]), xytext=(-118, 4), textcoords="offset points",
            fontsize=7, color=ORANGE, arrowprops={"arrowstyle": "-", "color": ORANGE, "lw": 0.7})
ticks = [int(seg.index.searchsorted(pd.Timestamp(f"{d} 09:00"))) for d in ("2026-11-23", "2026-11-24", "2026-11-25")]
ax.set_xticks(ticks)
ax.set_xticklabels(["Monday", "Tuesday", "Wednesday"], fontsize=8)
ax.set_xlim(0, len(seg) - 1)
ax.yaxis.set_major_formatter(fmt_usd)
ax.set_ylabel("$/oz")
c_cotw = save(fig, "cotw_intraday")

# Friday to Wednesday, across markets
BT = [("Gold", "GC=F"), ("Silver", "SI=F"), ("Miners\n(GDX)", "GDX"), ("Juniors\n(GDXJ)", "GDXJ"), ("S&P 500", "^GSPC"),
      ("Nasdaq-100", "^NDX"), ("Dollar", "DX-Y.NYB"), ("Copper", "HG=F"), ("Brent", "BZ=F"), ("Bitcoin", "BTC-USD")]
fig, ax = plt.subplots(figsize=(9.4, 2.1))
vals = [PERF[t]["wtd"] * 100 for _, t in BT]
ax.bar(range(len(BT)), vals, color=[GOLDC if t == "GC=F" else "#1c5cab" for _, t in BT], width=0.6)
for i_, v in enumerate(vals):
    ax.text(i_, v + (0.3 if v >= 0 else -0.3), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7.4, color=INK2)
ax.set_xticks(range(len(BT)))
ax.set_xticklabels([n for n, _ in BT], fontsize=7.4)
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_ylabel("Fri 20 to Wed 25 Nov, %", fontsize=7.4)
ax.set_ylim(min(vals) - 1.5, max(vals) + 1.5)
c_bars = save(fig, "bars")

# hawkish Fed: gold against the real yield and the 2-year yield
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.2, 3.6), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
gs = gold.loc["2026-09-01":]
a1.plot(gs.index, gs.values, color=GOLDC, lw=1.4)
a1.set_ylabel("COMEX gold, $/oz", fontsize=7.6)
a1.yaxis.set_major_formatter(fmt_usd)
rs = real10.loc["2026-09-01":]
d2 = fred["DGS2"].dropna().loc["2026-09-01":]
a2.plot(rs.index, rs.values, color=BLUE, lw=1.4, label="10-yr real yield (TIPS)")
a2.plot(d2.index, d2.values, color=ORANGE, lw=1.2, label="2-yr Treasury yield (to 24 Nov)")
a2.set_ylabel("%", fontsize=7.6)
a2.legend(loc="center left", ncol=2, fontsize=7)
a2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
c_fed = save(fig, "fed")

# cycles: drawdown paths after each bear-market peak (monthly averages)
fig, ax = plt.subplots(figsize=(6.0, 3.3))
labs = []
for k, v in CY["paths"].items():
    v = np.asarray(v[:49]) * 100
    ax.plot(range(len(v)), v, color=NEUTRAL, lw=1.0)
    labs.append([float(np.clip(v[-1], -58, 38)), len(v) - 1, k[:7]])
labs.sort()
for j in range(1, len(labs)):                    # keep end labels at least 4 points apart
    labs[j][0] = max(labs[j][0], labs[j - 1][0] + 4)
for yv, xv, k in labs:
    ax.text(xv, yv, f" {k}", fontsize=6.2, color=MUTED, va="center")
v26 = np.asarray(CY["path26"]) * 100
ax.plot(range(len(v26)), v26, color=GOLDC, lw=2.6, label="2026 (November: month to date)")
ax.axvline(9, color=ORANGE, lw=0.8, ls=":")
ax.text(9, 0.98, " month 9", transform=ax.get_xaxis_transform(), color=ORANGE, fontsize=7, va="top")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xlabel("Months after the peak month", fontsize=7.6)
ax.set_ylabel("% from the peak month's average", fontsize=7.6)
ax.set_xlim(0, 55)
ax.set_ylim(-60, 40)
ax.legend(loc="lower left", fontsize=7)
c_cycles = save(fig, "cycles")

# ETF flows by week
wkf = pd.DataFrame({"GLD": pd.Series(FL["GLD"]["weekly"]), "GLDM": pd.Series(FL["GLDM"]["weekly"])}) / 1e9
wkf.index = pd.to_datetime(wkf.index)
wkf = wkf.iloc[-13:]
fig, ax = plt.subplots(figsize=(6.2, 2.7))
xx = np.arange(len(wkf))
ax.bar(xx - 0.2, wkf["GLD"], width=0.4, color=BLUE, label="GLD")
ax.bar(xx + 0.2, wkf["GLDM"], width=0.4, color=AQUA, label="GLDM")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xticks(xx)
ax.set_xticklabels([d.strftime("%d/%m") for d in wkf.index[:-1]] + ["23-25\nNov"], fontsize=7)
ax.set_ylabel("Weekly flows, $bn", fontsize=7.6)
ax.legend(loc="lower left", fontsize=7, ncol=2)
c_etf = save(fig, "etf")

# miners against gold and stocks, two weeks
ix = daily[["GC=F", "GDX", "GDXJ", "^GSPC"]].dropna().loc[PREV:CUT]
ix = ix / ix.iloc[0] * 100
fig, ax = plt.subplots(figsize=(6.2, 2.7))
for col, name, cc, lw in (("GC=F", "Gold", GOLDC, 2.0), ("GDX", "Miners (GDX)", BLUE, 1.4), ("GDXJ", "Juniors (GDXJ)", VIOLET, 1.4),
                          ("^GSPC", "S&P 500", NEUTRAL, 1.4)):
    ax.plot(ix.index, ix[col], color=cc, lw=lw, marker="o", ms=2.5, label=name)
ax.axhline(100, color="#c3c2b7", lw=0.8)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.set_ylabel("13 Nov close = 100", fontsize=7.6)
ax.legend(loc="lower left", fontsize=7, ncol=2)
c_miners = save(fig, "miners")

# partial-week attribution: residual first
cg = ATT["contrib"]
parts = [("Unexplained", ATT["residual"], NEUTRAL), ("Rates and\ninflation", cg["d_real"] + cg["d_be"], BLUE),
         ("Dollar", cg["r_dxy"], ORANGE), ("Stress\n(VIX)", cg["d_vix"], AQUA), ("US stocks", cg["r_spx"], YELLOW),
         ("Oil", cg["r_oil"], VIOLET), ("ETF flows*", cg["flow"], PINK)]
fig, ax = plt.subplots(figsize=(6.2, 2.9))
cum = 0.0
for i_, (lab, v, col) in enumerate(parts):
    v *= 100
    ax.bar(i_, v, bottom=cum if v >= 0 else cum + v, color=col, width=0.62)
    ax.text(i_, cum + v + (0.08 if v >= 0 else -0.08), f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7.4)
    cum += v
ax.bar(len(parts), ATT["r_gold"] * 100, color="#3c3c3a", width=0.62)
ax.text(len(parts), ATT["r_gold"] * 100 + 0.08, f"{ATT['r_gold'] * 100:+.2f}", ha="center", va="bottom", fontsize=7.6, fontweight="bold")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.set_xticks(range(len(parts) + 1))
ax.set_xticklabels([p[0] for p in parts] + ["Gold,\nFri-Wed"], fontsize=7)
ax.set_ylabel("% points (log)", fontsize=7.6)
c_attr = save(fig, "attr")

# volatility
gvz = daily["^GVZ"].dropna()
rv = (np.log(gold).diff().rolling(21).std() * np.sqrt(252) * 100).loc["2025-01-01":]
fig, ax = plt.subplots(figsize=(6.0, 2.7))
ax.plot(gvz.loc["2025-01-01":].index, gvz.loc["2025-01-01":].values, color=BLUE, lw=1.3, label="GVZ (implied, 30 days)")
ax.plot(rv.index, rv.values, color=ORANGE, lw=1.3, label="Realised, past 21 days")
ax.set_ylabel("%", fontsize=7.6)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.legend(loc="upper left", fontsize=7)
c_vol = save(fig, "vol")

# ------------------------------------------------------------------ slides
rr_chg = (WD["real10"] - F_["real10"]) * 100
_d2 = fred["DGS2"].dropna()
d2_lw = (float(_d2.loc[:FRI].iloc[-1]) - float(_d2.loc[:PREV].iloc[-1])) * 100
m_chg, t_chg, w_chg = M_["GC=F"] / F_["GC=F"] - 1, T_["GC=F"] / M_["GC=F"] - 1, WD["GC=F"] / T_["GC=F"] - 1
spx_w = PERF["^GSPC"]["wtd"]
mon_pub = 0.968        # Monday's 1-day percentile as published in the 20 Nov note (preliminary close $3,632)

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
cv.drawString(48, 126, "Thanksgiving week, to Wednesday 25 November 2026")
cv.setFont("SUI-R", 11)
cv.drawString(48, 104, "Flows, narratives, the Fed and gold's past cycles")
cv.setFont("SUI-R", 8.5)
cv.drawString(48, 52, "Holiday-week note: data to the Wednesday 25 November close; the weekly forecast is logged at Friday's close")

# 2 what you need to know
new_slide("What you need to know – a whipsaw week, back where it started",
          "Chart of the week: COMEX December futures, 5-minute bars, New York time; dots mark the 13:30 settlements. Bars: Yahoo Finance closes. Gold: settlement prices.")
bar_header(36, 446, 440, "Highlights")
bar_header(484, 446, 440, "Chart of the week: +3.9%, -2.5%, then a PCE plunge and recovery")
text_block(36, 440, 440, [
    f"Gold settled Wednesday at <b>{usd(G['close'])}</b>, {pc(G['wtd'])} from Friday, after swinging {pc(m_chg)} Monday, "
    f"{pc(t_chg)} Tuesday and {pc(w_chg)} Wednesday. It is {pc(G['ytd'])} for the year and "
    f"{pc(CY['daily_dd'], 0)} from the January record.",
    f"<b>Hawkish Fed, confirmed:</b> core PCE rose to 3.3% a year, the highest since 2023; a December hike is priced at "
    f"94-98%. Gold fell to {usd(INTR['wed_low'])} at 10:15 ET, then recovered to {usd(INTR['wed_1655'])} by 17:00.",
    f"<b>Equities led, gold followed:</b> the S&amp;P 500 rose {ap(spx_w)} and gold miners {ap(MI['GDX']['wtd'])}, "
    f"while GLD lost another {usd(abs(FL['GLD']['wtd']) / 1e6)}m. Gold moved with risk assets again.",
    "<b>Narratives:</b> the hawkish Fed is the backdrop; forced selling and its unwind best explain the swings. The "
    "bull case (central banks, a Fed that stops) is real but slow (p. 4-5).",
    f"<b>Cycles:</b> nine months after its peak, gold is {ap(-CY['path26'][-1], 0)} below the peak month on monthly "
    "averages, deeper than all but one past cycle at this stage (p. 7).",
], bg=BOX, h=262)
image(c_cotw, 490, 438, w=428)
iw_, ih_ = ImageReader(c_bars).getSize()
image(c_bars, 36 + (888 - 132 * iw_ / ih_) / 2, 170, h=132)

# 3 desk view
new_slide("Desk view", "Model: GARCH(1,1) with Student-t shocks on daily COMEX settlements, zero drift. The shadow refit uses Wednesday's close and is not stored; the weekly record is Friday's close.")
key_block(36, 470, 450, 250, "THE DESK VIEW, AT WEDNESDAY'S CLOSE", [
    "<b>Direction: no call.</b> No drift rule, no positioning or flow signal and no spring toward value has passed our "
    "pre-registered tests. The narratives below explain moves after the fact; none has predicted them.",
    f"<b>Volatility: still rising.</b> A refit at Wednesday's close puts next-day volatility at {SH['vol_next'] * 100:.1f}% "
    f"(20 Nov: {SH['vol_next_20nov'] * 100:.1f}%), with a half-life of {SH['half_life']:.0f} trading days. Daily swings of "
    "2-4% are the base case into the 9 Dec FOMC.",
    f"<b>Regime: gold trades as a risk asset.</b> Stocks explain {cg['r_spx'] * 100:.1f} points of gold's {pc(ATT['r_gold'])} "
    "this week, the same channel that drove last week's fall.",
])
bar_header(500, 446, 424, "What we watch for a turn")
text_block(500, 440, 424, [
    "<b>Gold up on a day stocks fall:</b> the safe-haven link back; it has not happened since the selloff began.",
    "<b>GLD inflows for a full week:</b> a confirmation, not a signal (flows follow the price, H2).",
    "<b>A dovish hike on 9 Dec:</b> a hike with projections that signal the end of tightening would ease the real-yield "
    "cap. A hawkish one with 2027 hikes keeps it.",
    f"<b>Range:</b> the refit gives a {SH['touch_1w']['3430.0'] * 100:.0f}% chance of a close below $3,430 within a week and "
    f"{SH['touch_1w']['3700.0'] * 100:.0f}% above $3,700; a break of either is noise unless it holds.",
], bg=BOX, h=220)
bar_header(36, 206, 450, "The model, Friday and Wednesday")
q5w = SH["q"]["5"]
rows = [["Desk model", "20 Nov (logged)", "25 Nov (shadow)"],
        ["Next-day volatility, annualised", f"{SH['vol_next_20nov'] * 100:.1f}%", f"{SH['vol_next'] * 100:.1f}%"],
        ["Long-run volatility", "21.5%", f"{SH['vol_long_run'] * 100:.1f}%"],
        ["Tail thickness (t degrees of freedom)", "4.78", f"{SH['nu']:.2f}"],
        ["1-week 90% range", "$3,298-$3,751", f"{usd(q5w['5'])}-{usd(q5w['95'])}"]]
table(rows, 36, 178, [230, 110, 110], size=8.6)
bar_header(500, 206, 424, "The 20 Nov forecast so far")
rows = [["Day", "Settlement", "Percentile", "Status"]]
for k_, lab in (("2026-11-23", "Mon 23 (day 1)"), ("2026-11-24", "Tue 24 (day 2)"), ("2026-11-25", "Wed 25 (day 3)")):
    p_ = P20[k_]
    rows.append([lab, usd(p_["close"]), f"{p_['pit'] * 100:.1f}", "scored, outside 90%" if k_ == "2026-11-23" else "information only"])
table(rows, 500, 178, [110, 90, 80, 144], size=8.6)

# 4 bear narratives
new_slide("The narratives (1): the bear case, against our data",
          "What is said: press and official sources as dated. What our data says: desk model and pre-registered tests (H1-H3 on 21 Nov, spring H4-H6 on 23 Nov).")
lw = DRV["week"]
rows = [["Narrative", "What is said", "What our data says", "Verdict"],
        ["<b>The Fed stays hawkish</b>",
         "Almost all officials see more hikes; Waller backs 50 bp (Fed minutes, CNBC, 18 Nov). Core PCE 3.3% a year, the "
         "highest since 2023 (BEA, CNBC, 25 Nov). A December hike priced at 94-98% (CME FedWatch via press, 25 Nov).",
         f"The 10-yr real yield moved {bp(rr_chg)} this week while gold swung 2-4% a day. Since 2022 gold's link to real "
         f"yields is about half what it was (H1: slope {DRV['h1']['beta_before']:.3f} to {DRV['h1']['beta_after']:.3f}). Rates "
         f"and inflation explained {(lw['d_real'] + lw['d_be']) * 100:+.1f} points of last week's {lw['r_gold'] * 100:.1f}.",
         "The backdrop that caps rallies, not the trigger of the crash."],
        ["<b>Forced selling: gold is sold for cash</b>",
         "Investors sold precious metals to cover losses on Wall Street (Jiji/Nation, 24 Nov); a broad short-covering "
         "wave lifted all markets on Monday (investingLive, 23 Nov).",
         f"{DRV['week']['residual'] / DRV['week']['r_gold'] * 100:.0f}% of last week's fall was unexplained, with gold falling "
         f"alongside stocks while Treasuries rallied. This week stocks explain {cg['r_spx'] * 100:+.1f} points of gold's "
         f"{ATT['r_gold'] * 100:+.1f}: the unwind runs through the same channel.",
         "The best fit for both the crash and the bounce."],
        ["<b>The dollar is too strong</b>",
         "The dollar index near a 19-month high (Jiji/Nation, 24 Nov; another report had it easing the same day).",
         f"The dollar rose 0.4% last week and moved {pc(PERF['DX-Y.NYB']['wtd'])} this week. Its contribution: "
         f"{lw['r_dxy'] * 100:+.1f} points last week, {cg['r_dxy'] * 100:+.2f} this week.",
         "Minor this month."],
        ["<b>ETF investors are leaving</b>",
         f"Western investors are selling gold ETFs; GLD lost {usd(abs(FL['GLD']['prev']) / 1e6)}m last week and "
         f"{usd(abs(FL['GLD']['wtd']) / 1e6)}m from Monday to Wednesday (State Street).",
         f"Flows follow the price and do not lead it (H2 confirmed, H3 failed). GLDM took in "
         f"${FL['GLDM']['ytd'] / 1e9:.1f}bn this year while GLD lost ${abs(FL['GLD']['ytd']) / 1e9:.1f}bn: part of the exit is "
         "a switch to the cheaper fund.",
         "A symptom of the fall, not its cause."]]
table(rows, 36, 470, [128, 280, 320, 160], size=9, header_bg="#5b3f86")

# 5 bull narratives
new_slide("The narratives (2): the bull case, against our data",
          "Bank forecasts: one secondary source (Yahoo Finance, citing a Reuters poll), not checked against the banks. WGC: Gold Demand Trends Q3 2026.")
rows = [["Narrative", "What is said", "What our data says", "Verdict"],
        ["<b>Central banks keep buying</b>",
         "Central-bank demand 321 t in Q3, +42% on a year; reported purchases 120 t, led by China (63 t) and Poland (40 t) "
         "(World Gold Council, Gold Demand Trends Q3 2026).",
         "Quarterly data cannot enter a weekly model. Central banks bought through the peak and the fall: they set a slow "
         "floor under demand, not the weekly path.",
         "Real, but slow; no shield against forced selling."],
        ["<b>The AI rout will stop the Fed</b>",
         "Less fear of aggressive Fed tightening as the AI selloff clouds the outlook (Kitco, 23 Nov).",
         f"The 2-yr yield moved {bp(d2_lw)} last week and the real 10-yr {bp(rr_chg)} this week, but December stayed priced at "
         "94-98% after PCE, and GDP was revised up to 4.3%.",
         "Open; the test is 9 Dec."],
        ["<b>Oversold: a bounce is due</b>",
         "Gold bounced $160 from a 14-month low, but the bottom is not confirmed (bifu.co, 23 Nov). The 9-week RSI is near 24.",
         f"Our spring tests found no pull back toward value after big stretches (H4-H6 failed; H5 p = {SPR['h5'][0]['p_one_sided']:.3f}). "
         f"Monday's +3.9% came and went: Wednesday settled {pc(G['wtd'])} on the week.",
         "Not supported by 20 years of data."],
        ["<b>Positioning is washed out</b>",
         f"Speculators have cut longs (CFTC: managed money {COT['mm_t'] - COT['mm_t_prev']:+.0f} t in the week to 17 Nov).",
         f"The managed-money net long is still {COT['share'] * 100:.0f}% of open interest, the "
         f"{nth(COT['share_pct'])} percentile since 2006: mid-range. Positioning does not predict the next month (H3).",
         "Not yet."],
        ["<b>The banks still see higher prices</b>",
         "Goldman cut its end-2026 forecast to $4,150; UBS sees $5,000 by end-2027; a Reuters poll's 2027 median is $4,650 "
         "(via Yahoo Finance, one source).",
         "Targets follow the price with a lag. The desk model has no drift: its one-month median is today's price, and "
         "no target-based signal has been tested.",
         "Opinion, not evidence."]]
table(rows, 36, 470, [128, 280, 320, 160], size=9, header_bg=TEAL)

# 6 hawkish Fed in numbers
new_slide("The hawkish Fed in numbers",
          "Sources: PCE (BEA via CNBC, Morningstar, Advisor Perspectives), GDP (BEA), durable goods and claims (TMGM, The Edge), Beige Book (Minneapolis Fed, investingLive), FedWatch via press. Real yield: Treasury par real curve.")
bar_header(36, 446, 470, "This week's US data")
eco = [["Date", "What", "Consensus", "Actual"],
       ["Wed 25", "Core PCE, m/m (Oct)", "0.3%", "0.3%"],
       ["Wed 25", "Core PCE, y/y (Oct)", "3.2%", "3.3%"],
       ["Wed 25", "PCE, y/y (Oct)", "3.8%", "3.8%"],
       ["Wed 25", "GDP, 2nd estimate (Q3), annualised", "3.4-3.5%", "4.3%"],
       ["Wed 25", "Durable goods orders, m/m (Oct)", "0.4-0.6%", "0.2%"],
       ["Wed 25", "Initial jobless claims (week to 21 Nov)", "200k", "189k"],
       ["Wed 25", "Continuing claims", "–", "1.697m"],
       ["Mon 23", "Flash PMI, services (Nov)", "prior 56.1", "54.7"]]
y = table(eco, 36, 418, [60, 240, 85, 85], size=8.8,
          styles=[("TEXTCOLOR", (3, 2), (3, 2), C(RED)), ("TEXTCOLOR", (3, 4), (3, 4), C(GREEN)), ("TEXTCOLOR", (3, 5), (3, 5), C(RED)),
                  ("TEXTCOLOR", (3, 6), (3, 6), C(GREEN))])
text_block(36, y - 8, 470, [
    "<b>Beige Book:</b> 8 of 12 districts grew, 4 were flat; wages rose at a moderate pace (up from modest); prices rose "
    "moderately.",
    "<b>For the Fed:</b> hotter core inflation, faster growth and low layoffs all point to a hike on 9 Dec (94-98% priced); "
    "softer PMIs and the equity rout are the only counterweight.",
])
bar_header(520, 446, 404, "Gold, the real yield and the 2-year yield")
y = image(c_fed, 526, 440, w=392)
text_block(520, y - 6, 404, [
    f"The real 10-yr yield went from {F_['real10']:.2f}% to {WD['real10']:.2f}% this week ({bp(rr_chg)}), lower even "
    "after a hot PCE: the market reads the hike as already in the price.",
    "Gold's fall since October came with real yields near 2.8-2.9%, high for this cycle, but its day-to-day swings "
    "followed stocks more than yields.",
], bg=BOX)

# 7 cycles
new_slide("Gold's past cycles: where 2026 stands",
          "Monthly averages (WGC/LBMA via datahub; Nov 2026 = COMEX month to date). Bear markets by the 20/20 rule. Real rate: 10-yr yield minus CPI (TIPS from 2003). Eight cycles describe, not forecast.")
bar_header(36, 446, 452, "Drawdown after each peak")
y = image(c_cycles, 42, 440, w=440)
bar_header(500, 446, 424, "The peaks compared")
rows = [["Peak", "Rise before", "Fall to low", "Months to low", "Years to regain", "Real rate at peak", "At month 9"]]
for p_ in CY["peaks"]:
    if p_["peak"] == "2026-02":
        continue
    a9 = CY["at9"].get(p_["peak"])
    rows.append([p_["peak"], f"{p_['runup_pct'] * 100:+.0f}%", f"{p_['fall_pct'] * 100:.0f}%", f"{p_['months_to_trough']}",
                 f"{p_['months_to_regain'] / 12:.1f}" if p_.get("months_to_regain") else "–", f"{p_['rr_at_peak']:+.1f}%",
                 f"{a9 * 100:.0f}%" if a9 is not None else "–"])
p26 = [p_ for p_ in CY["peaks"] if p_["peak"] == "2026-02"][0]
rows.append(["<b>2026-02</b>", f"{p26['runup_pct'] * 100:+.0f}%", f"{CY['path26'][-1] * 100:.0f}% so far", "9 so far", "–",
             f"{p26['rr_at_peak']:+.1f}%", f"{CY['path26'][-1] * 100:.0f}%"])
y2 = table(rows, 500, 418, [56, 56, 64, 52, 56, 70, 70], size=7.8,
           styles=[("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), C("#f6ecd2"))])
falls = sorted(p_["fall_pct"] for p_ in CY["peaks"] if p_["peak"] != "2026-02")
text_block(36, min(y, y2) - 8, 888, [
    f"<b>Depth:</b> at month 9, 2026 ({CY['path26'][-1] * 100:.0f}%) is deeper than every past cycle except the 1980-09 peak "
    f"({CY['at9']['1980-09'] * 100:.0f}%). Past falls ended between {falls[-1] * 100:.0f}% and {falls[0] * 100:.0f}% "
    f"(median {np.median(falls) * 100:.0f}%), 4 to 61 months after the peak.",
    f"<b>The backdrop differs:</b> the big peaks of 1974, 1980, 2008 and 2011 came with negative real rates and ended as "
    f"real rates rose. 2026 peaked with real rates already at {p26['rr_at_peak']:+.1f}%, and the fall came with a Fed that "
    "is still hiking. The cycles of 1983, 1987 and 1996, with positive real rates, fell 32-39% and took 8-23 years to regain.",
], bullets=True)

# 8 ETF flows
gl, gm = FL["GLD"], FL["GLDM"]
new_slide("Gold ETF flows",
          "State Street NAV history: flows = change in shares x NAV; tonnes = shares x ounces per share (60-day median of NAV / COMEX). IAU (iShares): price only. GLD's NAV is struck at the LBMA PM price, 10:00 New York.")
bar_header(36, 446, 470, "GLD and GLDM, this week")
rows = [["Fund", "Mon 23", "Tue 24", "Wed 25", "Mon-Wed", "Last week", "Year to date", "Assets"]]
for t in ("GLD", "GLDM"):
    f_ = FL[t]
    dd = [f_["days"].get(k, 0.0) / 1e6 for k in ("2026-11-23", "2026-11-24", "2026-11-25")]
    rows.append([t] + [f"{v:+,.0f}" for v in dd] + [f"{f_['wtd'] / 1e6:+,.0f}", f"{f_['prev'] / 1e6:+,.0f}",
                                                       f"{f_['ytd'] / 1e9:+.1f}bn", f"${f_['aum'] / 1e9:.0f}bn"])
y = table(rows, 36, 418, [50, 55, 55, 55, 62, 62, 70, 61], size=8.8)
cv.setFont("SUI-R", 7)
cv.setFillColor(C(MUTED))
cv.drawString(36, y - 10, "US$ millions unless shown.")
text_block(36, y - 18, 470, [
    f"GLD holdings: {gl['tonnes']:,.0f} t, {gl['tonnes_wtd']:+.1f} t this week and {gl['tonnes_ytd']:+.0f} t this year "
    f"(estimated). GLDM: {gm['tonnes']:,.0f} t, {gm['tonnes_ytd']:+.0f} t this year.",
    f"Selling continued on Monday and Tuesday, into the bounce; Wednesday saw the first inflow ({gl['days']['2026-11-25'] / 1e6:+,.0f}m). "
    f"GLD's NAV fell {ap(gl['nav_wed_chg'])} on Wednesday because the London price was struck near the post-PCE low.",
    f"IAU, the second-largest US gold ETF, moved {pc(WD['IAU'] / F_['IAU'] - 1)} on the week (price only; iShares share "
    "counts were not collected).",
    "Our test of 21 Nov: flows follow the price (H2) and do not predict it (H3). Watch them as a thermometer.",
])
bar_header(520, 446, 404, "Weekly flows since September")
image(c_etf, 526, 440, w=392)

# 9 equity and money flows
new_slide("Equities, sectors and cash: where the money went",
          "Fund flows: State Street NAV history (SPY, XLK, XLU, XLP, BIL to 24 Nov). Money funds: ICI, week to 24 Nov. Prices: Yahoo Finance. Beta: one year of daily returns.")
bar_header(36, 446, 470, "Fund flows, US$ millions")
rows = [["Fund", "What it holds", "Mon 23-Tue 24", "Last week", "Year to date"]]
for t, what in (("SPY", "S&P 500"), ("XLK", "Technology"), ("XLP", "Consumer staples"), ("XLU", "Utilities"), ("BIL", "1-3 month T-bills")):
    f_ = FL[t]
    rows.append([t, what, f"{f_['wtd'] / 1e6:+,.0f}", f"{f_['prev'] / 1e6:+,.0f}", f"{f_['ytd'] / 1e9:+.1f}bn"])
y = table(rows, 36, 418, [50, 130, 100, 90, 100], size=8.8)
text_block(36, y - 8, 470, [
    f"<b>Back into stocks:</b> SPY took in ${FL['SPY']['wtd'] / 1e9:.1f}bn on Monday and Tuesday after "
    f"${abs(FL['SPY']['prev']) / 1e9:.1f}bn left last week; technology (XLK) and staples (XLP) gained, utilities (XLU) lost. "
    "Large SPY creations can also reflect dealer hedging, so read the direction, not the size.",
    f"<b>Cash stays high:</b> money-market funds held ${MMF['total_bn'] / 1000:.2f}tn on {pd.Timestamp(MMF['date']):%d %b} "
    f"(up ${MMF['chg_bn']:.1f}bn on the week and ${MMF['chg4_bn']:.0f}bn over four weeks); T-bill fund BIL added "
    f"${FL['BIL']['wtd'] / 1e6:,.0f}m.",
    f"<b>Gold miners:</b> GDX rose {ap(MI['GDX']['wtd'])} and GDXJ {ap(MI['GDXJ']['wtd'])} while gold rose {ap(G['wtd'])}: "
    f"they traded with stocks. Over a year their beta to gold is {MI['GDX']['beta_1y']:.1f} and {MI['GDXJ']['beta_1y']:.1f}; "
    f"this week's gap is equity risk, not gold.",
])
bar_header(520, 446, 404, "Gold, miners and stocks since 13 Nov")
y = image(c_miners, 526, 440, w=392)
rows = [["", "Fri-Wed", "Year to date", "From 2026 high"],
        ["Gold", pc(G["wtd"]), pc(G["ytd"]), pc(CY["daily_dd"])],
        ["GDX", pc(MI["GDX"]["wtd"]), pc(MI["GDX"]["ytd"]), pc(MI["GDX"]["from_high"])],
        ["GDXJ", pc(MI["GDXJ"]["wtd"]), pc(MI["GDXJ"]["ytd"]), pc(MI["GDXJ"]["from_high"])]]
table(rows, 526, y - 8, [90, 90, 100, 112], size=8.6)

# 10 week in review
new_slide("The week in review", "Settlement and close prices from Yahoo Finance; real yield from the Treasury par real curve. News: CNBC, Jiji/Nation, Kitco, investingLive, BigGo Finance (single source, flagged *).")
rows = [["", "Fri 20", "Mon 23", "Tue 24", "Wed 25", "Fri-Wed"]]
SPEC = [("Gold, COMEX Dec", "GC=F", "${:,.1f}", "pct"), ("Silver", "SI=F", "{:.2f}", "pct"), ("S&P 500", "^GSPC", "{:,.0f}", "pct"),
        ("Nasdaq-100", "^NDX", "{:,.0f}", "pct"), ("Dollar index", "DX-Y.NYB", "{:.2f}", "pct"), ("US 10-yr yield", "^TNX", "{:.2f}%", "bp"),
        ("US 10-yr real yield", "real10", "{:.2f}%", "bp"), ("VIX", "^VIX", "{:.1f}", "pct"), ("Gold miners (GDX)", "GDX", "{:.2f}", "pct")]
for name, t, f_, u in SPEC:
    vv = [d[t] for d in (F_, M_, T_, WD)]
    chg = pc(vv[-1] / vv[0] - 1) if u == "pct" else bp((vv[-1] - vv[0]) * 100)
    rows.append([name] + [f_.format(v) for v in vv] + [chg])
y = table(rows, 36, 470, [170, 110, 110, 110, 110, 100], size=9)
text_block(36, y - 10, 888, [
    f"<b>Monday:</b> gold {pc(m_chg)} to {usd(M_['GC=F'])} on short covering and bargain hunting (Kitco, investingLive), with "
    f"stocks up {ap(M_['^GSPC'] / F_['^GSPC'] - 1)}. Note: our 20 Nov note used a preliminary $3,632; the settlement was "
    f"{usd(M_['GC=F'])}, which lifts Monday's score from the {mon_pub * 100:.1f}th to the {P20['2026-11-23']['pit'] * 100:.1f}th percentile.",
    f"<b>Tuesday:</b> gold {pc(t_chg)} as traders priced the December hike and sold metals to cover losses (Jiji/Nation, CNBC). "
    "Nvidia jumped after its board reinstated Jensen Huang as CEO (BigGo Finance*, which dates it to 24 Nov).",
    f"<b>Wednesday:</b> hot core PCE; gold fell to {usd(INTR['wed_low'])} at 10:15 ET, settled {usd(WD['GC=F'])} at 13:30 and "
    f"reached {usd(INTR['wed_1655'])} by 17:00. Stocks swung too: the Nasdaq fell 4.7% intraday and the Dow erased an "
    "1,100-point drop after S&amp;P put Nvidia's rating on negative watch (BigGo Finance*).",
])

# 11 week ahead
new_slide("The week ahead", "Half-day hours: press reports (stocks 13:00, bonds 14:00 ET). ISM and payrolls: the usual first-business-day and first-Friday slots, to be confirmed on the ISM and BLS calendars. FedWatch via press.")
bar_header(36, 446, 520, "Calendar")
cal = [["Date", "What", "Why it matters"],
       ["Fri 27 Nov", "Half day; the desk logs its weekly forecast at the close", "First regular origin since 20 Nov"],
       ["From Thu 26", "Continuous futures roll to February", f"Feb trades {usd(G['roll_gap'])} above Dec"],
       ["Mon 30 Nov", "CFTC report for 24 Nov (delayed by the holiday)", "How much of the long was sold"],
       ["Tue 1 Dec", "ISM manufacturing (Nov)", "Growth scare or not"],
       ["Fri 4 Dec", "Payrolls (Nov)", "Last big print before the FOMC"],
       ["8-9 Dec", "FOMC: 25 bp hike priced at 94-98%", "Projections for 2027"]]
table(cal, 36, 418, [80, 260, 180], size=9)
bar_header(570, 446, 354, "Things to look out for")
text_block(570, 418, 354, [
    f"<b>The roll:</b> from 26 Nov Yahoo's continuous gold series is the February contract, {usd(G['roll_gap'])} "
    f"({G['roll_gap'] / G['close'] * 100:.1f}%) above December. Friday's weekly change will include it; so will the scores "
    "of the 13 Nov and 30 Oct forecasts due on 30 Nov and 1 Dec. We will flag it.",
    "<b>Friday's 1-day outcome</b> covers Thanksgiving's Globex trading plus a half day: thin markets, wide swings.",
    "<b>Stocks:</b> gold has followed equities for two weeks; an AI-led relapse would test whether forced selling returns.",
    "<b>Positioning:</b> the 24 Nov CFTC report shows whether speculators sold into the crash or into the bounce.",
], bg=BOX, h=300)

# 12 ranges and scorecard
new_slide("Ranges and the scorecard", "Day percentiles: 20,000 paths rebuilt from the stored 20 Nov fit (they reproduce the stored grids to within $0.01). Shadow refit: Wednesday's close, not stored. Touch: a close through the level within 5 trading days.")
bar_header(36, 446, 470, "The 20 Nov forecast, day by day")
rows = [["Day", "Settlement", "90% range that day", "Percentile", "Status"]]
for k_, lab in (("2026-11-23", "Mon 23"), ("2026-11-24", "Tue 24"), ("2026-11-25", "Wed 25")):
    p_ = P20[k_]
    rows.append([lab, usd(p_["close"]), f"{usd(p_['q5'])}-{usd(p_['q95'])}", f"{p_['pit'] * 100:.1f}",
                 "scored (1-day)" if k_ == "2026-11-23" else "information"])
y = table(rows, 36, 418, [60, 80, 130, 80, 120], size=8.8, styles=[("TEXTCOLOR", (3, 1), (3, 1), C(RED))])
text_block(36, y - 8, 470, [
    f"Monday was above the 1-day range (scored at the {P20['2026-11-23']['pit'] * 100:.1f}th percentile with the settlement; "
    f"{mon_pub * 100:.1f} as published). By Wednesday gold was back at the {P20['2026-11-25']['pit'] * 100:.0f}th percentile "
    "of the day-3 distribution: the swings were large, the net move small.",
    "Live record: 4 of 6 scored ranges held. The misses went opposite ways on consecutive days (below 20 Nov, above "
    "23 Nov): ranges too narrow for a liquidation and its reversal, not a biased centre. The 1-week score of 20 Nov is due "
    "on 30 Nov.",
])
bar_header(520, 446, 404, "Shadow refit at Wednesday's close")
rows = [["Horizon", "5%", "25%", "Median", "75%", "95%"]]
for h, lab in (("5", "1 week"), ("21", "1 month")):
    qq = SH["q"][h]
    rows.append([lab] + [usd(qq[q]) for q in ("5", "25", "50", "75", "95")])
y = table(rows, 520, 418, [74, 66, 66, 66, 66, 66], size=8.8)
rows = [["Level", "Chance of a close through it within a week"]]
for lv, note in (("3250.0", "$3,250"), ("3430.0", "$3,430 (press support)"), ("3700.0", "$3,700 (press resistance)"), ("3886.3", "$3,886 (13 Nov close)")):
    rows.append([note, f"{SH['touch_1w'][lv] * 100:.0f}%"])
table(rows, 520, y - 12, [170, 234], size=8.8)

# 13 performance
new_slide("Market performance", "Closes on Wed 25 Nov (US 2-yr yield: FRED, 24 Nov). One month: 21 trading days. Yields in basis points. Gold: COMEX December settlement.")
rows = [["Asset", "Wed close", "Fri 20 to Wed 25", "One month", "Year to date"]]
sty = []
for i_, r_ in enumerate(W_["perf"], start=1):
    if r_.get("unit") == "bp":
        rows.append([r_["asset"], f"{r_['close']:.2f}%", bp(r_["wtd"]), bp(r_["m1"]), bp(r_["ytd"])])
    else:
        cl = f"{r_['close']:,.0f}" if r_["close"] > 500 else f"{r_['close']:,.2f}"
        rows.append([r_["asset"], cl, pc(r_["wtd"]), pc(r_["m1"]), pc(r_["ytd"])])
        for j, v in ((2, r_["wtd"]), (3, r_["m1"]), (4, r_["ytd"])):
            sty.append(("TEXTCOLOR", (j, i_), (j, i_), C(GREEN if v > 0 else RED)))
table(rows, 36, 470, [220, 150, 170, 170, 178], size=9.2, header_bg="#5b3f86", styles=sty)

# 14 attribution
bx = ATT["x"]
new_slide("What moved gold this week (driver model)",
          f"Betas: 156 weeks to 20 Nov ({ATT['window'][0]} to {ATT['window'][1]}), without positioning (no CFTC report for 23-25 Nov) and without the intercept. Real yield on 25 Nov from the Treasury par real curve. *Flows follow the price (H2): not a cause.")
bar_header(36, 446, 470, "Friday 20 to Wednesday 25 November")
y = image(c_attr, 42, 440, w=458)
text_block(36, y - 8, 470, [
    f"Unexplained: {ATT['residual'] * 100:+.2f} points of {ATT['r_gold'] * 100:+.2f}. Stocks ({cg['r_spx'] * 100:+.2f}) and the "
    f"VIX ({cg['d_vix'] * 100:+.2f}) did most of the work: gold rose with equities and fell back as stress eased.",
])
bar_header(520, 446, 404, "How to read it")
text_block(520, 438, 404, [
    "Weekly betas applied to three days: a rough split. Out of sample the model explains 27% of weekly moves since 2009 "
    "and 15% in 2026, less over three days.",
    "Gold settles at 13:30 ET, stocks close at 16:00: Wednesday's late recovery in gold is outside its settlement, the "
    "stock moves are inside.",
    f"The stock beta ({ATT['betas']['r_spx']:.2f}) now includes last week's crash, when gold and stocks fell together; "
    "before it the link was weaker. A higher stock beta is itself the sign of a market where gold is a source of cash.",
    f"The flow bar ({cg['flow'] * 100:+.2f}) has the largest beta ({ATT['betas']['flow']:.2f}), but flows follow the price; "
    "read it as part of the move, not its cause.",
], bg=BOX)

# 15 positioning and volatility
new_slide("Positioning and volatility", "CFTC Commitments of Traders, disaggregated, futures only, contracts x 100 oz. GVZ: CBOE gold ETF volatility index. Realised: daily COMEX returns.")
bar_header(36, 446, 440, "COMEX positioning (latest report: 17 Nov)")
rows = [["Measure", "17 Nov", "10 Nov"],
        ["Managed money net long", f"{COT['mm_t']:,.0f} t", f"{COT['mm_t_prev']:,.0f} t"],
        ["Net long, share of open interest", f"{COT['share'] * 100:.0f}%", f"{COT['share_prev'] * 100:.0f}%"],
        ["Percentile since 2006", nth(COT["share_pct"]), "–"]]
y = table(rows, 36, 418, [220, 110, 110], size=9)
text_block(36, y - 8, 440, [
    "The 24 Nov report, the first to cover the crash days of 18-20 Nov and Monday's bounce, is delayed by Thanksgiving.",
    "At 25% of open interest the speculative long is mid-range: there is still room to sell if forced selling returns.",
])
bar_header(484, 446, 440, "Volatility")
rows = [["Measure", "Level", "Note"],
        ["GVZ, 30-day implied", f"{VOL['gvz']:.1f}", f"Fri 20 Nov: {VOL['gvz_fri']:.1f}"],
        ["Realised, 21 days", f"{VOL['rv21'] * 100:.1f}%", "Daily settlements"],
        ["Desk model, next day (shadow)", f"{SH['vol_next'] * 100:.1f}%", f"20 Nov: {SH['vol_next_20nov'] * 100:.1f}%"],
        ["VIX", f"{VOL['vix']:.1f}", f"Fri 20 Nov: {F_['^VIX']:.1f}"]]
y = table(rows, 484, 418, [170, 100, 170], size=9)
image(c_vol, 490, y - 10, w=428)

# 16 method and sources
new_slide("Method, checks and sources", "")
text_block(36, 470, 888, [
    "<b>Data:</b> Yahoo Finance daily closes to Wed 25 Nov (COMEX December gold, checked against the contract itself; the "
    "Thanksgiving bar of 26 Nov is dropped), 5-minute futures, FRED, the Treasury par real yield curve for 25 Nov, CFTC "
    "(17 Nov), State Street fund files (GLD, GLDM, SPY, XLK, XLU, XLP, BIL), ICI money funds (24 Nov).",
    "<b>Model:</b> the 20 Nov live forecast (GARCH(1,1), Student-t, zero drift, 20,000 paths) is rebuilt from its stored "
    "fit to place each day; only the 1-day outcome is a score. The Wednesday refit is a shadow and is not stored "
    "(checks.json holds a hash of store/live.jsonl before and after). The weekly record is Friday's close.",
    "<b>Tests quoted:</b> H1 decoupling from real yields (confirmed), H2 procyclical ETF flows (confirmed), H3 positioning "
    "and flows as predictors (failed), all pre-registered on 21 Nov (commit 0a7239c); spring H4-H6 (failed), "
    "pre-registered on 23 Nov (commit 59b21e2). Cycles: the 19 Nov note, November updated to 25 Nov.",
    f"<b>Checks:</b> {sum(c['result'] == 'PASS' for c in CHECKS)} of {len(CHECKS)} passed (checks.json), including the "
    "contract check, the real-yield cross-check against FRED, GLD against COMEX, ICI totals, the rebuilt forecast grids "
    "and the unchanged forecast store.",
    "<b>News:</b> CNBC (PCE, Fed minutes, Waller, gold on 24 Nov), Morningstar, Advisor Perspectives and FXStreet (PCE), "
    "BEA and The Boston Report (GDP), TMGM and The Edge (durable goods, claims), Minneapolis Fed and investingLive (Beige "
    "Book), Jiji/Nation (24 Nov), Kitco and investingLive (23 Nov), World Gold Council (Q3 2026), Yahoo Finance (bank "
    "forecasts, one source), bifu.co (23 Nov), BigGo Finance (Nvidia, single source), CME FedWatch via press.",
])
cv.save()
print("wrote", out_pdf, "pages", page[0])
