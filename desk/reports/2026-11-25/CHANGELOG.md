# CHANGELOG: Nova Gold Weekly, edition 25 Nov 2026

This file records the revision of `gold_desk_2026-11-25.pdf` (16 pages, commit 415ee15) into `nova_gold_weekly_2026-11-25.pdf` (12 pages), made on 27 Nov 2026 after an internal review. Page numbers marked "old" refer to the 16-page version; "new" refers to the 12-page version.

## 1. Review items and where each is fixed

| Item | Fix | Where |
|---|---|---|
| A1: the 20 Nov note cannot hold a 23 Nov price | The 96.8 came from the Monday update of the 20 Nov note, published on the evening of 23 Nov. The reference now says so. | new p.6; `build_note.py` |
| A2: p.3 contradicts p.4 on last week | Computed: stocks explained 34% of last week's fall (-3.4 of -10.0 log points), the VIX jump added back +2.4, and 91% stayed unexplained on market factors. "Unexplained" is gold minus the factor contributions, with the intercept included, the same for both weeks. The text now says this. | new p.2, p.8; `analyse_week.py` (`attr_last`) |
| A3: why H5 failed | Added: H5 p = 0.036 missed the pre-registered 0.025 (0.05 split over two anchors, commit 59b21e2). | new p.3 |
| A4: "rise before" | Redefined as trough to peak, from the preceding bear market's trough under the 20/20 rule; all rows recomputed. 1980-01 and 1980-09 are noted as a double top; the statistics use 7 independent cycles. | `gold_desk/cycles.py` (`bear_markets`, `rise_before`), new p.9, tests |
| A5: real-rate definition | One definition for every cycle: 10-yr minus CPI y/y, labelled "trailing real rate" (a backward-looking proxy, not a true ex-post rate). TIPS added as its own column from 2003. The "negative real rates at big peaks" sentence is rewritten: it holds only on the trailing measure. p.4 says which real rate is meant. | `gold_desk/cycles.py` (`trailing_real_rate`, `tips_monthly`), new p.4, p.9 |
| A6: Waller and the minutes | Split into two claims: the minutes (CNBC, 18 Nov) and Waller (Bloomberg, 10 Nov). | new p.3 |
| A7: log points | Log points are labelled wherever the driver model appears, and simple returns are given alongside (-10.0 log points = -9.5%). | new p.2, p.3, p.8, glossary |
| A8: "daily swings of 2-4%" | Computed from the 20 Nov fit, with the variance carried through Mon-Wed and no re-estimation. A move above 2% is expected on 22% of days to 9 Dec, with an 87% chance of at least one. Above 4%: 4% of days, 28%. | `gold_desk/model.py` (`filter_variance`, `exceed_odds`), new p.2, p.6 |
| A9: dashes | The heading dash is removed. A check fails on " – " or "—" in any page or chart text. | `gold_desk/nova_style.py` (`find_dashes`, text recorder), render check |
| A10: small fixes | Separate Prior column; GDP advance 3.4% shown; Units column; partial-week ETF bar hatched; daily record (29 Jan) vs peak monthly average (Feb) stated. | new p.4, p.7, p.10, p.1, p.9 |
| B1: time mismatch | Gold at 16:00 ET is built from 5-minute December futures (contract identity checked every day). It is used for gold vs stocks on p.1, p.2 and p.5, for the miners chart, for the current-week attribution and for the gold-up/stocks-down list. History stays on settlements; the method page says so. | `analyse_week.py` (`gold16`, `matched`), new p.1, p.2, p.5, p.8, p.10, p.12 |
| B2: driver model | ETF flows and positioning are removed as regressors and shown as a contemporaneous line only. Only contributions are compared. The out-of-sample method is explained (rolling 156 weeks, past data only). The model was rerun, with a reconciliation to the old figures. | `gold_desk/drivers.py` (`MARKET_FACTORS`), new p.8 |
| B3: futures roll | Scores convert outcomes after a roll to the forecast's contract (`rolls.json`, ratio GCZ26/GCG27 on 25 Nov). Only confirmed rolls are applied: `load_rolls()` skips `"verified": false`. `score()` takes rolls explicitly; `__main__` and `report.py` pass them. A check confirms every scored pair uses the same contract (trivially true with data to 25 Nov). | `gold_desk/rolls.py`, `rolls.json`, `backtest.py`, `__main__.py`, `report.py`, tests, check |
| B4: scorecard | Binomial context added (2 of 6 at p = 0.1: 11%, indicative because the pairs overlap). "Not a biased centre" removed. Calibration plot planned from 20 live scores. | new p.6 |
| B5: forced selling | Verdict is now "most consistent with the data, not proven", with a list of what would confirm it. Our cross-asset data for 18-20 Nov is cited. | new p.3 |
| B6: sources | Nvidia: reinstatement on Mon 23 Nov (Nvidia 8-K, CNN) and S&P CreditWatch on 25 Nov (Yahoo Finance, Seeking Alpha); the claim was wrongly dated 24 Nov before. bifu.co is replaced by Kitco. The dollar claim is checked on our DXY data. Fed odds are one number with a timestamp. | new p.3, p.5 |
| B7: GLD tonnes | Ounces per share now come from NAV / December futures at 10:00 ET (the NAV's pricing time), median of 16-25 Nov, spread 0.35%. The official SPDR file could not be read (see section 3). | `analyse_week.py` (`oz`), new p.10 |
| B8: pre-registration | A sentence on partly seen data is added. | new p.12 |
| C1: name and masthead | Renamed Nova Gold Weekly. Page 1 carries NOVA CAPITAL and the report name in a teal band; the separate masthead line was dropped with the return to the previous style. File: `nova_gold_weekly_2026-11-25.pdf`. | `gold_desk/nova_style.py`, `build_note.py` |
| C2: house style | Tried the blueprint palette (cream, deep blue, Cambria/Calibri); on 27 Nov the user preferred the previous look, so the template uses the desk's teal style (white pages, Segoe UI, gold title bar, teal section bars and table headers, grey text boxes, one teal key block). One table style throughout; all fonts embedded (checked); exactly one key block (checked). | `gold_desk/nova_style.py` |
| C3: chart titles | Every chart has a takeaway title and a plain subtitle, drawn through one helper (checked: 7 of 7). | `nova_style.Deck.chart` |
| C4: length | 12 pages: 8 core and 4 appendix. | `build_note.py` |
| C5: missing sections | Physical market: placeholders for Shanghai premium and EFP, plus WGC central-bank data. Technicals: ranked levels, 55- and 200-day averages and RSI from our own data. z-score column added. | new p.7, p.11 |
| C6: board-friendly | Glossary of 9 terms. "What this means for Nova" line on the desk-view page. | new p.12, p.2 |
| D1: checks | 17 data checks and 7 render checks, all PASS (`checks.json`). New checks: no dashes, contract consistency, 16:00 gold present, units present, fonts embedded, one blue block, chart titles, one price basis per table, contract identity of the 5-minute bars, cycles reproduce the 19 Nov peaks, rolls leave existing scores unchanged. | `checks.json` |
| D2: unit tests | Tests added for: rise before (trough to peak), trailing real rate with the missing CPI month, exceed odds (share and at least once), variance filter, score with rolls (None = [], only crossing pairs adjusted), dash rule, font embedding and blue-block count. Plus a regression test that the H1-H6 outcomes are unchanged. 30 tests in total (including the unverified-roll skip). | `tests/test_desk.py` |
| D3: look at every page | All 12 pages viewed as rendered page images. No PNG converter (pdftoppm, pymupdf, pypdf) is installed, so the pages were viewed through the document viewer instead of converted to PNG files. | |

## 2. Numbers that changed

| Page (new) | Item | Old value | New value | Reason |
|---|---|---|---|---|
| 6 | Monday 23 Nov 1-day score, reference | "96.8 as published" in "our 20 Nov note" | 98.0 on the $3,651.4 settlement; 96.8 was the preliminary $3,632 in the Monday update of the 20 Nov note (23 Nov evening) | A1 |
| 2, 8 | Last week: stocks contribution | -3.3 log points (with flows and positioning) | -3.4 | B2: market factors only |
| 2, 8 | Last week: unexplained | -8.3 (83%, intercept left out); -8.1 (81%) on the new definition | -9.15 (91%) | B2; one definition for both weeks (intercept included) |
| 8 | Last week: rates and inflation | +0.5 | +0.7 | B2 |
| 8 | Last week: dollar | -0.3 | -0.4 | B2 |
| 8 | Last week: VIX | +2.5 | +2.4 | B2 |
| 8 | Last week: flows; positioning | -0.8; -0.2 as drivers | removed as drivers; flows shown as a contemporaneous line (-0.8) | B2 |
| 8 | Out-of-sample share explained since 2009 | 27% | 17% | B2: no flows or positioning |
| 8 | Out-of-sample share explained in 2026 | 15% | -1% | B2 |
| 2, 8 | This week: gold move in the attribution | +0.58 (settlements) | +1.23 log points (16:00 ET) | B1 |
| 8 | This week: stocks; VIX; unexplained | +1.97; -0.95; -0.14 (with flows -0.65) | +1.98; -0.91; -0.15 (no flows) | B1, B2 |
| 1 | Gold, Fri to Wed | +0.6% | +0.6% (settlements) and +1.2% (16:00 ET) | B1 |
| 2 | "Daily swings of 2-4% are the base case" | (no number) | >2%: 22% of days, 87% at least once to 9 Dec; >4%: 4%, 28% | A8 |
| 2 | "Gold up on a day stocks fall ... has not happened since the selloff began" | claim | Wed 25 Nov: gold +0.55%, S&P -0.25% at 16:00 ET; same direction on 6 of 7 days since 17 Nov | B1 |
| 9 | Rise before, 1974-12 | +43% | +426% (from 1970-01) | A4 |
| 9 | Rise before, 1980-01 | +514% | +514% (from 1976-08) | A4, unchanged |
| 9 | Rise before, 1980-09 | +491% | +31% (from 1980-05) | A4 |
| 9 | Rise before, 1983-02 | +105% | +56% (from 1982-06) | A4 |
| 9 | Rise before, 1987-12 | +63% | +63% | A4, unchanged |
| 9 | Rise before, 1996-02 | +23% | +23% | A4, unchanged |
| 9 | Rise before, 2008-03 | +152% | +278% (from 1999-07) | A4 |
| 9 | Rise before, 2011-09 | +149% | +133% (from 2008-11) | A4 |
| 9 | Rise before, 2026-02 | +202% | +367% (from 2015-12) | A4 |
| 9 | Real-rate label | "10-yr minus CPI (TIPS from 2003)" | "trailing real rate" for all; values unchanged (they were always CPI-based); TIPS column: 2008 +1.09%, 2011 +0.08%, 2026 +1.82% | A5 |
| 9 | Range of past falls | -21% to -53%, median -38%, 4 to 61 months (8 peaks) | -21% to -53%, median -39%, 8 to 61 months (7 independent cycles) | A4 |
| 9 | 2026 at month 9 | "deeper than all but one" | deeper than all seven independent cycles (narrowly below 1974 and 1983) | A4 |
| 10 | GLD tonnes | 1,024 (-6.5 on the week) | 1,027 (-6.5) | B7 |
| 10 | GLDM tonnes | 237 | 238 (-0.4) | B7 |
| 1, 3, 4, 5 | December hike pricing | "94-98%" | 94.4% at 16:01 UTC 25 Nov (CME FedWatch, relayed) | B6 |
| 3 | Dollar claim | "near a 19-month high" (press) | Monday's 104.32 was the highest close since 26 Mar 2025 (our data) | B6 |
| 5 | Nvidia reinstatement date | 24 Nov (single source) | Mon 23 Nov (Nvidia 8-K, CNN) | B6 |
| 6 | Binomial context | none | 11% (2 of 6 at p = 0.1, indicative) | B4 |
| 7 | z-scores | none | added (for example S&P 500 +2.36) | C5 |
| 3 | 2-year yield, last week | "fell 12 bp" (stale; already corrected to a computed value before this revision) | -25 bp (FRED, 13 to 20 Nov) | consistency |

## 3. Not fixed or not verified

- **GLD and GLDM official ounces per share:** not verified. SPDR's archive URL returns a PDF, not a CSV, and no PDF reader is installed; the GLDM archive returns 404. The tonnes use an estimate (NAV / December futures at 10:00 ET) and are labelled "est.".
- **Roll date 26 Nov:** unverified. It was taken from Yahoo data fetched on 26 Nov and must be confirmed on the 27 Nov settlement (`rolls.json`, `"verified": false`).
- **Rolls in the 2006-2026 backfill:** not adjusted, a known limitation. Each week that crosses a roll scores on a jump of about 0.3-0.8%.
- **Model inputs:** the GARCH fit's daily returns still include each roll jump. On 26 Nov that is about +0.8%, and the 27 Nov record will be fitted on it, with spot on the February contract. This is a known limitation, not fixed in this revision.
- **Unverified roll:** until `rolls.json` is confirmed on the 27 Nov settlement, `load_rolls()` skips it, so the 30 Nov and 1 Dec scores would not be roll-adjusted.
- **Physical market:** the Shanghai premium and COMEX-London EFP are not wired yet; the page shows placeholders.
- **Primary documents:** the Nvidia 8-K, Nvidia's press release and S&P's CreditWatch notice were seen as search results that list the primary documents. The documents themselves were not opened.
- **Fed odds:** the 94.4% figure is relayed by CoinCentral, not pulled from CME FedWatch directly.
- **Bank forecasts** (Goldman, UBS, Reuters poll): one secondary source, labelled as such.
- **ISM and payroll dates (1 and 4 Dec):** the usual schedule, still to be confirmed.
- **Page images:** viewed through the document viewer, because no PNG converter is installed.
- **Audit with worktree isolation:** not possible in this session (worktree path check). A clean clone was used instead.
