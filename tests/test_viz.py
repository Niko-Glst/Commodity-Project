"""Tests voor de visualisatielaag.

Deze tests controleren de berekeningen achter de figuren, niet hoe ze eruit
zien. Een test die pixels vergelijkt breekt bij elke matplotlib-update en
zegt niets over de juistheid van de statistiek.

Wat we wél toetsen: dat de statistische grootheden kloppen op data waarvan we
de uitkomst vooraf kennen. Als ``compute_returns`` of de kurtosisberekening
fout is, ziet elke figuur er nog steeds prima uit — en dat is precies de fout
die je in een sollicitatiegesprek niet wilt hoeven uitleggen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # geen venster openen tijdens tests

from goldmodel.viz.distributions import compute_returns  # noqa: E402
from goldmodel.viz.style import COLORS, ROLE, apply_style  # noqa: E402


# -- log-rendementen ------------------------------------------------------


def test_log_returns_match_formula() -> None:
    """compute_returns berekent ln(P_t / P_{t-1})."""
    index = pd.date_range("2024-01-01", periods=4, freq="D", name="date")
    panel = pd.DataFrame({"price": [100.0, 110.0, 99.0, 99.0]}, index=index)

    returns = compute_returns(panel, "price")

    assert len(returns) == 3
    assert returns.iloc[0] == pytest.approx(np.log(110 / 100))
    assert returns.iloc[1] == pytest.approx(np.log(99 / 110))
    assert returns.iloc[2] == pytest.approx(0.0)


def test_log_returns_are_additive() -> None:
    """De som van de dagrendementen is het rendement over de hele periode.

    Dit is de eigenschap waarom we logs gebruiken in plaats van procenten.
    """
    index = pd.date_range("2024-01-01", periods=5, freq="D", name="date")
    prices = [100.0, 105.0, 102.0, 108.0, 103.0]
    panel = pd.DataFrame({"price": prices}, index=index)

    returns = compute_returns(panel, "price")

    assert returns.sum() == pytest.approx(np.log(prices[-1] / prices[0]))


def test_log_returns_skip_missing_days() -> None:
    """Gaten in de reeks leveren geen NaN-rendementen op.

    Belangrijk detail: we laten de gaten weg vóór het berekenen, dus het
    rendement overbrugt een weekend of feestdag in plaats van NaN te worden.
    Dat is wat je wilt bij handelsdata, maar het betekent wel dat een
    'dagrendement' soms over drie kalenderdagen loopt.
    """
    index = pd.date_range("2024-01-01", periods=5, freq="D", name="date")
    panel = pd.DataFrame({"price": [100.0, np.nan, 110.0, np.nan, 121.0]}, index=index)

    returns = compute_returns(panel, "price")

    assert not returns.isna().any()
    assert len(returns) == 2


# -- de statistiek achter de figuren --------------------------------------


def test_normal_sample_has_near_zero_excess_kurtosis() -> None:
    """Data uit een normale verdeling geeft exces-kurtosis rond 0.

    Dit toetst dat we het begrip goed hanteren: pandas' .kurtosis() geeft
    exces-kurtosis (dus met de 3 er al vanaf), niet het ruwe vierde moment.
    Verwarring daarover is een klassieke fout.
    """
    rng = np.random.default_rng(42)
    normal_sample = pd.Series(rng.standard_normal(50_000))

    assert normal_sample.kurtosis() == pytest.approx(0.0, abs=0.1)
    assert normal_sample.skew() == pytest.approx(0.0, abs=0.05)


def test_t_distribution_has_fat_tails() -> None:
    """Een t-verdeling met weinig vrijheidsgraden heeft positieve kurtosis."""
    rng = np.random.default_rng(42)
    t_sample = pd.Series(rng.standard_t(df=5, size=50_000))

    # Theoretisch: 6/(df-4) = 6 bij df=5. Steekproefschattingen van kurtosis
    # zijn zeer variabel, dus we toetsen alleen de richting.
    assert t_sample.kurtosis() > 2.0


def test_skewness_sign_follows_the_long_tail() -> None:
    """Een reeks met een lange linkerstaart heeft negatieve scheefheid."""
    rng = np.random.default_rng(7)
    base = rng.standard_normal(10_000)
    # Voeg een paar grote negatieve uitschieters toe.
    left_skewed = pd.Series(np.concatenate([base, [-8.0, -9.0, -10.0, -12.0]]))

    assert left_skewed.skew() < 0
    assert (-left_skewed).skew() > 0


def test_kurtosis_is_dominated_by_extremes() -> None:
    """Eén extreme waarneming verhoogt de kurtosis fors.

    Dit is de eigenschap die figuur 2 laat zien: door de vierde macht bepaalt
    een handvol dagen het grootste deel van het getal.
    """
    rng = np.random.default_rng(3)
    clean = pd.Series(rng.standard_normal(5_000))
    with_outlier = pd.concat([clean, pd.Series([15.0])], ignore_index=True)

    assert with_outlier.kurtosis() > clean.kurtosis() + 5


def test_three_sigma_count_matches_normal_theory() -> None:
    """Bij normale data ligt het aantal dagen buiten 3 sd rond 0,27%."""
    rng = np.random.default_rng(11)
    sample = pd.Series(rng.standard_normal(100_000))
    z = (sample - sample.mean()) / sample.std()

    fraction = (z.abs() > 3).mean()

    assert fraction == pytest.approx(0.0027, abs=0.0008)


# -- opmaak ---------------------------------------------------------------


def test_apply_style_runs() -> None:
    """De opmaak laat zich toepassen zonder fouten."""
    apply_style()
    assert matplotlib.rcParams["axes.spines.top"] is False


def test_role_colors_are_valid_hex() -> None:
    """Alle rolkleuren zijn geldige hexcodes."""
    for name, value in ROLE.items():
        assert value.startswith("#"), name
        assert len(value) == 7, name
        int(value[1:], 16)  # gooit ValueError bij ongeldige hex


def test_categorical_colors_are_distinct() -> None:
    """Geen twee categorische kleuren zijn identiek.

    Kleur draagt identiteit in de figuren; twee reeksen dezelfde kleur geven
    maakt ze onleesbaar.
    """
    assert len(set(COLORS.values())) == len(COLORS)


# -- momentopnamen en vergelijking ----------------------------------------


def test_snapshot_roundtrip(tmp_path, monkeypatch) -> None:
    """Een momentopname laat zich opslaan en terugleggen zonder verlies."""
    import json

    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import compare_runs

    monkeypatch.setattr(compare_runs, "SNAPSHOT_DIR", tmp_path)

    payload = {
        "captured_at": "2026-01-01T00:00:00+00:00",
        "panel_rows": 100,
        "panel_columns": 4,
        "panel_last_date": "2026-01-01",
        "series": {},
    }
    path = compare_runs.snapshot_path("test")
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_snapshot_statistics_match_manual_computation() -> None:
    """compute_snapshot berekent dezelfde getallen als een directe berekening.

    Dit vangt de fout af die bij het bouwen van dit script optrad: een
    momentopname die stilzwijgend andere data beschrijft dan je denkt. De
    test controleert dat de grootheden bij de opgegeven data horen.
    """
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from compare_runs import compute_snapshot

    rng = np.random.default_rng(5)
    index = pd.date_range("2020-01-01", periods=600, freq="B", name="date")
    prices = pd.Series(100 * np.exp(np.cumsum(rng.standard_normal(600) * 0.01)), index=index)
    panel = pd.DataFrame({"gold_futures": prices})

    snap = compute_snapshot(panel, "gold_futures")
    assert snap is not None

    returns = np.log(prices / prices.shift(1)).dropna()
    assert snap.n_observations == len(returns)
    assert snap.last_date == str(prices.index.max().date())
    assert snap.last_price == pytest.approx(float(prices.iloc[-1]))
    assert snap.excess_kurtosis == pytest.approx(float(returns.kurtosis()))
    assert snap.skewness == pytest.approx(float(returns.skew()))


def test_snapshot_reflects_the_data_it_was_given() -> None:
    """Data afkappen verandert de momentopname aantoonbaar.

    Zonder deze eigenschap kun je twee momentopnamen vergelijken die in
    werkelijkheid dezelfde data beschrijven, en concludeer je ten onrechte
    dat er niets veranderd is.
    """
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from compare_runs import compute_snapshot

    rng = np.random.default_rng(9)
    index = pd.date_range("2020-01-01", periods=600, freq="B", name="date")
    prices = pd.Series(100 * np.exp(np.cumsum(rng.standard_normal(600) * 0.01)), index=index)
    panel = pd.DataFrame({"gold_futures": prices})

    full = compute_snapshot(panel, "gold_futures")
    truncated = compute_snapshot(panel.iloc[:-10], "gold_futures")

    assert full is not None and truncated is not None
    assert full.n_observations == truncated.n_observations + 10
    assert full.last_date != truncated.last_date


def test_compute_snapshot_skips_short_series() -> None:
    """Een te korte reeks levert None op in plaats van onzinstatistieken."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from compare_runs import compute_snapshot

    index = pd.date_range("2024-01-01", periods=20, freq="D", name="date")
    panel = pd.DataFrame({"gold_futures": np.arange(20, dtype=float) + 100}, index=index)

    assert compute_snapshot(panel, "gold_futures") is None
    assert compute_snapshot(panel, "bestaat_niet") is None
