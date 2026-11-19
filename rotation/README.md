# Rotation and cash: where is the money going?

A side project next to the paper, the gold desk and the copper project. Question (19 Nov 2026):
metals and tech are falling and the dollar is strong. Are investors taking profits and moving into
cash, and how can you check where money moves?

## The short answer (prices to the 18 Nov close)

Note: [rotation_2026-11-18.pdf](reports/2026-11-18/rotation_2026-11-18.pdf); numbers in
[results.json](reports/2026-11-18/results.json).

- **Profit-taking: yes.** Across 28 ETFs, the 12-month gain up to the Nasdaq's 6 Oct 2026 high and
  the move since have a rank correlation of -0.50 (p = 0.007): last year's winners (oil,
  semiconductors, energy, copper miners, tech) fell hardest, -17% on average against -4% for the rest.
  The measure (12 months to the peak vs since the peak) was fixed in code before it was computed.
- **Rotation, not a flight to cash (until 13 Nov).** Since 6 Oct, staples (+11%), health care (+8%),
  utilities, real estate, long Treasuries and the dollar rose; the equal-weight S&P 500 (+1.5%) beat
  the index (-6.3%). Fund managers cut tech by a record in BofA's November survey but also cut cash
  (3.6% from 3.9%); ETF buyers put $54bn into equity funds in the week to 13 Nov; T-bill ETFs saw
  outflows; money market funds slipped from their $8.02tn record.
- **This week is different.** From 11 to 18 Nov, 27 of 28 assets lost to cash; only the dollar beat
  it. That is the first broad de-risking, and the flow data that would show money going into cash
  (ICI money funds, CFTC positioning) are not out yet.

## A seller always needs a buyer

Trading does not change the amount of cash: the buyer pays what the seller receives. "Money moving
into cash" can only be seen where money enters or leaves a pool: fund flows (ETFs and money market
funds create or redeem shares), futures positioning, and surveys of how much cash managers hold.
Prices show which assets lost to cash, not who sold.

## How to check it yourself

| What | Where | When | How to read it |
|---|---|---|---|
| Which assets lose to cash | `python -m moneyflow check` (this project), or any chart against BIL / SGOV | Daily | Most assets below cash = de-risking; a split = rotation |
| Money market fund assets | [ICI](https://www.ici.org/research/stats/mmf) | Thursday 16:30 ET | A fast jump in a sell-off = flight to cash; a slow rise = chasing the yield |
| ETF flows | [ETF.com weekly flows](https://www.etf.com/sections/weekly-etf-flows), ICI combined flows | Weekly | Creations and redemptions are real money in and out |
| Fund-manager cash | BofA Global Fund Manager Survey (via press) | Mid-month | Above 5% = fear (contrarian buy); 4% or less = complacency |
| Futures positioning | [CFTC Commitments of Traders](https://publicreporting.cftc.gov) | Friday 15:30 ET (Tuesday data) | Speculators cutting net longs = money leaving |
| Gold ETF holdings | spdrgoldshares.com, World Gold Council | Daily, monthly | Tonnes falling = metal leaving ETFs |
| Breadth | RSP vs SPY | Daily | Equal weight ahead = leaders sold, the rest held |
| Liquidity backdrop | FRED: M2SL, RRPONTSYD | Monthly, daily | Slow; says little about one week |

The page `assetmarketcap.com/asset/CASH-USD` showed no data on 19 Nov (placeholder fields); its method
note says currencies use M2, which is bank deposits and savings, not investors switching to cash.

## Running

```bash
cd rotation
python -m pip install -r requirements.txt
python -m moneyflow check            # fresh prices, CFTC and FRED; prints the dashboard
python -m moneyflow report           # results.json + PDF; needs reports/<last close>/external.json
python -m pytest -q
```

`external.json` holds the numbers that cannot be fetched automatically (BofA survey, ICI, ETF flows),
with their source and date, written by hand like the desk's `news.json`.

## Layout

```
rotation/
  moneyflow/
    data.py       Yahoo total returns (29 ETFs), CFTC positioning, FRED cash series
    analysis.py   returns vs cash, the profit-taking test, positioning changes
    report.py     the PDF
  data/           snapshot used (prices.csv, cot.csv, fred.csv)
  reports/<last close>/
  tests/
```
