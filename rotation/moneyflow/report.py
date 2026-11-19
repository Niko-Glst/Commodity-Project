"""The rotation note (PDF), in the style of the gold desk notes."""

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
from .data import CASH  # noqa: E402

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
UP, DOWN, NEUTRAL = "#1c5cab", "#eb6834", "#898781"     # beat cash / lost to cash / cash itself
GOLD_C, COPPER_C = "#1c5cab", "#eb6834"                  # validated pair
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


def chart_bars(perf: pd.DataFrame, out: Path) -> Path:
    x = perf.sort_values("since_peak")
    cash = perf.loc[CASH, "since_peak"]
    col = [NEUTRAL if t == CASH else (UP if v > cash else DOWN) for t, v in x.since_peak.items()]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.barh(range(len(x)), x.since_peak, color=col, height=0.72)
    ax.set_yticks(range(len(x)))
    ax.set_yticklabels([f"{n} ({t})" for t, n in zip(x.index, x.name)], fontsize=7.2, color=INK2)
    for i, v in enumerate(x.since_peak):
        ax.text(v + (0.004 if v >= 0 else -0.004), i, f"{v:+.1%}", va="center", ha="left" if v >= 0 else "right",
                fontsize=6.8, color=INK)
    ax.axvline(0, color=AXIS, lw=0.8)
    ax.axvline(cash, color=NEUTRAL, lw=0.8, ls=(0, (3, 2)))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.xaxis.set_major_formatter(pctfmt)
    ax.set_xlim(x.since_peak.min() - 0.06, x.since_peak.max() + 0.05)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=UP, label="Beat cash"), Patch(color=DOWN, label="Lost to cash"),
                       Patch(color=NEUTRAL, label="Cash (T-bills)")], loc="lower right")
    return _save(fig, out / "r_bars.png")


def chart_scatter(perf: pd.DataFrame, pt: dict, out: Path) -> Path:
    x = perf.drop(index=CASH)
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.scatter(x.year_to_peak, x.since_peak, s=26, color=UP, edgecolor="white", lw=1.0, zorder=3)
    xs = np.linspace(x.year_to_peak.min(), x.year_to_peak.max(), 50)
    ax.plot(xs, pt["intercept"] + pt["slope"] * xs, color=INK2, lw=1.0, ls=(0, (3, 2)))
    label = {"USO", "SMH", "XLE", "COPX", "XLK", "XLP", "XLV", "BTC-USD", "SLV", "GLD", "TLT", "XLU", "QQQ", "UUP"}
    offsets = {"XLU": (-5, 3, "right"), "TLT": (-5, -10, "right"), "UUP": (5, 3, "left")}
    for t, r in x.iterrows():
        if t in label:
            dx, dy, ha = offsets.get(t, (5, 2, "left"))
            ax.annotate(r["name"], (r.year_to_peak, r.since_peak), xytext=(dx, dy), textcoords="offset points",
                        fontsize=6.8, color=INK2, ha=ha)
    ax.axhline(0, color=AXIS, lw=0.7)
    ax.axvline(0, color=AXIS, lw=0.7)
    ax.xaxis.set_major_formatter(pctfmt)
    ax.yaxis.set_major_formatter(pctfmt)
    ax.set_xlabel("Return in the 12 months to the Nasdaq peak (6 Oct 2025 - 6 Oct 2026)")
    ax.set_ylabel("Return since the peak")
    ax.grid(axis="x", color=GRID, lw=0.6)
    return _save(fig, out / "r_scatter.png")


def chart_cot(c: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 2.2))
    for name, col in (("Gold", GOLD_C), ("Copper", COPPER_C)):
        s = (c[name] / c[name + " | OI"]).dropna()
        ax.plot(s.index, s.values, color=col, lw=1.5, label=f"{name}: managed money, net long")
        ax.annotate(f"{s.iloc[-1]:.0%}", (s.index[-1], s.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=7.2, color=INK, va="center")
    ax.axhline(0, color=AXIS, lw=0.7)
    ax.yaxis.set_major_formatter(pctfmt)
    ax.set_ylabel("Share of open interest")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    return _save(fig, out / "r_cot.png")


W, H = A4
M = 16 * mm
CW = W - 2 * M
C = colors.HexColor


def _st(name, **kw):
    return ParagraphStyle(name, **{"fontName": "SUI", "fontSize": 8.8, "leading": 12.2, "textColor": C(INK), **kw})


def build_pdf(p: pd.DataFrame, c: pd.DataFrame, folder: Path) -> Path:
    R = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    perf = pd.DataFrame(R["performance"]).set_index("ticker")
    pt, pos, ext = R["profit_taking"], pd.DataFrame(R["positioning"]), R["external"]
    charts = folder / "_charts"
    charts.mkdir(exist_ok=True)
    pdfmetrics.registerFont(TTFont("SUI", FONT[0]))
    pdfmetrics.registerFont(TTFont("SUI-B", FONT[1]))
    registerFontFamily("SUI", normal="SUI", bold="SUI-B", italic="SUI", boldItalic="SUI-B")
    S = {
        "h2": _st("h2", fontName="SUI-B", fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3, textColor=C(NAVY)),
        "body": _st("body"), "small": _st("small", fontSize=7.4, leading=9.8, textColor=C(INK2)),
        "bul": _st("bul", leftIndent=10, bulletIndent=0, spaceAfter=2.2),
        "cell": _st("cell", fontSize=7.8, leading=10.0), "cellb": _st("cellb", fontName="SUI-B", fontSize=7.8, leading=10.0),
        "cap": _st("cap", fontSize=7.4, leading=9.6, textColor=C(MUTED), spaceBefore=1, spaceAfter=3),
    }
    last = pd.Timestamp(R["last_close"])

    def header_footer(cv, doc):
        cv.saveState()
        cv.setFillColor(C(NAVY)); cv.rect(0, H - 24 * mm, W, 24 * mm, stroke=0, fill=1)
        cv.setFillColor(colors.white)
        cv.setFont("SUI-B", 15); cv.drawString(M, H - 12 * mm, "ROTATION  |  CASH")
        cv.setFont("SUI", 9.5); cv.drawString(M, H - 18 * mm, "Side project: where is the money going?")
        cv.setFont("SUI-B", 9.5); cv.drawRightString(W - M, H - 12 * mm, f"Prices to {last:%d %B %Y} close")
        cv.setFont("SUI", 8.5); cv.drawRightString(W - M, H - 18 * mm, "Total returns of US-listed ETFs; flows as dated")
        cv.setStrokeColor(C(GRID)); cv.setLineWidth(0.6); cv.line(M, 12 * mm, W - M, 12 * mm)
        cv.setFillColor(C(MUTED)); cv.setFont("SUI", 7)
        cv.drawString(M, 8 * mm, "Rerun: python -m moneyflow check (from rotation/)")
        cv.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
        cv.restoreState()

    out_pdf = folder / f"rotation_{last:%Y-%m-%d}.pdf"
    doc = BaseDocTemplate(str(out_pdf), pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm,
                          bottomMargin=14 * mm, title=f"Rotation and cash, {last:%d %b %Y}", author="Nikolay Gelshtein")
    frame = Frame(M, 14 * mm, CW, H - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])

    def table(rows, widths):
        data = [[Paragraph(f"<b>{h}</b>", S["cell"]) for h in rows[0]]]
        data += [[Paragraph(str(x), S["cellb"] if j == 0 else S["cell"]) for j, x in enumerate(r)] for r in rows[1:]]
        t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4), ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        return t

    def img(path, width=CW):
        iw, ih = ImageReader(str(path)).getSize()
        return Image(str(path), width=width, height=width * ih / iw)

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
        t.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, C(DOWN)), ("BACKGROUND", (0, 0), (-1, -1), C("#fbf7f3")),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
        return t

    bp, bn, bw = R["beat_cash"]["since_peak"], R["beat_cash"]["november"], R["beat_cash"]["last_week"]
    g = lambda t, col="since_peak": perf.loc[t, col]  # noqa: E731
    top_names = ", ".join(perf.loc[t, "name"].lower() for t in pt["top5"])

    # ---------------- page 1
    story = [kpis([
        ("Last week", f"{bw[1] - bw[0]} of {bw[1]}", "assets lost to cash", INK),
        ("Since 6 Oct peak", f"{bp[1] - bp[0]} of {bp[1]}", "assets lost to cash", INK),
        ("Winners sold", f"{pt['spearman']:+.2f}", "rank corr., last year vs now", INK),
        ("Fund-manager cash", ext["fms_cash"], ext["fms_cash_sub"], INK),
        ("Money market funds", ext["mmf"], ext["mmf_sub"], INK),
    ]), Spacer(1, 7)]
    story.append(callout(
        "<b>Bottom line.</b> This is mostly <b>rotation and profit-taking, not a rush into cash</b>. Since the Nasdaq's "
        f"6 Oct high, last year's biggest winners fell hardest ({top_names}: {pt['top5_since_peak']:+.0%} on average, "
        f"against {pt['rest_since_peak']:+.0%} for the rest), while consumer staples, health care, utilities, real estate "
        f"and long Treasuries rose and the average S&amp;P 500 stock (equal weight, {g('RSP'):+.1%}) beat the index "
        f"({g('SPY'):+.1%}). The flow data up to 13 Nov point the same way: fund managers cut tech by a record but also "
        "cut cash, and ETF buyers added to broad equity funds. What changed is <b>this week</b>: from 11 to 18 Nov "
        f"{bw[1] - bw[0]} of {bw[1]} assets lost to cash and only the dollar beat it, the first broad de-risking. Whether "
        "money actually moved into cash shows up in tonight's money-fund data (16:30 ET) and Friday's CFTC report."))
    story += [Paragraph("Since the Nasdaq high of 6 October", S["h2"]), img(chart_bars(perf, charts)),
              Paragraph(f"Total returns, 6 Oct to {last:%d %b} close, dividends included. Cash is the 1-3 month T-bill ETF "
                        f"(BIL, {g(CASH):+.2%}): a bar left of the dashed line lost to simply holding cash.", S["cap"])]
    rows = [["Group", "Since 6 Oct", "November", "Last week"]]
    groups = [("Defensive sectors (staples, health care, utilities, real estate)", ["XLP", "XLV", "XLU", "XLRE"]),
              ("AI and growth (semis, tech, software, Nasdaq-100)", ["SMH", "XLK", "IGV", "QQQ"]),
              ("Metals (gold, silver, copper, copper miners)", ["GLD", "SLV", "CPER", "COPX"]),
              ("Safe havens (long Treasuries, dollar)", ["TLT", "UUP"]),
              ("Cash (T-bills)", [CASH])]
    for name, ts in groups:
        rows.append([name] + [f"{perf.loc[ts, col].mean():+.1%}" for col in ("since_peak", "november", "last_week")])
    story += [Spacer(1, 4), table(rows, [0.55, 0.15, 0.15, 0.15]),
              Paragraph("Simple averages of the ETFs in each group.", S["cap"])]

    # ---------------- page 2
    story.append(PageBreak())
    story += [Paragraph("Profit-taking: last year's winners fell hardest", S["h2"]),
              Paragraph(f"If the selling is profit-taking, the assets that gained most should give back most. Across "
                        f"{pt['n']} assets, the rank correlation between the 12-month gain up to the peak and the move since is "
                        f"<b>{pt['spearman']:+.2f}</b> (p = {pt['p']:.3f}). The measure was fixed before it was computed. The "
                        "assets overlap (tech is in the Nasdaq-100), so the p-value is optimistic; the pattern itself is "
                        "clear.", S["body"]), Spacer(1, 2), img(chart_scatter(perf, pt, charts)),
              Paragraph("Each dot is one ETF; dashed: least-squares line. Oil's fall is older: Brent lost about 20% in "
                        "November alone (Kitco).", S["cap"])]


    story += [Paragraph("Futures positioning (CFTC, as of Tuesday 10 Nov)", S["h2"]), img(chart_cot(c, charts))]
    rows = [["Market", "Trader group", "Net position", "1 week", "4 weeks", "Range since 2024"]]
    for _, r in pos.iterrows():
        rows.append([r.series.replace(", leveraged", "").replace("&", "&amp;"), r.group, f"{r.net:,.0f}", f"{r.chg_1w:+,.0f}",
                     f"{r.chg_4w:+,.0f}", f"{r.range_pct:.0%}"])
    story += [table(rows, [0.24, 0.17, 0.15, 0.13, 0.13, 0.18]),
              Paragraph("Contracts long minus short. 'Range since 2024': 0% = most bearish, 100% = most bullish since Jan 2024. "
                        "The data predate this week's drop; the next report (Tuesday 17 Nov) comes out on Friday.", S["cap"])]

    # ---------------- page 3
    story.append(PageBreak())
    story.append(Paragraph("Is money moving into cash? What the flow data say", S["h2"]))
    rows = [["Measure", "Latest", "Reading"]] + ext["evidence"]
    story += [table(rows, [0.27, 0.45, 0.28]),
              Paragraph("Flow figures come from the named providers via press reports and are not checked against raw "
                        "data here; the gold ETF numbers conflict between providers.", S["cap"])]
    story.append(Paragraph("A seller always needs a buyer", S["h2"]))
    story.append(Paragraph(
        "Money does not leave a market the way water leaves a bath. When someone sells stock for cash, the buyer hands "
        "over the same amount of cash: the total is unchanged, only the price and the owner change. Prices fall when "
        "sellers are keener than buyers. So 'money moving into cash' can only be measured where new money is created "
        "or destroyed: <b>fund flows</b> (ETFs and money-market funds issue or redeem shares), <b>positioning</b> (who "
        "holds futures) and <b>surveys</b> (how much cash managers keep). Prices tell you which assets lost to cash, "
        "not who sold.", S["body"]))
    story.append(Paragraph("How to check it yourself", S["h2"]))
    rows = [["What", "Where", "When", "How to read it"],
            ["Which assets lose to cash", "This tool: python -m moneyflow check; or chart any asset against BIL or SGOV",
             "Daily", "Most assets below cash = de-risking; a split = rotation"],
            ["Money market fund assets", "ici.org/research/stats/mmf", "Thursday 16:30 ET (week to Wednesday)",
             "A fast jump during a sell-off = flight to cash; a slow rise = investors chasing the yield"],
            ["ETF flows", "etf.com weekly flows; ICI combined flows", "Weekly",
             "Creations and redemptions are real money in and out of each fund"],
            ["Fund-manager cash", "BofA Global Fund Manager Survey (via press)", "Monthly, mid-month",
             "Cash above 5% = fear (BofA: contrarian buy); 4% or less = complacency (sell signal)"],
            ["Futures positioning", "CFTC Commitments of Traders, publicreporting.cftc.gov", "Friday 15:30 ET (Tuesday data)",
             "Speculators cutting net longs = money leaving that market"],
            ["Gold ETF holdings", "spdrgoldshares.com (tonnes); World Gold Council", "Daily; monthly",
             "Tonnes falling = metal leaving ETFs"],
            ["Breadth", "S&amp;P 500 equal weight (RSP) vs cap weight (SPY)", "Daily",
             "Equal weight ahead = leaders sold, the rest held: rotation"],
            ["Liquidity backdrop", "FRED: M2SL (M2), RRPONTSYD (Fed reverse repo)", "Monthly; daily",
             "Slow-moving; says little about one week"]]
    story.append(table(rows, [0.18, 0.31, 0.17, 0.34]))
    story.append(KeepTogether([Paragraph("About the page you sent", S["h2"]), Paragraph(
        "assetmarketcap.com/asset/CASH-USD showed no data on 19 Nov: every field read '-' and the news items were "
        "placeholders. Its method note says currencies use M2 money supply. M2 is mostly bank deposits and savings of "
        f"households and firms (${R['m2']:,.0f}bn in {pd.Timestamp(R['m2_date']):%B %Y}, FRED); it grows with the economy "
        "and moves too slowly to show investors switching into cash in a given week.", S["body"])]))
    story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
        "Total returns of US-listed ETFs from Yahoo Finance (dividends reinvested; bitcoin spot), closes to "
        f"{last:%d %b %Y}. Profit-taking test: Spearman rank correlation of the return from 6 Oct 2025 to 6 Oct 2026 "
        "with the return since 6 Oct 2026, cash excluded. Positioning: CFTC disaggregated and financial futures reports "
        "via publicreporting.cftc.gov. Flows and surveys: ICI (money market funds, 12 Nov release), Crane Data, BofA "
        "Global Fund Manager Survey as reported by HedgeCo and Longbridge, ETF.com, ETF Action, Invezz (13-19 Nov 2026). "
        "M2: FRED.", S["small"])]))
    doc.build(story)
    return out_pdf
