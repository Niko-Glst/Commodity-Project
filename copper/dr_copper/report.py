"""The Dr. Copper note (PDF), in the style of the gold desk notes."""

from __future__ import annotations

import json
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

from . import analysis as A  # noqa: E402

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
COPPER_C, NASDAQ_C, SOX_C = "#eb6834", "#1c5cab", "#0d8a7a"     # validated categorical set, fixed per entity
RED, GREEN = "#d03b3b", "#006300"
FONT = ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf")

for fp in FONT:
    font_manager.fontManager.addfont(fp)
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 8.5, "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False, "legend.fontsize": 7.8,
})


def _save(fig, path: Path) -> Path:
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_recent(df: pd.DataFrame, out: Path) -> Path:
    """Copper, Nasdaq and SOX since January 2025, each rebased to 100, with each one's high marked."""
    series = [("HG=F", "Copper", COPPER_C, 8), ("^IXIC", "Nasdaq Composite", NASDAQ_C, -14), ("^SOX", "SOX", SOX_C, 6)]
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    for t, name, c, dy in series:
        s = df[t].dropna().loc["2025-01-01":]
        s = 100 * s / s.iloc[0]
        ax.plot(s.index, s.values, color=c, lw=1.6, label=name)
        hi = s.idxmax()
        ax.scatter([hi], [s[hi]], s=26, color=c, edgecolor="white", lw=1.2, zorder=4)
        ax.annotate(f"{name.split()[0]} high, {hi.day} {hi:%b}", (hi, s[hi]), xytext=(-4, dy), textcoords="offset points",
                    fontsize=7, color=INK2, ha="right", bbox=dict(facecolor="white", edgecolor="none", pad=0.4))
        ax.annotate(f"{s.iloc[-1]:.0f}", (s.index[-1], s.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=7.4, color=INK, va="center")
    ax.axhline(100, color=AXIS, lw=0.7)
    ax.set_ylabel("2 Jan 2025 = 100")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    return _save(fig, out / "c_recent.png")


def chart_rolling(df: pd.DataFrame, out: Path) -> Path:
    wr = A.weekly_returns(df)
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    for t, name, c, lw in (("^IXIC", "Nasdaq Composite", NASDAQ_C, 1.6), ("^SOX", "SOX", SOX_C, 1.1)):
        r = wr[A.COPPER].rolling(52).corr(wr[t]).dropna()
        ax.plot(r.index, r.values, color=c, lw=lw, label=f"Copper vs {name}")
    for name, (start, end) in A.ERAS.items():
        x = wr[[A.COPPER, "^IXIC"]].loc[start:end].dropna()
        ax.hlines(x[A.COPPER].corr(x["^IXIC"]), pd.Timestamp(start), x.index[-1], color=INK, lw=1.0, ls=(0, (3, 2)))
    ax.axvline(pd.Timestamp("2022-11-30"), color=MUTED, lw=0.6, ls=":")
    ax.text(pd.Timestamp("2022-11-30"), 0.86, " ChatGPT", fontsize=7, color=MUTED, va="top")
    ax.axhline(0, color=AXIS, lw=0.7)
    ax.set_ylim(-0.2, 0.9)
    ax.set_ylabel("Correlation, past 52 weeks")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    h, l_ = ax.get_legend_handles_labels()
    h.append(plt.Line2D([], [], color=INK, lw=1.0, ls=(0, (3, 2))))
    l_.append("Era average, Nasdaq")
    ax.legend(h, l_, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    return _save(fig, out / "c_rolling.png")


def chart_ratio(df: pd.DataFrame, out: Path) -> Path:
    """Copper/gold ratio and the 10-year yield in two panels on a shared time axis (no second y-axis)."""
    w = A.weekly_closes(pd.DataFrame({"ratio": 1000 * df[A.COPPER] / df[A.GOLD], "tnx": df["^TNX"]}).dropna())
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 2.6), sharex=True)
    a1.plot(w.index, w.ratio, color=COPPER_C, lw=1.3)
    a1.set_ylabel("Copper/gold\n(x1000)")
    a2.plot(w.index, w.tnx, color=INK2, lw=1.3)
    a2.set_ylabel("US 10Y yield, %")
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for a in (a1, a2):
        a.axvspan(pd.Timestamp("2023-01-01"), w.index[-1], color="#f4f3ef", lw=0, zorder=0)
    a1.text(pd.Timestamp("2023-02-01"), a1.get_ylim()[1], "since 2023", fontsize=7, color=MUTED, va="top")
    return _save(fig, out / "c_ratio.png")


def chart_cumulative(df: pd.DataFrame, out: Path) -> Path:
    """Cumulative squared-error gain over the historical mean: rising = the copper signal helped."""
    p = A.panel(df)
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    styles = [(INK, "-", 1.5), (INK2, (0, (4, 2)), 1.3), (MUTED, (0, (1, 1.5)), 1.5)]
    ends = []
    for (name, (kind, k)), (c, ls, lw) in zip(A.CANDIDATES.items(), styles):
        fc = A.oos(p, f"{kind}_{k}").dropna(subset=["outcome"])
        gain = ((fc.outcome - fc.fc_mean) ** 2 - (fc.outcome - fc.fc_model) ** 2).cumsum() * 100
        ax.plot(gain.index, gain.values, color=c, ls=ls, lw=lw, label=name)
        ends.append([gain.iloc[-1], name.replace(", past", ","), gain.index[-1]])
    ends.sort()
    for i in range(1, len(ends)):                      # keep end labels at least 0.45 apart
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.45)
    for y, label, x in ends:
        ax.annotate(label, (x, y), xytext=(4, 0), textcoords="offset points", fontsize=7, color=INK2, va="center")
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.set_ylabel("Cumulative gain\n(squared error x100)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    return _save(fig, out / "c_cumulative.png")


# ---------------------------------------------------------------- PDF
W, H = A4
M = 16 * mm
CW = W - 2 * M
C = colors.HexColor


def _st(name, **kw):
    return ParagraphStyle(name, **{"fontName": "SUI", "fontSize": 8.8, "leading": 12.2, "textColor": C(INK), **kw})


def build_pdf(df: pd.DataFrame, folder: Path) -> Path:
    R = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    charts = folder / "_charts"
    charts.mkdir(exist_ok=True)
    pdfmetrics.registerFont(TTFont("SUI", FONT[0]))
    pdfmetrics.registerFont(TTFont("SUI-B", FONT[1]))
    registerFontFamily("SUI", normal="SUI", bold="SUI-B", italic="SUI", boldItalic="SUI-B")
    S = {
        "h2": _st("h2", fontName="SUI-B", fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3, textColor=C(NAVY)),
        "body": _st("body"), "small": _st("small", fontSize=7.4, leading=9.8, textColor=C(INK2)),
        "bul": _st("bul", leftIndent=10, bulletIndent=0, spaceAfter=2.2),
        "cell": _st("cell", fontSize=8.0, leading=10.2), "cellb": _st("cellb", fontName="SUI-B", fontSize=8.0, leading=10.2),
        "cap": _st("cap", fontSize=7.4, leading=9.6, textColor=C(MUTED), spaceBefore=1, spaceAfter=3),
    }
    last = pd.Timestamp(R["last_close"])
    sn = R["snapshot"]
    cu, nq, sx = sn["HG=F"], sn["^IXIC"], sn["^SOX"]
    pre = pd.DataFrame(R["preregistered"])
    n_pass = int(pre.qualifies.sum())

    def header_footer(c, doc):
        c.saveState()
        c.setFillColor(C(NAVY)); c.rect(0, H - 24 * mm, W, 24 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("SUI-B", 15); c.drawString(M, H - 12 * mm, "COPPER  |  TECH")
        c.setFont("SUI", 9.5); c.drawString(M, H - 18 * mm, "Side project: is Dr. Copper an indicator for the Nasdaq?")
        c.setFont("SUI-B", 9.5); c.drawRightString(W - M, H - 12 * mm, f"Data to {last:%d %B %Y} close")
        c.setFont("SUI", 8.5); c.drawRightString(W - M, H - 18 * mm, "COMEX copper (HG=F) vs Nasdaq, SOX")
        c.setStrokeColor(C(GRID)); c.setLineWidth(0.6); c.line(M, 12 * mm, W - M, 12 * mm)
        c.setFillColor(C(MUTED)); c.setFont("SUI", 7)
        c.drawString(M, 8 * mm, "Pre-registered test: commit 00f4748, before the first run")
        c.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
        c.restoreState()

    out_pdf = folder / f"dr_copper_{last:%Y-%m-%d}.pdf"
    doc = BaseDocTemplate(str(out_pdf), pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm,
                          bottomMargin=14 * mm, title=f"Dr. Copper and the tech market, {last:%d %b %Y}",
                          author="Nikolay Gelshtein")
    frame = Frame(M, 14 * mm, CW, H - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])

    def table(rows, widths, bold_first=True):
        data = [[Paragraph(f"<b>{h}</b>", S["cell"]) for h in rows[0]]]
        data += [[Paragraph(str(c_), S["cellb"] if (j == 0 and bold_first) else S["cell"]) for j, c_ in enumerate(r)]
                 for r in rows[1:]]
        t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6), ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        return t

    def img(path):
        iw, ih = ImageReader(str(path)).getSize()
        return Image(str(path), width=CW, height=CW * ih / iw)

    def kpis(items):
        cells = [[Paragraph(f'<font size="7.2" color="{MUTED}">{k.upper()}</font><br/>'
                            f'<font name="SUI-B" size="14" color="{col}">{v_}</font><br/>'
                            f'<font size="7.2" color="{INK2}">{sub}</font>', _st("k", leading=15))
                  for k, v_, sub, col in items]]
        t = Table(cells, colWidths=[CW / len(items)] * len(items))
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C("#f4f3ef")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
        return t

    def callout(html):
        t = Table([[Paragraph(html, S["body"])]], colWidths=[CW])
        t.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, C(COPPER_C)),
                               ("BACKGROUND", (0, 0), (-1, -1), C("#fbf7f3")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
        return t

    era = {b: pd.DataFrame(v) for b, v in R["eras"].items()}
    e_nq, e_sx = era["^IXIC"], era["^SOX"]
    ai_p = R["ai_vs_2010s"]["^IXIC"]["p"]
    best = pre.sort_values("cw_p").iloc[0]
    rv = R["ratio_vs_10y"]
    lh = pd.Timestamp(R["rolling_corr_last_higher"])
    pct = lambda x: f"{x:+.1%}"  # noqa: E731
    pct2 = lambda x: "0.00%" if abs(x) < 5e-5 else f"{x:+.2%}"  # noqa: E731

    # ---------------- page 1
    story = [kpis([
        ("Copper, $/lb", f"{cu['last']:.2f}", f"{pct(cu['from_high'])} from 9 Sep record", INK),
        ("Nasdaq, November", pct(nq["nov"]), f"{pct(nq['from_high'])} from 6 Oct high", RED),
        ("SOX, November", pct(sx["nov"]), f"{pct(sx['from_high'])} from 22 Jun high", RED),
        ("Moving together", f"{R['rolling_corr_now']:.2f}", "52-week correlation with the Nasdaq", INK),
        ("Leads the Nasdaq?", "No", f"{n_pass} of {len(pre)} pre-registered signals pass", INK),
    ]), Spacer(1, 7)]
    story.append(callout(
        f"<b>Bottom line.</b> Copper and tech do move together: the weekly correlation with the Nasdaq is "
        f"{R['rolling_corr_now']:.2f} over the past year, the highest since {lh:%B %Y}, and both are falling this "
        f"autumn. But copper is <b>not a leading indicator</b>. In a test fixed before it was run, none of three "
        f"copper signals forecast the Nasdaq's next four weeks better than its plain historical average, on "
        f"{int(pre.n.max()):,} weekly forecasts since 2005 (best: R² {best.r2_os:+.1%}, p = {best.cw_p:.2f}). Nor does "
        f"the Nasdaq lead copper. The AI era has not made the link tighter either: since 2023 the correlation is "
        f"{e_nq.iloc[-1]['corr']:.2f}, against {e_nq.loc[e_nq.era == '2010-2019', 'corr'].iloc[0]:.2f} in 2010-19. "
        "Copper and tech react to the same news at the same time; neither gives the other a head start."))

    story += [Paragraph("This autumn", S["h2"]), img(chart_recent(df, charts)),
              Paragraph("Daily closes rebased to 100 on 2 Jan 2025; dots mark each series' high. The three did not top "
                        "in a fixed order: semiconductors in June, copper in September, the Nasdaq in October. The spike and drop "
                        "in COMEX copper in July 2025 is the US tariff episode.", S["cap"])]
    rows = [["Claim in the text", f"Data to {last:%d %b} close", "Verdict"],
            ["Copper down roughly 11-17% from its September record",
             f"Record close ${cu['high']:.2f} on 9 Sep (Yahoo; CNN reported a ${6.89:.2f} settlement); now "
             f"${cu['last']:.2f}, {pct(cu['from_high'])}, after {pct(cu['day'])} on {last:%d %b}", "Holds, at the top end"],
            ["Nasdaq Composite down over 4% in November", f"{pct(nq['nov'])} since 30 Oct", "Holds, just"],
            ["SOX down about 10.4% in November", f"{pct(sx['nov'])} since 30 Oct; {pct(sx['from_high'])} since 22 Jun",
             "Close; the bigger fall started in June"],
            ["Copper and tech tightly linked because of AI",
             f"52-week correlation {R['rolling_corr_now']:.2f} now; AI-era average {e_nq.iloc[-1]['corr']:.2f} vs "
             f"{e_nq.loc[e_nq.era == '2010-2019', 'corr'].iloc[0]:.2f} in 2010-19 (difference p = {ai_p:.2f})",
             "Linked now; not more than before AI"],
            ["A strong dollar weighed on both", f"Dollar index {pct(R['dollar_since_copper_high'])} since copper's "
             "record on 9 Sep", "Consistent"],
            ["Copper might be an indicator for tech", f"0 of 3 pre-registered signals pass (page 3)", "No"]]
    story += [Paragraph("The claims, checked", S["h2"]), table(rows, [0.33, 0.47, 0.20])]

    # ---------------- page 2
    story.append(PageBreak())
    story += [Paragraph("Moving together", S["h2"]),
              Paragraph("Correlation of weekly returns (Friday to Friday), so both markets are measured over the same "
                        "days. A correlation of 0.4 means copper explains about a sixth of the Nasdaq's weekly moves "
                        "(0.4² = 0.16), in the same week.", S["body"]), Spacer(1, 2),
              img(chart_rolling(df, charts)),
              Paragraph(f"The current {R['rolling_corr_now']:.2f} is high but not a record: the peak was "
                        f"{R['rolling_corr_max']:.2f} in {pd.Timestamp(R['rolling_corr_max_date']):%B %Y}. Correlations "
                        "rise in sell-offs, when one risk-on/risk-off factor drives everything.", S["cap"])]
    rows = [["Period", "Weeks", "Copper vs Nasdaq", "95% interval", "Copper vs SOX", "95% interval"]]
    for (_, a), (_, b) in zip(e_nq.iterrows(), e_sx.iterrows()):
        rows.append([a.era, int(a.n), f"{a['corr']:.2f}", f"{a.lo:.2f} to {a.hi:.2f}", f"{b['corr']:.2f}",
                     f"{b.lo:.2f} to {b.hi:.2f}"])
    story += [table(rows, [0.22, 0.10, 0.17, 0.17, 0.17, 0.17]),
              Paragraph(f"AI era vs 2010-19: Nasdaq p = {ai_p:.2f}, SOX p = {R['ai_vs_2010s']['^SOX']['p']:.2f}, "
                        f"S&amp;P 500 p = {R['ai_vs_2010s']['^GSPC']['p']:.2f} (Fisher test). The link was strongest in "
                        "the 2008-09 crisis and has not strengthened since 2023, despite copper's role in data centres.",
                        S["cap"])]
    story += [Paragraph("Dr. Copper's classic signal: yields", S["h2"]),
              Paragraph(f"The original Dr. Copper idea is about growth and rates, not tech. Since 2000 the copper/gold "
                        f"ratio and the 10-year yield have moved together: correlation {rv['level_corr']:.2f} in levels and "
                        f"{rv['chg13_corr']:.2f} in 13-week changes. Since 2023 the changes still agree "
                        f"({rv['chg13_corr_2023']:.2f}), but the levels have split ({rv['level_corr_2023']:+.2f}): gold's "
                        "rally pushed the ratio down while yields rose, so the ratio no longer says where yields stand.",
                        S["body"]), Spacer(1, 2), img(chart_ratio(df, charts)),
              Paragraph("Weekly closes; copper in $/lb, gold in $/oz. Shaded: since 2023.", S["cap"])]

    # ---------------- page 3
    story.append(PageBreak())
    story += [Paragraph("Does copper lead? The pre-registered test", S["h2"]),
              Paragraph(f"Each week since 2005 a regression on all earlier weeks turns the copper signal into a forecast "
                        f"of the Nasdaq Composite's next four weeks; the benchmark is the Nasdaq's average four-week return "
                        f"up to that week. The signal stops the day before each forecast, so it is always known in time. "
                        f"Copper passes only with R² above zero, a Clark-West p-value below {R['rule']['p_max']:.4f} and R² "
                        "above zero in both halves. The rule was committed before the first run.", S["body"]), Spacer(1, 3)]
    rows = [["Signal", "Forecasts", "R² vs average", "p (Clark-West)", "R², 1st half", "R², 2nd half", "Passes"]]
    for _, r in pre.iterrows():
        rows.append([r.candidate, f"{int(r.n):,}", f"{r.r2_os:+.2%}", f"{r.cw_p:.2f}", f"{r.r2_early:+.2%}",
                     f"{r.r2_late:+.2%}", "Yes" if r.qualifies else "No"])
    story += [table(rows, [0.30, 0.11, 0.13, 0.13, 0.12, 0.12, 0.09]), Spacer(1, 2), img(chart_cumulative(df, charts)),
              Paragraph("Squared-error gain of each copper signal over the historical average, added up week by week. "
                        "A signal that helps climbs steadily; these drift around zero and end below it.", S["cap"])]
    sec = pd.DataFrame(R["secondary"])
    rows = [["Also checked (not part of the rule)", "R² vs average", "p", "Direction right"]]
    for _, r in sec.iterrows():
        rows.append([r.test, pct2(r.r2_os), f"{r.cw_p:.2f}", f"{r.hit_rate:.0%}"])
    story.append(KeepTogether([table(rows, [0.52, 0.16, 0.12, 0.20]), Paragraph(
        "'Direction right': how often the signal moved the forecast above or below the average in the direction "
        "the market then went; 50% is a coin flip.", S["cap"])]))

    rg = pd.DataFrame(R["regimes"])
    bp = pd.DataFrame(R["bear_peaks"])
    oh = R["copper_off_high"]
    block = [Paragraph("Two simpler checks", S["h2"]),
             Paragraph(f"<b>After copper fell over 13 weeks</b>, the Nasdaq rose {rg.iloc[1]['mean']:+.2%} on average over "
                       f"the next four weeks ({rg.iloc[1]['share_up']:.0%} of the time up), against {rg.iloc[0]['mean']:+.2%} "
                       f"after copper rose ({rg.iloc[0]['share_up']:.0%} up). The gap has p = {rg.iloc[0]['gap_p']:.2f}: "
                       "no difference.", S["body"]),
             Paragraph(f"<b>At Nasdaq tops.</b> At the start of each of the {len(bp)} Nasdaq bear markets since 2001 "
                       f"(falls of 20% or more), copper stood a median {-bp.copper_off_high_at_peak.median():.0%} below its "
                       f"six-month high. On an ordinary day it stands {-oh['median']:.0%} below it, and on "
                       f"{oh['share_7pct']:.0%} of days more than 7% below. With {len(bp)} tops this does not separate a "
                       f"warning from normal noise. Today copper is {-oh['now']:.0%} below its six-month high and the Nasdaq "
                       f"{-nq['from_high']:.1%} below its high, not in a bear market.", S["body"])]
    story.append(KeepTogether(block))

    story.append(KeepTogether([Paragraph("What it means", S["h2"])] + [Paragraph(t_, S["bul"], bulletText="\u2022") for t_ in [
        "Copper is a <b>thermometer, not a forecast</b>: it confirms risk appetite in the same week but does not warn "
        "ahead of it. Prices react to the same news, AI spending, rates and the dollar, at the same time.",
        "Copper's fall this autumn shows that the news on AI spending and industrial demand is already in prices; it "
        "adds nothing about the Nasdaq's next month.",
        "The co-movement matters as a <b>risk</b> fact: the link was strongest in the 2008-09 crisis and is high again "
        "now, so copper and tech exposure diversify each other least in a sell-off.",
    ]]))
    story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
        "Daily closes from Yahoo Finance since 2000 (snapshot in copper/data/prices.csv). Weekly returns are log changes "
        "between the last closes of each week. Correlation intervals use the Fisher transformation. Out-of-sample test: "
        "expanding OLS, first forecast after 260 known weekly pairs, Clark-West test with Newey-West errors (3 lags) "
        "for the overlapping 4-week windows; 13-week tests use 12 lags. Bear markets by the 20/20 rule (a fall of 20% "
        "from a high, ending at a rise of 20% from the low). News context: CNN (copper record, 10 Sep 2026), "
        "GuruFocus and Rio Times (18 Nov 2026).", S["small"])]))
    doc.build(story)
    return out_pdf
