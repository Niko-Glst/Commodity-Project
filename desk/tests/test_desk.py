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
