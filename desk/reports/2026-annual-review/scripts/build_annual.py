"""Gold Desk Annual Review 2026 (year to 20 Nov): portrait report, layout modelled on a long-form annual gold
report; own branding. Reads the weekly snapshot (../2026-11-20-weekly/data), the driver results and earlier desk
results. Writes annual.json and the PDF.

Usage (from desk/): python reports/2026-annual-review/scripts/build_annual.py reports/2026-annual-review
"""
import json
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
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,  # noqa: E402
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

N = Path(sys.argv[1])
REP = N.parent
WK = REP / "2026-11-20-weekly"
D = WK / "data"
DESK = REP.parent
sys.path.insert(0, str(DESK))
from gold_desk.model import fit  # noqa: E402

FRI, YEND = pd.Timestamp("2026-11-20"), pd.Timestamp("2025-12-31")
OZ_PER_T = 32150.7466
NAVY, GOLDH, BG, NOTE, INK, INK2, MUTED, GRID = "#2e3f6e", "#c2a467", "#e7f1f8", "#2b8fc4", "#1d1d1b", "#4a4a48", "#8a8a86", "#dfe5ea"
BLUE, YEL, ORANGE, AQUA, NEUTRAL = "#2a78d6", "#eda100", "#eb6834", "#1baf7a", "#b5b3ad"

daily = pd.read_csv(D / "daily.csv", index_col=0, parse_dates=True)
daily = daily[daily.index <= FRI]
fred = pd.read_csv(D / "fred.csv", index_col=0, parse_dates=True)
DRV = json.load(open(WK / "drivers.json"))
WEEK = json.load(open(WK / "week.json"))
R20 = json.load(open(REP / "2026-11-20" / "results.json"))
CYC = json.load(open(REP / "2026-11-19-cycles" / "cycles.json"))
gold = daily["GC=F"].dropna()
g26 = gold.loc["2026-01-01":]


def ser(t):
    return (fred[t] if t in fred else daily[t]).dropna()


# ------------------------------------------------------------------ numbers
peak, peak_d = float(gold.max()), gold.idxmax()
ye = float(gold.loc[:YEND].iloc[-1])
ath_2026 = int((gold.loc["2026-01-01":] >= gold.cummax().loc["2026-01-01":]).sum())
mar = float(gold.loc[:"2026-03-31"].iloc[-1] - gold.loc[:"2026-02-28"].iloc[-1])
mar_low = float(gold.loc["2026-03-01":"2026-04-30"].min())
summer = gold.loc["2026-05-20":"2026-08-31"]
fx = {"US dollar": gold, "Euro": gold / ser("EURUSD=X"), "British pound": gold / ser("GBPUSD=X"),
      "Swiss franc": gold * ser("CHF=X"), "Japanese yen": gold * ser("JPY=X"), "Chinese yuan": gold * ser("CNY=X"),
      "Indian rupee": gold * ser("INR=X")}
ccy = []
for k, s in fx.items():
    s = s.dropna()
    ccy.append({"ccy": k, "ytd": float(s.iloc[-1] / s.loc[:YEND].iloc[-1] - 1),
                "from_peak": float(s.iloc[-1] / s.loc["2026"].max() - 1), "y2025": float(s.loc[:YEND].iloc[-1] / s.loc[:"2024-12-31"].iloc[-1] - 1)})
silver = ser("SI=F")
gsr = (gold / silver).dropna()
spx = ser("^GSPC")
spx_gold = (spx / gold).dropna()
real, be, cpi = ser("DFII10"), ser("T10YIE"), ser("CPIAUCSL")
cpi = np.exp(np.log(cpi).reindex(pd.date_range(cpi.index[0], cpi.index[-1], freq="MS")).interpolate(limit_area="inside"))
dxy = ser("DX-Y.NYB")
debt = ser("GFDEGDQ188S")
# GLD flows and tonnes (shares x ounces per share)
g = pd.read_excel(D / "ssga_navhist_GLD.xlsx", header=None, engine="openpyxl")
s0 = g.index[g[0].astype(str).str.strip() == "Date"][0] + 1
g = g.iloc[s0:, :3]
g.columns = ["date", "nav", "shares"]
g["date"] = pd.to_datetime(g["date"], format="%d-%b-%Y", errors="coerce")
g[["nav", "shares"]] = g[["nav", "shares"]].apply(pd.to_numeric, errors="coerce")
g = g.dropna().set_index("date").sort_index()
g["flow"] = g.shares.diff() * g.nav
ozs = (g.nav / gold.reindex(g.index, method="ffill")).rolling(60, min_periods=20).median()
g["tonnes"] = g.shares * ozs / OZ_PER_T
gld_2026 = g.loc["2026-01-01":]
gld_cum = gld_2026.flow.cumsum() / 1e9
gld_peak_t = float(g.tonnes.loc["2026-01-01":].max())
c = pd.read_csv(D / "cftc_gold_full.csv")
cot = pd.DataFrame({"mm": (pd.to_numeric(c.m_money_positions_long_all) - pd.to_numeric(c.m_money_positions_short_all)).values * 100 / OZ_PER_T,
                    "share": ((pd.to_numeric(c.m_money_positions_long_all) - pd.to_numeric(c.m_money_positions_short_all)) / pd.to_numeric(c.open_interest_all)).values},
                   index=pd.to_datetime(c.report_date_as_yyyy_mm_dd).values)
cot26 = cot.loc["2025-12-01":]
f_now = fit(gold)
r = np.log(gold).diff().dropna()
from arch import arch_model  # noqa: E402
res = arch_model(r * 100, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(disp="off", show_warning=False)
cvol = (res.conditional_volatility / 100 * np.sqrt(252)).loc["2025-01-01":]

A = {"close": float(gold.iloc[-1]), "ytd": float(gold.iloc[-1] / ye - 1), "y2025": float(ye / gold.loc[:"2024-12-31"].iloc[-1] - 1),
     "peak": peak, "peak_date": str(peak_d.date()), "from_peak": float(gold.iloc[-1] / peak - 1), "ath_2026": ath_2026,
     "march_change": mar, "spring_low": mar_low, "summer_lo": float(summer.min()), "summer_hi": float(summer.max()),
     "gsr_now": float(gsr.iloc[-1]), "gsr_2026_low": float(gsr.loc["2026"].min()), "gsr_low_date": str(gsr.loc["2026"].idxmin().date()),
     "spx_gold_now": float(spx_gold.iloc[-1]), "spx_gold_ye": float(spx_gold.loc[:YEND].iloc[-1]),
     "real_now": float(real.iloc[-1]), "real_ye": float(real.loc[:YEND].iloc[-1]), "be_now": float(be.iloc[-1]), "be_ye": float(be.loc[:YEND].iloc[-1]),
     "cpi_yoy": float(cpi.iloc[-1] / cpi.iloc[-13] - 1), "cpi_ye": float(cpi.loc[:"2025-12-01"].iloc[-1] / cpi.loc[:"2024-12-01"].iloc[-1] - 1),
     "dxy_ytd": float(dxy.iloc[-1] / dxy.loc[:YEND].iloc[-1] - 1), "fed_upper": float(ser("DFEDTARU").iloc[-1]),
     "debt_gdp": float(debt.iloc[-1]), "debt_date": str(debt.index[-1].date()),
     "gld_flow_bn": float(gld_cum.iloc[-1]), "gld_t_now": float(g.tonnes.iloc[-1]), "gld_t_ye": float(g.tonnes.loc[:YEND].iloc[-1]),
     "gld_t_peak": gld_peak_t, "mm_now": float(cot.mm.iloc[-1]), "mm_ye": float(cot.mm.loc[:YEND].iloc[-1]),
     "mm_peak26": float(cot.mm.loc["2026"].max()), "mm_peak_date": str(cot.mm.loc["2026"].idxmax().date()),
     "share_now": float(cot.share.iloc[-1]), "share_pct": float((cot.share < cot.share.iloc[-1]).mean()),
     "vol_now": f_now.vol_next, "vol_max26": float(cvol.loc["2026"].max()), "vol_max_date": str(cvol.loc["2026"].idxmax().date()),
     "ccy": ccy, "gvz": WEEK["vol"]["gvz"]}
ev = pd.DataFrame(DRV["events"])
ev_done = ev.dropna(subset=["fwd13"])
A["events"] = {"n": len(ev_done), "pos13": int((ev_done.fwd13 > 0).sum()), "mean13": float(ev_done.fwd13.mean()),
               "neg4": int((ev_done.fwd4 < 0).sum()), "mean4": float(ev_done.fwd4.mean()), "all13": DRV["events_all_weeks"]["13"]}
(N / "annual.json").write_text(json.dumps(A, indent=1, default=float), encoding="utf-8")

# ------------------------------------------------------------------ charts
for fp in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 8.6, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e6e6e2", "grid.linewidth": 0.6,
                     "legend.frameon": False, "legend.fontsize": 8})
CH = N / "_charts"
CH.mkdir(exist_ok=True)
usd = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")


def save(fig, name):
    p = CH / f"{name}.png"
    fig.savefig(p, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(p)


# 1 gold 2024-2026 with drawdown levels from the record
fig, ax = plt.subplots(figsize=(6.6, 3.0))
gp = gold.loc["2024-01-01":]
ax.plot(gp.index, gp.values, color=NAVY, lw=1.3)
for k in (0.05, 0.10, 0.20, 0.30):
    lvl = peak * (1 - k)
    ax.axhline(lvl, color=MUTED, lw=0.6, ls=(0, (3, 2)))
    ax.text(gp.index[0], lvl, f" {lvl:,.0f} (-{k:.0%})", fontsize=7, color=INK2, va="bottom")
ax.scatter([peak_d, gp.index[-1]], [peak, gp.iloc[-1]], s=18, color=[NAVY, ORANGE], zorder=4)
ax.annotate(f"{gp.iloc[-1]:,.0f}", (gp.index[-1], gp.iloc[-1]), xytext=(4, -2), textcoords="offset points", fontsize=7.5)
ax.yaxis.set_major_formatter(usd)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
c_gold = save(fig, "gold")

# 2 ratios: S&P/gold and gold/silver since 2000 (two panels)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 2.5))
sg = spx_gold.resample("ME").last().loc["2000":]
a1.plot(sg.index, sg.values, color=NAVY, lw=1.2)
a1.axhline(sg.median(), color=MUTED, lw=0.7, ls=(0, (3, 2)))
a1.text(sg.index[0], sg.median(), f" median {sg.median():.2f}", fontsize=7, color=INK2, va="bottom")
a1.set_title("S&P 500 / gold", fontsize=8.6, color=INK2, loc="left")
gs = gsr.resample("ME").last().loc["2000":]
a2.plot(gs.index, gs.values, color=NAVY, lw=1.2)
a2.axhline(gs.median(), color=MUTED, lw=0.7, ls=(0, (3, 2)))
a2.text(gs.index[0], gs.median(), f" median {gs.median():.0f}", fontsize=7, color=INK2, va="bottom")
a2.set_title("Gold / silver", fontsize=8.6, color=INK2, loc="left")
for a in (a1, a2):
    a.xaxis.set_major_locator(mdates.YearLocator(10))
    a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
c_ratio = save(fig, "ratios")

# 3 macro: real yield and breakeven (one panel), dollar (second panel)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.8, 3.3), sharex=True)
rr, bb = real.loc["2024-01-01":], be.loc["2024-01-01":]
a1.plot(rr.index, rr.values, color=BLUE, lw=1.3, label="10-year real yield (TIPS)")
a1.plot(bb.index, bb.values, color=YEL, lw=1.3, label="10-year breakeven inflation")
a1.set_ylabel("%")
a1.legend(loc="upper left", ncol=2)
dd = dxy.loc["2024-01-01":]
a2.plot(dd.index, dd.values, color=NAVY, lw=1.2)
a2.set_ylabel("Dollar index")
a2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
c_macro = save(fig, "macro")

# 4 flows and positioning in 2026 (two panels, tonnes)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 2.5))
gt = g.tonnes.loc["2025-10-01":]
a1.plot(gt.index, gt.values, color=NAVY, lw=1.3)
a1.set_title("GLD holdings, tonnes", fontsize=8.6, color=INK2, loc="left")
a2.bar(cot26.index, cot26.mm, width=5, color=BLUE)
a2.set_title("COMEX managed-money net long, tonnes", fontsize=8.6, color=INK2, loc="left")
for a in (a1, a2):
    a.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    a.tick_params(axis="x", labelsize=7)
c_flows = save(fig, "flows")

# 5 sell-offs compared: indexed paths
starts = [("2008-07-15", "Jul 2008 (Lehman)", BLUE), ("2020-03-06", "Mar 2020 (Covid)", AQUA), (str(peak_d.date()), "Jan 2026 (record)", ORANGE)]
fig, ax = plt.subplots(figsize=(6.6, 2.9))
for st_, lab, col in starts:
    s = gold.loc[st_:].iloc[:260]
    ax.plot(np.arange(len(s)), 100 * s.values / s.iloc[0], color=col, lw=1.6 if "2026" in lab else 1.2, label=lab)
ax.axhline(100, color="#c3c2b7", lw=0.7)
ax.set_xlabel("Trading days after the high")
ax.set_ylabel("High = 100")
ax.legend(loc="upper left")
c_sell = save(fig, "selloffs")

# 6 monthly attribution 2026
GROUPS = [("Rates and inflation", ["d_real", "d_be"], BLUE), ("Dollar", ["r_dxy"], ORANGE), ("Stress (VIX)", ["d_vix"], AQUA),
          ("US stocks", ["r_spx"], YEL), ("Oil", ["r_oil"], "#6250d6"), ("Positioning and flows", ["d_mm", "flow"], "#e87ba4"),
          ("Trend (past 3 years)", ["alpha"], "#3c3c3a"), ("Unexplained", ["residual"], NEUTRAL)]
mon = DRV["monthly"]
months = list(mon)
fig, ax = plt.subplots(figsize=(6.8, 2.5))
xs = np.arange(len(months))
pb, nb = np.zeros(len(months)), np.zeros(len(months))
for gname, ks, col in GROUPS:
    v = np.array([sum(mon[m].get(k, 0.0) for k in ks) * 100 for m in months])
    ax.bar(xs, np.where(v > 0, v, 0), bottom=pb, color=col, width=0.66, label=gname)
    ax.bar(xs, np.where(v < 0, v, 0), bottom=nb, color=col, width=0.66)
    pb += np.where(v > 0, v, 0)
    nb += np.where(v < 0, v, 0)
ax.plot(xs, [mon[m]["r_gold"] * 100 for m in months], color="#8a6d1f", lw=1.5, marker="o", ms=3.5, label="Gold return")
ax.axhline(0, color="#c3c2b7", lw=0.7)
ax.set_xticks(xs)
ax.set_xticklabels([pd.Period(m).strftime("%b") for m in months])
ax.set_ylabel("% points (log)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=5, fontsize=7)
c_attr = save(fig, "attribution")

# 7 rolling 52-week correlation of gold with real yields and the dollar
rl = DRV["rolling"]
rd = pd.to_datetime(rl["dates"])
fig, ax = plt.subplots(figsize=(6.8, 1.75))
ax.plot(rd, rl["corr_real"], color=BLUE, lw=1.3, label="with weekly change in the TIPS yield")
ax.plot(rd, rl["corr_dxy"], color=YEL, lw=1.3, label="with the dollar index")
ax.axhline(0, color="#c3c2b7", lw=0.8)
ax.axvline(pd.Timestamp("2022-03-01"), color=MUTED, lw=0.6, ls=":")
ax.text(pd.Timestamp("2022-03-01"), 0.2, " Mar 2022", fontsize=7, color=MUTED)
ax.set_ylabel("Correlation, 52 weeks")
ax.legend(loc="lower left", ncol=2, fontsize=7.4)
c_corr = save(fig, "corr")

# 8 model volatility 2025-2026
fig, ax = plt.subplots(figsize=(6.6, 2.4))
ax.plot(cvol.index, cvol.values * 100, color=NAVY, lw=1.2)
ax.set_ylabel("Model volatility, %")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
c_vol = save(fig, "vol")

# 9 cover image
fig, ax = plt.subplots(figsize=(6.0, 3.4))
gg = gold.loc["2020-01-01":].resample("W-FRI").last()
ax.fill_between(gg.index, gg.min() * 0.9, gg.values, color="#3d5288", lw=0)
ax.plot(gg.index, gg.values, color="#d9b863", lw=2.4)
ax.axis("off")
fig.patch.set_facecolor(NAVY)
c_cover = str(CH / "cover.png")
fig.savefig(c_cover, dpi=200, bbox_inches="tight", facecolor=NAVY)
plt.close(fig)

# ------------------------------------------------------------------ PDF
for nm, f_ in (("G", "georgia.ttf"), ("G-B", "georgiab.ttf"), ("G-I", "georgiai.ttf"), ("G-BI", "georgiaz.ttf"),
               ("S", "segoeui.ttf"), ("S-B", "segoeuib.ttf")):
    pdfmetrics.registerFont(TTFont(nm, f"C:/Windows/Fonts/{f_}"))
registerFontFamily("G", normal="G", bold="G-B", italic="G-I", boldItalic="G-BI")
registerFontFamily("S", normal="S", bold="S-B", italic="S", boldItalic="S-B")
W, H = A4
M = 50
CW = W - 2 * M
C = colors.HexColor
ps = lambda n, **k: ParagraphStyle(n, **{"fontName": "G", "fontSize": 9.3, "leading": 13.2, "textColor": C(INK), **k})  # noqa: E731
S = {"h1": ps("h1", fontName="S-B", fontSize=26, leading=30, textColor=C(NAVY), spaceAfter=10),
     "h2": ps("h2", fontName="S-B", fontSize=14, leading=18, textColor=C(NAVY), spaceBefore=10, spaceAfter=6),
     "body": ps("body", alignment=4, spaceAfter=7), "note": ps("note", fontName="G-BI", fontSize=10.5, leading=14, textColor=C(NOTE)),
     "notesrc": ps("ns", fontName="S", fontSize=7, leading=9, textColor=C(INK2)),
     "kt": ps("kt", fontName="S", fontSize=9, leading=12.6, leftIndent=10, bulletIndent=0, spaceAfter=5, textColor=C(NAVY)),
     "cell": ps("c", fontName="S", fontSize=8, leading=10), "cellb": ps("cb", fontName="S-B", fontSize=8, leading=10),
     "ct": ps("ct", fontName="S-B", fontSize=10, leading=13, textColor=C(NAVY)), "cs": ps("cs", fontName="S", fontSize=6.8, leading=8.5, textColor=C(INK2)),
     "bul": ps("bul", leftIndent=10, bulletIndent=0, spaceAfter=4, alignment=4)}


def on_page(cv, doc):
    cv.saveState()
    cv.setFillColor(C(BG))
    cv.rect(0, 0, W, H, stroke=0, fill=1)
    cv.setFillColor(C(NAVY))
    cv.setFont("S-B", 11)
    pn = doc.page
    if pn % 2 == 0:
        cv.drawString(M, H - 38, str(pn))
        cv.setFont("S-B", 7.5)
        cv.drawRightString(M + 300, H - 38, "The Year Gold Was Tested")
        cv.line(M, H - 46, M + 300, H - 46)
    else:
        cv.drawRightString(W - M - 44, H - 38, str(pn))
        cv.setFont("S-B", 7.5)
        cv.drawString(W - M - 300, H - 38, "Gold Desk Annual Review 2026")
        cv.line(W - M - 300, H - 46, W - M - 40, H - 46)
    cv.setFillColor(C(GOLDH))
    cv.rect(W - M - 34, H - 58, 34, 34, stroke=0, fill=1)
    cv.setFillColor(colors.white)
    cv.setFont("S-B", 8)
    cv.drawCentredString(W - M - 17, H - 39, "GOLD")
    cv.drawCentredString(W - M - 17, H - 49, "DESK")
    cv.setStrokeColor(C(NAVY))
    cv.setLineWidth(0.6)
    cv.line(M, 40, W - M, 40)
    cv.restoreState()


def on_cover(cv, doc):
    cv.saveState()
    cv.setFillColor(C(NAVY))
    cv.rect(0, 0, W, H, stroke=0, fill=1)
    cv.drawImage(c_cover, 0, 300, W, W * 0.56)
    cv.setFillColor(C(GOLDH))
    cv.rect(W - 170, H - 120, 120, 70, stroke=0, fill=1)
    cv.setFillColor(colors.white)
    cv.setFont("S-B", 22)
    cv.drawCentredString(W - 110, H - 88, "GOLD DESK")
    cv.setFont("S", 10)
    cv.drawCentredString(W - 110, H - 106, "Annual Review")
    cv.setStrokeColor(C(GOLDH))
    cv.roundRect(50, H - 150, 210, 100, 8, stroke=1, fill=0)
    cv.setFont("S-B", 13)
    cv.drawString(64, H - 76, "Year to 20 November 2026")
    cv.setFont("S", 8.5)
    cv.drawString(64, H - 96, "Full-year edition after the 31 December")
    cv.drawString(64, H - 108, "close. Prices: COMEX gold futures, USD/oz.")
    cv.setFont("S-B", 52)
    cv.drawString(50, 230, "The Year")
    cv.drawString(50, 172, "Gold Was")
    cv.setFillColor(C(GOLDH))
    cv.drawString(50, 114, "Tested")
    cv.setFillColor(colors.white)
    cv.setFont("S", 10)
    cv.drawString(50, 64, "Gold Desk  |  2026 review of price, macro, flows, positioning and the drivers behind them")
    cv.restoreState()


doc = BaseDocTemplate(str(N / "gold_annual_review_2026.pdf"), pagesize=A4, leftMargin=M, rightMargin=M, topMargin=70, bottomMargin=55,
                      title="Gold Desk Annual Review 2026", author="Nikolay Gelshtein")
fr_ = Frame(M, 55, CW, H - 125, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="cover", frames=[fr_], onPage=on_cover), PageTemplate(id="page", frames=[fr_], onPage=on_page)])


def chart(path, title, source, width=CW):
    iw, ih = ImageReader(path).getSize()
    inner = width - 24
    t = Table([[Paragraph(title, S["ct"])], [Image(path, width=inner, height=inner * ih / iw)], [Paragraph(f"Source: {source}", S["cs"])]],
              colWidths=[width])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                           ("TOPPADDING", (0, 0), (0, 0), 10), ("BOTTOMPADDING", (0, -1), (-1, -1), 9)]))
    return KeepTogether([t, Spacer(1, 10)])


def with_note(note, body_flow, src=None):
    left = [Paragraph(f"\u201d {note}", S["note"])] + ([Paragraph(src, S["notesrc"])] if src else [])
    t = Table([[left, body_flow]], colWidths=[130, CW - 140])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (0, 0), 10), ("RIGHTPADDING", (1, 0), (1, 0), 0)]))
    return t


def table(rows, widths, header=NAVY, size=8):
    cs = ps("tc", fontName="S", fontSize=size, leading=size + 2.3)
    cb = ps("tb", fontName="S-B", fontSize=size, leading=size + 2.3, textColor=colors.white)
    cf = ps("tf", fontName="S-B", fontSize=size, leading=size + 2.3)
    data = [[Paragraph(str(v), cb) for v in rows[0]]] + [[Paragraph(str(v), cf if j == 0 else cs) for j, v in enumerate(r_)] for r_ in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), C(header)), ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                           ("LINEBELOW", (0, 1), (-1, -1), 0.3, C(GRID)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    return t


def takeaways(items):
    t = Table([[Paragraph("Key Takeaways", S["h2"])]] + [[Paragraph(x, S["kt"], bulletText="\u25aa")] for x in items], colWidths=[CW])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.8, C(NAVY)), ("LINEBELOW", (0, -1), (-1, -1), 0.8, C(NAVY)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1)]))
    return t


pc = lambda v, d=1: f"{v * 100:+.{d}f}%"  # noqa: E731


def nth(q):
    n_ = int(round(q * 100))
    return f"{n_}{'th' if 10 <= n_ % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n_ % 10, 'th')}"


P = lambda t: Paragraph(t, S["body"])  # noqa: E731
H1 = DRV["h1"]
H2 = DRV["h2"]
H3 = DRV["h3"]
E = A["events"]
ytd_attr = DRV["ytd"]
cov = pd.DataFrame(R20["coverage"])
c5 = cov[(cov.window == "All history") & (cov.h == 5)].iloc[0]
c21l = cov[(cov.window == "Last 52 weeks") & (cov.h == 21)].iloc[0]

story = [NextPageTemplate("page"), PageBreak()]
# contents
story += [Paragraph("Contents", S["h1"]), Spacer(1, 8)]
toc = [("1", "Introduction: the year gold was tested"), ("2", "The status quo of gold"), ("3", "Gold relative to stocks, silver and commodities"),
       ("4", "The macro backdrop: rates, inflation, the dollar, debt"), ("5", "Demand, flows and positioning"),
       ("6", "Two sell-offs: March and November, against 2008 and 2020"), ("7", "What drives gold: the desk's driver model"),
       ("8", "The In Gold We Trust 2026 theses, checked against the data"), ("9", "The desk model's year"), ("10", "Outlook: what would decide 2027"),
       ("11", "Method and sources")]
pages_ = ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
story.append(table([["", "Chapter", "Page"]] + [[a, b, pg] for (a, b), pg in zip(toc, pages_)], [40, CW - 100, 60], size=10.5))
story.append(Spacer(1, 16))
story.append(P("This review covers 2026 to the close of Friday 20 November. It follows the structure of long-form annual gold reports, "
               "but every number comes from the desk's own data snapshot and every claim from an outside source is attributed. "
               "A full-year update follows after the 31 December close."))
story.append(PageBreak())

# 1 introduction
story += [Paragraph("Introduction: the Year Gold Was Tested", S["h1"]), takeaways([
    f"Gold set {A['ath_2026']} record closes in January 2026, peaking at ${peak:,.0f} on {peak_d:%d %B}, then fell {abs(A['from_peak']):.0%} to "
    f"${A['close']:,.0f} by 20 November: {pc(A['ytd'])} for the year after {pc(A['y2025'], 0)} in 2025.",
    "The year had two sell-offs. March was an oil-and-rates shock that pulled gold down with everything else; November was a rate shock "
    "that turned into forced selling, with gold falling alongside stocks and bitcoin.",
    f"Real yields drove the year: the 10-year TIPS yield rose from {A['real_ye']:.2f}% to {A['real_now']:.2f}% as inflation reaccelerated to "
    f"{A['cpi_yoy']:.1%} and the Fed moved toward hikes. The dollar gained {pc(A['dxy_ytd'])}.",
    f"Tested against the data, two In Gold We Trust theses hold: gold's link to real yields has weakened (by about half since 2022), and "
    "Western ETF investors trade procyclically. Neither positioning nor ETF flows predicted the next month's move.",
    f"The desk's driver model explains {DRV['explained_oos']:.0%} of weekly moves since 2009 but only {DRV['explained_2026']:.0%} in 2026: "
    "this year's gold market was driven by a structural bid and its unwind, which the classic drivers do not capture.",
]), Spacer(1, 10)]
story.append(with_note(f"Gold fell {abs(A['from_peak']):.0%} from its record in under ten months, after rising more than 200% in the three years before.",
                       [P("In January the debate was about how high gold could go; by November it was about how far it could fall. "
                          "The record of 29 January capped a rise that had been carried by central-bank buying and strong ETF demand, and "
                          "that had continued even as real interest rates rose. That decoupling, celebrated as a new regime, did not stop "
                          "gold from falling once rates rose further and investors needed cash."),
                        P("This review asks what actually moved gold in 2026, and which of the year's big theses survive contact with the "
                          "data. It uses the desk's GARCH model for the size of moves, a new driver model for their causes, and three "
                          "tests fixed before they were run.")]))
story.append(PageBreak())

# 2 status quo
story += [Paragraph("The Status Quo of Gold", S["h1"]),
          chart(c_gold, "Gold, in USD, and drawdown levels from the 2026 record, 01/2024-11/2026", "Yahoo Finance (COMEX front-month futures), Gold Desk")]
rows = [["Gold in", "2025", "2026 to 20 Nov", "From the 2026 high"]]
for r_ in ccy:
    rows.append([r_["ccy"], pc(r_["y2025"]), pc(r_["ytd"]), pc(r_["from_peak"])])
gave_back = (ye - A["close"]) / (ye - float(gold.loc[:"2024-12-31"].iloc[-1]))
story.append(with_note(f"In March gold fell ${abs(A['march_change']):,.0f} in one month; by 20 November it had given back {gave_back:.0%} of 2025's gain.",
                       [table(rows, [130, 70, 95, 100], size=8.6), Spacer(1, 6),
                        P(f"Gold lost ground in every major currency in 2026, least in those that weakened against the dollar. The March "
                          f"sell-off took it to ${A['spring_low']:,.0f} by April; from late May to August it traded between ${A['summer_lo']:,.0f} and "
                          f"${A['summer_hi']:,.0f}, before the autumn's rate shock broke the range.")]))
story.append(PageBreak())

# 3 relative
story += [Paragraph("Gold Relative to Stocks, Silver and Commodities", S["h1"]),
          chart(c_ratio, "S&amp;P 500 / gold ratio and gold / silver ratio, monthly, 01/2000-11/2026", "Yahoo Finance, Gold Desk")]
story.append(with_note(f"The gold/silver ratio went from {A['gsr_2026_low']:.0f} in {pd.Timestamp(A['gsr_low_date']):%B} to {A['gsr_now']:.0f}: silver fell far harder than gold.",
                       [P(f"The S&amp;P 500 / gold ratio stands at {A['spx_gold_now']:.2f}, up from {A['spx_gold_ye']:.2f} at the end of 2025: "
                          "gold gave back part of its long outperformance against US stocks, even as stocks themselves fell sharply in November."),
                        P(f"Silver, the high-beta sister metal, magnified every move. The gold/silver ratio fell to {A['gsr_2026_low']:.0f} at "
                          f"silver's January peak and has since risen to {A['gsr_now']:.0f}, above its long-run median. Commodities more "
                          "broadly were held up by oil, which stayed elevated after the spring's Middle East shock.")]))
story.append(PageBreak())

# 4 macro
story += [Paragraph("The Macro Backdrop", S["h1"]),
          chart(c_macro, "US 10-year real yield and breakeven inflation (%), and the dollar index, 01/2024-11/2026", "FRED, Yahoo Finance")]
story.append(with_note(f"The 10-year real yield rose {A['real_now'] - A['real_ye']:+.2f} points in 2026, to its highest outside this year since 2008.",
                       [P(f"Inflation reaccelerated: CPI rose {A['cpi_yoy']:.1%} over the twelve months to October, against {A['cpi_ye']:.1%} a year "
                          f"earlier, pushed by the energy shock. The Fed's target range is {A['fed_upper'] - 0.25:.2f}-{A['fed_upper']:.2f}%, and by "
                          "November futures priced a December hike at above 95% (CME FedWatch, as reported)."),
                        P(f"Markets did not price lasting inflation: breakevens ended near {A['be_now']:.2f}%, so the rise in nominal yields came "
                          f"through real yields, the variable that costs gold most. The dollar gained {pc(A['dxy_ytd'])}. Federal debt stood at "
                          f"{A['debt_gdp']:.0f}% of GDP in the latest quarter ({pd.Timestamp(A['debt_date']):%b %Y}), a backdrop that supports the "
                          "long-run case for gold but did not prevent this year's fall.")]))
story.append(PageBreak())

# 5 demand, flows, positioning
story += [Paragraph("Demand, Flows and Positioning", S["h1"]),
          chart(c_flows, "GLD holdings (tonnes) and COMEX managed-money net long (tonnes), late 2025-11/2026", "State Street, CFTC, Gold Desk estimates")]
wgc = [["World Gold Council, Q3 2026", "Tonnes", "Change y/y"], ["Central banks (net)", "321", "+42%"], ["Central banks, year to date", "675", "+6%"],
       ["Gold ETFs (flows)", "+211", "inflows after Q2 outflows"], ["Global ETF holdings, end Q3", "4,256", "record"],
       ["Bar and coin", "268", "-19%"], ["Jewellery", "313", "-17%"], ["Technology", "85", "+3%"], ["Total demand incl. OTC", "1,369", "-1%"]]
story.append(with_note("Central banks kept buying through the year; Western ETF holders and futures speculators did the selling.",
                       [table(wgc, [180, 70, 120], size=8.4), Spacer(1, 6),
                        P(f"GLD, the largest gold ETF, saw {'outflows' if A['gld_flow_bn'] < 0 else 'inflows'} of ${abs(A['gld_flow_bn']):.1f}bn in 2026; its holdings went from {A['gld_t_ye']:,.0f} t "
                          f"to {A['gld_t_now']:,.0f} t (estimate). Managed money cut its COMEX net long from {A['mm_peak26']:,.0f} t at the 2026 high "
                          f"to {A['mm_now']:,.0f} t on 17 November, the {nth(A['share_pct'])} percentile of its history since 2006 as a share of open interest.")],
                       src="Source: World Gold Council, Gold Demand Trends Q3 2026 (3 Nov 2026)."))
story.append(PageBreak())

# 6 sell-offs
story += [Paragraph("Two Sell-offs, Against 2008 and 2020", S["h1"]),
          chart(c_sell, "Gold after its highs: Jul 2008, Mar 2020 and Jan 2026 (high = 100), trading days", "Yahoo Finance, Gold Desk")]
evr = [["Week", "Gold that week", "VIX", "4 weeks later", "13 weeks later", "26 weeks later"]]
for _, e in ev.iterrows():
    evr.append([pd.Timestamp(e.week).strftime("%d %b %Y"), pc(e.gold_week), f"{e.vix:.0f}",
                pc(e.fwd4) if pd.notna(e.fwd4) else "", pc(e.fwd13) if pd.notna(e.fwd13) else "", pc(e.fwd26) if pd.notna(e.fwd26) else ""])
story.append(with_note("After past stress sell-offs gold was usually higher three months later, but the first month was a coin toss.",
                       [table(evr, [70, 62, 36, 62, 66, 66], size=7.6), Spacer(1, 6),
                        P(f"Weeks with the VIX at 30 or more and gold down 4% or more: in {E['pos13']} of {E['n']} past cases gold was higher 13 weeks "
                          f"later, by {pc(E['mean13'])} on average against {pc(E['all13'])} for all weeks; after 4 weeks it was lower in {E['neg4']} of "
                          f"{E['n']}. The cases cluster (four in autumn 2008) and the sample is too small for a test, so this is description, not "
                          "a forecast. In 2008 and 2020 the rebound came once central banks cut rates; in 2026 the Fed is moving the other way.")]))
story.append(PageBreak())

# 7 drivers
story += [Paragraph("What Drives Gold: the Driver Model", S["h1"]),
          chart(c_attr, "Gold's monthly return in 2026 split into drivers (% points, log)", "Gold Desk driver model (gold_desk.drivers)")]
fac_ytd = {gname: sum(ytd_attr.get(k, 0.0) for k in ks) for gname, ks, _ in GROUPS}
story.append(with_note(f"In 2026 the drivers explain {DRV['explained_2026']:.0%} of weekly moves, against {DRV['explained_oos']:.0%} since 2009.",
                       [P("Each week's gold return is split into real yields and breakevens, the dollar, the VIX, US stocks, oil, speculative "
                          "positioning and ETF flows, using sensitivities estimated on the previous three years only. Over 2026 to date the "
                          f"split is: rates and inflation {fac_ytd['Rates and inflation'] * 100:+.1f}, dollar {fac_ytd['Dollar'] * 100:+.1f}, stress "
                          f"{fac_ytd['Stress (VIX)'] * 100:+.1f}, stocks {fac_ytd['US stocks'] * 100:+.1f}, oil {fac_ytd['Oil'] * 100:+.1f}, positioning and "
                          f"flows {fac_ytd['Positioning and flows'] * 100:+.1f}, trend {fac_ytd['Trend (past 3 years)'] * 100:+.1f} and unexplained "
                          f"{fac_ytd['Unexplained'] * 100:+.1f} points (log)."),
                        P("The two large items tell the story. The 'trend' is the steady rise gold showed from 2023 to 2025 that none of the "
                          "drivers explained: the structural bid of central banks and Asian buyers. The 'unexplained' fall of 2026 is that bid "
                          "unwinding, concentrated in March and November."),
                        P(f"The correlation chart shows the same shift. In 2025 gold even rose with real yields (correlation up to "
                          f"{max(rl['corr_real'][-60:]):+.1f}); in 2026 the old negative link returned, near {rl['corr_real'][-1]:+.1f} now, "
                          "as real yields rose and the structural bid faded.")]))
story.append(chart(c_corr, "Gold's 52-week correlation with real yields and the dollar, weekly changes", "FRED, Yahoo Finance, Gold Desk"))
story.append(PageBreak())

# 8 IGWT theses
story += [Paragraph("The In Gold We Trust 2026 Theses, Checked", S["h1"]),
          P("The In Gold We Trust report 2026 (Incrementum, 20 May 2026) is the most widely read annual gold study. Its theses below are "
            "quoted from the compact version; the verdicts use the desk's data to 20 November. Tests H1 to H3 were fixed in code before "
            "they were run (commit 0a7239c).")]
thes = [["Thesis (IGWT 2026)", "What the data show", "Verdict"],
        ["Gold is decoupling from real interest rates (p. 30)",
         f"H1: weekly slope on the TIPS yield {H1['beta_before']:.3f} in 2010-21, {H1['beta_after']:.3f} since Mar 2022 (p = {H1['p_one_sided']:.3f}); "
         "the same with the dollar held constant", "Confirmed: the link halved but did not vanish"],
        ["Western ETF investors sell procyclically (p. 21)", f"H2: GLD flows rise after four weeks of gains (slope p = {H2['p']:.4f})", "Confirmed"],
        ["Liquidity-driven pullbacks are buying opportunities (p. 12)",
         f"After {E['n']} past stress sell-offs gold was higher 13 weeks later in {E['pos13']}; first month negative in {E['neg4']}", "Supported, small sample"],
        ["Volatile sideways range of USD 4,500-4,950 through early summer (p. 37)",
         f"Late May to August: ${A['summer_lo']:,.0f}-${A['summer_hi']:,.0f}", "Missed on the downside"],
        ["Year-end 2026: base case USD 3,247, inflationary USD 4,772 (p. 46)", f"${A['close']:,.0f} on 20 Nov", "Between the two, nearer the base case"],
        ["Central banks keep buying; 95% expect reserves to rise (p. 27)", "WGC: 675 t bought to Q3, 6% above 2025", "Confirmed"],
        ["A credible inflation hawk at the Fed is the main bear risk (p. 45)",
         f"Real yields {A['real_ye']:.2f}% to {A['real_now']:.2f}%; a December hike priced", "The bear case materialised"],
        ["Positioning: speculation not crowded (39th percentile in March, p. 13)",
         f"Net long share at the {nth(A['share_pct'])} percentile on 17 Nov; H3: positioning does not predict the next month", "Neutral; not a timing signal"],
        ["Gold-silver ratio fluctuates around 60 after the Iran war (p. 50)", f"Ratio {A['gsr_now']:.0f} on 20 Nov", "Silver fell much further"],
        ["The bull market is in its public-participation phase, not a bubble (p. 18)", "Dow Theory phases cannot be tested", "Not testable"]]
story.append(table(thes, [160, 200, CW - 360], size=7.8))
story.append(Spacer(1, 10))
h3txt = "; ".join(f"{(h['label'] if h['label'].startswith('GLD') else h['label'][0].lower() + h['label'][1:])}: R\u00b2 {h['r2'] * 100:+.1f}%" for h in H3)
story.append(P(f"<b>H3, positioning and flows as predictors.</b> None of the three candidates beat the historical average out of sample ({h3txt}). "
               "Flows and positioning describe who moved the price; they do not tell where it goes next."))
story.append(PageBreak())

# 9 model year
story += [Paragraph("The Desk Model's Year", S["h1"]),
          chart(c_vol, "Desk model volatility (GARCH-t, annualised), 01/2025-11/2026", "Gold Desk")]
tests = [["Test", "Result", "Verdict"]] + [[t["test"], t["result"], t["verdict"]] for t in R20["tests"]] + [
    ["H1 decoupling from real yields (21 Nov)", f"p = {H1['p_one_sided']:.3f}", "Confirmed"],
    ["H2 procyclical ETF flows (21 Nov)", f"p = {H2['p']:.4f}", "Confirmed"],
    ["H3 positioning and flows as predictors (21 Nov)", "All out-of-sample R\u00b2 below zero", "No"]]
story.append(with_note(f"Model volatility peaked at {A['vol_max26']:.0%} in {pd.Timestamp(A['vol_max_date']):%B}; it is {A['vol_now']:.0%} now.",
                       [P(f"Over {int(c5.n):,} weekly forecasts since 2006 the one-week 90% ranges held {c5.inside90:.1%} of the time. Over the last 52 "
                          f"weeks the one-month ranges held {c21l.inside90:.1%}: the misses came in the two sell-offs, when several shocks hit at once."),
                        table(tests, [128, 137, CW - 140 - 265], size=7.2)]))
story.append(PageBreak())

# 10 outlook
pk80 = CYC["peaks"][1]
story += [Paragraph("Outlook: What Would Decide 2027", S["h1"]),
          P("History offers no calendar for gold: the gaps between bear-market peaks since 1974 range from 8 months to 14 years. What does "
            "repeat is the role of real interest rates. Every earlier major peak came with negative real rates and was followed by rising ones; "
            "the 2026 peak is the first with positive real rates, which is why the old playbook fits only in part.")]
sc = [["Scenario", "What would have to happen", "Past parallel", "Signposts"],
      ["Liquidation ends, rates stabilise", "Forced selling fades; the Fed hikes once and pauses", "2008: rebound within weeks once policy turned",
       "VIX back below VIX3M; credit spreads narrowing; GVZ easing"],
      ["Real rates keep rising", "The Fed hikes repeatedly; TIPS yields above 3%; the dollar firm", f"1980 (-{abs(pk80['fall_pct']):.0%}) and 2011: years of weakness",
       "Core PCE at or above 0.3% a month; 2-year yield rising"],
      ["Inflation outruns the Fed", "CPI near 5-6% annualised while breakevens rise and real yields fall", "1975-76: a pause, then a much higher peak",
       "Breakevens up while TIPS yields fall"],
      ["Central-bank bid returns", "Official buying stays near 2025 levels while Western selling exhausts", "2022-25: gold rose despite positive real rates",
       "WGC quarterly data; GLD holdings stabilising"]]
story.append(table(sc, [100, 130, 120, CW - 350], size=7.8))
story.append(Spacer(1, 10))
story.append(P("The desk does not forecast direction: every direction signal tested this year failed out of sample. It sizes moves. At "
               f"{A['vol_now']:.0%} model volatility and a GVZ near {A['gvz']:.0f}, the coming weeks carry wider ranges than at any time since the "
               "spring, in both directions."))
story.append(PageBreak())

# 11 method
story += [Paragraph("Method and Sources", S["h1"]),
          P("<b>Data.</b> COMEX gold and silver futures, indices, ETFs and currencies from Yahoo Finance (daily closes to 20 Nov 2026); real "
            "yields, breakevens, CPI, the Fed's target and federal debt from FRED; managed-money positions from the CFTC disaggregated report "
            "(17 Nov); GLD shares outstanding and NAV from State Street; demand data from the World Gold Council (Gold Demand Trends Q3 2026)."),
          P("<b>Models.</b> Volatility: the desk's GARCH(1,1) with Student-t shocks on daily closes since 2003. Drivers: weekly regressions with "
            "sensitivities estimated on the previous 156 weeks only. Tests H1-H3: rules committed before the first run (gold_desk/drivers.py). "
            "Earlier tests: desk/reports/2026-11-13, the copper and rotation side projects, desk/reports/2026-11-19-cycles."),
          P("<b>Estimates.</b> GLD tonnes = shares x ounces per share (60-day median of NAV / COMEX price). COMEX tonnes = contracts x 100 oz. "
            "Futures trade a few dollars above spot."),
          P("<b>Outside sources.</b> Incrementum, In Gold We Trust report 2026, compact version (20 May 2026), for the theses on p. 8 and its "
            "projections; World Gold Council press release and report (3 Nov 2026); news as cited in the desk's weekly notes (CNBC, Reuters, "
            "Kitco, Quartz).")]
doc.build(story)
print("wrote", N / "gold_annual_review_2026.pdf")
