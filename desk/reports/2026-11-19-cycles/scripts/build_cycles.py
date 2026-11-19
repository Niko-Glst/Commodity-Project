"""Gold cycles since 1975: peaks and calm periods compared with now (desk note).

Usage (from desk/): python reports/2026-11-19-cycles/scripts/build_cycles.py reports/2026-11-19-cycles <out.pdf>
"""
import json
import sys

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
from reportlab.lib.units import mm  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,  # noqa: E402
                                Paragraph, Spacer, Table, TableStyle)

N, OUT = sys.argv[1], sys.argv[2]
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"   # validated, fixed per peak
SHADE = "#f1efe8"
R = json.load(open(f"{N}/cycles.json"))
mo = pd.read_csv(f"{N}/monthly.csv", index_col=0)
mo.index = pd.PeriodIndex(mo.index, freq="M").to_timestamp(how="start")
fred = pd.read_csv(f"{N}/data/fred_monthly.csv", index_col=0, parse_dates=True)
peaks = pd.DataFrame(R["peaks"]).set_index("peak")
MAJOR = {"1974-12": BLUE, "1980-01": ORANGE, "2008-03": AQUA, "2011-09": YELLOW}
NOW = "2026-02"
now, now_date = R["now_price"], pd.Timestamp(R["now_date"])
cpi = np.exp(np.log(fred["CPIAUCSL"]).interpolate(limit_area="inside"))
cpi_now = cpi.dropna().iloc[-1]
rec80 = 850 * cpi_now / cpi.loc["1980-01-01"]
rec11 = 1895 * cpi_now / cpi.loc["2011-09-01"]
p26 = peaks.loc[NOW]
from_daily_peak = now / 5318.4 - 1
tips_feb, tips_nov = mo.loc["2026-02-01", "tips_10y"], mo.loc["2026-11-01", "tips_10y"]

for fp in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 8.2, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False, "legend.fontsize": 7.5,
})


def save(fig, name):
    path = f"{N}/{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# 1. history since 1975: price (nominal and real), real rate, inflation
x = mo.loc["1974-01-01":]
fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(7.2, 5.0), sharex=True, gridspec_kw={"height_ratios": [2.2, 1, 1]})
for c in R["calm"]:
    for a in (a1, a2, a3):
        a.axvspan(pd.Timestamp(c["from"]), pd.Timestamp(c["to"]) + pd.offsets.MonthEnd(0), color=SHADE, lw=0, zorder=0)
a1.plot(x.index, x.gold_real, color=BLUE, lw=1.3, label="In October-2026 dollars")
a1.plot(x.index, x.gold_avg, color=INK, lw=1.3, label="Price at the time")
a1.set_yscale("log")
a1.set_yticks([100, 200, 500, 1000, 2000, 5000])
a1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
a1.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
LBL = {"1974-12": (0, -13, "center"), "1980-01": (-5, -12, "right"), "2008-03": (-5, 4, "right"),
       "2011-09": (0, -14, "center"), "2026-02": (-6, 3, "right")}
for pk in list(MAJOR) + [NOW]:
    t = pd.Timestamp(pk)
    a1.scatter([t], [x.loc[t, "gold_avg"]], s=18, color=INK, zorder=4)
    dx, dy, ha = LBL[pk]
    a1.annotate(f"{t:%b %Y}", (t, x.loc[t, "gold_avg"]), xytext=(dx, dy), textcoords="offset points", ha=ha,
                fontsize=6.8, color=INK2, bbox=dict(facecolor="white", edgecolor="none", pad=0.4))
a1.set_ylabel("Gold, $/oz (log)")
a1.legend(loc="upper left", ncol=2)
a2.plot(x.index, x.real_rate_expost, color=INK2, lw=1.1, label="10-year yield minus CPI inflation")
a2.plot(x.index, x.tips_10y, color=BLUE, lw=1.3, label="10-year TIPS yield (from 2003)")
a2.axhline(0, color=AXIS, lw=0.8)
a2.set_ylabel("Real rate, %")
a2.legend(loc="upper right", ncol=2, fontsize=7)
a3.plot(x.index, x.cpi_yoy, color=ORANGE, lw=1.2)
a3.axhline(2, color=AXIS, lw=0.7, ls=(0, (3, 2)))
a3.set_ylabel("CPI inflation, %")
a3.xaxis.set_major_locator(mdates.YearLocator(5))
a3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
hist_png = save(fig, "c_history")

# 2. after each peak, and 3. into each peak
fig, (b1, b2) = plt.subplots(1, 2, figsize=(7.2, 2.7), sharey=False)
ends = []
for pk, col in MAJOR.items():
    up = np.array(R["runups"][pk]) * 100
    b1.plot(np.arange(-len(up) + 1, 1), up, color=col, lw=1.3, label=pd.Period(pk, "M").strftime("%b %Y"))
    dn = np.array(R["paths"][pk][:37]) * 100
    b2.plot(np.arange(len(dn)), dn, color=col, lw=1.3)
    ends.append([dn[-1], pk[:4], len(dn) - 1])
ends.sort()
for i in range(1, len(ends)):
    ends[i][0] = max(ends[i][0], ends[i - 1][0] + 6)
for y, lab, xx in ends:
    b2.annotate(lab, (xx, y), xytext=(3, 0), textcoords="offset points", fontsize=6.8, color=INK2, va="center")
up = np.array(R["runups"][NOW]) * 100
b1.plot(np.arange(-len(up) + 1, 1), up, color=INK, lw=2.0, label="Feb 2026")
dn = np.array(R["paths"][NOW]) * 100
b2.plot(np.arange(len(dn)), dn, color=INK, lw=2.0)
b2.scatter([len(dn) - 1], [(now / p26.peak_avg - 1) * 100], s=18, color=INK, zorder=4)
b2.annotate(f"2026, today's price: {(now / p26.peak_avg - 1):+.0%}", (len(dn) - 1, (now / p26.peak_avg - 1) * 100),
            xytext=(1, -49), textcoords="data", fontsize=7, color=INK, fontweight="bold", ha="left",
            arrowprops=dict(arrowstyle="-", color=INK, lw=0.6))
fig.legend(*b1.get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.5, -0.17), ncol=5)
b1.set_title("Into the peak (peak month = 100)", fontsize=8.2, color=INK2, loc="left")
b1.set_xlabel("Months before the peak")
b2.set_title("After the peak (% from the peak month)", fontsize=8.2, color=INK2, loc="left")
b2.set_xlabel("Months after the peak")
b2.axhline(0, color=AXIS, lw=0.7)
b2.set_xlim(-1, 44)
b1.set_xlim(-66, 1)
paths_png = save(fig, "c_paths")

# ---------------------------------------------------------------- PDF
pdfmetrics.registerFont(TTFont("SUI", "C:/Windows/Fonts/segoeui.ttf"))
pdfmetrics.registerFont(TTFont("SUI-B", "C:/Windows/Fonts/segoeuib.ttf"))
registerFontFamily("SUI", normal="SUI", bold="SUI-B", italic="SUI", boldItalic="SUI-B")
W, Hp = A4
M = 16 * mm
CW = W - 2 * M
C = colors.HexColor


def st(name, **kw):
    return ParagraphStyle(name, **{"fontName": "SUI", "fontSize": 8.7, "leading": 12.0, "textColor": C(INK), **kw})


S = {"h2": st("h2", fontName="SUI-B", fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3, textColor=C(NAVY)),
     "body": st("body"), "small": st("small", fontSize=7.3, leading=9.6, textColor=C(INK2)),
     "bul": st("bul", leftIndent=10, bulletIndent=0, spaceAfter=2.4),
     "cell": st("cell", fontSize=7.7, leading=9.8), "cellb": st("cellb", fontName="SUI-B", fontSize=7.7, leading=9.8),
     "cap": st("cap", fontSize=7.2, leading=9.4, textColor=C(MUTED), spaceBefore=1, spaceAfter=3)}


def header_footer(c, doc):
    c.saveState()
    c.setFillColor(C(NAVY)); c.rect(0, Hp - 24 * mm, W, 24 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("SUI-B", 15); c.drawString(M, Hp - 12 * mm, "GOLD  |  CYCLES SINCE 1975")
    c.setFont("SUI", 9.5); c.drawString(M, Hp - 18 * mm, "Desk note: are the peaks and quiet periods repeating?")
    c.setFont("SUI-B", 9.5); c.drawRightString(W - M, Hp - 12 * mm, f"{now_date:%d %B %Y}")
    c.setFont("SUI", 8.5); c.drawRightString(W - M, Hp - 18 * mm, "Monthly average prices, USD/oz")
    c.setStrokeColor(C(GRID)); c.setLineWidth(0.6); c.line(M, 12 * mm, W - M, 12 * mm)
    c.setFillColor(C(MUTED)); c.setFont("SUI", 7)
    c.drawString(M, 8 * mm, "Companion to the 19 Nov summary note")
    c.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm, bottomMargin=14 * mm,
                      title="Gold cycles since 1975", author="Nikolay Gelshtein")
frame = Frame(M, 14 * mm, CW, Hp - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])


def table(rows, widths):
    data = [[Paragraph(f"<b>{h}</b>", S["cell"]) for h in rows[0]]]
    data += [[Paragraph(str(v), S["cellb"] if j == 0 else S["cell"]) for j, v in enumerate(r)] for r in rows[1:]]
    t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4), ("LEFTPADDING", (0, 0), (-1, -1), 4),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def img(path):
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=CW, height=CW * ih / iw)


def kpis(items):
    cells = [[Paragraph(f'<font size="7.1" color="{MUTED}">{k.upper()}</font><br/>'
                        f'<font name="SUI-B" size="14" color="{INK}">{v_}</font><br/>'
                        f'<font size="7.1" color="{INK2}">{sub}</font>', st("k", leading=15)) for k, v_, sub in items]]
    t = Table(cells, colWidths=[CW / len(items)] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C("#f4f3ef")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    return t


def callout(html):
    t = Table([[Paragraph(html, S["body"])]], colWidths=[CW])
    t.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, C(ORANGE)), ("BACKGROUND", (0, 0), (-1, -1), C("#fbf7f3")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    return t


mon = lambda p: pd.Period(p, "M").strftime("%b %Y")  # noqa: E731
gaps_major = [(pd.Period(b, "M") - pd.Period(a, "M")).n / 12 for a, b in (("1974-12", "1980-01"), ("1980-01", "2011-09"),
                                                                            ("2011-09", "2026-02"))]
p9 = {pk: R["paths"][pk][9] for pk in R["paths"] if len(R["paths"][pk]) > 9}

story = [kpis([
    ("Gold now", f"{now:,.0f}", f"{from_daily_peak:+.0%} from the 29 Jan close of 5,318"),
    ("Gap 1980 to 2011 peak", f"{gaps_major[1]:.0f} years", "2011 to 2026: " f"{gaps_major[2]:.0f} years"),
    ("1980 record, today's $", f"{rec80:,.0f}", "$850 on 21 Jan 1980, CPI-adjusted"),
    ("Real rate at the peak", f"{p26.rr_at_peak:+.1f}%", "1974-2011 peaks: all negative"),
    ("Fall after 9 months", f"{p26.fall_pct:+.0%}", "monthly averages; 1974 and 1983: -22%"),
]), Spacer(1, 7)]
story.append(callout(
    "<b>Bottom line. There is no fixed cycle; there is a repeating backdrop.</b> The gaps between gold's big peaks were "
    f"{gaps_major[0]:.0f}, {gaps_major[1]:.0f} and {gaps_major[2]:.0f} years, and between all nine bear-market peaks since "
    "1974 anywhere from 8 months to 14 years, so a rule like 'next rise in four years' has nothing behind it. What does "
    "repeat is the setting: every earlier big peak (1974, 1980, 2008, 2011) came with <b>negative real interest rates</b>, and "
    "each was followed by a sharp rise in real rates. The 2026 peak is the first with positive real rates "
    f"({p26.rr_at_peak:+.1f}%), carried by central-bank buying. The fall so far ({p26.fall_pct:.0%} in monthly averages after "
    f"nine months, {from_daily_peak:.0%} from the daily high) matches the start of earlier bear markets. What came next split "
    "two ways: in 1975-77 inflation stayed high, real rates went back below zero and gold rose sixfold; after 1980 and 2011 "
    "real rates kept rising and gold needed 26 and 9 years to regain its peak. Today the market's real yield (TIPS) is up "
    f"{tips_nov - tips_feb:.1f} points since the peak to {tips_nov:.1f}%, as real rates rose after 1980 and 2011, while "
    f"inflation is rising too ({R['now_infl']:.1f}%), as in the 1970s. The real-rate path decides, not the calendar."))
story += [Paragraph("Gold since 1975, with the rates behind it", S["h2"]), img(hist_png),
          Paragraph("Monthly averages (World Gold Council / LBMA via datahub to Oct 2026, then COMEX futures); real price "
                    "deflated by US CPI to October 2026. Shaded: the quiet periods compared on page 3. The real rate before "
                    "2003 is the 10-year Treasury yield minus CPI inflation over the past year; the TIPS yield is the "
                    "market's own measure since 2003.", S["cap"])]

# ---------------- page 2: peaks
story.append(PageBreak())
story += [Paragraph("The big peaks compared", S["h2"]), img(paths_png),
          Paragraph("Monthly averages relative to each peak month. Left: the climb over the five years before; right: the "
                    "first three years after. Black: 2026, with today's price as the last point.", S["cap"])]
rows = [["Peak (monthly average)", "Price", "In today's $", "Climb before", "Fall after", "Back at the peak",
         "Inflation", "Real rate", "Real rate, next 12 months"]]
for pk in list(MAJOR) + [NOW]:
    r = peaks.loc[pk]
    back = (f"{r.months_to_regain / 12:.1f} yrs" if pd.notna(r.months_to_regain) else "not yet")
    fall = f"{r.fall_pct:+.0%} in {r.months_to_trough:.0f} mo" + (" (so far)" if pk == NOW else "")
    rows.append([mon(pk), f"{r.peak_avg:,.0f}", f"{r.real_peak:,.0f}", f"{r.runup_pct:+.0%} in {r.runup_months:.0f} mo",
                 fall, back, f"{r.infl_at_peak:.1f}%", f"{r.rr_at_peak:+.1f}%",
                 f"{r.rr_change_peak_to_12m:+.1f} pt" + (f" (9 mo); TIPS {tips_nov - tips_feb:+.1f} pt" if pk == NOW else "")])
story += [table(rows, [0.13, 0.08, 0.10, 0.13, 0.15, 0.11, 0.08, 0.09, 0.13]),
          Paragraph(f"Daily records were higher than the monthly averages: $850 on 21 Jan 1980 (about ${rec80:,.0f} in today's "
                    f"money), $1,895 on 5 Sep 2011 (about ${rec11:,.0f}) and $5,318 (COMEX close) on 29 Jan 2026. In today's "
                    "dollars gold has only just fallen back to its 1980 record.", S["cap"])]
story.append(Paragraph("What made each peak, and what ended it", S["h2"]))
for t_ in [
    "<b>Dec 1974.</b> Gold had just been freed from the $35 Bretton Woods peg (1971) and inflation ran at 12% after the "
    "first oil shock, with real rates near -5%. It then fell 40% to Aug 1976 as inflation eased for a while. It was a pause, "
    "not an end: inflation came back and gold rose sixfold from the 1976 low to 1980.",
    "<b>Jan 1980.</b> Inflation 14%, real rates negative, the Iranian revolution and the Soviet invasion of Afghanistan. "
    "Volcker's Fed pushed rates to about 20% and real rates up by 4 points within a year; a second top in Sep 1980 started "
    "a fall of 53%. Gold needed 26 years to regain the 1980 average in dollars and until 2025 in real terms.",
    "<b>Mar 2008.</b> Falling real rates, a weak dollar and the start of the financial crisis. Forced selling in late 2008 "
    "cut 21%, but quantitative easing and near-zero rates sent gold to new highs within 18 months.",
    "<b>Sep 2011.</b> Real rates below zero after QE, the euro crisis and the US downgrade. The 2013 'taper tantrum' lifted "
    "real yields and a strong dollar followed: -39% over four years, then quiet until 2019.",
    f"<b>Feb 2026.</b> A climb of {p26.runup_pct:.0%} in {p26.runup_months:.0f} months from Oct 2022, with real rates "
    f"<i>positive</i> ({p26.rr_at_peak:+.1f}%): driven by central-bank buying after 2022, geopolitics and safe-haven "
    "demand rather than cheap money. The fall began as the Fed moved toward hikes and the dollar strengthened. By the "
    "backward-looking measure real rates dipped after the peak because inflation jumped; the TIPS yield rose.",
]:
    story.append(Paragraph(t_, S["bul"], bulletText="\u2022"))

# ---------------- page 3: calm periods, gaps, what to watch
story.append(PageBreak())
story.append(Paragraph("The quiet periods compared with now", S["h2"]))
rows = [["Period", "Length", "Low-high range", "Trend per year", "Volatility", "Inflation", "Real rate"]]
for c in R["calm"]:
    rr = f"{c['rr']:+.1f}%" + (f" (TIPS {c['tips']:.1f}%)" if c["tips"] is not None else "")
    rows.append([f"{c['name']} ({mon(c['from'])} to {mon(c['to'])})", f"{c['years']:.1f} yrs",
                 f"{c['low']:,.0f}-{c['high']:,.0f} ({c['range_pct']:.0%})", f"{c['trend_pa']:+.0%}", f"{c['vol']:.0%}",
                 f"{c['infl']:.1f}%", rr])
story += [table(rows, [0.34, 0.08, 0.17, 0.10, 0.09, 0.08, 0.14]),
          Paragraph("Volatility from monthly averages (lower than from daily prices). Real rate: average of 10-year yield "
                    "minus CPI inflation over the period. Periods chosen by eye from the chart.", S["cap"])]
calm = {c["name"]: c for c in R["calm"]}
c_now, c74 = calm["Now: since the 2026 peak"], calm["After the 1974 peak"]
story.append(Paragraph(
    f"<b>Now is not quiet yet.</b> The real quiet periods (1983-2001, 2013-19, 2020-23) had volatility around 10% and almost "
    f"no trend. Since February 2026 volatility is {c_now['vol']:.0%} and the trend {c_now['trend_pa']:+.0%} a year: that "
    f"looks like 1975-77 ({c74['vol']:.0%}, {c74['trend_pa']:+.0%} a year), the shake-out after the 1974 peak, not like a "
    "settled range. Quiet periods came after the selling was done and real rates had stopped rising: in 1983-2001 real rates "
    "averaged over 4% and gold drifted lower for 18 years; in 2013-19 they sat near 1% and gold went sideways.", S["body"]))

rows = [["Bear market peak", "Gap since the previous peak", "Fall", "Time to bottom"]]
prev = None
for r in R["peaks"]:
    gap = "" if prev is None else f"{(pd.Period(r['peak'], 'M') - pd.Period(prev, 'M')).n / 12:.1f} years"
    rows.append([mon(r["peak"]), gap, f"{r['fall_pct']:+.0%}" + (" (so far)" if r["peak"] == NOW else ""),
                 f"{r['months_to_trough']} months"])
    prev = r["peak"]
story.append(KeepTogether([Paragraph("Is there a shrinking cycle?", S["h2"]),
                           Paragraph("Every fall of 20% or more in monthly averages since 1974 (a bear market ends when "
                                     "gold rises 20% from its low):", S["body"]), Spacer(1, 2),
                           table(rows, [0.25, 0.30, 0.20, 0.25]),
                           Paragraph("The gaps run 5, 0.7, 2.4, 4.8, 8.2, 12.1, 3.5 and 14.4 years: no regular rhythm, and "
                                     "no shrinking series. With two or three big peaks almost any pattern fits, so a "
                                     "calendar rule cannot be tested.", S["cap"])]))
story.append(KeepTogether([Paragraph("Which past does today look like?", S["h2"]), table([
    ["Signal", "1974-76: pause, then much higher", "1980 and 2011: long bear", "Now"],
    ["Real rates", "Negative and falling back", "Turned sharply positive",
     f"TIPS {tips_nov:.1f}%, {tips_nov - tips_feb:+.1f} pt since the peak"],
    ["Inflation", "High and rising again", "Falling", f"{R['now_infl']:.1f}% and rising"],
    ["Central bank", "Behind the curve", "Hiking hard (Volcker; taper)", "Hiking; Waller floats 50 bp"],
    ["Dollar", "Weak", "Strong", "Strongest since Apr 2025"],
    ["Fall after 9 months", "-22%", "1980: -2% then -43%; 2011: -10% then -39%", f"{p26.fall_pct:.0%}"],
], [0.18, 0.27, 0.29, 0.26]), Paragraph(
    "Three of four signals point to the 1980 and 2011 path; inflation points to 1974-76. The thing to watch is whether "
    "the Fed stays ahead of inflation: if real rates keep rising, history says years of weakness or sideways trade; if "
    "inflation outruns the Fed and real rates fall, the 1970s pattern returns.", S["body"])]))
story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
    "Monthly average gold prices: World Gold Council / LBMA data via datahub.io (to Oct 2026), November 2026 as the COMEX "
    "futures average to 19 Nov; the two series agree within 1.6% where they overlap. CPI (October 2025 was never published "
    "and is interpolated), 10-year yields and TIPS yields: FRED. Bear markets by the 20/20 rule on monthly averages. Daily "
    "records: LBMA fixes (1980, 2011) and the COMEX close (2026). Historical context from standard accounts of each period; "
    "with this few cycles, the comparisons describe, they do not forecast.", S["small"])]))
doc.build(story)
print("wrote", OUT)
