"""Gold intraday flash note, 12 Nov 2026: today's move and volatility clustering."""
import json
import sys

import matplotlib
import numpy as np
import pandas as pd
from arch import arch_model
from scipy import stats

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

N, OUT = sys.argv[1], sys.argv[2]
ASOF = "09:05 ET"

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
B100, B200, B300, B550 = "#cde2fb", "#9ec5f4", "#6da7ec", "#1c5cab"
ORANGE, RED, GREEN, AMBER = "#eb6834", "#d03b3b", "#006300", "#a35f00"

T = json.load(open(f"{N}/today.json"))
daily = pd.read_csv(f"{N}/data/daily.csv", index_col=0, parse_dates=True)
gold = daily["GC=F"].dropna()
recent = pd.read_csv(f"{N}/recent.csv", index_col=0, parse_dates=True)
volp = pd.read_csv(f"{N}/vol_path.csv", index_col=0, parse_dates=True)
intra = pd.read_csv(f"{N}/data/gold_5m.csv", index_col=0)
intra.index = pd.to_datetime(intra.index, utc=True).tz_convert("America/New_York").tz_localize(None)

now, yc = T["now"], T["y_close"]
today = pd.Timestamp(T["today"])
sess_start = pd.Timestamp("2026-11-11 18:00")

# ---------------------------------------------------------------- forward ranges from now
# Refit with this morning's price as the latest observation, start from the next-day variance.
ret = np.log(gold).diff().dropna() * 100
res = arch_model(ret, vol="GARCH", p=1, q=1, dist="t", mean="Constant").fit(disp="off", show_warning=False)
p = res.params
var_next = float(res.forecast(horizon=1, reindex=False).variance.iloc[-1, 0]) / 1e4
nu = float(p["nu"]); sc = np.sqrt(nu / (nu - 2)); om = float(p["omega"]) / 1e4
a, b = float(p["alpha[1]"]), float(p["beta[1]"])
rng = np.random.default_rng(42); NP, H = 20_000, 21
v = np.full(NP, var_next); x = np.zeros((NP, H + 1))
for d in range(H):
    e = np.sqrt(v) * rng.standard_t(nu, NP) / sc
    x[:, d + 1] = x[:, d] + e
    v = om + a * e ** 2 + b * v
paths = now * np.exp(x[:, 1:])
fwd_dates = pd.bdate_range(today + pd.Timedelta(days=1), periods=H)
fq = {k: np.percentile(paths, k, axis=0) for k in (5, 25, 50, 75, 95)}
touch = {lvl: float((paths.min(1) <= lvl).mean() if lvl < now else (paths.max(1) >= lvl).mean())
         for lvl in (3800, 4000)}

# ---------------------------------------------------------------- charts
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


# 1. intraday: Tuesday to Thursday sessions, 5-minute closes
seg = intra.loc["2026-11-09 18:00":]
before, todays = seg.loc[:sess_start - pd.Timedelta(minutes=1)], seg.loc[sess_start:]
fig, ax = plt.subplots(figsize=(7.2, 2.5))
band_x = [sess_start, todays.index[-1] + pd.Timedelta(hours=3)]
ax.fill_between(band_x, T["band90"][0], T["band90"][1], color=B100, lw=0, zorder=0,
                label="Today's 90% range from Wed close")
ax.plot(before.index, before["Close"], color=INK2, lw=1.1, label="Tue and Wed sessions")
ax.plot(todays.index, todays["Close"], color=ORANGE, lw=1.6, label="Today's session")
ax.axhline(yc, color=INK2, lw=0.7, ls=(0, (3, 2)))
ax.text(seg.index[0], yc, f" Wed close {yc:,.0f}", fontsize=7.2, color=INK2, va="bottom")
for t_, lab in ((pd.Timestamp("2026-11-10 08:30"), "CPI"), (pd.Timestamp("2026-11-12 08:30"), "Claims")):
    ax.axvline(t_, color=MUTED, lw=0.6, ls=":")
    ax.text(t_, ax.get_ylim()[1], f" {lab}", fontsize=7, color=MUTED, va="top")
for t_ in (pd.Timestamp("2026-11-10 17:00"), pd.Timestamp("2026-11-11 17:00")):
    ax.axvline(t_, color=AXIS, lw=0.8)
low_t = todays["Low"].idxmin()
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

# 2. clustering: daily moves against the model's +/-2 sigma band, and volatility
start = pd.Timestamp("2026-05-01")
rr = recent_all = pd.DataFrame({"ret": np.log(gold).diff()}).loc[start:]
cs = volp["vol_model"].reindex(rr.index) / np.sqrt(252)
cs.iloc[-1] = T["sigma_day"]                       # today: the model's sigma for today
outside = rr["ret"].abs() > 2 * cs
fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 3.3), sharex=True, gridspec_kw={"height_ratios": [1.6, 1]})
from matplotlib.patches import Patch
a1.fill_between(rr.index, -2 * cs, 2 * cs, color=B100, lw=0, step="mid")
col = np.where(outside, RED, INK2)
col[-1] = ORANGE
a1.bar(rr.index, rr["ret"], width=1.0, color=col, lw=0)
a1.axhline(0, color=AXIS, lw=0.6)
a1.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
a1.set_ylabel("Daily move")
a1.legend(handles=[Patch(color=B100, label="Model ±2σ for that day"), Patch(color=INK2, label="Inside"),
                   Patch(color=RED, label="Outside ±2σ"), Patch(color=ORANGE, label=f"Today, {ASOF}")],
          loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4)
vm = volp["vol_model"].loc[start:]
vr = volp["vol_real21"].loc[start:]
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
    c.setFont("SUI", 9.5); c.drawString(M, Hp - 18 * mm, "Desk note: intraday flash and volatility clustering")
    c.setFont("SUI-B", 9.5); c.drawRightString(W - M, Hp - 12 * mm, f"{today:%d %B %Y}, {ASOF}")
    c.setFont("SUI", 8.5); c.drawRightString(W - M, Hp - 18 * mm, "Prices: COMEX gold futures, USD/oz")
    c.setStrokeColor(C(GRID)); c.setLineWidth(0.6); c.line(M, 12 * mm, W - M, 12 * mm)
    c.setFillColor(C(MUTED)); c.setFont("SUI", 7)
    c.drawString(M, 8 * mm, "Previous note: 2 Nov 2026")
    c.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm, bottomMargin=14 * mm,
                      title="Gold desk note, 12 Nov 2026", author="Nikolay Gelshtein")
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


pct = lambda a_, b_: f"{b_ / a_ - 1:+.1%}"  # noqa: E731
cl = T["clustering"]
story = [kpis([
    ("Now", f"{now:,.0f}", f"{today:%d %b}, {ASOF}", INK),
    ("Today", f"{T['r_today']:+.1%}", f"from {yc:,.0f} (Wed close)", RED),
    ("Size of move", f"{abs(T['z_today']):.1f}σ", f"about a 1-in-{T['one_in']:.0f}-day move", INK),
    ("Model vol", f"{T['vol_next']:.1%}", f"{T['vol_pct_since_2003']:.0%} percentile since 2003", INK),
    ("From peak", f"{now / T['peak'] - 1:+.1%}", f"{T['peak']:,.0f} on 29 Jan 2026", RED),
]), Spacer(1, 7)]

story.append(callout(
    f"<b>Bottom line.</b> Gold is down {abs(T['r_today']):.1%} this morning at <b>{now:,.0f}</b>, just below the "
    f"30 Oct close of {T['year_low_before']:,.0f}, the lowest close of 2026. That is {abs(T['z_today']):.1f} times the "
    f"model's expected daily move and sits below today's 90% range ({T['band90'][0]:,.0f} to {T['band90'][1]:,.0f}), "
    f"but inside its 98% range. This is now a rates-and-dollar sell-off: since last Friday the 10-year yield is up "
    f"17 bp and the dollar index is at a year-to-date high, while oil has fallen. It is the fourth move above 2% in "
    f"ten sessions: volatility is clustering, and the model expects it to stay around {T['term']['21']:.1%} for the "
    f"coming month. Next: October PPI tomorrow at 08:30 ET."))

story += [Paragraph("Today's session", S["h2"]), img(intra_png),
          Paragraph(f"5-minute closes, New York time; the session opened Wednesday 18:00 ET. Low so far "
                    f"{todays['Low'].min():,.1f} at {low_t:%H:%M} ET, high {todays['High'].max():,.1f}. "
                    "The shaded band is the model's 90% range for today's close.", S["cap"])]

wk = gold.loc["2026-11-06":]
notes = {
    "2026-11-06": "Previous Friday close",
    "2026-11-09": "Higher as the oil rout weighs on the dollar",
    "2026-11-10": "October CPI hot: headline +0.4% m/m vs +0.3% expected, core +0.3% vs +0.2%",
    "2026-11-11": "Dollar surges; spot gold slips below $4,000 late in the day",
    "2026-11-12": f"Dollar index at a year-to-date high; session low after 08:30 jobless claims ({ASOF}, not a close)",
}
rows = [["Date", "Close", "Day", "What happened"]]
for d_, v_ in wk.items():
    prev = gold.shift(1).loc[d_]
    rows.append([f"{d_:%a %d %b}", f"{v_:,.0f}", "" if d_ == wk.index[0] else f"{v_ / prev - 1:+.1%}",
                 notes.get(f"{d_:%Y-%m-%d}", "")])
story += [Paragraph("The week", S["h2"]), table(rows, [0.13, 0.10, 0.09, 0.68])]

story.append(Paragraph("What is driving it", S["h2"]))
for t_ in [
    "<b>Fed repricing:</b> a 25 bp December hike is fully priced. After the hot CPI, Governor Waller said a 50 bp "
    "move should be considered if core inflation stays near 0.3%; CME FedWatch puts the odds of 50 bp at about 13%. "
    "The FOMC meets 8-9 December.",
    "<b>Dollar and yields, not oil:</b> unlike late October, when gold fell while yields dropped and oil rose, this "
    "week's drop runs through the classic channel. The 10-year yield is up and the dollar index hit a year-to-date "
    "high near 103.1 this morning, while WTI is down.",
    "<b>Data this morning:</b> gold made its session low after the 08:30 ET jobless claims (200,000 vs 195,000 "
    "expected, per IndexBox). A softer labour print did not help gold; the dollar dominated.",
    "<b>Support:</b> analysts point to steady central-bank buying as the floor under the market; ING flags tomorrow's "
    "PPI as the next possible trigger for the dollar.",
]:
    story.append(Paragraph(t_, S["bul"], bulletText="\u2022"))

# ---------------- page 2
story.append(PageBreak())
d6 = daily.loc[:"2026-11-06"].ffill().iloc[-1]
dy = daily.loc[:"2026-11-11"].ffill().iloc[-1]
dn = daily.ffill().iloc[-1]
rows = [["Market", "Fri 6 Nov", "Wed 11 Nov", f"Now ({ASOF})", "Week", "Today"]]
for t_, name, fmt in [("GC=F", "Gold", "{:,.0f}"), ("SI=F", "Silver", "{:.2f}"), ("CL=F", "WTI crude", "{:.2f}"),
                      ("^TNX", "US 10Y yield", "{:.2f}%"), ("DX-Y.NYB", "Dollar index", "{:.2f}"),
                      ("^VIX", "VIX", "{:.1f}")]:
    if t_ == "^TNX":
        w_, t2 = f"{(dn[t_] - d6[t_]) * 100:+.0f} bp", f"{(dn[t_] - dy[t_]) * 100:+.0f} bp"
    else:
        w_, t2 = pct(d6[t_], dn[t_]), pct(dy[t_], dn[t_])
    rows.append([name, fmt.format(d6[t_]), fmt.format(dy[t_]), fmt.format(dn[t_]), w_, t2])
story += [Paragraph("Cross-asset", S["h2"]), table(rows, [0.20, 0.14, 0.14, 0.18, 0.17, 0.17]),
          Paragraph("Daily closes from Yahoo Finance; 'Now' is the latest print. US stocks were not yet open.", S["cap"])]

story += [Paragraph("Volatility clustering", S["h2"]),
          Paragraph("Large moves in gold come in clusters: a big day makes another big day more likely, while the "
                    "direction of the next move stays unpredictable. The GARCH model captures this by raising its "
                    "expected volatility after every shock and letting it fade slowly.", S["body"]),
          Spacer(1, 2), img(clu_png),
          Paragraph(f"Top: daily moves since May against the model's ±2σ band for that day; "
                    f"{int(outside.iloc[:-1].sum())} of {len(outside) - 1} finished sessions fell outside it, against "
                    f"{2 * stats.t.cdf(-2 * np.sqrt(nu / (nu - 2)), nu):.1%} expected. Bottom: the model's day-ahead "
                    "volatility and realised volatility over the past 21 days.", S["cap"])]
rows = [["Measure (daily data since 2003)", "After a big week", "After a calm week", "Ratio"],
        [f"Chance of a big day (move above {cl['threshold_pct']:.1f}%)", f"{cl['p_after_big']:.1%}",
         f"{cl['p_after_calm']:.1%}", f"{cl['ratio']:.1f}x"],
        ["Same, with moves scaled by the model's volatility", f"{cl['z_p_after_big']:.1%}",
         f"{cl['z_p_after_calm']:.1%}", f"{cl['z_p_after_big'] / cl['z_p_after_calm']:.1f}x"]]
story += [table(rows, [0.46, 0.18, 0.18, 0.18]),
          Paragraph(f"'Big week': at least one big day in the previous five sessions. Autocorrelation of the size of "
                    f"daily moves at 1, 5 and 21 days: {cl['acf_abs'][0]:.2f}, {cl['acf_abs'][1]:.2f}, "
                    f"{cl['acf_abs'][2]:.2f}; of the moves themselves: {cl['acf_ret'][0]:+.2f}, {cl['acf_ret'][1]:+.2f}, "
                    f"{cl['acf_ret'][2]:+.2f}. Size persists, direction does not. Once moves are scaled by the model's "
                    "volatility, the clustering disappears: the model accounts for it.", S["cap"])]
rows = [["Volatility now", "Value", "What it means"],
        ["Model, day ahead", f"{T['vol_next']:.1%}", f"{T['vol_pct_since_2003']:.0%} of days since 2003 had lower model volatility"],
        ["Long-run level", f"{T['vol_lr']:.1%}", "Where volatility returns to without new shocks"],
        ["Expected, next week / month / quarter",
         f"{T['term']['5']:.1%} / {T['term']['21']:.1%} / {T['term']['63']:.1%}", "Average expected volatility over each horizon"],
        ["Half-life of a shock", f"{T['half_life']:.0f} days", f"Persistence {T['persistence']:.3f}: shocks fade slowly"]]
story.append(KeepTogether([table(rows, [0.34, 0.20, 0.46])]))

block = [Paragraph("Ranges", S["h2"]),
         Paragraph(f"From Wednesday's close the model's 90% range for today was {T['band90'][0]:,.0f} to "
                   f"{T['band90'][1]:,.0f} and its 98% range {T['band98'][0]:,.0f} to {T['band98'][1]:,.0f}; the price "
                   f"now sits at the {T['pit_today']:.0%} percentile. From here, with this morning's price as the "
                   f"latest observation: in {touch[3800]:.0%} of simulated paths gold trades below $3,800 within a month, "
                   f"in {touch[4000]:.0%} it gets back above $4,000.", S["body"]), Spacer(1, 3)]
rows = [["Horizon", "Ends", "5%", "25%", "Median", "75%", "95%", "90% move"]]
for h_, name in ((5, "1 week"), (21, "1 month")):
    i = h_ - 1
    rows.append([name, f"{fwd_dates[i]:%d %b}"] + [f"{fq[k][i]:,.0f}" for k in (5, 25, 50, 75, 95)]
                + [f"{fq[5][i] / now - 1:+.1%} / {fq[95][i] / now - 1:+.1%}"])
block.append(table(rows, [0.13, 0.11, 0.11, 0.11, 0.11, 0.11, 0.11, 0.21]))
story.append(KeepTogether(block))

ev = [["Date, level or event", "Why it matters"],
      ["Fri 13 Nov, 08:30 ET: October PPI", "Next test of the hot-inflation story; a strong print could extend the dollar rally"],
      ["Tue-Wed 8-9 Dec: FOMC", "25 bp priced; any move toward 50 bp pricing weighs on gold"],
      [f"{T['year_low_before']:,.0f} (30 Oct close)", "A close below it is a new 2026 low and the lowest since October 2025"],
      ["$3,800", f"{touch[3800]:.0%} of model paths trade below it within a month"],
      ["$4,000", "Lost on Wednesday; first level to reclaim"]]
story.append(KeepTogether([Paragraph("Watch list", S["h2"]), table(ev, [0.34, 0.66])]))

story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
    "GARCH(1,1) with Student-t shocks and no drift, fitted on daily COMEX gold futures (GC=F) closes since 2003; "
    "today's move is scored against the model's day-ahead distribution from Wednesday's close. Ranges from here use "
    f"this morning's price ({ASOF}, not a close) as the latest observation and 20,000 simulated paths. Futures trade "
    "about $20-40 above spot. News: FXStreet, Kitco, Investing.com, Mining.com, Invezz, IndexBox, FX Leaders, "
    "APMEX, Mining.com.au, Fortune (9-12 Nov 2026). Data: Yahoo Finance.", S["small"])]))

doc.build(story)
print("wrote", OUT, "| touch", touch, "| fwd 1w", [round(fq[k][4]) for k in (5, 50, 95)])
