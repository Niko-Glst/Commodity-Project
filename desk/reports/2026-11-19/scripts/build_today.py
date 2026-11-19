"""Gold desk summary note, 19 Nov 2026: why gold is falling and what is going on.

Usage (from desk/): python reports/2026-11-19/scripts/build_today.py reports/2026-11-19 <out.pdf>
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
BLUE, ORANGE, RED = "#1c5cab", "#eb6834", "#d03b3b"     # validated pair for two-series panels

T = json.load(open(f"{N}/today.json"))
ASOF = f"{T['asof']} ET"
d = pd.read_csv(f"{N}/data/daily.csv", index_col=0, parse_dates=True)
fred = pd.read_csv(f"{N}/data/fred.csv", index_col=0, parse_dates=True)
today = pd.Timestamp(T["today"])
now, yc = T["now"], T["y_close"]
HOL = ["2026-11-26", "2026-12-25"]
bday = pd.offsets.CustomBusinessDay(holidays=HOL)
fwd_dates = pd.date_range(today + bday, periods=21, freq=bday)
fan = {int(k): np.array(v) for k, v in T["fan"].items()}
X = T["cross"]

for fp in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 8.3, "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False, "legend.fontsize": 7.6,
})


def save(fig, name):
    path = f"{N}/{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# drivers chart: gold, real yield and breakeven, dollar (stacked panels, one axis each)
start = pd.Timestamp("2026-09-01")
gold = d["GC=F"].dropna().loc[start:].copy()
gold.iloc[-1] = now
real, be = fred["DFII10"].dropna().loc[start:], fred["T10YIE"].dropna().loc[start:]
dxy = d["DX-Y.NYB"].dropna().loc[start:]
fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(7.2, 4.3), sharex=True, gridspec_kw={"height_ratios": [1.5, 1, 1]})
a1.plot(gold.index[:-1], gold.values[:-1], color=INK, lw=1.4)
a1.plot(gold.index[-2:], gold.values[-2:], color=ORANGE, lw=1.4)
a1.scatter([gold.index[-1]], [now], s=22, color=ORANGE, edgecolor="white", lw=1.1, zorder=4)
a1.annotate(f"{now:,.0f}", (gold.index[-1], now), xytext=(5, 0), textcoords="offset points", fontsize=7.4, va="center")
a1.set_ylabel("Gold, $/oz")
a1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
a2.plot(real.index, real.values, color=BLUE, lw=1.4, label="10-year real yield (TIPS)")
a2.plot(be.index, be.values, color=ORANGE, lw=1.4, label="10-year breakeven inflation")
for s_, c_ in ((real, BLUE), (be, ORANGE)):
    a2.annotate(f"{s_.iloc[-1]:.2f}%", (s_.index[-1], s_.iloc[-1]), xytext=(5, 0), textcoords="offset points",
                fontsize=7.2, va="center", color=INK)
a2.set_ylabel("%")
a2.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=7.2)
fig.subplots_adjust(hspace=0.32)
a3.plot(dxy.index, dxy.values, color=INK2, lw=1.4)
a3.annotate(f"{dxy.iloc[-1]:.1f}", (dxy.index[-1], dxy.iloc[-1]), xytext=(5, 0), textcoords="offset points",
            fontsize=7.2, va="center")
a3.set_ylabel("Dollar index")
a3.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
for a in (a1, a2, a3):
    for t_, lab in ((pd.Timestamp("2026-10-06"), "6 Oct: stocks peak"), (pd.Timestamp("2026-11-18"), "18 Nov: Fed minutes")):
        a.axvline(t_, color=MUTED, lw=0.6, ls=":")
        if a is a1:
            a.text(t_, a.get_ylim()[1], f" {lab}", fontsize=6.9, color=MUTED, va="top")
drivers_png = save(fig, "s_drivers")

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
     "bul": st("bul", leftIndent=12, bulletIndent=0, spaceAfter=2.6),
     "cell": st("cell", fontSize=7.9, leading=10.1), "cellb": st("cellb", fontName="SUI-B", fontSize=7.9, leading=10.1),
     "cap": st("cap", fontSize=7.3, leading=9.5, textColor=C(MUTED), spaceBefore=1, spaceAfter=3)}


def header_footer(c, doc):
    c.saveState()
    c.setFillColor(C(NAVY)); c.rect(0, Hp - 24 * mm, W, 24 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("SUI-B", 15); c.drawString(M, Hp - 12 * mm, "GOLD  |  GC=F")
    c.setFont("SUI", 9.5); c.drawString(M, Hp - 18 * mm, "Desk note: why gold is falling, and what is going on")
    c.setFont("SUI-B", 9.5); c.drawRightString(W - M, Hp - 12 * mm, f"{today:%d %B %Y}, {ASOF}")
    c.setFont("SUI", 8.5); c.drawRightString(W - M, Hp - 18 * mm, "Prices: COMEX gold futures, USD/oz")
    c.setStrokeColor(C(GRID)); c.setLineWidth(0.6); c.line(M, 12 * mm, W - M, 12 * mm)
    c.setFillColor(C(MUTED)); c.setFont("SUI", 7)
    c.drawString(M, 8 * mm, "Previous notes: weekly 13 Nov, flash 18 Nov 2026")
    c.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm, bottomMargin=14 * mm,
                      title="Gold desk note, 19 Nov 2026", author="Nikolay Gelshtein")
frame = Frame(M, 14 * mm, CW, Hp - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])


def table(rows, widths):
    data = [[Paragraph(f"<b>{h}</b>", S["cell"]) for h in rows[0]]]
    data += [[Paragraph(str(x), S["cellb"] if j == 0 else S["cell"]) for j, x in enumerate(r)] for r in rows[1:]]
    t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6), ("LEFTPADDING", (0, 0), (-1, -1), 4),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def img(path):
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=CW, height=CW * ih / iw)


def kpis(items):
    cells = [[Paragraph(f'<font size="7.1" color="{MUTED}">{k.upper()}</font><br/>'
                        f'<font name="SUI-B" size="14" color="{col}">{v_}</font><br/>'
                        f'<font size="7.1" color="{INK2}">{sub}</font>', st("k", leading=15)) for k, v_, sub, col in items]]
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


def nth(q):
    n = int(round(q * 100))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


re_, be_, hy, f13, fl = T["real"], T["breakeven"], T["hy"], T["f13"], T["flash"]
low_since = pd.Timestamp(T["low_since"])

story = [kpis([
    ("Now", f"{now:,.0f}", f"{today:%d %b}, {ASOF}", INK),
    ("Today", f"{T['r_today']:+.1%}", f"low {T['session_low']:,.0f} at {T['session_low_t']} ET", RED),
    ("Two days", f"{T['two_day']:+.1%}", f"from {X['GC=F']['now'] / (1 + T['two_day']):,.0f} on 17 Nov", RED),
    ("From record", f"{now / T['peak'] - 1:+.0%}", f"{T['peak']:,.0f} on 29 Jan 2026", RED),
    ("Model vol", f"{T['vol_now']:.1%}", f"{nth(T['vol_pct'])} percentile since 2003", INK),
]), Spacer(1, 7)]

story.append(callout(
    f"<b>Bottom line.</b> Gold is down {abs(T['r_today']):.1%} at <b>{now:,.0f}</b> ({ASOF}), {abs(T['two_day']):.1%} in two "
    f"days and {abs(now / T['peak'] - 1):.0%} below its January record, at its lowest since {low_since:%B %Y}. Two forces "
    "are at work. Since early October the <b>inflation hedge has been unwinding</b>: oil fell, 10-year inflation "
    f"expectations dropped {abs(be_['peak_bp']):.0f} bp, and silver, copper and bitcoin fell even harder than gold in a broad "
    "de-risking. This week a <b>rate shock</b> came on top: the October Fed minutes showed almost all "
    f"officials expect more hikes, Governor Waller floated a half-point move in December, and the 10-year real yield "
    f"jumped {re_['wk_bp']:.0f} bp in a week, while the dollar is at its strongest since April 2025. Today's drop is an "
    f"ordinary day at {T['vol_now']:.0%} volatility, but the price now sits just below the 13 Nov forecast's 90% range for "
    f"today ({nth(f13['pit'])} percentile), a 1-in-20 outcome. Next: speculators' positions on Friday and the Fed on 8-9 Dec."))

story += [Paragraph("Gold and its drivers since September", S["h2"]), img(drivers_png),
          Paragraph(f"Daily closes; today at {ASOF}. Real yield and breakeven: FRED, to {pd.Timestamp(re_['date']):%d %b} and "
                    f"{pd.Timestamp(be_['date']):%d %b}. Since 6 Oct the fall in yields came from lower inflation expectations; "
                    "this week real yields turned sharply up.", S["cap"])]

story.append(Paragraph("Why gold is falling", S["h2"]))
for t_ in [
    "<b>1. The Fed is turning more hawkish.</b> The minutes of the 27-28 Oct meeting, out yesterday, say almost all "
    "officials judged further hikes \"would likely be appropriate\"; two voted for a hike in October and a couple saw a "
    "larger December move as possible (CNBC). Governor Waller said the Fed should consider a half-point hike and may have "
    "to \"shock\" markets; St. Louis Fed President Musalem sees up to a full point by spring 2027 (CNBC). Futures price a "
    "25 bp December hike at about 92% and 50 bp at about 8% (CME FedWatch via InvestmentNews).",
    f"<b>2. Real yields jumped.</b> The 10-year TIPS yield rose {re_['wk_bp']:.0f} bp in a week to {re_['now']:.2f}%; outside "
    f"2026 it was last this high in {pd.Timestamp(re_['last_higher_pre2026']):%B %Y}. The 2-year yield rose "
    f"{T['two_year']['wk_bp']:.0f} bp. Gold pays no interest, so every rise in real yields raises the cost of holding it.",
    f"<b>3. The dollar is strong.</b> The dollar index is at {T['dxy']['now']:.1f}, its highest since April 2025. Gold is "
    "priced in dollars: a stronger dollar makes it dearer for everyone else.",
    f"<b>4. The inflation hedge is losing its point.</b> Since 6 Oct, 10-year breakeven inflation fell "
    f"{abs(be_['peak_bp']):.0f} bp to {be_['now']:.2f}% as oil dropped (WTI {X['CL=F']['since_peak']:+.0%}; Brent about -20% "
    "in November, Kitco). Investors who held gold against inflation have less reason to.",
    f"<b>5. Broad de-risking.</b> Since 6 Oct silver fell {abs(X['SI=F']['since_peak']):.0%}, copper "
    f"{abs(X['HG=F']['since_peak']):.0%} and bitcoin {abs(X['BTC-USD']['since_peak']):.0%}, against "
    f"{abs(X['GC=F']['since_peak']):.0%} for gold. The high-yield credit spread widened {hy['peak_bp']:.0f} bp and the VIX is "
    f"at {X['^VIX']['now']:.0f}. Gold is \"again being treated as a liquidity asset\" (KCM Trade, CNBC). Speculators were "
    f"still net long {T['cftc']['net']:,.0f} contracts on {pd.Timestamp(T['cftc']['date']):%d %b}, mid-range for the past "
    "two years, so there is room for more selling; Friday's report covers this week.",
]:
    story.append(Paragraph(t_, S["bul"]))

# ---------------- page 2
story.append(PageBreak())
wk = d["GC=F"].dropna().loc["2026-11-13":].copy()
wk.iloc[-1] = now
notes = {
    "2026-11-13": "Weekly note: forecast logged at the close",
    "2026-11-16": "Tech-led stock sell-off (S&amp;P 500 -1.9%); Fed Chair Warsh gives no clear December signal (Kitco)",
    "2026-11-17": "NY Fed's Williams: the Fed will likely need to raise rates again; Nvidia beats after the close",
    "2026-11-18": "Below $3,800 in Asian trading; dollar index at a 19-month high; Fed minutes at 14:00 ET: almost all "
                  "officials see more hikes, Waller floats 50 bp",
    "2026-11-19": f"New low {T['session_low']:,.0f} at {T['session_low_t']} ET; silver and copper flat; S&amp;P 500 "
                  f"{X['^GSPC']['today']:+.1%} ({ASOF}, not a close)",
}
rows = [["Date", "Close", "Day", "What happened"]]
for d_, v_ in wk.items():
    prev = d["GC=F"].dropna().loc[:d_].iloc[-2]
    rows.append([f"{d_:%a %d %b}", f"{v_:,.0f}", "" if d_ == wk.index[0] else f"{v_ / prev - 1:+.1%}",
                 notes.get(f"{d_:%Y-%m-%d}", "")])
story += [Paragraph("This week", S["h2"]), table(rows, [0.12, 0.09, 0.08, 0.71])]

rows = [["Market", "Now", "Since 6 Oct", "Since 13 Nov", "Today"]]
spec = [("GC=F", "Gold", "{:,.0f}", "pct"), ("SI=F", "Silver", "{:.2f}", "pct"), ("HG=F", "Copper", "{:.2f}", "pct"),
        ("CL=F", "WTI crude", "{:.2f}", "pct"), ("DX-Y.NYB", "Dollar index", "{:.2f}", "pct"),
        ("^TNX", "US 10Y yield", "{:.2f}%", "bp"), ("^GSPC", "S&amp;P 500", "{:,.0f}", "pct"),
        ("^VIX", "VIX", "{:.1f}", "pts"), ("^GVZ", "GVZ (gold implied vol)", "{:.1f}", "pts"),
        ("BTC-USD", "Bitcoin", "{:,.0f}", "pct")]
for t_, name, fmt, unit in spec:
    x = X[t_]
    f_ = {"pct": lambda v: f"{v:+.1%}", "bp": lambda v: f"{100 * v:+.0f} bp", "pts": lambda v: f"{v:+.1f}"}[unit]
    rows.append([name, fmt.format(x["now"]), f_(x["since_peak"]), f_(x["since_13nov"]), f_(x["today"])])
story += [Paragraph("Across markets", S["h2"]), table(rows, [0.28, 0.18, 0.18, 0.18, 0.18]),
          Paragraph(f"Latest prints at {ASOF}; the 10-year yield and GVZ as last published. Real yields and credit spreads "
                    f"come from FRED with a one-day lag: high-yield spread {hy['now']:.2f}% on "
                    f"{pd.Timestamp(hy['date']):%d %b}, {hy['peak_bp']:+.0f} bp since 6 Oct.", S["cap"])]

story.append(Paragraph("What the model says", S["h2"]))
story.append(Paragraph(
    f"Today's move is {abs(T['z_today']):.1f} times the model's expected daily move, inside today's 90% range "
    f"({T['band90'][0]:,.0f} to {T['band90'][1]:,.0f}): the size of the day is normal at this volatility. What is unusual is "
    f"the run: the weekly forecast of 13 Nov put today's 90% range at {f13['band_k'][0]:,.0f} to {f13['band_k'][1]:,.0f}, and "
    f"gold now sits at its {nth(f13['pit'])} percentile; tomorrow's close is the end of that forecast's week "
    f"(90% range {f13['band_week'][0]:,.0f} to {f13['band_week'][1]:,.0f}). The flash note of 18 Nov gave a "
    f"{fl['touch3700_week']:.0%} chance of a close below $3,700 within a week; gold is below it today. Model volatility is "
    f"{T['vol_now']:.1%}, and the options market agrees: the GVZ is {T['gvz']['last']:.1f}, or {T['gvz']['corrected']:.1%} after "
    "the desk's premium correction.", S["body"]))
rows = [["Horizon", "Ends", "5%", "25%", "Median", "75%", "95%"]]
for h_, name in ((5, "1 week"), (21, "1 month")):
    i = h_ - 1
    rows.append([name, f"{fwd_dates[i]:%d %b}"] + [f"{fan[k][i]:,.0f}" for k in (5, 25, 50, 75, 95)])
tw, tm = T["touch_week"], T["touch"]
lv = [["Level", "Within a week", "Within a month"]] + [[f"${int(k):,}", f"{tw[k]:.0%}", f"{tm[k]:.0%}"]
                                                     for k in ("3500", "3600", "3800", "4000")]
story += [Spacer(1, 3), table(rows, [0.16, 0.12, 0.144, 0.144, 0.144, 0.144, 0.144]), Spacer(1, 4),
          table(lv, [0.30, 0.35, 0.35]),
          Paragraph("Ranges and the chance of a close through each level, from 20,000 simulated paths with this morning's "
                    "price as the latest observation. No drift: the model sizes moves, it does not call direction.", S["cap"])]

# ---------------- page 3
story.append(PageBreak())
story.append(Paragraph("What would change the picture", S["h2"]))
for t_ in [
    "<b>Real yields and the dollar turn.</b> The two price drivers of this week. A softer inflation print or a Fed that "
    "pushes back on a half-point move would take pressure off both.",
    "<b>Speculators wash out.</b> Managed money was still net long on 10 Nov. Friday's CFTC report (positions of 17 Nov) "
    "shows how much of the long was sold this week; a large cut means less selling left.",
    "<b>Stress spreads or fades.</b> If high-yield spreads keep widening and the VIX curve stays inverted, gold can keep "
    "being sold to raise cash. If they calm, the liquidity selling stops.",
    "<b>Buyers on the dip.</b> UBS said on 16 Nov that with gold near the year's lows, further downside is \"less "
    "attractive as a trade\" (Investing.com). Central-bank buying is often cited as a floor; no new figures this week.",
]:
    story.append(Paragraph(t_, S["bul"]))

ev = [["Date or level", "Why it matters"],
      ["Thu 19 Nov, 16:30 ET: money market fund assets (ICI)", "Whether investors moved into cash this week"],
      ["Fri 20 Nov, 15:30 ET: CFTC positioning (17 Nov)", "How much speculators sold during the drop"],
      ["Fri 20 Nov: end of the 13 Nov forecast week", f"Its 90% range for Friday's close starts at {f13['band_week'][0]:,.0f}"],
      ["Thu 26 Nov: Thanksgiving", "US holiday: no COMEX settlement, thin trading around it"],
      ["Tue-Wed 8-9 Dec: FOMC", "25 bp is priced; a half-point move is not"],
      ["$3,600", f"{tw['3600']:.0%} of model paths close below it within a week, {tm['3600']:.0%} within a month"],
      ["$3,800", f"Lost on 18 Nov; {tm['3800']:.0%} of paths get back above it within a month"]]
story.append(KeepTogether([Paragraph("Watch list", S["h2"]), table(ev, [0.42, 0.58])]))
story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
    "Model: the desk's GARCH(1,1) with Student-t shocks and no drift, fitted on daily COMEX gold futures closes since "
    "2003; today's move is scored against the fit to yesterday's close; the 13 Nov comparison re-simulates that week's "
    f"stored fit with the same seed. Ranges use this morning's price ({ASOF}, not a close) and 20,000 paths, seed 42. "
    "Data: Yahoo Finance (prices), FRED (real yield, breakeven, 2-year yield, high-yield spread), CFTC (positioning). "
    "News: CNBC (Fed minutes, Waller, Musalem, 18 Nov), InvestmentNews (FedWatch), Kitco (16-17 Nov), Investing.com "
    "(UBS), CNBC (KCM Trade, 18 Nov). The cross-asset and flow analysis behind points 4 and 5 is in the rotation side "
    "project (branch copper-tech, rotation/).", S["small"])]))

doc.build(story)
print("wrote", OUT)
