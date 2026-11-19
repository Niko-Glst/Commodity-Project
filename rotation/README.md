# Rotation or de-risking: where is the money going?

A side project next to the paper, the gold desk and the copper project. Question (19 Nov 2026):
metals and tech are falling and the dollar is strong. Are investors taking profits and moving into
cash, and how can you check where money moves?

Note: [rotation_2026-11-18.pdf](reports/2026-11-18/rotation_2026-11-18.pdf) (4 pages); every number in
[results.json](reports/2026-11-18/results.json). Revised the same day after a review; the first version
led with price measures and claimed money moved into defensive sectors, which the flow data do not show.

## Findings (data to 18 Nov 2026)

**Prices rotated, ETF money did not, and stress rose this week.**

- **Prices:** since the 6 Oct high, AI stocks (-18%) and silver and copper (-23%) fell while defensive
  sectors (+8%) and also financials, consumer discretionary and industrials (+2%) rose. The same holds
  from 1 Oct, 15 Oct or 1 Nov. Consumer discretionary's gain is broad (equal weight +8.8% vs XLY +6.7%).
- **ETF flows** (computed from State Street's daily shares outstanding, SPDR funds only): XLK +$2.5bn and
  SPY +$16bn since 6 Oct, while utilities (-$1.3bn), financials (-$1.4bn) and staples lost money. Defensive
  prices rose without ETF money. No fund's flow last week was unusual against its past year.
- **Cash:** money market funds (ICI) had one unusual week (+$114bn to 4 Nov, z = 3.0) and gave back $36bn
  the next (z = -0.9). The T-bill ETF BIL took in $1.7bn in November. BofA's November survey: managers
  hold 3.6% cash, a sell signal by BofA's own rule.
- **Stress:** the high-yield spread is up 40 bp since 6 Oct (3.43%, 91st percentile since 2024), the VIX
  curve inverted on 17 and 18 Nov (7% of days since 2024), and the 10-year real yield rose 23 bp in a week
  (z = 2.8). Bond volatility (MOVE) is calm; sector correlation is up (0.40 from 0.28) but far from panic
  levels (0.88 in May 2025), and dispersion is high.
- **Profit-taking:** the pre-registered cross-asset test gives -0.50 (p = 0.007), but post-hoc checks show
  it is mostly volatility: controlling for each asset's volatility, momentum's t-value is about zero.
  Within equity sectors something remains (t -1.2 to -3.9; about -2 beyond beta), and the momentum ETF
  trails the S&P 500 by 13 points: among stocks, last year's winners are being sold.

## How to check it yourself

`python -m moneyflow check` prints all automated measures below in one go.

| Question | Measure | Source | When |
|---|---|---|---|
| Real risk-off or reshuffle? | High-yield and IG credit spreads | FRED `BAMLH0A0HYM2`, `BAMLC0A0CM` | Daily |
| Stress in stocks? | VIX / VIX3M (above 1 = inverted), MOVE for bonds | Yahoo `^VIX`, `^VIX3M`, `^MOVE` | Daily |
| Rotation or panic? | Average sector correlation and dispersion, 21 days | computed from sector ETFs | Daily |
| Winners sold? | Momentum ETF vs S&P 500 and min-vol (MTUM, SPY, USMV) | Yahoo | Daily |
| Where did ETF money go? | Change in shares outstanding x NAV | State Street SPDR NAV-history files | Daily |
| Into cash? | Money market fund assets, weekly change and z-score | [ICI](https://www.ici.org/research/stats/mmf) weekly file | Thursday 16:30 ET |
| How much cash do managers hold? | BofA Global Fund Manager Survey | press, by hand | Mid-month |
| Who holds futures? | CFTC Commitments of Traders | publicreporting.cftc.gov | Friday 15:30 ET |
| Rates driver? | 2y, 10y, real yield, breakeven | FRED `DGS2`, `DGS10`, `DFII10`, `T10YIE` | Daily |
| Liquidity backdrop | Fed assets - TGA - reverse repo | FRED `WALCL`, `WTREGEN`, `RRPONTSYD` | Weekly |

Net liquidity uses Fed total assets, not bank reserves: reserves are already net of the Treasury account
and reverse repo, so `WRESBAL - TGA - RRP` would count those twice.

A seller always needs a buyer: trading does not change the amount of cash. "Money moving into cash" is
visible only in fund flows, positioning and surveys; prices show which assets did worse than T-bills.

## Not covered yet

EPFR flows (BofA Flow Show: no November issue found), prime-brokerage and retail positioning, sector
earnings revisions (FactSet), the share of S&P 500 stocks above their 50-day average, Cboe implied
correlation (no history on Yahoo), and flows for iShares, Vanguard and Invesco funds. ICI's file starts in
July 2026, so the money-fund z-scores rest on 18 weekly changes.

## Running

```bash
cd rotation
python -m pip install -r requirements.txt
python -m moneyflow check            # fresh data and the dashboard
python -m moneyflow report           # results.json + PDF; needs reports/<last close>/external.json
python -m pytest -q
```

`external.json` holds what cannot be fetched (BofA survey, press flow figures), with source and date.

## Layout

```
rotation/
  moneyflow/
    data.py       Yahoo total returns and stress gauges, CFTC, FRED, State Street flows, ICI money funds
    analysis.py   returns vs T-bills, profit-taking test and robustness, flows, stress, rates
    report.py     the PDF
  data/           snapshot used (prices, market, cot, fred, flows, mmf)
  reports/<last close>/
  tests/
```
