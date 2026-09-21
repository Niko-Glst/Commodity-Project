"""Tests voor het tellen van onafhankelijke episodes.

Waarom dit een eigen testbestand krijgt: het onderscheid tussen "aantal dagen"
en "aantal episodes" is een terugkerende valkuil in dit project. Bij de
cyclusanalyse leidde het bijna tot een gevonden 'cyclus' die twee
crisisperiodes was; bij de crack spread tot een schijnbare N van 298 waar het
er effectief twee zijn.

De functie die dat telt, vond bovendien iets wat een handmatige analyse over
het hoofd zag (dat de 2022-episode doorloopt tot januari 2023). Dat is precies
de reden om hem te testen in plaats van erop te vertrouwen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from verken_crack_spread import (  # noqa: E402
    GALLONS_PER_BARREL,
    compute_cracks,
    count_independent_episodes,
)


def make_series(values: list[float], *, start: str = "2020-01-01") -> pd.Series:
    """Bouwt een reeks met dagelijkse index."""
    return pd.Series(
        values, index=pd.date_range(start, periods=len(values), freq="D")
    )


# -- episodes tellen -------------------------------------------------------


def test_one_continuous_block_is_one_episode() -> None:
    """Twintig aaneengesloten hoge dagen zijn één gebeurtenis, niet twintig."""
    values = [1.0] * 180 + [100.0] * 20
    outcome = count_independent_episodes(make_series(values), quantile=0.9)

    assert outcome["n_days"] == 20
    assert outcome["n_episodes"] == 1


def test_two_separated_blocks_are_two_episodes() -> None:
    """Blokken met een ruime tussenruimte tellen apart."""
    values = [1.0] * 50 + [100.0] * 10 + [1.0] * 200 + [100.0] * 10
    outcome = count_independent_episodes(make_series(values), quantile=0.9)

    assert outcome["n_days"] == 20
    assert outcome["n_episodes"] == 2


def test_short_gap_within_a_crisis_stays_one_episode() -> None:
    """Een korte onderbreking binnen een crisis is geen nieuwe episode.

    Dit is de instelling die de 2022-2023-episode als één gebeurtenis
    herkent in plaats van als twee jaren.
    """
    # Twee hoge blokken met maar 10 dagen ertussen. De lage periode moet
    # ruim genoeg zijn dat het 90e percentiel eronder valt: bij 30 hoge van
    # 240 dagen ligt dat percentiel middenin het hoge blok en steekt er
    # niets bovenuit.
    values = [1.0] * 500 + [100.0] * 15 + [1.0] * 10 + [100.0] * 15
    outcome = count_independent_episodes(
        make_series(values), quantile=0.9, min_gap_days=60
    )

    assert outcome["n_days"] == 30
    assert outcome["n_episodes"] == 1


def test_gap_longer_than_threshold_splits_the_episode() -> None:
    """Een tussenruimte boven de drempel levert wel twee episodes op."""
    values = [1.0] * 200 + [100.0] * 15 + [1.0] * 90 + [100.0] * 15
    outcome = count_independent_episodes(
        make_series(values), quantile=0.9, min_gap_days=60
    )

    assert outcome["n_episodes"] == 2


def test_episode_dates_bracket_the_high_values() -> None:
    """De gerapporteerde begin- en einddatum omvatten het hoge blok."""
    values = [1.0] * 100 + [100.0] * 10 + [1.0] * 100
    series = make_series(values)
    outcome = count_independent_episodes(series, quantile=0.9)

    start, end = outcome["episodes"][0]
    assert start == series.index[100]
    assert end == series.index[109]


def test_no_episodes_when_series_is_flat() -> None:
    """Een constante reeks levert geen episodes op zonder te crashen.

    Randgeval: bij een vlakke reeks is niets strikt groter dan het
    percentiel, dus de functie moet nul teruggeven in plaats van een
    IndexError.
    """
    outcome = count_independent_episodes(make_series([5.0] * 100), quantile=0.95)

    assert outcome["n_days"] == 0
    assert outcome["n_episodes"] == 0
    assert outcome["episodes"] == []


def test_days_per_year_sums_to_total_days() -> None:
    """De jaarverdeling telt op tot het totaal."""
    rng = np.random.default_rng(3)
    values = rng.standard_normal(1500) * 5 + 20
    series = pd.Series(
        values, index=pd.date_range("2020-01-01", periods=1500, freq="D")
    )
    outcome = count_independent_episodes(series, quantile=0.95)

    assert sum(outcome["days_per_year"].values()) == outcome["n_days"]


def test_episode_count_never_exceeds_day_count() -> None:
    """Er kunnen niet meer episodes dan dagen zijn."""
    rng = np.random.default_rng(5)
    series = pd.Series(
        rng.standard_normal(800),
        index=pd.date_range("2020-01-01", periods=800, freq="D"),
    )
    outcome = count_independent_episodes(series, quantile=0.95)

    assert outcome["n_episodes"] <= outcome["n_days"]


# -- de crack-berekening ---------------------------------------------------


def test_crack_formulas_match_the_definition() -> None:
    """De spreads volgen exact de formules uit het voorstel.

    3-2-1 crack : ((2*RB + HO) * 42 - 3*CL) / 3
    diesel crack: HO * 42 - CL
    """
    energy = pd.DataFrame(
        {
            "crude": [80.0],
            "gasoline": [2.5],
            "heating_oil": [3.0],
        },
        index=pd.date_range("2024-01-01", periods=1, freq="D"),
    )
    cracks = compute_cracks(energy)

    expected_321 = ((2 * 2.5 + 3.0) * GALLONS_PER_BARREL - 3 * 80.0) / 3
    expected_diesel = 3.0 * GALLONS_PER_BARREL - 80.0

    assert float(cracks["crack_321"].iloc[0]) == expected_321
    assert float(cracks["diesel_crack"].iloc[0]) == expected_diesel


def test_crack_is_positive_when_products_are_worth_more() -> None:
    """Bij normale marges is de crack positief.

    Sanity check op de eenheden: vergeet je de factor 42, dan komt er een
    grote negatieve waarde uit en valt dat hier direct op.
    """
    energy = pd.DataFrame(
        {"crude": [80.0], "gasoline": [2.4], "heating_oil": [2.6]},
        index=pd.date_range("2024-01-01", periods=1, freq="D"),
    )
    cracks = compute_cracks(energy)

    assert float(cracks["crack_321"].iloc[0]) > 0
    assert float(cracks["diesel_crack"].iloc[0]) > 0
