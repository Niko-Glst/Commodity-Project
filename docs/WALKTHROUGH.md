# Walkthrough — five minutes

Read three files in this order. You will have seen the whole argument.

| # | File | What it answers |
|---|---|---|
| 1 | `src/goldmodel/models.py` → `walk_forward_validate` | Is the direction predictable? |
| 2 | `src/goldmodel/simulate.py` → `fit_garch` | Is the magnitude predictable? |
| 3 | `src/goldmodel/validation/coverage.py` | Does that beat a rule of thumb? |

Run everything: `python scripts/pipeline.py`.

---

## 1. `walk_forward_validate` — the honesty machine

```python
walk_forward_validate(target, drivers, min_train=1000, horizon=21, step=21)
```

Fit on the first 1,000 days, predict the next 21, slide forward 21, repeat.
The model is re-estimated every month and never sees its own future.

It produces **3,024 out-of-sample days over 12 years**, and the answer is
negative, though not in the way an earlier version of this document claimed:
directional accuracy 51.9% (p = 0.072) and out-of-sample R² +0.011, with a
Diebold-Mariano p of 0.170. Not distinguishable from zero.

That negative result is the foundation for everything else. If direction were
predictable, the project would be about trading it. It is not, so the project
is about something else.

### Worked example: the bug that made this look better than it was

The defaults on that function are still `horizon=1, step=21`. That is what
the pipeline originally passed, and it is wrong in a way worth studying,
because nothing crashes and no test fails.

**What it does.** Predict 1 day, then skip forward 21. Predict 1 day, skip 21
again. You end up with a few hundred isolated days scattered across the
calendar, each separated by a three-week hole.

**Why it looks fine.** The R² is computed over those days and it is a real
out-of-sample number. No look-ahead. Nothing is leaking. The code is doing
exactly what it was told to do.

**Why it is wrong.** 145 disjoint days is not a time series. You cannot
compute turnover from it, because "yesterday's position" is three weeks old.
You cannot compound returns through it. You cannot run a drawdown. Every
downstream measure that assumes consecutive days silently becomes
meaningless — and still returns a number.

**How it surfaced.** Not through a test. Through asking a question the output
should have been able to answer — *how many trading days is the backtest
actually based on?* — and getting 145 where 3,000 was expected.

**The fix.** `horizon=21, step=21`. Predict 21 days, move 21 days: windows
that tile the calendar with no gaps and no overlap.

**And then it happened again, in a worse way.** An earlier version of this
document stopped at the paragraph above and called the bug fixed. It was
fixed in `pipeline.py` — and not in `scripts/fase3_regressie.py`, which is
the script that produced every published phase-3 number. So the headline
claim of this project rested, for months, on the exact configuration this
page holds up as a cautionary tale.

| | n | R² | Accuracy | vs. random walk |
|---|---|---|---|---|
| `horizon=1, step=21` (published) | 145 | −0.0396 | 43.8% | +1.96% |
| `horizon=21, step=21` (correct) | 3,024 | +0.0110 | 51.9% | −0.55% |

The conclusion survived — direction is still not predictable, since the
corrected edge has p = 0.170 — but the evidence was wrong, and wrong in the
*flattering* direction: the old numbers made the negative result look much
stronger than the data supports.

**How it finally surfaced.** `scripts/freeze_results.py` was written as an
independent implementation and disagreed. Two implementations that disagree
find bugs that one implementation cannot find by running a hundred times.

**The lesson, revised.** A plausible number is not a correct number — and
reproducibility is not correctness. The old figure reproduced perfectly on
every run, because the script faithfully reproduced its own bug. What I
treated as confirmation was only determinism.

Two habits came out of this:

1. A result that matches your expectation deserves *more* scrutiny, not less.
   I checked the surprising numbers in this project carefully and waved
   through the one that fit the story.
2. The guard belongs in the code, not in the documentation. Writing "we fixed
   this" in a Markdown file prevented nothing. `walk_forward_validate` now
   **raises** on `horizon < step` unless you pass `allow_gaps=True`, and three
   tests enforce it.

---

## 2. `fit_garch` — what *is* predictable

Direction is unpredictable; size is not. Volatility clusters: calm follows
calm, turbulence follows turbulence.

```
persistence  alpha + beta = 0.9956
half-life    156 days
df (MLE)     4.80  (SE 0.30)
```

Persistence near 1 means a shock decays slowly — today's volatility tells you
a lot about next quarter's. That is the exploitable part, and it does not
require predicting anything about direction.

**Why df is estimated jointly and not from a QQ-plot.** Fitting a
t-distribution to raw returns gives df = 3.54. Below 4, population kurtosis is
infinite — a badly behaved region to build a risk model in. Estimating df
together with the GARCH parameters gives **4.80, 95% interval [4.21, 5.39]**,
entirely above 4.

Both numbers are correct measurements of different things. The raw fit sees
fat tails and cannot tell whether they come from clustering or from genuinely
thick-tailed shocks. GARCH removes the clustering first; what remains is the
shock distribution, and it is thinner than the raw fit suggests.

---

## 3. `coverage.py` — the part that could have failed

A model that produces a number is not validated. The test is whether a 99%
buffer is actually breached about 1% of the time.

Two tests, because there are two ways to be wrong:

- **Kupiec** — is the *count* right?
- **Christoffersen** — is the *timing* independent? Five breaches spread over
  twenty years is a different thing from five in one month. Clustered breaches
  mean the model misses the dynamics even when the average is fine.

Run against three benchmarks — fixed 25%, rolling 2-year 99th percentile,
EWMA λ=0.94 — over 78 non-overlapping quarters:

**GARCH-t does not win.** It ties the fixed 25% rule on breaches (1 each,
both tests passed) and loses on cost: 28.7% average buffer against 25.0%.
EWMA also passes both tests (2 breaches, 25.5% average buffer); only the
rolling percentile fails.

That is written up as the conclusion in [RESULTS.md](RESULTS.md) rather than
tuned away. Adjusting parameters until the preferred model wins would measure
my own degrees of freedom, not the model.

### The limitation that governs all of it

78 quarters at 99% means **0.78 expected breaches**. At that sample size no
test can discriminate between a good model and a bad one — 0, 1, 2 and 3
breaches are all consistent with the null.

Every result carries its N and an explicit `UNDERPOWERED` flag.
`tests/test_validation.py::test_kupiec_is_powerless_at_realistic_sample_size`
asserts this directly: it fails if the test ever turns out to have more power
than claimed. Real power would need ~500 quarters, roughly 125 years.

---

## What to look at if you have another five minutes

| Question | Where |
|---|---|
| Is there look-ahead anywhere? | `tests/test_data_layer.py::test_point_in_time_integrity_across_all_dates` |
| Is the result just luck? | `src/goldmodel/placebo.py` — real result sits at the 39th percentile |
| Is the execution lag real? | `run_backtest` raises on `execution_lag < 1` |
| What is actually claimed? | [de_claim.md](de_claim.md) |
| All the numbers | [RESULTS.md](RESULTS.md) |

---

## The shape of the argument

1. Direction is unpredictable. **Measured, not assumed** — and the losing
   backtest is kept in, because it is the evidence.
2. Magnitude is partly predictable. Volatility persistence 0.9956.
3. So size the margin buffer, not the trade.
4. Then test whether that actually beats a rule of thumb — **and report that
   it does not**, at this sample size.

Step 4 is the point. Steps 1–3 are a nice story; step 4 is the part that
could have come out the other way, and did.
