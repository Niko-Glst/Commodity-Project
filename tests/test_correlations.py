"""Tests voor de correlatie- en stabiliteitsanalyse."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from goldmodel.viz.correlations import (  # noqa: E402
    build_change_panel,
    correlations_with_gold,
    rolling_correlation,
    stability_summary,
)


def make_panel(n: int = 800, *, seed: int = 1) -> pd.DataFrame:
    """Bouwt een testpaneel met een bekende structuur.

    ``driver_linked`` correleert per constructie met goud, ``driver_noise``
    niet. Zo weten we vooraf wat de analyse hoort te vinden.
    """
    rng = np.random.default_rng(seed)
    index = pd.date_range("2015-01-01", periods=n, freq="B", name="date")

    shock = rng.standard_normal(n) * 0.01
    gold_returns = shock + rng.standard_normal(n) * 0.005
    linked_returns = -shock + rng.standard_normal(n) * 0.005

    return pd.DataFrame(
        {
            "gold_futures": 1000.0 * np.exp(np.cumsum(gold_returns)),
            "driver_linked": 100.0 * np.exp(np.cumsum(linked_returns)),
            "driver_noise": 50.0 + np.cumsum(rng.standard_normal(n) * 0.1),
        },
        index=index,
    )


# -- transformatie ---------------------------------------------------------


def test_prices_become_log_returns() -> None:
    """Reeksen in RETURN_SERIES worden log-rendementen."""
    panel = make_panel()
    changes = build_change_panel(panel)

    expected = np.log(
        panel["gold_futures"] / panel["gold_futures"].shift(1)
    ).dropna()
    actual = changes["gold_futures"].dropna()

    pd.testing.assert_series_equal(actual, expected, check_names=False)


def test_other_series_become_first_differences() -> None:
    """Reeksen buiten RETURN_SERIES worden eerste verschillen."""
    panel = make_panel()
    changes = build_change_panel(panel)

    expected = panel["driver_noise"].diff().dropna()
    actual = changes["driver_noise"].dropna()

    pd.testing.assert_series_equal(actual, expected, check_names=False)


def test_short_series_are_dropped() -> None:
    """Reeksen met te weinig waarnemingen vallen weg."""
    panel = make_panel()
    panel["te_kort"] = np.nan
    panel.iloc[:50, panel.columns.get_loc("te_kort")] = 1.0

    changes = build_change_panel(panel)

    assert "te_kort" not in changes.columns


# -- correlaties -----------------------------------------------------------


def test_finds_the_planted_relationship() -> None:
    """De ingebouwde negatieve samenhang wordt teruggevonden.

    Positieve controle: zonder deze test weet je niet of 'geen verband
    gevonden' betekent dat er geen is, of dat de code kapot is.
    """
    changes = build_change_panel(make_panel())
    table = correlations_with_gold(changes)

    linked = table[table["driver"] == "driver_linked"].iloc[0]
    noise = table[table["driver"] == "driver_noise"].iloc[0]

    assert linked["correlatie"] < -0.3
    assert linked["significant"]
    assert abs(noise["correlatie"]) < 0.1


def test_gold_is_not_correlated_with_itself_in_the_table() -> None:
    """Goud staat niet als eigen driver in de uitkomst."""
    changes = build_change_panel(make_panel())
    table = correlations_with_gold(changes)

    assert "gold_futures" not in set(table["driver"])


def test_r_squared_is_correlation_squared() -> None:
    """De verklaarde variantie is de correlatie in het kwadraat."""
    changes = build_change_panel(make_panel())
    table = correlations_with_gold(changes)

    for _, row in table.iterrows():
        assert row["r_kwadraat_pct"] == pytest.approx(
            row["correlatie"] ** 2 * 100
        )


def test_significance_bound_shrinks_with_more_data() -> None:
    """De toevalsgrens wordt kleiner bij meer waarnemingen."""
    small = correlations_with_gold(build_change_panel(make_panel(400)))
    large = correlations_with_gold(build_change_panel(make_panel(3000)))

    assert large["toevalsgrens"].mean() < small["toevalsgrens"].mean()


# -- stabiliteit -----------------------------------------------------------


def test_rolling_correlation_has_expected_length() -> None:
    """De voortschrijdende correlatie verliest window-1 waarnemingen."""
    changes = build_change_panel(make_panel(800))
    rolling = rolling_correlation(changes, "driver_linked", window=252)

    pair_length = len(
        pd.concat(
            [changes["gold_futures"], changes["driver_linked"]], axis=1
        ).dropna()
    )
    assert len(rolling) == pair_length - 251


def test_stable_relationship_does_not_switch_sign() -> None:
    """Een sterk, constant verband wisselt niet van teken.

    We bouwen een driver met een zeer sterke negatieve samenhang; die hoort
    in elk venster negatief te blijven.
    """
    rng = np.random.default_rng(5)
    n = 1500
    index = pd.date_range("2015-01-01", periods=n, freq="B", name="date")
    shock = rng.standard_normal(n) * 0.01

    panel = pd.DataFrame(
        {
            "gold_futures": 1000.0 * np.exp(np.cumsum(shock)),
            # Vrijwel spiegelbeeldig: heel weinig eigen ruis.
            "driver_strong": 100.0
            * np.exp(np.cumsum(-shock + rng.standard_normal(n) * 0.001)),
        },
        index=index,
    )
    changes = build_change_panel(panel)
    summary = stability_summary(changes, ["driver_strong"])

    assert bool(summary.iloc[0]["wisselt_teken"]) is False
    assert summary.iloc[0]["max"] < 0


def test_unstable_relationship_is_flagged() -> None:
    """Een verband dat per periode omklapt, wordt als wisselend gemarkeerd.

    Dit is het geval dat in de echte data bij vier van de vijf drivers
    optreedt, en het is de reden dat we niet op een gemiddelde correlatie
    mogen vertrouwen.
    """
    rng = np.random.default_rng(7)
    n = 1500
    index = pd.date_range("2015-01-01", periods=n, freq="B", name="date")
    shock = rng.standard_normal(n) * 0.01

    # Eerste helft positief verbonden, tweede helft negatief.
    sign = np.where(np.arange(n) < n // 2, 1.0, -1.0)
    driver_changes = sign * shock + rng.standard_normal(n) * 0.002

    panel = pd.DataFrame(
        {
            "gold_futures": 1000.0 * np.exp(np.cumsum(shock)),
            "driver_flip": 100.0 * np.exp(np.cumsum(driver_changes)),
        },
        index=index,
    )
    changes = build_change_panel(panel)
    summary = stability_summary(changes, ["driver_flip"])

    assert bool(summary.iloc[0]["wisselt_teken"]) is True
    assert summary.iloc[0]["spreiding"] > 1.0


def test_stability_summary_is_sorted_by_spread() -> None:
    """De meest instabiele driver staat bovenaan."""
    changes = build_change_panel(make_panel(1500))
    summary = stability_summary(changes, ["driver_linked", "driver_noise"])

    spreads = summary["spreiding"].tolist()
    assert spreads == sorted(spreads, reverse=True)


def test_mean_of_rolling_is_near_full_period_correlation() -> None:
    """Het gemiddelde van de vensters ligt in de buurt van de totale correlatie.

    Niet exact gelijk - overlappende vensters wegen de middelste periodes
    zwaarder - maar wel dezelfde orde van grootte. Wijkt het ver af, dan
    zit er een fout in de berekening.
    """
    changes = build_change_panel(make_panel(2000))
    rolling = rolling_correlation(changes, "driver_linked")
    pair = pd.concat(
        [changes["gold_futures"], changes["driver_linked"]], axis=1
    ).dropna()
    overall = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))

    assert abs(float(rolling.mean()) - overall) < 0.1
