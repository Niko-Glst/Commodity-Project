"""The rotation note (PDF): flows and stress first, prices second."""

from __future__ import annotations

import json
import re
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

from .data import CASH  # noqa: E402

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
UP, DOWN, NEUTRAL = "#1c5cab", "#eb6834", "#898781"     # in / out (above / below T-bills) / cash itself
FONT = ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf")

for fp in FONT:
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 8.2, "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False, "legend.fontsize": 7.8,
})
pctfmt = matplotlib.ticker.PercentFormatter(1.0, decimals=0)


def _save(fig, path: Path) -> Path:
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_stress(F: dict, m: pd.DataFrame, out: Path) -> Path:
    hy = F["BAMLH0A0HYM2"].dropna().loc["2025-01-01":]
    ratio = (m["^VIX"] / m["^VIX3M"]).loc["2025-01-01":]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 2.7), sharex=True)
    a1.plot(hy.index, hy.values, color=UP, lw=1.4)
    a1.set_ylabel("High-yield\nspread, %")
    a1.annotate(f"{hy.iloc[-1]:.2f}", (hy.index[-1], hy.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                fontsize=7.2, color=INK, va="center")
    a2.plot(ratio.index, ratio.values, color=INK2, lw=1.2)
    a2.axhline(1, color=DOWN, lw=0.8, ls=(0, (3, 2)))
    a2.text(pd.Timestamp("2025-08-01"), 1.13, "above 1 = inverted (stress)", fontsize=7, color=MUTED, va="center",
            bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
    a2.set_ylabel("VIX / VIX3M")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    for a in (a1, a2):
        a.axvline(pd.Timestamp("2026-10-06"), color=MUTED, lw=0.6, ls=":")
    a1.text(pd.Timestamp("2026-10-06"), a1.get_ylim()[1], " 6 Oct high", fontsize=7, color=MUTED, va="top")
    return _save(fig, out / "r_stress.png")


def chart_flows(fl: pd.DataFrame, nav_ret: pd.Series, out: Path) -> Path:
    x = fl.sort_values("flow_peak_pct")
    col = [UP if v > 0 else DOWN for v in x.flow_peak_pct]
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.barh(range(len(x)), x.flow_peak_pct, color=col, height=0.7)
    ax.set_yticks(range(len(x)))
    ax.set_yticklabels([f"{n} ({t})" for t, n in zip(x.ticker, x.name)], fontsize=7.2, color=INK2)
    for i, (_, r) in enumerate(x.iterrows()):
        v = r.flow_peak_pct
        lab = f"{'+' if r.flow_peak_bn >= 0 else '-'}${abs(r.flow_peak_bn):.1f}bn   price {nav_ret[r.ticker]:+.0%}"
        ax.text(v + (0.002 if v >= 0 else -0.002), i, lab,
                va="center", ha="left" if v >= 0 else "right", fontsize=6.6, color=INK)
    ax.axvline(0, color=AXIS, lw=0.8)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    lim = max(abs(x.flow_peak_pct).max(), 0.02)
    ax.set_xlim(-lim - 0.06, lim + 0.06)
    ax.set_xlabel("Net creations minus redemptions since 6 Oct, % of assets on 6 Oct")
    ax.legend(handles=[Patch(color=UP, label="Money in"), Patch(color=DOWN, label="Money out")], loc="lower right")
    return _save(fig, out / "r_flows.png")


def chart_bars(perf: pd.DataFrame, out: Path) -> Path:
    x = perf.sort_values("since_peak")
    cash = perf.loc[CASH, "since_peak"]
    col = [NEUTRAL if t == CASH else (UP if v > cash else DOWN) for t, v in x.since_peak.items()]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.barh(range(len(x)), x.since_peak, color=col, height=0.72)
    ax.set_yticks(range(len(x)))
    ax.set_yticklabels([f"{n} ({t})" for t, n in zip(x.index, x.name)], fontsize=6.9, color=INK2)
    for i, v in enumerate(x.since_peak):
        ax.text(v + (0.004 if v >= 0 else -0.004), i, f"{v:+.1%}", va="center", ha="left" if v >= 0 else "right",
                fontsize=6.5, color=INK)
    ax.axvline(0, color=AXIS, lw=0.8)
    ax.axvline(cash, color=NEUTRAL, lw=0.8, ls=(0, (3, 2)))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.xaxis.set_major_formatter(pctfmt)
    ax.set_xlim(x.since_peak.min() - 0.06, x.since_peak.max() + 0.05)
    ax.legend(handles=[Patch(color=UP, label="Above T-bills"), Patch(color=DOWN, label="Below T-bills"),
                       Patch(color=NEUTRAL, label="T-bills")], loc="lower right")
    return _save(fig, out / "r_bars.png")


def chart_scatter(perf: pd.DataFrame, pt: dict, out: Path) -> Path:
    x = perf.drop(index=CASH)
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.scatter(x.year_to_peak, x.since_peak, s=24, color=UP, edgecolor="white", lw=1.0, zorder=3)
    xs = np.linspace(x.year_to_peak.min(), x.year_to_peak.max(), 50)
    ax.plot(xs, pt["intercept"] + pt["slope"] * xs, color=INK2, lw=1.0, ls=(0, (3, 2)))
    label = {"USO", "SMH", "XLE", "COPX", "XLK", "XLP", "XLV", "BTC-USD", "SLV", "GLD", "XLU", "QQQ", "UUP"}
    offsets = {"XLU": (-5, 3, "right"), "UUP": (5, 3, "left")}
    for t, r in x.iterrows():
        if t in label:
            dx, dy, ha = offsets.get(t, (5, 2, "left"))
            ax.annotate(r["name"], (r.year_to_peak, r.since_peak), xytext=(dx, dy), textcoords="offset points",
                        fontsize=6.6, color=INK2, ha=ha)
    ax.axhline(0, color=AXIS, lw=0.7)
    ax.axvline(0, color=AXIS, lw=0.7)
    ax.xaxis.set_major_formatter(pctfmt)
    ax.yaxis.set_major_formatter(pctfmt)
    ax.set_xlabel("Return in the 12 months to 6 Oct 2026")
    ax.set_ylabel("Return since 6 Oct")
    ax.grid(axis="x", color=GRID, lw=0.6)
    return _save(fig, out / "r_scatter.png")


W, H = A4
M = 16 * mm
CW = W - 2 * M
C = colors.HexColor


def _st(name, **kw):
    return ParagraphStyle(name, **{"fontName": "SUI", "fontSize": 8.6, "leading": 11.8, "textColor": C(INK), **kw})


def build_pdf(b, folder: Path) -> Path:
    R = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    perf = pd.DataFrame(R["performance"]).set_index("ticker")
    pt, pos, ext = R["profit_taking"], pd.DataFrame(R["positioning"]), R["external"]
    cr = pd.DataFrame(R["credit_and_rates"]).set_index("id")
    st_, fa, mm_, nl = R["stress"], R["factors"], R["mmf"], R["net_liquidity"]
    fl = pd.DataFrame(R["etf_flows"])
    rob = pd.DataFrame(R["robustness"])
    gbs = pd.DataFrame(R["groups_by_start"])
    charts = folder / "_charts"
    charts.mkdir(exist_ok=True)
    pdfmetrics.registerFont(TTFont("SUI", FONT[0]))
    pdfmetrics.registerFont(TTFont("SUI-B", FONT[1]))
    registerFontFamily("SUI", normal="SUI", bold="SUI-B", italic="SUI", boldItalic="SUI-B")
    S = {
        "h2": _st("h2", fontName="SUI-B", fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3, textColor=C(NAVY)),
        "body": _st("body"), "small": _st("small", fontSize=7.3, leading=9.6, textColor=C(INK2)),
        "bul": _st("bul", leftIndent=10, bulletIndent=0, spaceAfter=2.0),
        "cell": _st("cell", fontSize=7.6, leading=9.6), "cellb": _st("cellb", fontName="SUI-B", fontSize=7.6, leading=9.6),
        "cap": _st("cap", fontSize=7.2, leading=9.3, textColor=C(MUTED), spaceBefore=1, spaceAfter=3),
    }
    last = pd.Timestamp(R["last_close"])

    def header_footer(cv, doc):
        cv.saveState()
        cv.setFillColor(C(NAVY)); cv.rect(0, H - 24 * mm, W, 24 * mm, stroke=0, fill=1)
        cv.setFillColor(colors.white)
        cv.setFont("SUI-B", 15); cv.drawString(M, H - 12 * mm, "ROTATION  |  CASH")
        cv.setFont("SUI", 9.5); cv.drawString(M, H - 18 * mm, "Rotation or de-risking? Flows, stress and prices")
        cv.setFont("SUI-B", 9.5); cv.drawRightString(W - M, H - 12 * mm, f"Data to {last:%d %B %Y}")
        cv.setFont("SUI", 8.5); cv.drawRightString(W - M, H - 18 * mm, "Each measure dated where it ends earlier")
        cv.setStrokeColor(C(GRID)); cv.setLineWidth(0.6); cv.line(M, 12 * mm, W - M, 12 * mm)
        cv.setFillColor(C(MUTED)); cv.setFont("SUI", 7)
        cv.drawString(M, 8 * mm, "Revised after review, 19 Nov 2026. Rerun: python -m moneyflow check (from rotation/)")
        cv.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
        cv.restoreState()

    out_pdf = folder / f"rotation_{last:%Y-%m-%d}.pdf"
    doc = BaseDocTemplate(str(out_pdf), pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm,
                          bottomMargin=14 * mm, title=f"Rotation or de-risking, {last:%d %b %Y}", author="Nikolay Gelshtein")
    frame = Frame(M, 14 * mm, CW, H - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])

    def table(rows, widths):
        esc = lambda v: re.sub(r"&(?!amp;)", "&amp;", str(v))  # noqa: E731
        data = [[Paragraph(f"<b>{esc(h)}</b>", S["cell"]) for h in rows[0]]]
        data += [[Paragraph(esc(x), S["cellb"] if j == 0 else S["cell"]) for j, x in enumerate(r)] for r in rows[1:]]
        t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2), ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        return t

    def img(path):
        iw, ih = ImageReader(str(path)).getSize()
        return Image(str(path), width=CW, height=CW * ih / iw)

    def kpis(items):
        cells = [[Paragraph(f'<font size="7.0" color="{MUTED}">{k.upper()}</font><br/>'
                            f'<font name="SUI-B" size="13.5" color="{INK}">{v_}</font><br/>'
                            f'<font size="7.0" color="{INK2}">{sub}</font>', _st("k", leading=14.5))
                  for k, v_, sub in items]]
        t = Table(cells, colWidths=[CW / len(items)] * len(items))
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C("#f4f3ef")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
        return t

    def callout(html):
        t = Table([[Paragraph(html, S["body"])]], colWidths=[CW])
        t.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, C(DOWN)), ("BACKGROUND", (0, 0), (-1, -1), C("#fbf7f3")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
        return t

    d = lambda s: f"{pd.Timestamp(s).day} {pd.Timestamp(s):%b}"  # noqa: E731
    usd = lambda x, dec=1: f"{'+' if x >= 0 else '-'}${abs(x):,.{dec}f}bn"  # noqa: E731

    def nth(q):
        n = int(round(q * 100))
        return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
    f_ = fl.set_index("ticker")
    hy, ig, real = cr.loc["BAMLH0A0HYM2"], cr.loc["BAMLC0A0CM"], cr.loc["DFII10"]
    g = gbs.set_index("group")
    peak_col = "2026-10-06"
    ai, metals, defs, cyc = (g.loc[k, peak_col] for k in (
        "AI and growth (semis, tech, software, Nasdaq-100)", "Silver, copper, copper miners",
        "Defensive sectors (staples, health care, utilities, real estate)",
        "Cyclical sectors (financials, discretionary, industrials)"))
    orig = rob[(rob.start == peak_col) & (rob.universe == "All 28")].iloc[0]
    eq = rob[rob.universe == "Equity sectors"]
    days = [x.split() for x in st_["inverted_days_recent"][-2:]]
    inv = (f"{int(days[0][0])} and {int(days[1][0])} {days[1][1]}" if len(days) == 2 and days[0][1] == days[1][1]
           else ", ".join(" ".join(x) for x in days) or "no day")

    # ---------------- page 1
    story = [kpis([
        ("High-yield spread", f"{hy.now:.2f}%", f"{hy.chg_peak_bp:+.0f} bp since 6 Oct, {nth(hy.pct_since_2024)} pctile"),
        ("VIX / VIX3M", f"{st_['ratio']:.2f}", f"inverted on {inv}: stress"),
        ("Tech ETF XLK flow", usd(f_.loc['XLK', 'flow_peak_bn']), f"since 6 Oct, price {perf.loc['XLK', 'since_peak']:+.0%}"),
        ("Money funds (ICI)", f"${mm_['total_tn']:.2f}tn", f"{usd(mm_['chg_bn'], 0)} wk to {d(mm_['date'])} (z {mm_['z']:+.1f})"),
        ("Fund-manager cash", ext["fms_cash"], "BofA: at or below 4% = sell signal"),
    ]), Spacer(1, 7)]
    story.append(callout(
        f"<b>Bottom line. Prices rotated, ETF money did not, and stress rose this week.</b> Since the 6 Oct high, AI "
        f"stocks ({ai:+.0%}) and silver and copper ({metals:+.0%}) fell while the rest of the market held up: not only "
        f"defensive sectors ({defs:+.0%}) but also financials, consumer discretionary and industrials ({cyc:+.0%}). The "
        "pattern is the same from 1 Oct, 15 Oct or 1 Nov. Real ETF flows did not follow the prices: the tech fund XLK "
        f"took in {usd(f_.loc['XLK', 'flow_peak_bn'])[1:]} and SPY {usd(f_.loc['SPY', 'flow_peak_bn'], 0)[1:]}, while utilities "
        f"({usd(f_.loc['XLU', 'flow_peak_bn'])}) and staples lost money: defensive prices rose without ETF money. "
        f"Cash builds only slowly: money funds had one unusual week (+${mm_['prev_chg_bn']:.0f}bn to {d(mm_['prev_date'])}, "
        f"z = {mm_['prev_z']:.1f}) and gave back ${-mm_['chg_bn']:.0f}bn the next; fund managers hold just {ext['fms_cash']}, "
        f"a sell signal by BofA's own rule. What changed is stress: the high-yield spread is up {hy.chg_peak_bp:.0f} bp "
        f"since the high, the VIX curve inverted on {inv}, and the 10-year real yield rose {real.chg_1w_bp:.0f} bp in a "
        f"week (z = {real.z_1w:.1f}). A rotation is turning into de-risking, alongside a jump in real yields."))

    story.append(Paragraph("Rotation or de-risking? The measures that decide", S["h2"]))
    rows = [["Measure", "Now", "Since 6 Oct", "Last week", "Reads as"],
            ["High-yield credit spread", f"{hy.now:.2f}%", f"{hy.chg_peak_bp:+.0f} bp", f"{hy.chg_1w_bp:+.0f} bp (z {hy.z_1w:+.1f})",
             f"De-risking, moderate: below the {hy.max_since_2024:.2f}% of {pd.Timestamp(hy.max_date):%b %Y}"],
            ["Investment-grade spread", f"{ig.now:.2f}%", f"{ig.chg_peak_bp:+.0f} bp", f"{ig.chg_1w_bp:+.0f} bp", "Mild"],
            ["VIX / VIX3M (equity vol curve)", f"{st_['ratio']:.2f}", f"from {st_['ratio_peak']:.2f}", f"inverted {inv}",
             f"Stress: inverted on {st_['inverted_share_since_2024']:.0%} of days since 2024"],
            ["MOVE (Treasury vol)", f"{st_['move']:.0f}", f"from {st_['move_peak']:.0f}", "",
             f"Calm ({nth(st_['move_pct'])} percentile since 2024)"],
            ["Sector correlation, 21 days", f"{st_['corr']:.2f}", f"from {st_['corr_peak']:.2f}", "",
             f"Rising, far from panic ({st_['corr_max']:.2f} in {pd.Timestamp(st_['corr_max_date']):%b %Y})"],
            ["Sector dispersion, 21 days", f"{nth(st_['disp_pct'])} pctile", "", "", "High: sectors moving apart = rotation"],
            ["Momentum ETF vs S&amp;P 500", f"{fa['mtum_vs_spy']:+.1%}", "since 6 Oct", f"{fa['mtum_vs_spy_week']:+.1%}",
             "Last year's winners unwinding"],
            ["10-year real yield", f"{real.now:.2f}%", f"{real.chg_peak_bp:+.0f} bp", f"{real.chg_1w_bp:+.0f} bp (z {real.z_1w:+.1f})",
             "Rate shock last week"],
            ["Net liquidity (Fed - TGA - RRP)", f"${nl['now_bn'] / 1e3:.2f}tn", f"{nl['now_bn'] - nl['at_peak_bn']:+.0f}bn",
             f"4 wk {nl['chg_4w_bn']:+.0f}bn", "Flat: not a driver"]]
    story += [table(rows, [0.25, 0.11, 0.13, 0.17, 0.34]),
              Paragraph(f"Credit and rates: FRED to {d(hy.date)}. Volatility, correlation and prices to {d(last)} close. "
                        "z: last week's change against the weekly changes of the past year. Net liquidity: weekly, to "
                        f"{d(nl['date'])}.", S["cap"]),
              img(chart_stress(b.fred_series, b.market, charts)),
              Paragraph("The high-yield spread (top) and the VIX curve (bottom) since January 2025. Both turned up after the "
                        "6 Oct high; both stay well below April 2025.", S["cap"])]

    # ---------------- page 2
    story.append(PageBreak())
    nav_ret = {t: grp.sort_values("date").pipe(lambda x: x.nav.iloc[-1] / x.loc[x.date <= "2026-10-06", "nav"].iloc[-1] - 1)
               for t, grp in b.flows.groupby("ticker")}
    story += [Paragraph("Where ETF money went (State Street SPDR funds, daily share counts)", S["h2"]),
              Paragraph("Each day an ETF creates or redeems shares as money comes in or goes out. Change in shares times "
                        "NAV is the flow, computed here from State Street's own files, not from press reports. It covers "
                        "the SPDR family only: the largest sector funds, but not iShares, Vanguard or Invesco (QQQ).",
                        S["body"]), Spacer(1, 2),
              img(chart_flows(fl[fl.ticker != CASH], pd.Series(nav_ret), charts)),
              Paragraph("Bars: flow since 6 Oct as a share of each fund's assets; labels: dollars and the NAV change over "
                        "the same period.", S["cap"])]
    rows = [["Fund", "Since 6 Oct", "November", "Last week", "Last week vs past year"]]
    for t in ["SPY", "XLK", "XLV", "XLU", "XLP", "XLF", "XME", CASH]:
        r = f_.loc[t]
        rows.append([f"{r['name']} ({t})", f"{usd(r.flow_peak_bn, 2)} ({r.flow_peak_pct:+.1%})",
                     f"{usd(r.flow_nov_bn, 2)} ({r.flow_nov_pct:+.1%})", usd(r.flow_week_bn, 2), f"z {r.z_week:+.1f}"])
    zmax = fl.z_week.abs().max()
    story += [table(rows, [0.30, 0.19, 0.19, 0.14, 0.18]),
              Paragraph(f"No fund's flow last week was unusual against its own past year (largest |z| {zmax:.1f}).", S["cap"])]
    story.append(Paragraph("Cash: building slowly", S["h2"]))
    story += [Paragraph(t_, S["bul"], bulletText="\u2022") for t_ in [
        f"<b>Money market funds (ICI):</b> ${mm_['total_tn']:.2f}tn in the week to {d(mm_['date'])}, "
        f"{usd(mm_['chg_bn'])} (z {mm_['z']:+.1f}); the week before, {usd(mm_['prev_chg_bn'])} to "
        f"${mm_['prev_total_tn']:.2f}tn (z {mm_['prev_z']:+.1f}), one unusual week. The z-scores use the {mm_['n_weeks']} "
        f"weekly changes in ICI's 2026 file (standard deviation ${mm_['sd_bn']:.0f}bn); early-month weeks often carry "
        "month-end cash.",
        f"<b>T-bill ETF (BIL):</b> {usd(f_.loc[CASH, 'flow_nov_bn'], 2)} in November ({f_.loc[CASH, 'flow_nov_pct']:+.1%} of assets), "
        f"after {usd(f_.loc[CASH, 'flow_peak_bn'] - f_.loc[CASH, 'flow_nov_bn'], 2)} from 6 to 30 Oct.",
        f"<b>Fund managers (BofA survey, 6-12 Nov):</b> cash {ext['fms_cash']}, down from 3.9%. BofA's cash rule gives a sell "
        "signal at 4% or less: investors hold little cash to cushion a sell-off, so a fall can force selling.",
    ] + [f"<b>{r[0]}:</b> {r[1]}. {r[2]}." for r in ext["evidence"]]]

    # ---------------- page 3
    story.append(PageBreak())
    story += [Paragraph("Prices: returns since 6 Oct against T-bills", S["h2"]), img(chart_bars(perf, charts)),
              Paragraph(f"Total returns to {d(last)}. Above or below T-bills says how an asset did against holding cash, "
                        "not where money went.", S["cap"])]
    rows = [["Group (simple average)", "From 1 Oct", "From 6 Oct", "From 15 Oct", "From 1 Nov"]]
    for _, r in gbs.iterrows():
        rows.append([r.group] + [f"{r[c]:+.1%}" for c in ("2026-10-01", "2026-10-06", "2026-10-15", "2026-11-01")])
    story += [table(rows, [0.48, 0.13, 0.13, 0.13, 0.13]),
              Paragraph(f"The picture does not depend on starting at the high. Consumer discretionary's gain is broad: the "
                        f"equal-weight fund (RSPD) rose {fa['rspd']:+.1%} against {fa['xly']:+.1%} for XLY; Amazon "
                        f"{fa['names']['AMZN']:+.0%}, Tesla {fa['names']['TSLA']:+.0%}, Home Depot {fa['names']['HD']:+.0%}, "
                        f"McDonald's {fa['names']['MCD']:+.0%}.", S["cap"])]

    # ---------------- page 3, continued
    story += [Paragraph("Profit-taking, or just volatility?", S["h2"]),
              Paragraph(f"Across 28 assets, the 12-month gain to 6 Oct and the move since have a rank correlation of "
                        f"{orig.raw:+.2f} (p = {orig.raw_p:.3f}), the test fixed beforehand. But volatile assets rise most and "
                        "fall most whatever the reason. The checks below were added after review, so they are exploratory.",
                        S["body"]), Spacer(1, 2), img(chart_scatter(perf, pt, charts))]
    rows = [["Start", "Assets", "Raw", "Risk-adjusted", "Winners, beyond volatility (t)", "Beyond beta (t)"]]
    for _, r in rob.iterrows():
        rows.append([d(r.start), f"{r.universe} ({r.n})", f"{r.raw:+.2f} (p {r.raw_p:.2f})",
                     f"{r.scaled:+.2f} (p {r.scaled_p:.2f})", f"{r.t_mom_vol:+.1f}", f"{r.t_mom_beta:+.1f}"])
    story.append(KeepTogether([table(rows, [0.10, 0.22, 0.16, 0.18, 0.20, 0.14]),
              Paragraph("Raw and risk-adjusted: Spearman rank correlations (risk-adjusted divides both returns by each "
                        "asset's own volatility). t-values: momentum's coefficient in a regression of the move on momentum "
                        "plus volatility, or plus beta to the S&amp;P 500; below -2 means winners fell more than their "
                        "risk explains.", S["cap"]),
              Paragraph(f"<b>Reading:</b> across all assets the pattern is mostly volatility: controlling for it, momentum's t "
                        f"is {orig.t_mom_vol:+.1f} from 6 Oct. Within equity sectors something is left (t {eq.t_mom_vol.max():+.1f} "
                        f"to {eq.t_mom_vol.min():+.1f}; beyond beta about -2), and the momentum ETF trails the S&amp;P 500 by "
                        f"{-fa['mtum_vs_spy']:.0%}: among stocks, last year's winners are being sold. 'Profit-taking' fits "
                        "stocks, not the whole cross-asset move.", S["body"])]))
    rates = [["Rates", "Now", "Since 6 Oct", "Last week"]]
    for sid in ("DGS2", "DGS10", "DFII10", "T10YIE"):
        r = cr.loc[sid]
        rates.append([r.series, f"{r.now:.2f}%", f"{r.chg_peak_bp:+.0f} bp", f"{r.chg_1w_bp:+.0f} bp (z {r.z_1w:+.1f})"])
    story.append(KeepTogether([Paragraph("Why long Treasuries rose and then fell", S["h2"]), table(rates, [0.40, 0.18, 0.2, 0.22]),
                               Paragraph("Since 6 Oct the 10-year yield fell on lower inflation expectations (breakevens, "
                                         "with oil down), not lower real yields. Last week real yields jumped with the 2-year "
                                         "as the market priced a December hike: the rate shock that hit everything at once.",
                                         S["cap"])]))
    pos_rows = [["Futures (CFTC, 10 Nov)", "Group", "Net", "1 week", "4 weeks", "Range since 2024"]]
    for _, r in pos.iterrows():
        pos_rows.append([r.series.replace(", leveraged", ""), r.group, f"{r.net:,.0f}",
                         f"{r.chg_1w:+,.0f}", f"{r.chg_4w:+,.0f}", f"{r.range_pct:.0%}"])
    story.append(KeepTogether([Paragraph("Positioning before this week's drop", S["h2"]),
                               table(pos_rows, [0.24, 0.17, 0.15, 0.13, 0.13, 0.18])]))
    story.append(KeepTogether([Paragraph("Not covered yet", S["h2"]), Paragraph(
        "EPFR fund flows (BofA's Flow Show: no November issue found in the press), prime-brokerage and retail positioning "
        "(Goldman, Deutsche Bank, Vanda), earnings revisions by sector (FactSet Earnings Insight), the share of S&amp;P 500 "
        "stocks above their 50-day average, and Cboe implied correlation (COR3M has no history on Yahoo). Flows for "
        "iShares, Vanguard and Invesco funds are not computed.", S["body"])]))
    story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
        "ETF flows: change in shares outstanding times NAV from State Street SPDR NAV-history files. Money market funds: "
        "ICI weekly file (2026). Credit spreads, yields, Fed balance sheet, TGA and reverse repo: FRED. Volatility "
        "indices and total returns: Yahoo Finance. Positioning: CFTC Commitments of Traders. Fund-manager survey: BofA, "
        "as reported by HedgeCo and Longbridge. All-ETF and gold-ETF flows: ETF.com, ETF Action, Invezz (press). "
        "Profit-taking test: Spearman correlation of the return 6 Oct 2025 to 6 Oct 2026 with the return since, fixed "
        "before computing; robustness checks added after review.", S["small"])]))
    doc.build(story)
    return out_pdf
