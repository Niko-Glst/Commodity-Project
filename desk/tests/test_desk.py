import numpy as np
import pandas as pd
import pytest

from gold_desk.backtest import (diebold_mariano, drift_check, garch_vol_21, iv_check, iv_qualifies, iv_targets,
                                kupiec, quantile_loss, score, window_check, window_qualifies)
from gold_desk.data import drop_unfinished_day
from gold_desk.model import FAN_Q, GRID_Q, HORIZONS, Fit, Forecast, fit, make_forecast, simulate


def _gold(n=1500, seed=0, last_shock=0.0):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(5, n) * 0.008
    r[-1] = last_shock
    idx = pd.bdate_range("2015-01-01", periods=n)
    return pd.Series(1000 * np.exp(np.cumsum(r)), index=idx)


def test_next_day_variance_includes_last_shock():
    calm, shocked = fit(_gold(last_shock=0.0)), fit(_gold(last_shock=-0.06))
    assert shocked.var_next > calm.var_next * 1.5


def test_simulate_shape_and_no_drift():
    f = Fit(mu=0, omega=1e-6, alpha=0.05, beta=0.93, nu=5, var_next=1e-4, n_obs=1000)
    x = simulate(f, horizon=10, n_paths=4000)
    assert x.shape == (4000, 11)
    assert (x[:, 0] == 0).all()
    assert abs(np.median(x[:, -1])) < 0.005


def test_forecast_quantiles_are_ordered_and_round_trip():
    fc, _ = make_forecast(_gold(), n_paths=2000)
    for h in HORIZONS:
        assert np.all(np.diff(fc.grid[h]) >= 0)
    lows, highs = fc.fan[FAN_Q[0]], fc.fan[FAN_Q[-1]]
    assert np.all(lows < fc.spot) and np.all(highs > fc.spot)
    back = Forecast.from_record(fc.to_record())
    assert back.origin == fc.origin and back.fit.alpha == pytest.approx(fc.fit.alpha)


def test_score_uses_the_close_h_days_after_origin():
    gold = pd.Series(np.arange(100.0, 130.0), index=pd.bdate_range("2026-01-05", periods=30))
    grid = {str(h): list(np.linspace(90, 130, len(GRID_Q))) for h in HORIZONS}
    rec = {"origin": "2026-01-05", "spot": 100.0, "source": "live", "grid": grid}
    s = score([rec], gold).set_index("h")
    assert s.loc[5, "realised"] == 105.0
    assert s.loc[21, "realised"] == 121.0
    assert bool(s.loc[1, "inside90"])


def test_kupiec_accepts_the_nominal_rate_and_rejects_far_off():
    assert kupiec(1000, 100, 0.10) > 0.9
    assert kupiec(1000, 200, 0.10) < 0.001
    assert 0 <= kupiec(50, 0, 0.10) <= 1


def test_quantile_loss_is_lowest_for_the_true_distribution():
    rng = np.random.default_rng(1)
    true = np.percentile(rng.normal(0, 1, 200_000), GRID_Q)
    draws = rng.normal(0, 1, 4000)
    right = np.mean([quantile_loss(r, true) for r in draws])
    shifted = np.mean([quantile_loss(r, true + 0.5) for r in draws])
    assert right < shifted


def test_diebold_mariano_detects_a_consistent_gap():
    rng = np.random.default_rng(2)
    assert diebold_mariano(rng.normal(-0.5, 1, 500), lags=1)[1] < 0.001
    assert diebold_mariano(rng.normal(0.0, 1, 500), lags=1)[1] > 0.01


def test_drift_check_prefers_drift_on_a_trending_series():
    n = 1300
    idx = pd.bdate_range("2010-01-01", periods=n)
    gold = pd.Series(1000 * np.exp(0.002 * np.arange(n)), index=idx)   # steady +0.2% a day
    grid = np.linspace(0.9, 1.1, len(GRID_Q))                          # zero-drift forecast
    recs = [{"origin": f"{d:%Y-%m-%d}", "spot": float(gold[d]), "source": "backfill",
             "grid": {str(h): list(gold[d] * grid) for h in HORIZONS}} for d in idx[100:1250:5]]
    check = drift_check(recs, gold).set_index("h")
    assert check.loc[21, "change"] < 0 and check.loc[5, "change"] < 0


def test_rolling_window_fits_only_the_last_returns():
    gold = _gold(n=1500)
    assert fit(gold, window=800).n_obs == 800
    assert fit(gold).n_obs == 1499
    # the window is the tail: refitting on the cut series gives the same estimates
    assert fit(gold, window=800).alpha == pytest.approx(fit(gold.iloc[-801:]).alpha)


def test_window_check_scores_the_better_spread_lower():
    """A forecast whose spread matches the realised moves beats one that is far too wide."""
    rng = np.random.default_rng(3)
    n = 1400
    idx = pd.bdate_range("2010-01-01", periods=n)
    gold = pd.Series(1000 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=idx)
    z = np.percentile(rng.normal(0, 1, 200_000), GRID_Q)

    def recs(scale):
        return [{"origin": f"{d:%Y-%m-%d}", "spot": float(gold[d]), "source": "backfill",
                 "grid": {str(h): list(gold[d] * np.exp(z * scale * np.sqrt(h))) for h in HORIZONS}}
                for d in idx[50:1300:5]]

    check = window_check(recs(0.03), recs(0.01), gold).set_index("h")
    assert check.loc[21, "change"] < 0 and check.loc[5, "change"] < 0
    assert window_qualifies(check.reset_index())
    assert not window_qualifies(window_check(recs(0.01), recs(0.03), gold))


def test_garch_vol_21_is_flat_at_the_long_run_level():
    fit_ = {"omega": 2e-6, "alpha": 0.05, "beta": 0.93, "var_next": 2e-6 / 0.02}
    assert garch_vol_21(fit_) == pytest.approx(np.sqrt(1e-4 * 252))
    high = dict(fit_, var_next=4e-4)
    assert np.sqrt(1e-4 * 252) < garch_vol_21(high) < np.sqrt(4e-4 * 252)


def test_iv_targets_use_no_future_data():
    """Changing everything after a date leaves the GVZ target and its correction up to that date unchanged."""
    gold = _gold(n=900, seed=4)
    gvz = pd.Series(np.linspace(15, 30, len(gold)), index=gold.index)
    cut = gold.index[600]
    base = iv_targets(gold, gvz)
    gold2, gvz2 = gold.copy(), gvz.copy()
    gold2[gold2.index > cut] *= 1.5
    gvz2[gvz2.index >= cut] = 80.0          # the same-day GVZ must not be used either
    moved = iv_targets(gold2, gvz2)
    pd.testing.assert_frame_equal(base.loc[:cut], moved.loc[:cut])


def test_iv_check_prefers_the_right_volatility():
    """Forecasts that are twice too wide get beaten once the implied vol tells the truth."""
    rng = np.random.default_rng(5)
    n = 1500
    idx = pd.bdate_range("2010-01-01", periods=n)
    sigma = 0.01
    gold = pd.Series(1000 * np.exp(np.cumsum(rng.normal(0, sigma, n))), index=idx)
    gvz = pd.Series(100 * sigma * np.sqrt(252), index=idx)              # implied = true vol
    z = np.percentile(rng.normal(0, 1, 200_000), GRID_Q)
    wide = 2 * sigma
    fit_ = {"omega": wide**2 * 0.02, "alpha": 0.05, "beta": 0.93, "var_next": wide**2,
            "mu": 0.0, "nu": 30.0, "n_obs": 1000}
    recs = [{"origin": f"{d:%Y-%m-%d}", "spot": float(gold[d]), "source": "backfill", "fit": fit_,
             "grid": {str(h): list(gold[d] * np.exp(z * wide * np.sqrt(h))) for h in HORIZONS}}
            for d in idx[300:1450:5]]
    check = iv_check(recs, gold, gvz).set_index(["candidate", "h"])
    gvz_only = check.loc["GVZ, bias-corrected"]
    assert gvz_only.loc[21, "change"] < 0 and gvz_only.loc[5, "change"] < 0
    assert gvz_only.loc[21, "scale_median"] == pytest.approx(0.5, abs=0.1)
    assert iv_qualifies(check.reset_index(), "GVZ, bias-corrected")


def test_unfinished_day_is_dropped_only_before_the_close():
    df = pd.DataFrame({"GC=F": [1.0, 2.0]}, index=pd.to_datetime(["2026-11-02", "2026-11-03"]))
    morning = pd.Timestamp("2026-11-03 09:00", tz="America/New_York")
    evening = pd.Timestamp("2026-11-03 18:00", tz="America/New_York")
    assert len(drop_unfinished_day(df, morning)) == 1
    assert len(drop_unfinished_day(df, evening)) == 2


def _driver_panel(n=1150, seed=7, beta_real=-0.02, shift_at=None, beta_after=None):
    from gold_desk.drivers import weekly_panel
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2004-01-02", periods=n * 5)
    real = 1 + np.cumsum(rng.normal(0, 0.03, len(idx)))
    b = np.full(len(idx), beta_real)
    if shift_at is not None:
        b[idx >= pd.Timestamp(shift_at)] = beta_after
    gold = 400 * np.exp(np.cumsum(b * np.diff(real, prepend=real[0]) + rng.normal(0, 0.008, len(idx))))
    daily = pd.DataFrame({"gold": gold, "real": real, "be": 2 + np.cumsum(rng.normal(0, 0.01, len(idx))),
                          "dxy": 90 * np.exp(np.cumsum(rng.normal(0, 0.004, len(idx)))),
                          "vix": 18 * np.exp(np.cumsum(rng.normal(0, 0.03, len(idx))) * 0.1),
                          "spx": 1000 * np.exp(np.cumsum(rng.normal(0, 0.01, len(idx)))),
                          "oil": 60 * np.exp(np.cumsum(rng.normal(0, 0.02, len(idx))))}, index=idx)
    return weekly_panel(daily)


def test_attribution_uses_only_past_betas():
    from gold_desk.drivers import attribution
    p = _driver_panel()
    a0 = attribution(p, ["d_real", "r_dxy"])
    moved = p.copy()
    cut = p.index[600]
    moved.loc[moved.index > cut, "r_gold"] *= -3
    a1 = attribution(moved, ["d_real", "r_dxy"])
    pd.testing.assert_frame_equal(a0.loc[:cut], a1.loc[:cut])


def test_decoupling_detects_a_weaker_real_yield_link():
    from gold_desk.drivers import decoupling
    assert decoupling(_driver_panel(beta_real=-0.08, shift_at="2022-03-01", beta_after=0.0))["confirmed"]
    assert not decoupling(_driver_panel(beta_real=-0.08))["confirmed"]


def test_h3_finds_a_real_predictor_and_rejects_noise():
    from gold_desk.drivers import evaluate, oos
    rng = np.random.default_rng(9)
    idx = pd.date_range("2006-01-06", periods=1000, freq="W-FRI")
    x = rng.normal(0, 1, 1000)
    good = pd.DataFrame({"target": 0.5 * x + rng.normal(0, 1, 1000), "sig": x}, index=idx)
    r = evaluate(oos(good, "sig"))
    assert r["r2"] > 0.05 and r["cw_p"] < 0.001
    noise = pd.DataFrame({"target": rng.normal(0, 1, 1000), "sig": x}, index=idx)
    assert evaluate(oos(noise, "sig"))["r2"] < 0.01


# ------------------------------------------------------------------ spring (H4-H6)

def _spring_series(n=3600, seed=11, phi=0.93, spring=True):
    """Log price = random-walk value + AR(1) stretch (a strong spring); spring=False gives a plain random walk."""
    rng = np.random.default_rng(seed)
    v = np.cumsum(rng.normal(0, 0.004, n))
    x = np.zeros(n)
    if spring:
        e = rng.normal(0, 0.012, n)
        for t in range(1, n):
            x[t] = phi * x[t - 1] + e[t]
    else:
        v = np.cumsum(rng.normal(0, 0.0065, n))
    idx = pd.bdate_range("2004-01-01", periods=n)
    return pd.Series(1000 * np.exp(v + x), index=idx)


def _spring_records(gold):
    sig = float(np.log(gold).diff().std())
    z = np.percentile(np.random.default_rng(0).normal(0, 1, 200_000), GRID_Q)
    return [{"origin": f"{d:%Y-%m-%d}", "spot": float(gold[d]), "source": "backfill",
             "fit": {"var_next": sig ** 2},
             "grid": {str(h): list(gold[d] * np.exp(z * sig * np.sqrt(h))) for h in HORIZONS}}
            for d in gold.index[250:-30:5]]


def test_stretch_uses_only_past_closes():
    from gold_desk.spring import stretch_panel
    gold = _spring_series()
    recs = _spring_records(gold)
    a = stretch_panel(recs, gold)
    changed = gold.copy()
    changed.iloc[1500:] *= 1.5
    b = stretch_panel(recs, changed)
    early = a["pos"] < 1500
    assert np.allclose(a.loc[early, "s50"], b.loc[early, "s50"])
    assert np.allclose(a.loc[early, "s200"], b.loc[early, "s200"])


def test_spring_tests_find_a_spring_and_reject_a_random_walk():
    from gold_desk.spring import h4, spring_check, spring_qualifies, stretch_panel
    gold = _spring_series(spring=True)
    recs = _spring_records(gold)
    p = stretch_panel(recs, gold)
    assert h4(p).set_index("anchor").loc[50, "passed"]
    check = spring_check(recs, gold, p, 50, burn_in=150)
    assert check.set_index("h").loc[21, "change"] < 0
    assert spring_qualifies(check, p_max=0.05)

    walk = _spring_series(spring=False)
    recs_w = _spring_records(walk)
    pw = stretch_panel(recs_w, walk)
    assert not h4(pw)["passed"].any()
    assert not spring_qualifies(spring_check(recs_w, walk, pw, 50, burn_in=150))


def test_big_moves_use_past_volatility_only():
    from gold_desk.spring import big_moves
    gold = _gold(n=600, seed=4)
    gold.iloc[400:] = gold.iloc[400:] * 0.9          # one 10% gap down on day 400
    ev = big_moves(gold)
    assert gold.index[400] in set(ev["date"])
    row = ev.set_index("date").loc[gold.index[400]]
    assert row["z"] < -3 and np.isclose(row["sigma"], np.log(gold).diff().iloc[337:400].std())


# ------------------------------------------------------------------ cycles and daily move odds (27 Nov 2026)

def test_rise_before_starts_at_the_preceding_bear_market_trough():
    from gold_desk.cycles import bear_markets, rise_before
    idx = pd.period_range("1990-01", periods=9, freq="M")
    s = pd.Series([100, 200, 150, 140, 180, 200, 210, 150, 160], index=idx)
    bears = bear_markets(s)
    assert [(str(p), str(t)) for p, t in bears] == [("1990-02", "1990-04"), ("1990-07", "1990-08")]
    rows = rise_before(s, bears, "1990-01")
    assert rows[0]["rise"] == pytest.approx(1.0)              # first peak: from the low since base_start (100 -> 200)
    assert rows[1]["rise"] == pytest.approx(210 / 140 - 1)    # second: from the first bear market's trough, not the window low
    assert str(rows[1]["from"]) == "1990-04"


def test_trailing_real_rate_interpolates_a_missing_cpi_month():
    from gold_desk.cycles import trailing_real_rate
    idx = pd.period_range("2024-01", periods=15, freq="M")
    cpi = pd.Series(100 * 1.002 ** np.arange(15), index=idx)
    cpi.iloc[13] = np.nan                                     # a month never published
    gs10 = pd.Series(4.0, index=idx)
    rr = trailing_real_rate(gs10, cpi)
    infl = (1.002 ** 12 - 1) * 100
    assert rr.iloc[-1] == pytest.approx(4.0 - infl, abs=1e-6)
    assert rr.index[-2] == idx[13]                            # the gap month gets a value instead of breaking the 12-month change


def test_exceed_prob_matches_the_normal_case():
    from scipy import stats
    from gold_desk.model import exceed_prob
    f = Fit(mu=0, omega=0.01 ** 2, alpha=0.0, beta=0.0, nu=200, var_next=0.01 ** 2, n_obs=1000)   # flat 1% sigma, near-normal
    p = exceed_prob(f, 0.02, days=5, n_paths=40_000)
    assert p == pytest.approx(2 * stats.norm.sf(2), abs=0.004)
    assert exceed_prob(f, 0.04, days=5, n_paths=40_000) < 0.001


def test_exceed_odds_reports_share_of_days_and_at_least_once():
    from gold_desk.model import exceed_odds
    f = Fit(mu=0, omega=0.01 ** 2, alpha=0.0, beta=0.0, nu=200, var_next=0.01 ** 2, n_obs=1000)
    o = exceed_odds(f, 0.02, days=9, n_paths=40_000)
    assert o["at_least_once"] == pytest.approx(1 - (1 - o["share_of_days"]) ** 9, abs=0.01)


def test_filter_variance_moves_with_shocks_and_keeps_parameters():
    from gold_desk.model import filter_variance
    f = Fit(mu=0.0, omega=1e-6, alpha=0.1, beta=0.85, nu=5, var_next=1e-4, n_obs=1000)
    g = filter_variance(f, [0.05])
    assert g.var_next == pytest.approx(1e-6 + 0.1 * 0.05 ** 2 + 0.85 * 1e-4)
    assert (g.omega, g.alpha, g.beta, g.nu) == (f.omega, f.alpha, f.beta, f.nu)
    assert filter_variance(f, []).var_next == f.var_next


def test_score_rolls_none_and_empty_are_identical_and_adjust_only_crossing_pairs():
    gold = _gold(n=400)
    recs = [{"origin": f"{d:%Y-%m-%d}", "spot": float(gold[d]), "source": "backfill",
             "grid": {str(h): list(gold[d] * np.linspace(0.9, 1.1, len(GRID_Q))) for h in HORIZONS}} for d in gold.index[300:380:5]]
    a, b = score(recs, gold), score(recs, gold, [])
    pd.testing.assert_frame_equal(a, b)
    roll = [{"date": str(gold.index[350].date()), "ratio": 0.99}]
    c = score(recs, gold, roll)
    crossing = c["roll_adjusted"]
    assert crossing.any() and (~crossing).any()
    assert np.allclose(c.loc[crossing, "realised"], a.loc[crossing, "realised"] * 0.99)
    assert np.allclose(c.loc[~crossing, "realised"], a.loc[~crossing, "realised"])
    for _, r in c[crossing].iterrows():          # every adjusted pair has a roll between origin and outcome
        assert r["origin"] < pd.Timestamp(roll[0]["date"])


def test_unverified_rolls_are_skipped_unless_asked(tmp_path):
    import json
    from gold_desk.rolls import load_rolls
    f = tmp_path / "r.json"
    f.write_text(json.dumps([{"date": "2026-11-26", "ratio": 0.99, "verified": False}, {"date": "2026-09-28", "ratio": 0.995}]))
    assert [r["date"] for r in load_rolls(f)] == ["2026-09-28"]
    assert len(load_rolls(f, include_unverified=True)) == 2


def test_published_test_outcomes_are_unchanged():
    """H1-H6 outcomes as committed (21 and 23 Nov 2026); the Nova revision must not change them."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "reports"
    drv = json.loads((root / "2026-11-20-weekly" / "drivers.json").read_text(encoding="utf-8"))
    spr = json.loads((root / "2026-11-20" / "spring.json").read_text(encoding="utf-8"))
    assert drv["h1"]["confirmed"] and drv["h2"]["confirmed"]
    assert not any(r.get("passed", False) for r in drv["h3"])
    assert not any(r["passed"] for r in spr["h4"]) and not any(r["passed"] for r in spr["h5"])
    assert not any(spr["h6_passed"].values())
    assert spr["h5"][0]["p_one_sided"] == pytest.approx(0.0357, abs=5e-4)


def test_nova_dash_rule_flags_dashes_but_not_ranges_or_empty_cells():
    from gold_desk.nova_style import find_dashes
    assert find_dashes(["What you need to know – a week", "an em—dash"]) == ["What you need to know – a week", "an em—dash"]
    assert find_dashes(["$3,298–3,751", "–", "1974-12", "plain text"]) == []


@pytest.mark.skipif(not __import__("gold_desk.nova_style", fromlist=["x"]).fonts_available(), reason="Segoe UI absent")
def test_nova_deck_embeds_fonts_and_counts_blue_blocks(tmp_path):
    from gold_desk.nova_style import Deck, fonts_embedded
    d = Deck(tmp_path / "t.pdf", "t", "Nova Gold Weekly | test", "footer")
    d.new_page("Title", "Source")
    d.blue_block(36, 400, 300, 100, "KEY", ["one point"])
    d.table([["A", "B"], ["x", "1"]], 36, 250, [100, 100])
    d.save()
    ok, detail = fonts_embedded(tmp_path / "t.pdf")
    assert ok, detail
    assert d.blue_blocks == 1 and "one point" in d.texts
