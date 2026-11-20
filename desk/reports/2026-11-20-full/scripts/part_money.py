# ---------------- full analysis: where money is going
stz, sf = EX["stress"], EX["sflows"]
pf_ = pd.DataFrame(EX["perf"]).set_index("ticker")
grp = {g_["group"].split(" (")[0]: g_ for g_ in EX["groups"]}
story.append(PageBreak())
story += [Paragraph("3. Where money is going now", S["h1"]),
          Paragraph("The macro logic: when real rates rise, growth cools and markets get nervous, money moves away from "
                    "promises of future growth and from raw materials, toward certainty: cash that pays interest, "
                    "Treasuries, the dollar, and companies with steady demand. Prices show which assets did better than "
                    "cash; fund flows show where new money actually went.", S["body"]), Spacer(1, 2), img(c_sectors),
          Paragraph(f"Total returns since 6 Oct (the stock-market high) to the latest print on {dd(EX['etf_last'])}, dividends "
                    "included. Dashed line: cash.", S["cap"])]
rows = [["Group (simple average of ETFs)", "Since the gold record", "Since 6 Oct", "This week", "Today"]]
for g_ in EX["groups"]:
    rows.append([g_["group"], pc(g_["since_record"]), pc(g_["since_oct6"]), pc(g_["week"]), pc(g_["today"])])
story += [table(rows, [0.44, 0.15, 0.14, 0.14, 0.13]),
          Paragraph(f"Momentum stocks against low-volatility stocks: {EX['mom_vs_lowvol']['since_oct6']:+.1%} since 6 Oct: "
                    "last year's winners are being sold.", S["cap"])]
FN = {"SPY": "S&P 500", "BIL": "T-bills (cash)", "XLK": "Technology", "XLC": "Communication", "XLY": "Consumer discretionary",
      "XLF": "Financials", "XLI": "Industrials", "XLE": "Energy", "XLB": "Materials", "XLV": "Health care",
      "XLP": "Consumer staples", "XLU": "Utilities", "XLRE": "Real estate", "XSD": "Semiconductors (equal weight)",
      "XME": "Metals and mining", "GLD": "Gold"}
rows = [["Fund (State Street data)", "Since the gold record", "Since 6 Oct", "This week*", "Week vs past year"]]
for t in sorted(sf, key=lambda k: sf[k]["since_record_bn"], reverse=True):
    rows.append([f"{FN[t]} ({t})", f"{bn(sf[t]['since_record_bn'])} ({sf[t]['since_record_pct']:+.1%})",
                 f"{bn(sf[t]['since_oct6_bn'])} ({sf[t]['since_oct6_pct']:+.1%})", bn(sf[t]["week_bn"], 2),
                 f"z {sf[t]['z_week']:+.1f}"])
story += [KeepTogether([Paragraph("Where new money went: fund flows", S["h2"]), table(rows, [0.31, 0.20, 0.18, 0.13, 0.18], size=7.1),
                        Paragraph(f"*To {dd(sf['SPY']['last'])}. Flows are the change in shares outstanding times NAV, from "
                                  "State Street's own files; they cover SPDR funds only.", S["cap"])])]
story += bullets([
    f"<b>Into cash and the broad market.</b> Since the gold record the S&amp;P 500 fund took in ${sf['SPY']['since_record_bn']:.1f}bn "
    f"and the T-bill fund ${sf['BIL']['since_record_bn']:.1f}bn ({sf['BIL']['since_record_pct']:.0%} of its assets). This week cash "
    f"was the clearest inflow (z {sf['BIL']['z_week']:+.1f}).",
    f"<b>Out of financials and gold.</b> Financials lost ${abs(sf['XLF']['since_record_bn']):.1f}bn and gold "
    f"${abs(sf['GLD']['since_record_bn']):.1f}bn. Defensive sector funds rose in price without much new money (consumer staples "
    f"{bn(sf['XLP']['since_record_bn'])}): they gained because they were sold less.",
    f"<b>Stress is rising.</b> VIX {stz['vix']:.1f}, {stz['vix_ratio']:.2f} times its 3-month version (above 1 = stress); "
    f"high-yield spread {stz['hy']:.2f}% ({stz['hy_since_oct6_bp']:+.0f} bp since 6 Oct). Sectors move together more (21-day "
    f"correlation {stz['corr21']:.2f}, from {stz['corr21_oct6']:.2f}) but far less than in the April 2025 crash "
    f"({stz['corr21_max']:.2f}); bond volatility (MOVE {stz['move']:.0f}) is moderate.",
])
btc = X["BTC-USD"]["since_oct6"]
mech = [["Macro force now", "Usually gains", "Usually loses", "Seen since 6 Oct"],
        ["Real rates high and rising", "Cash, short-term bonds, the dollar", "Growth and tech, gold, bitcoin",
         f"AI and growth {pc(grp['AI and growth']['since_oct6'], 0)}, gold {pc(grp['Gold']['since_oct6'], 0)}, bitcoin "
         f"{pc(btc, 0)}; cash {pc(grp['Cash']['since_oct6'])}"],
        ["Growth cooling", "Staples, health care, utilities", "Metals, miners, cyclicals",
         f"Defensives {pc(grp['Defensive sectors']['since_oct6'], 0)}, metals {pc(grp['Metals and miners']['since_oct6'], 0)}, "
         f"cyclicals {pc(grp['Cyclical sectors']['since_oct6'], 0)}"],
        ["Stress and forced selling", "Treasuries, the dollar, cash", "Everything with risk, gold included",
         f"This week: Treasuries {pc(grp['Treasuries']['week'])}, dollar {pc(grp['US dollar']['week'])}; every other group down"],
        ["Inflation up, Fed fighting it", "The dollar, cash; energy if oil rises", "Gold while real rates rise",
         f"Oil fell ({pc(X['CL=F']['since_oct6'], 0)}), so energy did not gain ({pc(pf_.loc['XLE', 'since_oct6'], 0)}); "
         f"gold {pc(grp['Gold']['since_oct6'], 0)}"]]
story += [KeepTogether([Paragraph("The mechanism, checked against what happened", S["h2"]), table(mech, [0.22, 0.24, 0.24, 0.30]),
                        Paragraph("Tendencies, not rules: markets know them, so part is priced in, and when the Fed or the "
                                  "panic turns, the hardest-hit sectors usually recover first.", S["cap"])])]

