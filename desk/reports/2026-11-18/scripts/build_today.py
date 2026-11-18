"""Gold flash note, 18 Nov 2026: the overnight break below $3,800, against the 13 Nov forecast.

Usage (from desk/): python reports/2026-11-18/scripts/build_today.py reports/2026-11-18 <out.pdf>
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

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

N, OUT = sys.argv[1], sys.argv[2]
DESK = Path(__file__).resolve().parents[3]

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
B100, B200, B300, B550 = "#cde2fb", "#9ec5f4", "#6da7ec", "#1c5cab"
ORANGE, RED, GREEN = "#eb6834", "#d03b3b", "#006300"

T = json.load(open(f"{N}/today.json"))
ASOF = f"{T['asof']} ET"
daily = pd.read_csv(f"{N}/data/daily.csv", index_col=0, parse_dates=True)
gold = daily["GC=F"].dropna()
volp = pd.read_csv(f"{N}/vol_path.csv", index_col=0, parse_dates=True)
intra = pd.read_csv(f"{N}/data/gold_5m.csv", index_col=0)
intra.index = pd.to_datetime(intra.index, utc=True).tz_convert("America/New_York").tz_localize(None)
live = [json.loads(x) for x in open(DESK / "store" / "live.jsonl")]
rec13 = [x for x in live if x["origin"] == "2026-11-13"][0]

now, yc = T["now"], T["y_close"]
today = pd.Timestamp(T["today"])
sess_start = pd.Timestamp("2026-11-17 18:00")
HOL = ["2026-11-26", "2026-12-25"]                                  # COMEX closed: Thanksgiving, Christmas
bday = pd.offsets.CustomBusinessDay(holidays=HOL)
fwd_dates = pd.date_range(today + bday, periods=21, freq=bday)
dates13 = pd.date_range(pd.Timestamp("2026-11-13") + bday, periods=21, freq=bday)
fan = {int(k): np.array(v) for k, v in T["fan"].items()}
fan13 = {int(k): np.array(v) for k, v in rec13["fan"].items()}
touch, touch_w, f13, gv, cl = T["touch"], T["touch_week"], T["f13"], T["gvz"], T["clustering"]

# ---------------------------------------------------------------- chart style
for fp in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"):
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 8.5, "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "legend.frameon": False, "legend.fontsize": 7.8,
})
usd = matplotlib.ticker.FuncFormatter(lambda v_, _: f"{v_:,.0f}")


def save(fig, name):
    path = f"{N}/{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# 1. intraday: Monday to Wednesday sessions, 5-minute closes
seg = intra.loc["2026-11-15 18:00":]
before, todays = seg.loc[:sess_start - pd.Timedelta(minutes=1)], seg.loc[sess_start:]
fig, ax = plt.subplots(figsize=(7.2, 2.3))
band_x = [sess_start, todays.index[-1] + pd.Timedelta(hours=3)]
ax.fill_between(band_x, T["band90"][0], T["band90"][1], color=B100, lw=0, zorder=0,
                label="Today's 90% range from Tue close")
ax.plot(before.index, before["Close"], color=INK2, lw=1.1, label="Mon and Tue sessions")
ax.plot(todays.index, todays["Close"], color=ORANGE, lw=1.6, label="Today's session")
ax.axhline(yc, color=INK2, lw=0.7, ls=(0, (3, 2)))
ax.text(pd.Timestamp("2026-11-17 13:30"), yc + 4, f"Tue close {yc:,.0f}", fontsize=7.2, color=INK2, va="bottom",
        ha="right", bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
ax.axhline(3800, color=RED, lw=0.7, ls=":")
ax.text(seg.index[0], 3800, " $3,800", fontsize=7.2, color=RED, va="bottom")
for t_ in (pd.Timestamp("2026-11-16 17:00"), pd.Timestamp("2026-11-17 17:00")):
    ax.axvline(t_, color=AXIS, lw=0.8)
for t_, lab in ((pd.Timestamp("2026-11-17 08:30"), "Retail sales"),
                (pd.Timestamp("2026-11-17 16:00"), "Nvidia")):
    ax.axvline(t_, color=MUTED, lw=0.6, ls=":")
    ax.text(t_, ax.get_ylim()[1], f" {lab}", fontsize=7, color=MUTED, va="top")
ax.scatter([todays.index[-1]], [now], s=24, color=ORANGE, edgecolor="white", lw=1.2, zorder=4)
ax.annotate(f"{now:,.0f}", (todays.index[-1], now), xytext=(5, 0), textcoords="offset points",
            fontsize=7.8, color=INK, va="center")
ax.yaxis.set_major_formatter(usd)
ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %H:%M"))
ax.set_ylabel("USD/oz")
ax.set_xlim(seg.index[0], seg.index[-1] + pd.Timedelta(hours=3))
h_, l_ = ax.get_legend_handles_labels()
ax.legend([h_[1], h_[2], h_[0]], [l_[1], l_[2], l_[0]], loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3)
intra_png = save(fig, "t_intraday")

# 2. the 13 Nov forecast cone, what happened, and the new cone from this morning
hist = gold.loc["2026-09-15":"2026-11-17"]
fig, ax = plt.subplots(figsize=(7.2, 2.35))
ax.fill_between(dates13, fan13[5], fan13[95], color=GRID, lw=0, label="13 Nov forecast, 90% range")
ax.fill_between(fwd_dates, fan[5], fan[95], color=B100, lw=0, label="From this morning, 90% range")
ax.fill_between(fwd_dates, fan[25], fan[75], color=B200, lw=0, label="50% range")
ax.plot(fwd_dates, fan[50], color=B550, lw=1.0, ls=(0, (3, 2)))
ax.plot(hist.index, hist.values, color=INK, lw=1.3, label="Daily close")
ax.plot([hist.index[-1], today], [hist.iloc[-1], now], color=ORANGE, lw=1.3)
ax.scatter([today], [now], s=24, color=ORANGE, edgecolor="white", lw=1.2, zorder=4, label=f"This morning, {ASOF}")
for lvl in (3600, 3700, 3800, 4000):
    ax.axhline(lvl, color=MUTED, lw=0.6, ls=":")
    ax.text(fwd_dates[-1] + pd.Timedelta(days=1), lvl, f"{lvl:,}", fontsize=7, color=MUTED, va="center")
ax.yaxis.set_major_formatter(usd)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.set_ylabel("USD/oz")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, fontsize=7.2)
cone_png = save(fig, "t_cone")

# 3. clustering: daily moves against the model's +/-2 sigma band, and volatility
start = pd.Timestamp("2026-05-01")
ret = np.log(gold).diff().loc[start:].copy()
ret.iloc[-1] = np.log(now / yc)
cs = (volp["vol_model"].reindex(ret.index) / np.sqrt(252)).copy()
cs.iloc[-1] = T["sigma_day"]
outside = ret.abs() > 2 * cs
fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 2.6), sharex=True, gridspec_kw={"height_ratios": [1.6, 1]})
a1.fill_between(ret.index, -2 * cs, 2 * cs, color=B100, lw=0, step="mid")
col = np.where(outside, RED, INK2)
col[-1] = ORANGE
a1.bar(ret.index, ret, width=1.0, color=col, lw=0)
a1.axhline(0, color=AXIS, lw=0.6)
a1.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
a1.set_ylabel("Daily move")
a1.legend(handles=[Patch(color=B100, label="Model ±2σ for that day"), Patch(color=INK2, label="Inside"),
                   Patch(color=RED, label="Outside ±2σ"), Patch(color=ORANGE, label=f"Today, {ASOF}")],
          loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4)
vm, vr = volp["vol_model"].loc[start:], volp["vol_real21"].loc[start:]
a2.plot(vr.index, vr.values, color=INK2, lw=1.1, label="Realised, past 21 days")
a2.plot(vm.index, vm.values, color=B550, lw=1.6, label="Model, day ahead")
a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
a2.set_ylabel("Vol, annualised")
a2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
a2.set_ylim(0.10, max(vm.max(), vr.max()) * 1.05)
a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
clu_png = save(fig, "t_cluster")

# ---------------------------------------------------------------- PDF
pdfmetrics.registerFont(TTFont("SUI", "C:/Windows/Fonts/segoeui.ttf"))
pdfmetrics.registerFont(TTFont("SUI-B", "C:/Windows/Fonts/segoeuib.ttf"))
registerFontFamily("SUI", normal="SUI", bold="SUI-B", italic="SUI", boldItalic="SUI-B")
W, Hp = A4
M = 16 * mm
CW = W - 2 * M
C = colors.HexColor


def st(name, **kw):
    return ParagraphStyle(name, **{"fontName": "SUI", "fontSize": 8.8, "leading": 12.2, "textColor": C(INK), **kw})


S = {
    "h2": st("h2", fontName="SUI-B", fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3, textColor=C(NAVY)),
    "body": st("body"), "small": st("small", fontSize=7.4, leading=9.8, textColor=C(INK2)),
    "bul": st("bul", leftIndent=10, bulletIndent=0, spaceAfter=2.2),
    "cell": st("cell", fontSize=8.1, leading=10.4), "cellb": st("cellb", fontName="SUI-B", fontSize=8.1, leading=10.4),
    "cap": st("cap", fontSize=7.4, leading=9.6, textColor=C(MUTED), spaceBefore=1, spaceAfter=3),
}


def header_footer(c, doc):
    c.saveState()
    c.setFillColor(C(NAVY)); c.rect(0, Hp - 24 * mm, W, 24 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("SUI-B", 15); c.drawString(M, Hp - 12 * mm, "GOLD  |  GC=F")
    c.setFont("SUI", 9.5); c.drawString(M, Hp - 18 * mm, "Desk note: flash, gold breaks below $3,800")
    c.setFont("SUI-B", 9.5); c.drawRightString(W - M, Hp - 12 * mm, f"{today:%d %B %Y}, {ASOF}")
    c.setFont("SUI", 8.5); c.drawRightString(W - M, Hp - 18 * mm, "Prices: COMEX gold futures, USD/oz")
    c.setStrokeColor(C(GRID)); c.setLineWidth(0.6); c.line(M, 12 * mm, W - M, 12 * mm)
    c.setFillColor(C(MUTED)); c.setFont("SUI", 7)
    c.drawString(M, 8 * mm, "Previous note: weekly, 13 Nov 2026")
    c.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm, bottomMargin=14 * mm,
                      title="Gold desk note, 18 Nov 2026", author="Nikolay Gelshtein")
frame = Frame(M, 14 * mm, CW, Hp - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])


def table(rows, widths):
    data = [[Paragraph(f"<b>{h}</b>", S["cell"]) for h in rows[0]]]
    data += [[Paragraph(str(c_), S["cellb"] if j == 0 else S["cell"]) for j, c_ in enumerate(r)] for r in rows[1:]]
    t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def img(path):
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=CW, height=CW * ih / iw)


def kpis(items):
    cells = [[Paragraph(f'<font size="7.2" color="{MUTED}">{k.upper()}</font><br/>'
                        f'<font name="SUI-B" size="14" color="{col}">{v_}</font><br/>'
                        f'<font size="7.2" color="{INK2}">{sub}</font>', st("k", leading=15))
              for k, v_, sub, col in items]]
    t = Table(cells, colWidths=[CW / len(items)] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C("#f4f3ef")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    return t


def callout(html):
    t = Table([[Paragraph(html, S["body"])]], colWidths=[CW])
    t.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, C(ORANGE)), ("BACKGROUND", (0, 0), (-1, -1), C("#fbf7f3")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    return t


def bullets(items):
    return [Paragraph(t_, S["bul"], bulletText="\u2022") for t_ in items]


pct = lambda a_, b_: f"{b_ / a_ - 1:+.1%}"  # noqa: E731


def nth(p_):
    n_ = int(round(p_ * 100))
    return f"{n_}{'th' if 10 <= n_ % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n_ % 10, 'th')}"

low_since = pd.Timestamp(T["low_since"])
d13, d17, dn = daily.loc["2026-11-13"], daily.loc["2026-11-17"], daily.iloc[-1]
es_today = dn["ES=F"] / d17["ES=F"] - 1
dxy_now = dn["DX-Y.NYB"]
silver_today = dn["SI=F"] / d17["SI=F"] - 1
vol_pct_now = float((volp["vol_model"] < T["vol_next_now"]).mean())

# ---------------- page 1
story = [kpis([
    ("Now", f"{now:,.0f}", f"{today:%d %b}, {ASOF}", INK),
    ("Today", f"{T['r_today']:+.1%}", f"from {yc:,.0f} (Tue close)", RED),
    ("Size of move", f"{abs(T['z_today']):.1f}σ", f"about a 1-in-{T['one_in']:.0f}-day move", INK),
    ("Model vol", f"{T['vol_next_now']:.1%}", f"{nth(vol_pct_now)} percentile since 2003", INK),
    ("From peak", f"{now / T['peak'] - 1:+.1%}", f"{T['peak']:,.0f} on 29 Jan 2026", RED),
]), Spacer(1, 7)]

story.append(callout(
    f"<b>Bottom line.</b> Gold is down {abs(T['r_today']):.1%} this morning at <b>{now:,.0f}</b>, through $3,800 and "
    f"at its lowest since {low_since:%d %B %Y}. "
    f"The move is {abs(T['z_today']):.1f} times the model's expected daily move: just below today's 90% range "
    f"({T['band90'][0]:,.0f} to {T['band90'][1]:,.0f}), well inside its 98% range. The driver is the Fed: a December "
    f"hike is priced at about 96% and the dollar index is at {dxy_now:.2f}, its highest since April 2025. It is not a "
    f"stock-market liquidation: S&amp;P 500 futures are up {es_today:.1%} since Tuesday's close after Nvidia's results, "
    f"while gold fell. The 13 Nov forecast holds: this morning's price is at its <b>{nth(f13['pit'])} percentile</b> "
    f"for today, and that note gave a {f13['touch3800_month']:.0%} chance of trading below $3,800 within a month. "
    f"Next: the FOMC minutes at 14:00 ET today."))

story += [Paragraph("Today's session", S["h2"]), img(intra_png),
          Paragraph(f"5-minute closes, New York time; today's session opened Tuesday 18:00 ET. Low so far "
                    f"{T['session_low']:,.1f} at {T['session_low_t']} ET, high {T['session_high']:,.1f}. The shaded "
                    "band is the model's 90% range for today's close, from Tuesday's close.", S["cap"])]

wk = gold.loc["2026-11-13":].copy()
wk.iloc[-1] = now
notes = {
    "2026-11-13": "Weekly note; forecast logged at the close",
    "2026-11-16": "Tech-led stock sell-off (S&amp;P 500 -1.9%); Empire State index 7.8 vs about 17.6 expected (Kitco); "
                  "Fed Chair Warsh gives no clear December signal (Kitco)",
    "2026-11-17": "Retail sales +0.2%, in line; NY Fed's Williams: the Fed will likely need to raise rates again, "
                  "but no case for a more aggressive path; Nvidia beats after the close",
    "2026-11-18": f"Below $3,800 in Asian trading; dollar index {dxy_now:.2f}; silver {silver_today:+.1%} "
                  f"({ASOF}, not a close)",
}
rows = [["Date", "Close", "Day", "What happened"]]
for d_, v_ in wk.items():
    prev = gold.loc[:d_].iloc[-2]
    rows.append([f"{d_:%a %d %b}", f"{v_:,.0f}", "" if d_ == wk.index[0] else f"{v_ / prev - 1:+.1%}",
                 notes.get(f"{d_:%Y-%m-%d}", "")])
story += [Paragraph("Since the weekly note", S["h2"]), table(rows, [0.13, 0.09, 0.08, 0.70])]

story.append(Paragraph("What is driving it", S["h2"]))
story += bullets([
    "<b>Fed:</b> CME FedWatch puts a 25 bp hike at the 8-9 December meeting at 95.7% and 50 bp at 4.3% (via "
    "Reuters and CNBC). On Tuesday NY Fed President Williams said the Fed will likely need to raise rates again, "
    "while pushing back against a more aggressive path. Today's minutes of the 27-28 October meeting show how many "
    "officials want more.",
    f"<b>Dollar and yields:</b> the dollar index is at {dxy_now:.2f} this morning, above every close since April "
    f"2025, and the 10-year yield closed Tuesday at {d17['^TNX']:.2f}%. Higher rates raise the cost of holding a "
    "metal that pays no yield.",
    "<b>Not forced selling, this time:</b> KCM Trade's Tim Waterer says gold \"is again being treated as a "
    "liquidity asset, with positions cut to cover volatility\" (CNBC). That fits Monday, when a tech-led sell-off "
    "took the S&amp;P 500 down 1.9% and gold with it. It does not fit last night: Nvidia beat after Tuesday's close "
    f"(revenue $115.8bn, up 103%, per its 8-K filing) and S&amp;P futures are up {es_today:.1%}, while gold fell "
    f"{abs(T['r_today']):.1%}. The overnight leg ran on rates and the dollar.",
    "<b>No safe-haven bid:</b> WTI is down again this morning and Brent has lost about 20% in November (Kitco). "
    "Iranian drones hitting a US radar site in Bahrain (Kitco) did not lift gold.",
    "<b>Other side:</b> UBS said on Monday that with gold near the year's lows, further downside is \"less "
    "attractive as a trade\" (Investing.com). OANDA's Kelvin Wong called the drop \"primarily driven by sentiment "
    "and technicality\" (CNBC).",
])

# ---------------- page 2
story.append(PageBreak())
rows = [["Market", "Fri 13 Nov", "Tue 17 Nov", f"Now ({ASOF})", "Since 13 Nov", "Today"]]
for t_, name, fmt in [("GC=F", "Gold", "{:,.0f}"), ("SI=F", "Silver", "{:.2f}"), ("CL=F", "WTI crude", "{:.2f}"),
                      ("^TNX", "US 10Y yield", "{:.2f}%"), ("DX-Y.NYB", "Dollar index", "{:.2f}"),
                      ("ES=F", "S&amp;P 500 futures", "{:,.0f}"), ("^VIX", "VIX", "{:.1f}"),
                      ("^GVZ", "GVZ (gold implied vol)", "{:.1f}")]:
    a_, b_, n_ = d13[t_], d17[t_], dn[t_]
    if t_ == "GC=F":
        n_ = now
    if pd.isna(n_):
        rows.append([name, fmt.format(a_), fmt.format(b_), "US hours only", (
            f"{(b_ - a_) * 100:+.0f} bp" if t_ == "^TNX" else pct(a_, b_)), ""])
        continue
    rows.append([name, fmt.format(a_), fmt.format(b_), fmt.format(n_), pct(a_, n_), pct(b_, n_)])
story += [Paragraph("Cross-asset", S["h2"]), table(rows, [0.24, 0.13, 0.13, 0.16, 0.17, 0.17]),
          Paragraph("Daily closes from Yahoo Finance; 'Now' is the latest print. The 10-year yield index and the GVZ are only "
                    "computed during US hours, so their 'Since 13 Nov' column runs to Tuesday's close.", S["cap"])]

story += [Paragraph("Against the 13 Nov forecast", S["h2"]),
          Paragraph(f"The weekly note of 13 Nov (spot {f13['spot']:,.1f}, model vol {f13['vol']:.1%}) gave a 90% range of "
                    f"{f13['band_k'][0]:,.0f} to {f13['band_k'][1]:,.0f} for today's close and {f13['band_week'][0]:,.0f} "
                    f"to {f13['band_week'][1]:,.0f} for Friday's. This morning's price sits at the "
                    f"<b>{nth(f13['pit'])} percentile</b> for today: low, but inside the range. The note put the chance of a "
                    f"close below $3,800 within a month at {f13['touch3800_month']:.0%} and within the first three "
                    f"sessions at {f13['touch3800_by_now']:.0%}. The model sized this move; as always, it said nothing "
                    "about its direction.", S["body"]),
          Spacer(1, 2), img(cone_png),
          Paragraph("Grey: the 13 Nov forecast. Blue: the forecast from this morning's price, refitted with it as the "
                    "latest observation. Dashed: the median, which has no drift.", S["cap"])]

block = [Paragraph("Ranges from here", S["h2"]),
         Paragraph(f"With this morning's price as the latest observation, model volatility is {T['vol_next_now']:.1%} "
                   f"(it was {T['vol_next']:.1%} at Tuesday's close and {f13['vol']:.1%} on 13 Nov).", S["body"]),
         Spacer(1, 3)]
rows = [["Horizon", "Ends", "5%", "25%", "Median", "75%", "95%", "90% move"]]
for h_, name in ((5, "1 week"), (21, "1 month")):
    i = h_ - 1
    rows.append([name, f"{fwd_dates[i]:%d %b}"] + [f"{fan[k][i]:,.0f}" for k in (5, 25, 50, 75, 95)]
                + [f"{fan[5][i] / now - 1:+.1%} / {fan[95][i] / now - 1:+.1%}"])
block += [table(rows, [0.13, 0.11, 0.11, 0.11, 0.11, 0.11, 0.11, 0.21]), Spacer(1, 4)]
rows = [["Level", "Distance", "Trades through it within a week", "Within a month"]]
for lvl in ("3600", "3700", "3900", "4000"):
    rows.append([f"${int(lvl):,}", f"{int(lvl) / now - 1:+.1%}", f"{touch_w[lvl]:.0%}", f"{touch[lvl]:.0%}"])
block += [table(rows, [0.16, 0.16, 0.38, 0.30]),
          Paragraph("Share of 20,000 simulated paths whose close goes through the level at least once. Levels below "
                    "and above can both be hit on the same path, so the columns do not add up.", S["cap"])]
story.append(KeepTogether(block))

# ---------------- page 3
story.append(PageBreak())
story += [Paragraph("Volatility clustering", S["h2"]),
          Paragraph(f"This is the sixth move above 2% in {T['n_sessions_since_oct15'] + 1} sessions since 15 October, and "
                    "the fifth down. Large moves come in clusters: a big day makes another big day more likely, while "
                    "the direction of the next move stays unpredictable. The model raises its expected volatility after "
                    "every shock and lets it fade slowly.", S["body"]),
          Spacer(1, 2), img(clu_png),
          Paragraph(f"Top: daily moves since May against the model's ±2σ band for that day; "
                    f"{int(outside.iloc[:-1].sum())} of {len(outside) - 1} finished sessions fell outside it, against "
                    f"{2 * stats.t.cdf(-2 * np.sqrt(T['nu'] / (T['nu'] - 2)), T['nu']):.1%} expected. Bottom: the "
                    "model's day-ahead volatility and realised volatility over the past 21 days. Since 2003 a move above "
                    f"{cl['threshold_pct']:.1f}% is {cl['p_after_big'] / cl['p_after_calm']:.1f} times as likely after a "
                    f"week with one ({cl['p_after_big']:.1%} vs {cl['p_after_calm']:.1%}); scaled by the model's volatility "
                    f"the ratio is {cl['z_p_after_big'] / cl['z_p_after_calm']:.1f}: the model accounts for the "
                    "clustering.", S["cap"])]
rows = [["Volatility now", "Value", "What it means"],
        ["Model, day ahead (this morning)", f"{T['vol_next_now']:.1%}",
         f"{vol_pct_now:.0%} of days since 2003 had lower model volatility"],
        ["Long-run level", f"{T['vol_lr']:.1%}", "Where volatility returns to without new shocks"],
        ["Expected, next week / month / quarter",
         f"{T['term_now']['5']:.1%} / {T['term_now']['21']:.1%} / {T['term_now']['63']:.1%}",
         "Average expected volatility over each horizon"],
        ["Half-life of a shock", f"{T['half_life']:.0f} days", f"Persistence {T['persistence']:.3f}: shocks fade slowly"],
        [f"GVZ, {pd.Timestamp(gv['date']):%d %b} close", f"{gv['last']:.1f}",
         f"Options market; {nth(gv['pct_1y'])} percentile of the past year. With the desk's premium correction "
         f"(x{gv['correction']:.2f}): {gv['corrected']:.1%}, close to the model's month ahead. Shadow only: the GVZ "
         "test of 17 Nov did not qualify"]]
story.append(KeepTogether([table(rows, [0.34, 0.14, 0.52])]))

ev = [["Date, level or event", "Why it matters"],
      ["Wed 18 Nov, 08:30 ET: October housing starts", "First US data of the day"],
      ["Wed 18 Nov, 14:00 ET: FOMC minutes (27-28 Oct)", "How many officials favour more hikes, and how fast; the "
                                                         "hike is priced, a faster path is not"],
      ["Thu 19 Nov, 08:30 ET: jobless claims, Philly Fed", "Labour market and factory prices"],
      ["Thu 26 Nov: Thanksgiving", "US holiday: no COMEX settlement, thin trading around it"],
      ["Tue-Wed 8-9 Dec: FOMC", "25 bp priced at 95.7%; 50 bp at 4.3%"],
      ["$3,800", "Broken this morning; a close below it is the lowest since September 2025"],
      ["$3,700", f"{touch_w['3700']:.0%} of model paths close below it within a week, {touch['3700']:.0%} within a month"],
      ["$4,000", f"{touch['4000']:.0%} of paths get back above it within a month"]]
story.append(KeepTogether([Paragraph("Watch list", S["h2"]), table(ev, [0.40, 0.60])]))

story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
    "GARCH(1,1) with Student-t shocks and no drift, fitted on daily COMEX gold futures (GC=F) closes since 2003, as in "
    "the weekly note; the simulation starts from the next-day variance. Today's move is scored against the day-ahead "
    "distribution from Tuesday's close. Ranges from here use this morning's price "
    f"({ASOF}, not a close) as the latest observation and 20,000 simulated paths, seed 42. The 13 Nov comparison "
    "re-simulates the stored fit of that week's live forecast with the same seed, which reproduces its paths exactly. Futures trade a few dollars above spot. News: CNBC "
    "and Reuters (via MarketScreener), Kitco, Investing.com, FXEmpire, Moneycontrol, NVIDIA Form 8-K, Federal Reserve "
    "calendar, Finviz calendar (16-18 Nov 2026). Data: Yahoo Finance.", S["small"])]))

doc.build(story)
print("wrote", OUT)
