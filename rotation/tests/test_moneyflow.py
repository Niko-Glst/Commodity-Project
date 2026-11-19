import numpy as np
import pandas as pd
import pytest

from moneyflow.analysis import beat_cash, performance, profit_taking, ret
from moneyflow.data import CASH


def _prices():
    idx = pd.bdate_range("2025-09-01", "2026-11-18")
    t = np.arange(len(idx))
    cols = {CASH: 100 * (1 + 0.0001) ** t}
    # assets that rose until the peak and fell after, by different amounts
    peak = idx.get_loc(pd.Timestamp("2026-10-06"))
    for k, (gain, fall) in enumerate([(0.8, -0.3), (0.4, -0.15), (0.1, -0.02), (-0.1, 0.05), (-0.2, 0.08)]):
        path = np.where(t <= peak, 1 + gain * t / peak, (1 + gain) * (1 + fall * (t - peak) / (len(t) - 1 - peak)))
        cols[["SMH", "XLK", "SPY", "XLP", "XLU"][k]] = 100 * path
    return pd.DataFrame(cols, index=idx)


def test_ret_uses_the_close_on_or_before_each_date():
    p = _prices()
    r = ret(p, "2026-10-04", "2026-10-06")            # 4 Oct 2026 is a Sunday: uses Friday 2 Oct
    assert r["SPY"] == pytest.approx(p.loc["2026-10-06", "SPY"] / p.loc["2026-10-02", "SPY"] - 1)


def test_profit_taking_is_negative_when_winners_fall_hardest():
    perf = performance(_prices())
    pt = profit_taking(perf)
    assert pt["spearman"] == pytest.approx(-1.0)
    assert beat_cash(perf) == (2, 5)                  # only the two that rose after the peak beat cash


def test_etf_flow_is_change_in_shares_times_nav():
    from moneyflow.analysis import etf_flows

    dates = pd.bdate_range("2025-09-01", "2026-11-18")
    shares = np.full(len(dates), 1_000_000.0)
    shares[dates > pd.Timestamp("2026-11-12")] += 50_000          # one creation of 50,000 shares on 13 Nov
    f = pd.DataFrame({"date": dates, "nav": 20.0, "shares": shares, "ticker": "XLP"})
    row = etf_flows(f).iloc[0]
    assert row.flow_week_bn == pytest.approx(50_000 * 20.0 / 1e9)
    assert row.flow_peak_bn == pytest.approx(row.flow_week_bn)
    assert row.flow_peak_pct == pytest.approx(0.05)


def test_mmf_z_uses_only_earlier_weeks():
    from moneyflow.analysis import mmf_stats

    idx = pd.date_range("2026-07-01", periods=12, freq="W-WED")
    total = 7_000_000 + np.cumsum([0] + [10_000, -10_000] * 5 + [50_000])
    m = mmf_stats(pd.DataFrame({"total": total}, index=idx))
    assert m["chg_bn"] == pytest.approx(50.0)
    assert m["n_weeks"] == 10 and m["z"] > 4


def test_net_liquidity_does_not_double_count_reserves():
    from moneyflow.analysis import net_liquidity

    idx = pd.date_range("2026-09-02", periods=12, freq="W-WED")
    F = {"WALCL": pd.Series(6_700_000.0, idx), "WTREGEN": pd.Series(900_000.0, idx),
         "RRPONTSYD": pd.Series(1.0, pd.bdate_range("2026-09-01", "2026-11-20"))}
    assert net_liquidity(F)["now_bn"] == pytest.approx(6_700 - 900 - 1)
