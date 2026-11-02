"""Render the weekly desk note (PDF) from summary.json, news.json, the forecast log and prices."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .backtest import score  # noqa: E402
from .data import GOLD  # noqa: E402
from .model import Forecast, touch_probabilities  # noqa: E402

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NAVY = "#e1e0d9", "#c3c2b7", "#0d366b"
B100, B200, B300, B550 = "#cde2fb", "#9ec5f4", "#6da7ec", "#1c5cab"
ORANGE, RED, GREEN, AMBER = "#eb6834", "#d03b3b", "#006300", "#a35f00"


# ---------------------------------------------------------------- fonts
def _fonts() -> tuple[str, str]:
    """Segoe UI where available (Windows), otherwise DejaVu Sans, which ships with matplotlib."""
    win = Path("C:/Windows/Fonts")
    if (win / "segoeui.ttf").exists():
        regular, bold = win / "segoeui.ttf", win / "segoeuib.ttf"
    else:
        ttf = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        regular, bold = ttf / "DejaVuSans.ttf", ttf / "DejaVuSans-Bold.ttf"
    for path in (regular, bold):
        font_manager.fontManager.addfont(str(path))
    pdfmetrics.registerFont(TTFont("Desk", str(regular)))
    pdfmetrics.registerFont(TTFont("Desk-B", str(bold)))
    pdfmetrics.registerFontFamily("Desk", normal="Desk", bold="Desk-B", italic="Desk", boldItalic="Desk-B")
    return font_manager.FontProperties(fname=str(regular)).get_name(), "Desk"


# ---------------------------------------------------------------- charts
def _style(family: str) -> None:
    plt.rcParams.update({
        "font.family": family, "font.size": 8.5, "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "legend.frameon": False, "legend.fontsize": 7.8,
    })


_usd = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")
_pct = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0%}" if v else "0%")


def _save(fig, path: Path) -> Path:
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def _fan(ax, dates, fan, origin, spot, prefix=""):
    d = [origin, *dates]
    band = lambda q: np.r_[spot, np.asarray(fan[q])[: len(dates)]]  # noqa: E731
    ax.fill_between(d, band(1), band(99), color=B100, lw=0, label=f"{prefix}98% range")
    ax.fill_between(d, band(5), band(95), color=B200, lw=0, label=f"{prefix}90% range")
    ax.fill_between(d, band(25), band(75), color=B300, lw=0, label=f"{prefix}50% range")
    ax.plot(d, band(50), color=B550, lw=1.2, ls=(0, (3, 2)), label="Model median")


def _levels(ax, levels, x):
    lo, hi = ax.get_ylim()
    for lvl in levels:
        if lo < lvl < hi:
            ax.axhline(lvl, color=INK2, lw=0.7, ls=(0, (1, 2)))
            ax.text(x, lvl, f" {lvl:,.0f}", fontsize=7.2, color=INK2, va="bottom")


def _legend(ax, ncol, order=None):
    h, lab = ax.get_legend_handles_labels()
    order = order or list(range(len(h)))[::-1]
    ax.legend([h[i] for i in order], [lab[i] for i in order], loc="upper center",
              bbox_to_anchor=(0.5, -0.12), ncol=ncol)


def chart_scorecard(gold, prev: Forecast, origin, levels, out: Path) -> Path:
    realised = gold.loc[prev.origin:origin].iloc[1:]
    n_show = max(len(realised), 5)
    extra = pd.bdate_range(realised.index[-1] + pd.Timedelta(days=1), periods=n_show - len(realised))
    dates = [*realised.index, *extra]
    fig, ax = plt.subplots(figsize=(7.2, 2.0))
    _fan(ax, dates, prev.fan, prev.origin, prev.spot, "Last week's ")
    hist = gold.loc[prev.origin - pd.Timedelta(days=45):prev.origin]
    ax.plot(hist.index, hist.values, color=INK2, lw=1.5, label="Gold, before last forecast")
    ax.plot([prev.origin, *realised.index], np.r_[prev.spot, realised.values], color=ORANGE, lw=2.0,
            label="Gold, this week")
    ax.scatter(realised.index[-1:], realised.values[-1:], s=26, color=ORANGE, edgecolor="white", lw=1.2, zorder=4)
    ax.axvline(prev.origin, color=AXIS, lw=0.8)
    ax.set_xlim(hist.index[0], dates[-1] + pd.Timedelta(days=1))
    _levels(ax, levels, hist.index[0])
    ax.yaxis.set_major_formatter(_usd)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_ylabel("USD/oz")
    _legend(ax, 3, [5, 4, 3, 2, 1, 0])
    return _save(fig, out)


def chart_forward(gold, fc: Forecast, levels, out: Path) -> Path:
    dates = pd.bdate_range(fc.origin + pd.Timedelta(days=1), periods=len(fc.fan[50]))
    fig, ax = plt.subplots(figsize=(7.2, 2.0))
    _fan(ax, dates, fc.fan, fc.origin, fc.spot)
    hist = gold.loc[fc.origin - pd.Timedelta(days=60):]
    ax.plot(hist.index, hist.values, color=INK2, lw=1.5, label="Gold")
    ax.axvline(fc.origin, color=AXIS, lw=0.8)
    ax.set_xlim(hist.index[0], dates[-1] + pd.Timedelta(days=7))
    for q in (5, 95):
        ax.annotate(f"{fc.fan[q][-1]:,.0f}", (dates[-1], fc.fan[q][-1]), xytext=(4, 0),
                    textcoords="offset points", fontsize=7.6, color=INK2, va="center")
    _levels(ax, levels, hist.index[0])
    ax.yaxis.set_major_formatter(_usd)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_ylabel("USD/oz")
    _legend(ax, 5)
    return _save(fig, out)


def chart_track(scores: pd.DataFrame, out: Path, weeks: int = 104) -> Path:
    s = scores[scores["h"] == 5].sort_values("origin").tail(weeks)
    lo, hi = s["q5"] / s["spot"] - 1, s["q95"] / s["spot"] - 1
    fig, ax = plt.subplots(figsize=(7.2, 1.5))
    ax.vlines(s["origin"], lo, hi, color=B200, lw=2.6, label="Forecast 90% range, 1 week")
    hit = s["inside90"]
    ax.scatter(s.loc[hit, "origin"], s.loc[hit, "ret"], s=9, color=INK2, zorder=3, label="Realised, inside")
    ax.scatter(s.loc[~hit, "origin"], s.loc[~hit, "ret"], s=16, color=RED, zorder=4, label="Realised, outside")
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.yaxis.set_major_formatter(_pct)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.set_ylabel("1-week move")
    _legend(ax, 3, [0, 1, 2])
    return _save(fig, out)


def chart_vol(records: list[dict], gold: pd.Series, out: Path, years: int = 3) -> Path:
    start = gold.index[-1] - pd.DateOffset(years=years)
    model = pd.Series({pd.Timestamp(r["origin"]): Forecast.from_record(r).fit.vol_next for r in records})
    model = model.loc[start:]
    realised = (np.log(gold).diff().rolling(21).std() * np.sqrt(252)).loc[start:]
    fig, ax = plt.subplots(figsize=(7.2, 1.25))
    ax.plot(realised.index, realised.values, color=INK2, lw=1.1, label="Realised, past 21 days")
    ax.plot(model.index, model.values, color=B550, lw=1.6, label="Model forecast, next day")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.set_ylabel("Volatility, annualised")
    _legend(ax, 2, [1, 0])
    return _save(fig, out)


# ---------------------------------------------------------------- PDF
def build_pdf(origin: str, report_dir: Path, prices: pd.DataFrame, records: list[dict]) -> Path:
    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    news_path = report_dir / "news.json"
    news = json.loads(news_path.read_text(encoding="utf-8")) if news_path.exists() else {}
    family, F = _fonts()
    _style(family)

    gold = prices[GOLD].dropna().loc[:origin]
    by_origin = {r["origin"]: r for r in records}
    fc = Forecast.from_record(by_origin[origin])
    earlier = [r for r in records if r["origin"] < origin]
    prev = Forecast.from_record(earlier[-1]) if earlier else None
    scores = score(records, gold)
    levels = news.get("levels", [])
    tmp = report_dir / "_charts"
    tmp.mkdir(exist_ok=True)

    W, H = A4
    M = 16 * mm
    CW = W - 2 * M
    C = colors.HexColor

    def st(name, **kw):
        return ParagraphStyle(name, **{"fontName": F, "fontSize": 8.8, "leading": 12.2, "textColor": C(INK), **kw})

    S = {
        "h2": st("h2", fontName=F + "-B", fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3, textColor=C(NAVY)),
        "body": st("body"),
        "small": st("small", fontSize=7.4, leading=9.8, textColor=C(INK2)),
        "bul": st("bul", leftIndent=10, bulletIndent=0, spaceAfter=2.2),
        "cell": st("cell", fontSize=8.1, leading=10.4),
        "cellb": st("cellb", fontName=F + "-B", fontSize=8.1, leading=10.4),
        "cap": st("cap", fontSize=7.4, leading=9.6, textColor=C(MUTED), spaceBefore=1, spaceAfter=3),
    }
    o = pd.Timestamp(origin)
    week = summary.get("week", {})

    def header_footer(c, doc):
        c.saveState()
        c.setFillColor(C(NAVY))
        c.rect(0, H - 24 * mm, W, 24 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(F + "-B", 15)
        c.drawString(M, H - 12 * mm, "GOLD  |  GC=F")
        c.setFont(F, 9.5)
        c.drawString(M, H - 18 * mm, news.get("title", "Desk note: weekly update"))
        c.setFont(F + "-B", 9.5)
        c.drawRightString(W - M, H - 12 * mm, f"{o:%d %B %Y} close")
        c.setFont(F, 8.5)
        c.drawRightString(W - M, H - 18 * mm, "Prices: COMEX gold futures, USD/oz")
        c.setStrokeColor(C(GRID))
        c.setLineWidth(0.6)
        c.line(M, 12 * mm, W - M, 12 * mm)
        c.setFillColor(C(MUTED))
        c.setFont(F, 7)
        if week:
            c.drawString(M, 8 * mm, f"Previous forecast: {pd.Timestamp(week['prev_origin']):%d %b %Y} close")
        c.drawRightString(W - M, 8 * mm, f"Page {doc.page}")
        c.restoreState()

    out = report_dir / f"gold_desk_{origin}.pdf"
    doc = BaseDocTemplate(str(out), pagesize=A4, leftMargin=M, rightMargin=M, topMargin=30 * mm,
                          bottomMargin=14 * mm, title=f"Gold desk note, {o:%d %b %Y}")
    frame = Frame(M, 14 * mm, CW, H - 43 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])

    def table(rows, widths):
        data = [[Paragraph(f"<b>{h}</b>", S["cell"]) for h in rows[0]]]
        data += [[Paragraph(str(c), S["cellb"] if j == 0 else S["cell"]) for j, c in enumerate(r)] for r in rows[1:]]
        t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1)
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, C(NAVY)), ("LINEBELOW", (0, 1), (-1, -1), 0.4, C(GRID)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        return t

    def img(path):
        iw, ih = ImageReader(str(path)).getSize()
        return Image(str(path), width=CW, height=CW * ih / iw)

    def kpis(items):
        cells = [[Paragraph(f'<font size="7.2" color="{MUTED}">{k.upper()}</font><br/>'
                            f'<font name="{F}-B" size="14" color="{col}">{v}</font><br/>'
                            f'<font size="7.2" color="{INK2}">{sub}</font>', st("k", leading=15))
                  for k, v, sub, col in items]]
        t = Table(cells, colWidths=[CW / len(items)] * len(items))
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C("#f4f3ef")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
        return t

    def callout(html):
        t = Table([[Paragraph(html, S["body"])]], colWidths=[CW])
        t.setStyle(TableStyle([
            ("LINEBEFORE", (0, 0), (0, -1), 3, C(ORANGE)), ("BACKGROUND", (0, 0), (-1, -1), C("#fbf7f3")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
        return t

    def tag(text, col):
        return f'<font name="{F}-B" color="{col}">{text}</font>'

    def signed(x, col_up=GREEN, col_down=RED):
        return col_up if x >= 0 else col_down

    m, ctx, fwd = summary["model"], summary["context"], summary["forward"]
    story = []

    # ---- KPIs and bottom line
    wk_change = week.get("change", 0.0)
    story.append(kpis([
        ("Close", f"{fc.spot:,.0f}", f"{o:%a %d %b}", INK),
        ("Week", f"{wk_change:+.1%}", f"from {week['prev_spot']:,.0f}" if week else "first note", signed(wk_change)),
        ("Model vol", f"{m['vol_next']:.1%}",
         f"last week {m['prev_vol_next']:.1%}" if m.get("prev_vol_next") else "annualised", INK),
        ("1-week 90% range", f"{fwd[0]['q5']:,.0f}-{fwd[0]['q95']:,.0f}", f"to {pd.Timestamp(fwd[0]['date']):%d %b}", INK),
        ("From peak", f"{ctx['from_peak']:+.1%}", f"{ctx['peak']:,.0f} on {pd.Timestamp(ctx['peak_date']):%d %b %Y}", RED),
    ]))
    story.append(Spacer(1, 7))
    if news.get("bottom_line"):
        story.append(callout(f"<b>Bottom line.</b> {news['bottom_line']}"))

    # ---- The week
    if week:
        story.append(Paragraph("The week", S["h2"]))
        notes = news.get("day_notes", {})
        rows = [["Date", "Close", "Day", "What happened"]]
        for d in week["days"]:
            day = pd.Timestamp(d["date"])
            label = notes.get(d["date"]) or ("Last forecast" if d["date"] == week["prev_origin"] else "")
            rows.append([f"{day:%a %d %b}", f"{d['close']:,.0f}", f"{d['ret']:+.1%}" if d["ret"] is not None else "",
                         label])
        story.append(table(rows, [0.14, 0.10, 0.09, 0.67]))

        story.append(Paragraph(f"Cross-asset: {pd.Timestamp(week['prev_origin']):%d %b} to {o:%d %b}", S["h2"]))
        reads = news.get("reads", {})
        fmt = {"GC=F": "{:,.0f}", "^GSPC": "{:,.0f}", "^TNX": "{:.2f}%", "DX-Y.NYB": "{:.1f}", "^VIX": "{:.1f}"}
        rows = [["Market", f"{pd.Timestamp(week['prev_origin']):%d %b}", f"{o:%d %b}", "Change", "Read"]]
        for x in summary.get("cross_asset", []):
            f_ = fmt.get(x["ticker"], "{:.2f}")
            ch = f"{x['change']:+.0f} bp" if x["unit"] == "bp" else f"{x['change']:+.1%}"
            rows.append([x["name"].replace("&", "&amp;"), f_.format(x["prev"]), f_.format(x["now"]), ch,
                         reads.get(x["ticker"], "")])
        rows += news.get("extra_rows", [])
        story.append(table(rows, [0.15, 0.11, 0.11, 0.10, 0.53]))

    if news.get("bullets"):
        story.append(Paragraph("What drove it", S["h2"]))
        for b in news["bullets"]:
            story.append(Paragraph(f"<b>{b['title']}:</b> {b['text']}", S["bul"], bulletText="\u2022"))

    # ---- Scorecard
    lf = summary.get("last_forecast")
    if prev is not None and lf:
        block = [Paragraph("Scorecard: last week's ranges vs what happened", S["h2"]),
                 img(chart_scorecard(gold, prev, o, levels, tmp / "score.png")), Spacer(1, 3)]
        pit = lf["pit"]
        verdict = (tag("Inside range", GREEN) if 0.05 <= pit <= 0.95 else tag("Outside 90% range", RED))
        if 0.05 <= pit < 0.15 or 0.85 < pit <= 0.95:
            verdict = tag("Inside, near the edge", AMBER)
        x_sigma = lf["worst_day_x_sigma"] or 0
        rows = [["Check", "Last week's model", "Realised", "Verdict"],
                [f"Close on {o:%d %b}", f"90% range {lf['band90'][0]:,.0f} to {lf['band90'][1]:,.0f}",
                 f"{fc.spot:,.0f}  ({pit:.0%} percentile)", verdict],
                ["Biggest daily drop", f"typical day {lf['prev_daily_sigma']:.2%}",
                 f"{lf['worst_day_ret']:+.2%} on {pd.Timestamp(lf['worst_day']):%a %d %b} ({x_sigma:.1f}x typical)",
                 tag("Tail day", RED) if x_sigma >= 2.5 else tag("Normal", GREEN)],
                ["Direction", "none (no drift)", "up" if wk_change >= 0 else "down", tag("Not forecast", MUTED)]]
        block.append(table(rows, [0.22, 0.28, 0.30, 0.20]))
        story.append(KeepTogether(block))

    # ---- Ranges from here
    touch = touch_probabilities(fc.fit, fc.spot, levels) if levels else {}
    touch_txt = " ".join(
        f"In <b>{p:.0%}</b> of simulated paths gold {'trades below' if lvl < fc.spot else 'trades above'} "
        f"${lvl:,.0f} at some point in the next month." for lvl, p in touch.items())
    block = [Paragraph("Ranges from here", S["h2"]),
             Paragraph(f"Refitted on all closes to {o:%d %b}. Model volatility is <b>{m['vol_next']:.1%}</b> "
                       f"annualised (long-run level {m['vol_long_run']:.1%}). {touch_txt}", S["body"]),
             Spacer(1, 2), img(chart_forward(gold, fc, levels, tmp / "forward.png")), Spacer(1, 3)]
    rows = [["Horizon", "Ends", "5%", "25%", "Median", "75%", "95%", "90% move"]]
    for r, name in zip(fwd, ("1 week", "2 weeks", "1 month"), strict=True):
        rows.append([name, f"{pd.Timestamp(r['date']):%d %b}"] + [f"{r[f'q{q}']:,.0f}" for q in (5, 25, 50, 75, 95)]
                    + [f"{r['q5'] / fc.spot - 1:+.1%} / {r['q95'] / fc.spot - 1:+.1%}"])
    block += [table(rows, [0.13, 0.11, 0.11, 0.11, 0.11, 0.11, 0.11, 0.21]),
              Paragraph("Percentiles of the simulated close, USD/oz.", S["cap"])]
    story.append(KeepTogether(block))

    if news.get("watch_list"):
        story.append(KeepTogether([Paragraph("Watch list", S["h2"]),
                                   table([["Date, level or event", "Why it matters"], *news["watch_list"]], [0.32, 0.68])]))

    # ---- Track record
    cov = pd.DataFrame(summary.get("coverage", []))
    if len(cov):
        first = cov.loc[cov["window"] == "All history", "first"].dropna().min()
        n_live = summary["n_live"]
        block = [Paragraph("Track record", S["h2"]),
                 Paragraph(f"Every weekly forecast since {pd.Timestamp(first):%b %Y} is scored against what followed: "
                           f"{summary['n_records']:,} forecasts, of which {n_live} made live. A calibrated model lands "
                           "90% of closes inside its 90% range, 5% below and 5% above.", S["body"]),
                 Spacer(1, 2), img(chart_track(scores, tmp / "track.png")), Spacer(1, 3)]
        rows = [["Window", "Horizon", "Forecasts", "Inside 90%", "Below 5%", "Above 95%", "Kupiec p"]]
        for _, r in cov[cov["h"].isin([5, 21])].iterrows():
            if not r["n"]:
                continue
            rows.append([r["window"], f"{r['h']} day{'s' if r['h'] > 1 else ''}", f"{r['n']:,}", f"{r['inside90']:.0%}",
                         f"{r['below5']:.0%}", f"{r['above95']:.0%}", f"{r['kupiec_p']:.2f}"])
        block += [table(rows, [0.20, 0.13, 0.13, 0.14, 0.13, 0.13, 0.14]),
                  Paragraph("Kupiec p below 0.05 means the hit rate differs significantly from 90%. "
                            "21-day windows overlap week to week, so their p-values are too optimistic.", S["cap"])]
        story.append(KeepTogether(block))

    dc = summary.get("drift_check")
    if dc:
        verdict = (tag("Drift qualifies: switch it on", GREEN) if dc["qualifies"]
                   else tag("Keep zero drift", INK))
        rows = [["Horizon", "Forecasts", "Score with drift", "p-value", "2006-15", "2016-26",
                 "Misses below / above: zero", "with drift"]]
        for r in dc["rows"]:
            rows.append([f"{r['h']} days", f"{r['n']:,}", f"{r['change']:+.1%}", f"{r['p']:.3f}",
                         f"{r['change_early']:+.1%}", f"{r['change_late']:+.1%}",
                         f"{r['below_zero']:.0%} / {r['above_zero']:.0%}",
                         f"{r['below_drift']:.0%} / {r['above_drift']:.0%}"])
        story.append(KeepTogether([
            Paragraph("Drift check (shadow test)", S["h2"]),
            Paragraph(f"The model runs without drift. Each week it re-tests a drift of half gold's long-run average "
                      f"return, using only data up to each forecast date. Verdict: {verdict}.", S["body"]),
            Spacer(1, 2),
            table(rows, [0.10, 0.10, 0.13, 0.09, 0.10, 0.10, 0.22, 0.16]),
            Paragraph("Score: average quantile loss vs zero drift; negative is better. The drift goes in only if it "
                      "improves the 1-month score with p &lt; 0.05, in both halves of the sample, without "
                      "worsening the 1-week score.", S["cap"])]))

    # ---- Model update
    block = [Paragraph("Model update", S["h2"]), img(chart_vol(records, gold, tmp / "vol.png")), Spacer(1, 3)]
    rows = [["Parameter", "This week", "Last week", "What it means"],
            ["Volatility, next day", f"{m['vol_next']:.1%}", f"{m['prev_vol_next']:.1%}" if m.get("prev_vol_next") else "",
             "Annualised; drives the width of all ranges"],
            ["Shock weight (alpha)", f"{m['alpha']:.3f}", f"{m['prev_alpha']:.3f}" if m.get("prev_alpha") else "",
             "How much a single day's move lifts tomorrow's volatility"],
            ["Memory (beta)", f"{m['beta']:.3f}", f"{m['prev_beta']:.3f}" if m.get("prev_beta") else "",
             f"Half-life of a volatility shock: {m['half_life_days']:.0f} trading days"],
            ["Tail thickness (df)", f"{m['nu']:.1f}", f"{m['prev_nu']:.1f}" if m.get("prev_nu") else "",
             "Lower means fatter tails; normal is infinite"]]
    block.append(table(rows, [0.22, 0.13, 0.13, 0.52]))
    story.append(KeepTogether(block))

    # ---- Method
    sources = ", ".join(s["name"] for s in news.get("sources", []))
    story.append(KeepTogether([Paragraph("Method and sources", S["h2"]), Paragraph(
        "GARCH(1,1) with Student-t shocks and no drift, refitted every week on all daily COMEX gold futures "
        "(GC=F) closes since 2003; 20,000 simulated paths starting from the next-day variance. The model sizes "
        "moves; it does not forecast direction. Futures trade about $20-40 above spot. Backfilled forecasts use "
        "only data up to their own date, but today's data vintage. "
        + (f"News: {sources}. " if sources else "") + "Data: Yahoo Finance.", S["small"])]))

    doc.build(story)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return out
