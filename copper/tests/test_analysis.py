import numpy as np
import pandas as pd
import pytest

from dr_copper.analysis import bear_markets, evaluate, fisher_ci, oos, panel, qualifies, weekly_closes
from dr_copper.data import drop_unfinished_day


def _prices(n=2600, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-09-01", periods=n)
    return pd.DataFrame({
        "HG=F": 2 * np.exp(np.cumsum(rng.normal(0, 0.015, n))),
        "GC=F": 300 * np.exp(np.cumsum(rng.normal(0, 0.010, n))),
        "^IXIC": 2000 * np.exp(np.cumsum(rng.normal(0, 0.012, n))),
    }, index=idx)


def test_weekly_closes_take_the_last_trading_day_of_each_week():
    df = _prices(30)
    w = weekly_closes(df)
    assert all(d.weekday() == 4 for d in w.index[:-1])
    assert w.loc[w.index[1], "HG=F"] == df.loc[w.index[1], "HG=F"]


def test_signals_and_forecasts_use_no_future_data():
    """Rewriting every price after a date leaves all signals and forecasts up to that date unchanged."""
    df = _prices()
    cut = df.index[1500]
    moved = df.copy()
    after = moved.index > cut
    for c in moved:
        moved.loc[after, c] = moved.loc[after, c].values[::-1] * 1.3
    p0, p1 = panel(df), panel(moved)
    signals = [c for c in p0 if c != "target_fwd"]
    pd.testing.assert_frame_equal(p0.loc[:cut, signals], p1.loc[:cut, signals])
    f0, f1 = oos(p0, "copper_4", burn_in=100), oos(p1, "copper_4", burn_in=100)
    cols = ["fc_model", "fc_mean", "slope", "signal"]
    pd.testing.assert_frame_equal(f0.loc[:cut, cols], f1.loc[:cut, cols])


def test_signal_ends_the_day_before_the_origin():
    df = _prices(200)
    p = panel(df)
    origin = p.index[10]
    prev = df.index[df.index.get_loc(origin) - 1]
    four_back = p.index[6]
    prev4 = df.index[df.index.get_loc(four_back) - 1]
    assert p.loc[origin, "copper_4"] == pytest.approx(np.log(df.loc[prev, "HG=F"] / df.loc[prev4, "HG=F"]))
    assert p.loc[origin, "target_fwd"] == pytest.approx(np.log(df.loc[p.index[14], "^IXIC"] / df.loc[origin, "^IXIC"]))


def test_oos_finds_a_real_predictor_and_rejects_noise():
    rng = np.random.default_rng(1)
    n = 1200
    idx = pd.date_range("2001-01-05", periods=n, freq="W-FRI")
    x = rng.normal(0, 1, n)
    p = pd.DataFrame({"sig": x, "target_fwd": 0.4 * x + rng.normal(0, 1, n)}, index=idx)
    res = evaluate(oos(p, "sig"))
    assert res["r2_os"] > 0.05 and res["cw_p"] < 0.001 and qualifies(res)
    p["target_fwd"] = rng.normal(0, 1, n)
    assert not qualifies(evaluate(oos(p, "sig")))


def test_bear_markets_follow_the_20_20_rule():
    idx = pd.bdate_range("2010-01-01", periods=9)
    s = pd.Series([100, 110, 95, 85, 90, 105, 120, 100, 92], index=idx)
    # high 110 -> falls 22.7% to 85 (bear) -> rises 23.5% to 105 (bear over) -> high 120 -> 92 (open bear, -23%)
    assert bear_markets(s) == [(idx[1], idx[3]), (idx[6], idx[8])]
    assert bear_markets(pd.Series([100, 95, 90, 99], index=idx[:4])) == []


def test_fisher_interval_brackets_the_estimate():
    lo, hi = fisher_ci(0.3, 500)
    assert lo < 0.3 < hi and hi - lo < 0.2


def test_unfinished_day_is_dropped_only_before_the_close():
    df = pd.DataFrame({"HG=F": [1.0, 2.0]}, index=pd.to_datetime(["2026-11-18", "2026-11-19"]))
    assert len(drop_unfinished_day(df, pd.Timestamp("2026-11-19 09:00", tz="America/New_York"))) == 1
    assert len(drop_unfinished_day(df, pd.Timestamp("2026-11-19 18:00", tz="America/New_York"))) == 2
