import numpy as np
import pandas as pd
import pytest

from gold_desk.backtest import kupiec, score
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


def test_unfinished_day_is_dropped_only_before_the_close():
    df = pd.DataFrame({"GC=F": [1.0, 2.0]}, index=pd.to_datetime(["2026-11-02", "2026-11-03"]))
    morning = pd.Timestamp("2026-11-03 09:00", tz="America/New_York")
    evening = pd.Timestamp("2026-11-03 18:00", tz="America/New_York")
    assert len(drop_unfinished_day(df, morning)) == 1
    assert len(drop_unfinished_day(df, evening)) == 2
