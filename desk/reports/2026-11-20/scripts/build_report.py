"""Full report, 20 Nov 2026: gold's fall from the 2026 record, the macro backdrop, the history and the tests.

Usage (from desk/): python reports/2026-11-20/scripts/build_report.py reports/2026-11-20 <out.pdf>
"""
import json
import re
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,  # noqa: E402
                                Paragraph, Spacer, Table, TableStyle)

N, OUT = Path(sys.argv[1]), sys.argv[2]
DESK = Path(__file__).resolve().parents[3]
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"     # validated categorical set
RED, SHADE = "#d03b3b", "#f1efe8"
R = json.load(open(N / "results.json"))
CHK = json.load(open(N / "checks.json"))
daily = pd.read_csv(N / "data" / "daily.csv", index_col=0, parse_dates=True)
fred = pd.read_csv(N / "data" / "fred.csv", index_col=0, parse_dates=True)
intra = pd.read_csv(N / "data" / "gold_5m.csv", index_col=0)
intra.index = pd.to_datetime(intra.index, utc=True).tz_convert("America/New_York").tz_localize(None)
now, yc, today = R["now"], R["y_close"], pd.Timestamp(R["today"])
ASOF = f"{R['asof']} ET"
X, MD, FL, CF, MM = R["cross"], R["model"], R["flows"], R["cftc"], R["mmf"]
macro = {row["measure"]: row for row in R["macro"]}
gold = daily["GC=F"].dropna().copy()
gold.iloc[-1] = now


def pc(x, d=1):
    return f"{x:+.{d}%}"


def bn(x, d=1):
    return f"{'+' if x >= 0 else '-'}${abs(x):,.{d}f}bn"


def nth(q):
    n = int(round(q * 100))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def dd(s):
    t = pd.Timestamp(s)
    return f"{t.day} {t:%b}"


# ---------------------------------------------------------------- charts
for fp in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 8.2, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False, "legend.fontsize": 7.4,
})
usd = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")


def save(fig, name):
    path = str(N / f"{name}.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# 1. gold since 2025 with the three phases
g = gold.loc["2025-01-01":]
fig, ax = plt.subplots(figsize=(7.2, 2.5))
phases = [("2026-01-29", "2026-10-06", "Real yields rising"), ("2026-10-06", "2026-11-13", "Hedge unwind, de-risking"),
          ("2026-11-13", R["today"], "This week")]
handles = []
for (a, b, lab), col in zip(phases, ("#ecebe4", "#d9d5c7", "#f6c9b1")):
    ax.axvspan(pd.Timestamp(a), pd.Timestamp(b) + pd.Timedelta(days=1), color=col, lw=0, zorder=0)
    handles.append(Patch(color=col, label=lab))
ax.legend(handles=handles, loc="upper left", ncol=3, fontsize=7)
ax.plot(g.index, g.values, color=INK, lw=1.3)
pk = pd.Timestamp(R["peak_date"])
ax.scatter([pk, today], [R["peak_close"], now], s=22, color=[INK, ORANGE], zorder=4, edgecolor="white", lw=1)
ax.annotate(f"Record {R['peak_close']:,.0f}\n{dd(pk)}", (pk, R["peak_close"]), xytext=(-8, -2), textcoords="offset points",
            ha="right", fontsize=7, color=INK2)
ax.annotate(f"{now:,.0f}", (today, now), xytext=(5, 0), textcoords="offset points", fontsize=7.4, va="center")
ax.set_ylim(2400, 6100)
ax.yaxis.set_major_formatter(usd)
ax.set_ylabel("COMEX gold, $/oz")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
c_overview = save(fig, "r_overview")

# 2. this week intraday
seg = intra.loc["2026-11-15 18:00":]
sess = pd.Timestamp("2026-11-19 18:00")
fig, ax = plt.subplots(figsize=(7.2, 2.4))
ax.fill_between([sess, seg.index[-1] + pd.Timedelta(hours=2)], MD["band90"][0], MD["band90"][1], color="#dbe8f8", lw=0,
                label="Today's 90% range from Thursday's close")
ax.plot(seg.loc[:sess].index, seg.loc[:sess, "Close"], color=INK2, lw=1.0, label="Mon-Thu")
ax.plot(seg.loc[sess:].index, seg.loc[sess:, "Close"], color=ORANGE, lw=1.5, label="Friday")
for t_, lab in ((pd.Timestamp("2026-11-18 14:00"), "Fed minutes"), (pd.Timestamp("2026-11-19 08:30"), "Jobless claims")):
    ax.axvline(t_, color=MUTED, lw=0.6, ls=":")
    ax.text(t_, 3925, f" {lab}", fontsize=6.8, color=MUTED, va="top")
for t_ in pd.date_range("2026-11-16 17:00", periods=4, freq="D"):
    ax.axvline(t_, color=AXIS, lw=0.7)
ax.yaxis.set_major_formatter(usd)
ax.set_ylim(3450, 3930)
ax.xaxis.set_major_locator(mdates.DayLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d"))
ax.legend(loc="lower left", ncol=3, fontsize=7)
c_week = save(fig, "r_week")

# 3. drivers since September
st = pd.Timestamp("2026-09-01")
fig, axs = plt.subplots(4, 1, figsize=(7.2, 3.9), sharex=True, gridspec_kw={"height_ratios": [1.3, 1, 0.8, 0.8]})
axs[0].plot(gold.loc[st:].index, gold.loc[st:].values, color=INK, lw=1.3)
axs[0].set_ylabel("Gold")
axs[0].yaxis.set_major_formatter(usd)
re_, be_ = fred["DFII10"].dropna().loc[st:], fred["T10YIE"].dropna().loc[st:]
axs[1].plot(re_.index, re_.values, color=BLUE, lw=1.3, label="10-year real yield (TIPS)")
axs[1].plot(be_.index, be_.values, color=ORANGE, lw=1.3, label="10-year breakeven inflation")
axs[1].legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=7)
axs[1].set_ylabel("%")
dx = daily["DX-Y.NYB"].dropna().loc[st:]
axs[2].plot(dx.index, dx.values, color=INK2, lw=1.3)
axs[2].set_ylabel("Dollar index")
hy = fred["BAMLH0A0HYM2"].dropna().loc[st:]
axs[3].plot(hy.index, hy.values, color=RED, lw=1.3)
axs[3].set_ylabel("High-yield\nspread, %")
for s_, a in ((gold.loc[st:], axs[0]), (re_, axs[1]), (be_, axs[1]), (dx, axs[2]), (hy, axs[3])):
    a.annotate(f"{s_.iloc[-1]:,.2f}" if s_.iloc[-1] < 50 else f"{s_.iloc[-1]:,.0f}", (s_.index[-1], s_.iloc[-1]),
               xytext=(4, 0), textcoords="offset points", fontsize=7, va="center")
for a in axs:
    a.axvline(pd.Timestamp("2026-10-06"), color=MUTED, lw=0.6, ls=":")
axs[3].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
fig.subplots_adjust(hspace=0.35)
c_drivers = save(fig, "r_drivers")

# 4. GLD flows
gl = pd.read_excel(N / "data" / "ssga_navhist_GLD.xlsx", header=None, engine="openpyxl")
s0 = gl.index[gl[0].astype(str).str.strip() == "Date"][0] + 1
gl = gl.iloc[s0:, :3].dropna()
gl.columns = ["date", "nav", "shares"]
gl["date"] = pd.to_datetime(gl["date"], format="%d-%b-%Y", errors="coerce")
gl[["nav", "shares"]] = gl[["nav", "shares"]].apply(pd.to_numeric, errors="coerce")
gl = gl.dropna().sort_values("date").set_index("date").loc["2025-01-01":]
cum = (gl.shares.diff() * gl.nav).fillna(0).cumsum() / 1e9
fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 2.8), sharex=True)
a1.plot(gold.loc["2025-01-01":].index, gold.loc["2025-01-01":].values, color=INK, lw=1.2)
a1.set_ylabel("Gold")
a1.yaxis.set_major_formatter(usd)
a2.fill_between(cum.index, 0, cum.values, color="#dbe8f8", lw=0)
a2.plot(cum.index, cum.values, color=BLUE, lw=1.3)
a2.set_ylabel("GLD flows since\nJan 2025, $bn")
a2.axhline(0, color=AXIS, lw=0.7)
for a in (a1, a2):
    a.axvline(pk, color=MUTED, lw=0.6, ls=":")
a2.annotate(f"{cum.iloc[-1]:+.1f}", (cum.index[-1], cum.iloc[-1]), xytext=(4, 0), textcoords="offset points", fontsize=7,
            va="center")
a2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
c_gld = save(fig, "r_gld")

# 5. the 13 Nov forecast cone and what happened
live = [json.loads(x) for x in open(DESK / "store" / "live.jsonl")]
rec = [x for x in live if x["origin"] == "2026-11-13"][0]
bday = pd.offsets.CustomBusinessDay(holidays=["2026-11-26", "2026-12-25"])
dts = pd.date_range(pd.Timestamp("2026-11-13") + bday, periods=21, freq=bday)
fanq = {int(k): np.array(v) for k, v in rec["fan"].items()}
hist = gold.loc["2026-10-01":"2026-11-19"]
fig, ax = plt.subplots(figsize=(7.2, 2.5))
ax.fill_between(dts, fanq[1], fanq[99], color="#eef3fb", lw=0, label="98% range")
ax.fill_between(dts, fanq[5], fanq[95], color="#cfe0f6", lw=0, label="90% range")
ax.fill_between(dts, fanq[25], fanq[75], color="#9fc2ee", lw=0, label="50% range")
ax.plot(hist.index, hist.values, color=INK, lw=1.3, label="Daily close")
ax.plot([hist.index[-1], today], [hist.iloc[-1], now], color=ORANGE, lw=1.3)
ax.scatter([today], [now], s=22, color=ORANGE, zorder=4, edgecolor="white", lw=1, label=f"Today, {ASOF}")
ax.yaxis.set_major_formatter(usd)
ax.set_xlim(pd.Timestamp("2026-10-01"), dts[-1] + pd.Timedelta(days=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, fontsize=7)
c_cone = save(fig, "r_cone")

# 6. after each peak
H_ = R["history"]
MAJOR = {"1974-12": BLUE, "1980-01": ORANGE, "2008-03": AQUA, "2011-09": YELLOW}
fig, ax = plt.subplots(figsize=(7.2, 2.6))
ends = []
for pk_, col in MAJOR.items():
    y = np.array(H_["paths"][pk_]) * 100
    ax.plot(np.arange(len(y)), y, color=col, lw=1.3, label=pd.Period(pk_, "M").strftime("%b %Y"))
    ends.append([y[-1], pk_[:4], len(y) - 1])
ends.sort()
for i in range(1, len(ends)):
    ends[i][0] = max(ends[i][0], ends[i - 1][0] + 6)
for y_, lab, x_ in ends:
    ax.annotate(lab, (x_, y_), xytext=(3, 0), textcoords="offset points", fontsize=6.8, color=INK2, va="center")
p26 = np.array(H_["path26"]) * 100
ax.plot(np.arange(len(p26)), p26, color=INK, lw=2.0, label="Feb 2026")
today_pct = (now / H_["feb_avg"] - 1) * 100
ax.scatter([len(p26) - 1], [today_pct], s=20, color=INK, zorder=4)
ax.annotate(f"2026, today's price: {today_pct:+.0f}%", (len(p26) - 1, today_pct), xytext=(1, -50), textcoords="data",
            fontsize=7, fontweight="bold", arrowprops=dict(arrowstyle="-", lw=0.6, color=INK))
ax.axhline(0, color=AXIS, lw=0.7)
ax.set_xlim(-1, 44)
ax.set_xlabel("Months after the peak (monthly averages, % from the peak month)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=5, fontsize=7)
c_peaks = save(fig, "r_peaks")

# ---------------------------------------------------------------- PDF
pdfmetrics.registerFont(TTFont("SUI", "C:/Windows/Fonts/segoeui.ttf"))
pdfmetrics.registerFont(TTFont("SUI-B", "C:/Windows/Fonts/segoeuib.ttf"))
registerFontFamily("SUI", normal="SUI", bold="SUI-B", italic="SUI", boldItalic="SUI-B")
W, Hp = A4
M = 16 * mm
CW = W - 2 * M
C = colors.HexColor


def sty(name, **kw):
    return ParagraphStyle(name, **{"fontName": "SUI", "fontSize": 8.6, "leading": 11.8, "textColor": C(INK), **kw})


S = {"h1": sty("h1", fontName="SUI-B", fontSize=12, leading=15, spaceBefore=2, spaceAfter=4, textColor=C(NAVY)),
     "h2": sty("h2", fontName="SUI-B", fontSize=10.2, leading=13, spaceBefore=6, spaceAfter=3, textColor=C(NAVY)),
     "body": sty("body"), "small": sty("small", fontSize=7.2, leading=9.5, textColor=C(INK2)),
     "num": sty("num", leftIndent=14, bulletIndent=0, spaceAfter=3),
     "bul": sty("bul", leftIndent=10, bulletIndent=0, spaceAfter=2.2),
     "cell": sty("cell", fontSize=7.6, leading=9.6), "cellb": sty("cellb", fontName="SUI-B", fontSize=7.6, leading=9.6),
     "cap": sty("cap", fontSize=7.1, leading=9.2, textColor=C(MUTED), spaceBefore=1, spaceAfter=3)}


def header_footer(c, doc):
    c.saveState()
    c.setFillColor(C(NAVY)); c.rect(0, Hp - 24 * mm, W, 24 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("SUI-B", 15); c.drawString(M, Hp - 12 * mm, "GOLD  |  THE 2026 SELL-OFF")
    c.setFont("SUI", 9.5); c.drawString(M, Hp - 18 * mm, "Report: what is happening, why, and how it compares with past peaks")
    c.setFont("SUI-B", 9.5); c.drawRightString(W - M, Hp - 12 * mm, f"{today:%d %B %Y}, {ASOF}")
    c.setFont("SUI", 8.5); c.drawRightString(W - M, Hp - 18 * mm, "COMEX gold futures, USD/oz")
    c.setStrokeColor(C(GRID)); c.setLineWidth(0.6); c.line(M, 12 * mm, W - M, 12 * mm)
    c.setFillColor(C(MUTED)); c.setFont("SUI", 7)
    c.drawString(M, 8 * mm, "Gold desk. Intraday prices are not settlements; today's close is scored in Sunday's weekly note.")
    c.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm, bottomMargin=14 * mm,
                      title="Gold: the 2026 sell-off", author="Nikolay Gelshtein")
frame = Frame(M, 14 * mm, CW, Hp - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])
esc = lambda v: re.sub(r"&(?!amp;)", "&amp;", str(v))  # noqa: E731


def table(rows, widths, size=None):
    cs, cb = (S["cell"], S["cellb"]) if size is None else (sty("c2", fontSize=size, leading=size + 2),
                                                           sty("c3", fontName="SUI-B", fontSize=size, leading=size + 2))
    data = [[Paragraph(f"<b>{esc(h)}</b>", cs) for h in rows[0]]]
    data += [[Paragraph(esc(v), cb if j == 0 else cs) for j, v in enumerate(r)] for r in rows[1:]]
    t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2), ("LEFTPADDING", (0, 0), (-1, -1), 4),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def img(path):
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=CW, height=CW * ih / iw)


def kpis(items):
    cells = [[Paragraph(f'<font size="7.0" color="{MUTED}">{k.upper()}</font><br/>'
                        f'<font name="SUI-B" size="13.5" color="{col}">{v_}</font><br/>'
                        f'<font size="7.0" color="{INK2}">{s_}</font>', sty("k", leading=14.5)) for k, v_, s_, col in items]]
    t = Table(cells, colWidths=[CW / len(items)] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C("#f4f3ef")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    return t


def bullets(items, style="bul"):
    return [Paragraph(t_, S[style], bulletText="\u2022") for t_ in items]


def numbered(items):
    return [Paragraph(t_, S["num"], bulletText=f"{i}.") for i, t_ in enumerate(items, 1)]


tw, tm, fan = R["touch_week"], R["touch"], {int(k): v for k, v in R["fan"].items()}
f13, fl18, s19 = R["f13"], R["flash18"], R["sum19"]
re_now = R["real"]
gld = FL["GLD"]
cov = pd.DataFrame(R["coverage"])
c5 = cov[(cov.window == "All history") & (cov.h == 5)].iloc[0]
c21 = cov[(cov.window == "All history") & (cov.h == 21)].iloc[0]
l5 = cov[(cov.window == "Last 52 weeks") & (cov.h == 5)].iloc[0]
two_day = now / R["week_days"]["2026-11-18"] - 1
eq2 = X["^GSPC"]["now"] / daily["^GSPC"].dropna().loc[:"2026-11-18"].iloc[-1] - 1
pk80, pk11 = H_["peaks"]["1980-01"], H_["peaks"]["2011-09"]

# ---------------- page 1: summary
story = [kpis([
    ("Gold now", f"{now:,.0f}", f"{dd(today)}, {ASOF}", INK),
    ("Today", pc(R["r_today"]), f"{MD['z_today']:.1f} times the expected daily move", RED),
    ("This week", pc(R["r_week"]), "worst week since at least 2000", RED),
    ("From the record", pc(R["from_peak"], 0), f"{R['peak_close']:,.0f} on {dd(R['peak_date'])}", RED),
    ("Model volatility", f"{MD['vol_now']:.1%}", f"{nth(MD['vol_pct'])} percentile since 2003", INK),
]), Spacer(1, 6)]
story.append(Paragraph("Summary", S["h1"]))
story += numbered([
    f"<b>The move.</b> Gold is at {now:,.0f} ({ASOF}), {pc(R['r_today'])} today and {pc(R['r_week'])} this week. If it closes "
    "here, this is the worst week for COMEX gold futures since at least 2000, when our data start. Today's drop is one of "
    f"{R['n_worse_days_since_2000'] + 1} days since 2000 this large. The price is {abs(R['from_peak']):.0%} below the "
    f"{dd(R['peak_date'])} record and the lowest since late August 2025.",
    f"<b>Three forces, one after the other.</b> (1) <i>Since February</i> the market's real yield (10-year TIPS) has risen "
    f"about {re_now['since_feb_bp'] / 100:.1f} points to {re_now['now']:.2f}%, the highest outside 2026 since 2008, while "
    "inflation rose and the Fed prepared to hike. (2) <i>Since early October</i> the inflation hedge has been unwinding: "
    f"breakeven inflation fell {abs(macro['10-year breakeven inflation']['now'] - macro['10-year breakeven inflation']['oct6']) * 100:.0f} bp "
    "and silver, copper and bitcoin fell harder than gold. (3) <i>This week</i> hawkish Fed signals (the minutes on "
    f"Wednesday, Waller's case for 50 bp) turned into liquidation: on Thursday and Friday stocks fell {abs(eq2):.1%}, the VIX reached "
    f"{X['^VIX']['now']:.0f} and the 10-year yield fell, yet gold fell {abs(two_day):.1%}. Gold is being sold to raise cash.",
    f"<b>Macro.</b> The Fed has held at 3.75-4.00% for a year but a December hike is priced at roughly 90-95%. CPI "
    f"inflation is {macro['CPI inflation, 12 months']['now']:.2f}% and {macro['CPI inflation, 3 months annualised']['now']:.1f}% "
    "annualised over three months; the labour market is cooling at the edges; the dollar is near a 19-month high; the "
    f"high-yield credit spread is {(macro['High-yield credit spread']['now'] - macro['High-yield credit spread']['oct6']) * 100:+.0f} bp since 6 Oct.",
    f"<b>Money flows.</b> GLD, the largest gold fund, has lost {abs(gld['since_peak_pct']):.1%} of its shares since the "
    f"record while the price fell {abs(R['from_peak']):.0%}: fund holders mostly held. Money funds were flat in the week "
    f"to {dd(MM['date'])}; the T-bill fund BIL took in {bn(FL['BIL']['nov_bn'])} in November. Speculators were still net "
    f"long {CF['net']:,.0f} contracts on {dd(CF['date'])}.",
    f"<b>The model.</b> Today is a {MD['z_today']:.1f}-sigma day for the desk model, about a 1-in-{1 / MD['p_today']:.0f}-day "
    f"event. The price is below the 1st percentile of the 13 Nov week-ahead forecast (lower than {f13['pit_sim']:.2%} of its "
    f"simulated paths), outside its 98% range. Over {int(c5.n):,} weekly forecasts since 2006 the 90% ranges held {c5.inside90:.1%} of the time; the "
    "misses come in clusters like this week.",
    "<b>History.</b> Every earlier big peak (1974, 1980, 2008, 2011) came with negative real rates and was followed by "
    "rising real rates; the 2026 peak is the first with positive real rates. In today's dollars gold is now "
    f"{abs(H_['now_vs_rec80']):.0%} below its 1980 record. After 1974, 1980 and 2011 the falls reached 40-53%; this one is "
    f"{abs(now / H_['feb_avg'] - 1):.0%} from the February monthly average and {abs(R['from_peak']):.0%} from the daily record.",
    "<b>The tests.</b> Eight extra signals tested this month (drift, a shorter estimation window, options-implied "
    "volatility, copper, breakevens, cycles and others) did not improve the forecasts. Direction is not forecastable; the "
    "size of moves is, on average.",
])
story += [Spacer(1, 2), img(c_overview),
          Paragraph("Daily closes; today at the latest print. Shaded: the three phases described above.", S["cap"])]

# ---------------- page 2: the latest move
story.append(PageBreak())
story += [Paragraph("1. The latest move", S["h1"]), img(c_week),
          Paragraph(f"5-minute prices, New York time. Low today {R['session_low']:,.0f} at {R['session_low_t']} ET, high "
                    f"{R['session_high']:,.0f}. The blue band is the model's 90% range for today's close.", S["cap"])]
notes = {
    "2026-11-13": "Weekly forecast logged",
    "2026-11-16": "Tech-led stock sell-off; S&P 500 -1.9%",
    "2026-11-17": "NY Fed's Williams: another hike likely; Nvidia beats after the close",
    "2026-11-18": "Below $3,800 overnight; Fed minutes: almost all officials see more hikes; Waller floats 50 bp",
    "2026-11-19": "Jobless claims 203k vs 197k expected; continuing claims highest since late August; stocks -2.0%",
    "2026-11-20": f"Broad liquidation: stocks, bitcoin and silver down, VIX {X['^VIX']['now']:.0f}, 10-year yield lower "
                  f"({ASOF}, not a close)",
}
rows = [["Date", "Gold", "Day", "What happened"]]
prev = None
for d_, v_ in R["week_days"].items():
    rows.append([pd.Timestamp(d_).strftime("%a %d %b"), f"{v_:,.0f}", "" if prev is None else pc(v_ / prev - 1),
                 notes.get(d_, "")])
    prev = v_
story += [table(rows, [0.12, 0.08, 0.08, 0.72])]
rows = [["Market", "Now", "Today", "This week", "Since 6 Oct", "Since the record"]]
spec = [("GC=F", "Gold", "{:,.0f}", "p"), ("SI=F", "Silver", "{:.2f}", "p"), ("HG=F", "Copper", "{:.2f}", "p"),
        ("^GSPC", "S&P 500", "{:,.0f}", "p"), ("BTC-USD", "Bitcoin", "{:,.0f}", "p"), ("DX-Y.NYB", "Dollar index", "{:.2f}", "p"),
        ("^TNX", "US 10-year yield", "{:.2f}%", "bp"), ("^VIX", "VIX", "{:.1f}", "pt"), ("^GVZ", "GVZ (gold implied vol)", "{:.1f}", "pt"),
        ("CL=F", "WTI crude", "{:.2f}", "p")]
for t, name, fmt, u in spec:
    x = X[t]
    f_ = {"p": lambda v: pc(v), "bp": lambda v: f"{v * 100:+.0f} bp", "pt": lambda v: f"{v:+.1f}"}[u]
    rows.append([name, fmt.format(x["now"]), f_(x["today"]), f_(x["week"]), f_(x["since_oct6"]), f_(x["since_peak"])])
story += [Spacer(1, 4), table(rows, [0.24, 0.13, 0.13, 0.15, 0.15, 0.20]),
          Paragraph(f"Latest prints at {ASOF}. Record date: 29 Jan 2026. VIX against its 3-month version: "
                    f"{R['vix_ratio']:.2f} (above 1 = stress).", S["cap"])]
story.append(Paragraph("What kind of selling is this?", S["h2"]))
story += bullets([
    "<b>Not a new rate shock today.</b> The 10-year yield fell and the dollar was flat: the two usual reasons for gold "
    "to fall were not at work on Friday.",
    f"<b>A dash for cash.</b> Stocks fell for a sixth day, bitcoin {pc(X['BTC-USD']['today'])}, silver "
    f"{pc(X['SI=F']['today'])}, and the VIX curve is inverted ({R['vix_ratio']:.2f}). Only Treasuries were bought. Critical "
    "Metals CEO Tony Sage told Reuters that the equity sell-off pushed some investors to sell gold to cover losses "
    "elsewhere; Reuters also reported Asian stocks heading for their worst week since 2020 (via Yoopya).",
    "<b>Gold's own volatility jumped.</b> The GVZ, the options market's measure of expected gold volatility, rose to "
    f"{MD['gvz']:.1f}, up {X['^GVZ']['week']:.1f} points this week.",
])

# ---------------- page 3: macro
story.append(PageBreak())
story += [Paragraph("2. The macro backdrop", S["h1"]), img(c_drivers),
          Paragraph("Since 6 Oct (dotted line) the 10-year yield fell on lower inflation expectations, not lower real "
                    "yields. Real yields jumped in the week to 17 Nov and have held near 2.9% since, while credit spreads "
                    "kept widening. FRED, latest available.",
                    S["cap"])]
fmt = {"pct": lambda v: f"{v:.2f}%", "k": lambda v: f"{v:,.0f}k", "idx": lambda v: f"{v:.1f}", "bn": lambda v: f"${v / 1e3:.2f}tn"}
rows = [["Measure", "Now", "On 6 Oct", "A year ago"]]
for row in R["macro"]:
    f_ = fmt[row["unit"]]
    rows.append([row["measure"], f_(row["now"]), f_(row["oct6"]), f_(row["year_ago"])])
story += [table(rows, [0.46, 0.18, 0.18, 0.18]),
          Paragraph("Each column uses only data published by that date (monthly data about six weeks after the month). "
                    "October 2025 CPI was never published and is interpolated. Latest dates: rates and spreads 18-19 Nov, "
                    "claims 14 Nov, CPI and jobs October, broad dollar 13 Nov.", S["cap"])]
story += bullets([
    "<b>The Fed.</b> The minutes of the 27-28 Oct meeting showed almost all officials expect further hikes; two voted "
    "for one in October (CNBC). Governor Waller has argued for a half-point move in December (CNBC); Philadelphia Fed "
    "President Paulson said inflation could warrant another increase (Reuters); Chicago's Goolsbee did not rule out a "
    "larger hike (Quartz). Futures price a December hike at roughly 90-95% (CME FedWatch, as reported). The policy rate "
    f"has been {macro['Fed funds target (upper)']['now'] - 0.25:.2f}-{macro['Fed funds target (upper)']['now']:.2f}% for a year.",
    f"<b>Inflation.</b> CPI {macro['CPI inflation, 12 months']['now']:.2f}% over 12 months and "
    f"{macro['CPI inflation, 3 months annualised']['now']:.1f}% annualised over three months; core "
    f"{macro['Core CPI inflation, 12 months']['now']:.2f}%. Yet markets expect less inflation ahead: breakevens and the "
    "5y5y forward fell since October. Investors believe the Fed will win, which is bad for gold as an inflation hedge.",
    f"<b>Growth.</b> Unemployment {macro['Unemployment rate']['now']:.1f}% (October), payrolls up "
    f"{macro['Payrolls, 3-month average change (000)']['now']:.0f}k a month on average; jobless claims 203k vs 197k "
    "expected and continuing claims at 1.76 million, the highest since late August (Reuters, Quartz). Cooling, not cracking.",
    f"<b>Real rates are the core of it.</b> The 10-year TIPS yield at {re_now['now']:.2f}% means an investor locks in "
    "almost 3% a year above inflation in Treasuries. Gold pays nothing; holding it now costs more than at any time since "
    "2008, outside this year.",
])

# ---------------- page 4: flows and positioning
story.append(PageBreak())
story += [Paragraph("3. Money flows and positioning", S["h1"]), img(c_gld),
          Paragraph(f"GLD flows: daily change in shares outstanding times NAV, from State Street's own files. Since the "
                    f"record the price fell {abs(R['from_peak']):.0%}; the fund lost {abs(gld['since_peak_pct']):.1%} of its "
                    "assets to redemptions.", S["cap"])]
rows = [["Fund (State Street data)", "Assets", "Since the record", "Since 6 Oct", "November", "This week*", "Week vs past year"]]
names = {"GLD": "Gold (GLD)", "SPY": "S&P 500 (SPY)", "XLK": "Technology (XLK)", "XLU": "Utilities (XLU)",
         "XLP": "Consumer staples (XLP)", "BIL": "T-bills 1-3 months (BIL)"}
for t, nm in names.items():
    f_ = FL[t]
    rows.append([nm, f"${f_['aum_bn']:,.0f}bn", f"{bn(f_['since_peak_bn'])} ({f_['since_peak_pct']:+.1%})",
                 f"{bn(f_['since_oct6_bn'])} ({f_['since_oct6_pct']:+.1%})", bn(f_["nov_bn"]), bn(f_["week_bn"], 2),
                 f"z {f_['z_week']:+.1f}"])
story += [table(rows, [0.22, 0.09, 0.17, 0.16, 0.11, 0.11, 0.14]),
          Paragraph(f"*This week to {dd(gld['last'])} (State Street publishes with a one-day lag). z: this week's flow "
                    "against the weekly flows of the past year.", S["cap"])]
story += bullets([
    f"<b>Gold funds: steady holders.</b> GLD's outflow since the record ({bn(gld['since_peak_bn'])}) is "
    f"{abs(gld['since_peak_pct']):.1%} of its assets; this week's {bn(gld['week_bn'], 2)} is normal (z "
    f"{gld['z_week']:+.1f}). The selling is in futures and in other hands, not a run on gold ETFs.",
    f"<b>Cash: building slowly.</b> Money market funds held ${MM['total_tn']:.2f}tn in the week to {dd(MM['date'])}, "
    f"{bn(MM['chg_bn'])} on the week (z {MM['z']:+.1f}) after a record ${MM['max_tn']:.2f}tn on {dd(MM['max_date'])} (ICI). "
    f"BIL took in {bn(FL['BIL']['nov_bn'])} in November ({FL['BIL']['nov_pct']:+.1%}). The Thursday-Friday liquidation is "
    "not yet in these figures.",
    f"<b>Speculators.</b> Managed money was net long {CF['net']:,.0f} gold futures on {dd(CF['date'])} "
    f"({CF['pct_oi']:.0%} of open interest, {nth(CF['pctile_since_2006'])} percentile since 2006), down from "
    f"{CF['max_2026']:,.0f} at the 2026 high. A long that size is fuel for more selling if prices keep falling.",
    "<b>Fund managers.</b> Cash at 3.6% in BofA's November survey, a sell signal under BofA's own rule: little cash "
    "cushion, so losses elsewhere force sales of what can be sold, gold included (HedgeCo, Longbridge).",
])

# ---------------- page 5: model and forecasts
story.append(PageBreak())
story += [Paragraph("4. What the desk model says", S["h1"]), img(c_cone),
          Paragraph("The weekly forecast of 13 Nov (fan) against what happened. Today's price is below its 98% range.", S["cap"])]
story += bullets([
    f"<b>Today.</b> A {pc(R['r_today'])} move is {MD['z_today']:.1f} times the model's daily volatility "
    f"({MD['sigma_day']:.2%}). The model's fat-tailed distribution gives it a {MD['p_today']:.2%} chance; in the data since "
    f"2003, {MD['emp_tail']:.2%} of days were this extreme against the model. Tails are slightly fatter than the model "
    "assumes, but the gap is small.",
    f"<b>The week.</b> The 13 Nov forecast put Friday's close in a 90% range of {f13['band90_week'][0]:,.0f} to "
    f"{f13['band90_week'][1]:,.0f} and its 1st percentile at {f13['q1_week']:,.0f}. Today's price is lower than "
    f"{f13['pit_sim']:.2%} of its simulated paths: about a 1-in-{1 / max(f13['pit_sim'], 1e-4):.0f} outcome. The 18 Nov "
    f"flash note gave a {fl18['touch3600']:.0%} chance of closing below $3,600 within a week and the 19 Nov note "
    f"{s19['touch3500w']:.0%} for $3,500: gold trades below the first and just above the second.",
    f"<b>The record.</b> Over {int(c5.n):,} weekly forecasts since 2006, the 1-week 90% range held {c5.inside90:.1%} of "
    f"the time (Kupiec p {c5.kupiec_p:.2f}) and the 1-month range {c21.inside90:.1%}. Over the last 52 weeks: "
    f"{l5.inside90:.1%}. On average the ranges are right; the misses bunch in stress, as now.",
    f"<b>Volatility now.</b> {MD['vol_now']:.1%} after today, {nth(MD['vol_pct'])} percentile since 2003 (long-run "
    f"{MD['vol_lr']:.1%}). The GVZ at {MD['gvz']:.1f} says the options market expects even more.",
])
rows = [["Horizon", "5%", "25%", "Median", "75%", "95%"]]
for h, nm in ((5, "1 week"), (21, "1 month")):
    rows.append([nm] + [f"{fan[k][h - 1]:,.0f}" for k in (5, 25, 50, 75, 95)])
lv = [["Level", "Within a week", "Within a month"]] + [[f"${int(k):,}", f"{tw[k]:.0%}", f"{tm[k]:.0%}"]
                                                     for k in ("3200", "3300", "3400", "3600", "3800", "4000")]
story += [Paragraph("Ranges from here", S["h2"]), table(rows, [0.20, 0.16, 0.16, 0.16, 0.16, 0.16]), Spacer(1, 3),
          table(lv, [0.3, 0.35, 0.35]),
          Paragraph("20,000 simulated paths with today's price as the latest observation; chance of a close through each "
                    "level. No drift: the model sizes moves, it does not call direction.", S["cap"])]

# ---------------- page 6: history
story.append(PageBreak())
story += [Paragraph("5. The past peaks compared", S["h1"]), img(c_peaks)]
rows = [["Peak", "Climb before", "Inflation", "Real rate at peak", "Real rate, next year", "Fall", "Back at peak"]]
for pk_ in ("1974-12", "1980-01", "2008-03", "2011-09"):
    p = H_["peaks"][pk_]
    rows.append([pd.Period(pk_, "M").strftime("%b %Y"), f"{p['runup_pct']:+.0%} in {p['runup_months']} mo",
                 f"{p['infl_at_peak']:.1f}%", f"{p['rr_at_peak']:+.1f}%", f"{p['rr_change_peak_to_12m']:+.1f} pt",
                 f"{p['fall_pct']:+.0%}", f"{p['months_to_regain'] / 12:.1f} yrs"])
rows.append(["Feb 2026", "+202% in 40 mo", "2.4%", "+1.7%", f"TIPS +{re_now['since_feb_bp'] / 100:.1f} pt so far",
             f"{now / H_['feb_avg'] - 1:+.0%} (today)", "not yet"])
story += [table(rows, [0.12, 0.16, 0.10, 0.15, 0.17, 0.14, 0.16]),
          Paragraph("Monthly averages. Real rate: 10-year yield minus CPI inflation (TIPS since 2003). The 1980 second "
                    "top (Sep 1980) led a fall of 53%.", S["cap"])]
story += bullets([
    "<b>What made each peak.</b> 1974 and 1980: double-digit inflation, deeply negative real rates, oil shocks. 2008 and "
    "2011: falling real rates, crisis, quantitative easing. 2026: a climb with positive real rates, carried by central-bank "
    "buying and safe-haven demand.",
    "<b>What ended them.</b> Rising real rates every time: Volcker's hikes after 1980 (gold needed 26 years to regain the "
    "peak), the 2013 taper after 2011 (9 years). In 1975-76 the fall was a pause: inflation came back, real rates turned "
    "negative and gold rose sixfold to 1980. In 2008 forced selling ended within weeks once rates were cut to zero.",
    f"<b>In today's money.</b> The 1980 record ($850) equals ${H_['rec80_today']:,.0f} today and the 2011 record ($1,895) "
    f"${H_['rec11_today']:,.0f}. Gold at {now:,.0f} is {abs(H_['now_vs_rec80']):.0%} below the 1980 record in real terms.",
    "<b>No calendar.</b> The gaps between all nine bear-market peaks since 1974 range from 0.7 to 14.4 years: there is "
    "no cycle that says when the next rise comes.",
])
story.append(KeepTogether([Paragraph("Which past does today resemble?", S["h2"]), table([
    ["Signal", "1975-76: pause, then much higher", "1980 and 2011: long bear", "2008: forced selling, then up", "Now"],
    ["Real rates", "Negative", "Rising sharply", "Cut toward zero", f"Positive and rising (TIPS {re_now['now']:.1f}%)"],
    ["Inflation", "High, coming back", "Falling", "Falling", f"{macro['CPI inflation, 12 months']['now']:.1f}%, rising"],
    ["Central bank", "Behind the curve", "Hiking hard", "Cutting fast", "About to hike"],
    ["Selling", "Gradual", "Gradual, for years", "Liquidation in weeks", "Liquidation this week"],
], [0.14, 0.21, 0.19, 0.21, 0.25])]))

# ---------------- page 7: tests
story.append(PageBreak())
story += [Paragraph("6. What the tests say", S["h1"]),
          Paragraph("Every idea below was turned into a forecasting rule fixed before the data were scored (except where "
                    "marked), and kept only if it beat the plain model out of sample.", S["body"]), Spacer(1, 3)]
rows = [["Test", "Question", "Result", "Verdict"]] + [[t["test"], t["question"], t["result"], t["verdict"]] for t in R["tests"]]
story += [table(rows, [0.22, 0.27, 0.31, 0.20]),
          Paragraph("Profit-taking robustness and the breakeven re-run were added after earlier results, so they are "
                    "exploratory. Sources: desk/reports/2026-11-13, copper/, rotation/, desk/reports/2026-11-19-cycles.", S["cap"])]
story += bullets([
    "<b>Direction is not forecastable</b> with these tools: drift, momentum-like signals, copper, breakevens and cycles all "
    "fail out of sample. That is consistent with an efficient gold market.",
    f"<b>Size is forecastable on average</b>: the model's ranges held {c5.inside90:.1%} of the time at one week. The one "
    "promising lead is options-implied volatility at the one-week horizon, which is now being tracked on live data.",
    "<b>Tails cluster.</b> Weeks like this one, when several shocks hit at once, are where every range model is weakest. "
    "The model raises its volatility quickly after a shock, which is why the ranges from here are much wider.",
])

# ---------------- page 8: scenarios, watch list, checks, sources
story.append(PageBreak())
story.append(Paragraph("7. What would decide the next move", S["h1"]))
story += bullets([
    "<b>Liquidation ends, rates stabilise</b> (2008 pattern): forced selling fades once the VIX curve un-inverts and credit "
    "spreads stop widening. Signposts: VIX back below its 3-month version, high-yield spread falling, GVZ easing.",
    "<b>Real rates keep rising</b> (1980 and 2011 pattern): the Fed hikes 50 bp or signals a longer path, TIPS yields push "
    "above 3%, the dollar keeps rising. History says years of weakness or sideways trade.",
    "<b>Inflation outruns the Fed</b> (1975-76 pattern): CPI keeps running near 5-6% annualised while breakevens turn up "
    "and real yields fall. Then the hedge returns.",
])
ev = [["When", "What", "Why it matters"],
      ["Fri 20 Nov, 15:30 ET", "CFTC positioning (as of 17 Nov)", "How much of the speculative long was sold"],
      ["Sun 22 Nov", "Weekly desk note", "Scores today's close against the 13 Nov forecast"],
      ["Thu 26 Nov", "Thanksgiving", "US holiday; thin trading"],
      ["Tue-Wed 8-9 Dec", "FOMC", "25 bp priced; a half-point move is not"],
      ["Levels", "$3,400 / $3,800", f"{tm['3400']:.0%} of paths close below $3,400 within a month; {tm['3800']:.0%} back above $3,800"]]
story += [Spacer(1, 2), table(ev, [0.18, 0.30, 0.52])]
rows = [["Number check", "Result", "Detail"]] + [[c["check"], c["result"], c["detail"]] for c in CHK]
n_pass = sum(c["result"] == "PASS" for c in CHK)
story += [Paragraph(f"Number checks: {n_pass} of {len(CHK)} passed", S["h2"]), table(rows, [0.30, 0.08, 0.62], size=6.8)]
story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
    "Prices: Yahoo Finance (COMEX futures, indices, ETFs), latest print at the time stated. Model: the desk's GARCH(1,1) "
    "with Student-t shocks and zero drift on daily closes since 2003; 20,000 paths, seed 42; the 13 Nov forecast is the "
    "stored live record. Macro: FRED (DFII10, T10YIE, T5YIFR, DGS2, DGS10, BAMLH0A0HYM2, BAMLC0A0CM, DTWEXBGS, DFEDTARU, "
    "CPIAUCSL, CPILFESL, UNRATE, PAYEMS, ICSA, WALCL, WTREGEN, RRPONTSYD). Flows: State Street NAV-history files (shares "
    "outstanding), ICI weekly money fund file. Positioning: CFTC Commitments of Traders. History: World Gold Council / "
    "LBMA monthly prices via datahub.io. News, each attributed in the text: CNBC (Fed minutes, Waller, 18 Nov), Reuters "
    "via Yoopya (Paulson, Sage, Asia equities, 20 Nov), Reuters via Investing.com and Quartz (jobless claims, 19 Nov), "
    "Quartz (Goolsbee), HedgeCo and Longbridge (BofA survey).", S["small"])]))
doc.build(story)
print("wrote", OUT)
