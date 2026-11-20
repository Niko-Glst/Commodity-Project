# ---------------- full analysis: other markets after each gold peak
story.append(PageBreak())
ap = EX["after_peaks"]
rows = [["Gold peak", "Gold", "S&P 500", "Dollar", "Oil", "10-year yield", "Fed funds", "Inflation: at peak, then"]]
for a in ap:
    rows.append([pd.Period(a["peak"], "M").strftime("%b %Y"), pc(a["gold"], 0), pc(a["spx"], 0),
                 "n/a" if a["dollar"] is None else pc(a["dollar"], 0), pc(a["oil"], 0), f"{a['y10']:+.2f} pt",
                 f"{a['ffr']:+.2f} pt", f"{a['infl_then']:.1f}% to {a['infl_after']:.1f}%"])
a26 = {a["peak"]: a for a in ap}
story += [Paragraph("7. What other markets did after each gold peak", S["h1"]),
          Paragraph(f"Changes over the {EX['after_months']} months after each peak month, the stretch 2026 has run so far "
                    "(monthly averages).", S["body"]), Spacer(1, 2),
          table(rows, [0.11, 0.08, 0.10, 0.08, 0.08, 0.13, 0.12, 0.30]),
          Paragraph("Fed funds: effective rate (2026 to October). Inflation: CPI over 12 months (2026: October). Dollar: "
                    "Yahoo dollar index from 1971; oil: FRED WTI, then COMEX futures for November.", S["cap"])]
story += bullets([
    f"<b>2026 is the odd one out.</b> It is the only case where inflation rose after the gold peak "
    f"({a26['2026-02']['infl_then']:.1f}% to {a26['2026-02']['infl_after']:.1f}%) and the Fed is about to hike. After 1974, 1980 "
    "and 2008 the Fed was cutting within nine months; after 2011 it stood still.",
    f"<b>Rates and oil.</b> The 10-year yield rose about a point after 1974, 1980 and now ({a26['2026-02']['y10']:+.2f} pt), and "
    f"fell after 2008 and 2011. Oil is up {a26['2026-02']['oil']:.0%} on the February average, more than after any earlier peak.",
    f"<b>Stocks and the dollar.</b> The S&amp;P 500 rose after three of the four earlier peaks and fell only in the 2008 crisis; "
    f"since February 2026 it is {pc(a26['2026-02']['spx'], 0)} (monthly averages). The dollar rose after every peak; now "
    f"{pc(a26['2026-02']['dollar'], 0)}.",
    "<b>Closest match.</b> On rates and inflation, 1974-80; on policy the opposite: then the Fed fell behind inflation, now "
    "it is moving ahead of it. In the past gold's recoveries came once the Fed cut or real rates fell; that trigger is "
    "absent for now.",
])
sa = EX["sect_after"]
SN = {"XLK": "Technology", "XLY": "Consumer discretionary", "XLF": "Financials", "XLI": "Industrials", "XLE": "Energy",
      "XLB": "Materials", "XLV": "Health care", "XLP": "Consumer staples", "XLU": "Utilities", "SPY": "S&P 500",
      "TLT": "Treasuries 20y+", "GLD": "Gold", "BIL": "T-bills (cash)"}
rows = [["Total return", "9 months after Mar 2008", "9 months after Sep 2011", "Since the end of Feb 2026"]]
for t, nm in SN.items():
    cell = lambda pk_: "n/a" if sa[pk_][t] is None else pc(sa[pk_][t], 0)  # noqa: E731
    rows.append([nm, cell("2008-03"), cell("2011-09"), cell("2026-02")])
story += [Paragraph("Sectors after the 2008 and 2011 gold peaks, and now", S["h2"]), table(rows, [0.31, 0.23, 0.23, 0.23]),
          Paragraph(f"Rank correlation of the nine sectors now with 2008: {EX['rank_corr']['2008-03']:+.2f}; with 2011: "
                    f"{EX['rank_corr']['2011-09']:+.2f}. SPDR sector funds start in 1998, so 1974 and 1980 are not covered.",
                    S["cap"])]
story += bullets([
    "<b>No sector pattern repeats.</b> After 2008 everything fell, defensives least; after 2011 everything rose. Since February "
    "2026 health care and energy lead, industrials and utilities lag. Which sectors win depends on the macro of the moment, "
    "not on where gold is in its cycle.",
])

