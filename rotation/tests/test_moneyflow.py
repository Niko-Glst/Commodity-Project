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
