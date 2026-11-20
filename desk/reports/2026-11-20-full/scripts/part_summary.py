story.append(Paragraph("Summary", S["h1"]))
EXs = R["extra"]
gs = {g_["group"].split(" (")[0]: g_ for g_ in EXs["groups"]}
a26s = {a["peak"]: a for a in EXs["after_peaks"]}["2026-02"]
worst = R["n_worse_weeks_since_2000"] == 0
story += numbered([
    f"<b>The move.</b> Gold is at {now:,.0f} ({ASOF}), {pc(R['r_today'])} today and {pc(R['r_week'])} this week"
    + (", the worst week for COMEX gold futures since at least 2000 if it closes here" if worst else "")
    + f". It is {abs(R['from_peak']):.0%} below the {dd(R['peak_date'])} record and the lowest since late August 2025.",
    f"<b>Three forces, one after the other.</b> (1) <i>Since February</i> the 10-year real yield (TIPS) has risen about "
    f"{re_now['since_feb_bp'] / 100:.1f} points to {re_now['now']:.2f}%, the highest outside 2026 since 2008. (2) <i>Since "
    "early October</i> the inflation hedge has been unwinding: breakeven inflation fell "
    f"{abs(macro['10-year breakeven inflation']['now'] - macro['10-year breakeven inflation']['oct6']) * 100:.0f} bp and "
    "silver, copper and bitcoin fell harder than gold. (3) <i>This week</i> hawkish Fed signals turned into liquidation: on "
    f"Thursday and Friday stocks fell {abs(eq2):.1%} and the VIX passed 30 while the 10-year yield fell, yet gold fell "
    f"{abs(two_day):.1%}. Gold is being sold to raise cash.",
    f"<b>Macro.</b> The Fed has held at 3.75-4.00% for a year; a December hike is priced at roughly 90-95%. CPI inflation is "
    f"{macro['CPI inflation, 12 months']['now']:.2f}% and {macro['CPI inflation, 3 months annualised']['now']:.1f}% annualised "
    "over three months; the labour market is cooling at the edges; the dollar is near a 19-month high; the high-yield spread "
    f"is {(macro['High-yield credit spread']['now'] - macro['High-yield credit spread']['oct6']) * 100:+.0f} bp since 6 Oct.",
    f"<b>Where money is going.</b> Since 6 Oct AI and growth stocks are {pc(gs['AI and growth']['since_oct6'], 0)}, metals "
    f"{pc(gs['Metals and miners']['since_oct6'], 0)} and gold {pc(gs['Gold']['since_oct6'], 0)}, while defensive sectors are "
    f"{pc(gs['Defensive sectors']['since_oct6'], 0)} and Treasuries {pc(gs['Treasuries']['since_oct6'], 0)}. New money went into "
    f"the S&amp;P 500 fund and cash (the T-bill fund took in {bn(EXs['sflows']['BIL']['since_record_bn'])} since the gold record) "
    "and out of financials and gold. This week only Treasuries, the dollar and cash rose: a flight to safety.",
    f"<b>The model.</b> Today is a {MD['z_today']:.1f}-sigma day, about a 1-in-{1 / MD['p_today']:.0f}-day event. The price is "
    f"below the 1st percentile of the 13 Nov week-ahead forecast. Over {int(c5.n):,} weekly forecasts since 2006 the 90% "
    f"ranges held {c5.inside90:.1%} of the time; the misses cluster in weeks like this.",
    "<b>The past peaks.</b> Every earlier big peak (1974, 1980, 2008, 2011) came with negative real rates; 2026 came with "
    "positive ones. After every earlier peak the Fed was cutting or holding within nine months; now inflation is rising "
    f"({a26s['infl_then']:.1f}% to {a26s['infl_after']:.1f}%) and the Fed is about to hike. In today's dollars gold is "
    f"{abs(H_['now_vs_rec80']):.0%} below its 1980 record. Earlier bear markets fell 40-53%; this one is "
    f"{abs(now / H_['feb_avg'] - 1):.0%} from the February average and {abs(R['from_peak']):.0%} from the daily record.",
    "<b>The tests.</b> Eight extra signals tested this month did not improve the forecasts. Direction is not forecastable; "
    "the size of moves is, on average. Sector patterns after past gold peaks do not repeat either.",
])
