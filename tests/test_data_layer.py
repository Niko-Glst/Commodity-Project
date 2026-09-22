"""Tests voor de datalaag.

Deze tests raken het netwerk niet: ze gebruiken verzonnen dataframes en een
tijdelijke cachemap. Dat is bewust — een test die van Yahoo's beschikbaarheid
afhangt, faalt op willekeurige momenten en zegt niets over jouw code.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.config import (
    ALL_SERIES,
    RevisionBehaviour,
    Source,
    core_series,
    series_by_name,
)
from goldmodel.data.cache import ParquetCache
from goldmodel.data.fred_client import as_known_on
from goldmodel.data.loader import DataLoader, LoadReport, LoadResult, LoadStatus


@pytest.fixture
def sample_frame() -> pd.DataFrame:
    """Een klein tijdreeksdataframe in het schema dat de clients opleveren."""
    index = pd.date_range("2024-01-01", periods=10, freq="D", name="date")
    return pd.DataFrame({"value": range(10)}, index=index, dtype="float64")


# -- cache ----------------------------------------------------------------


def test_cache_roundtrip_preserves_data(tmp_path: Path, sample_frame: pd.DataFrame) -> None:
    """Wegschrijven en teruglezen levert dezelfde waarden, index en dtypes op.

    ``check_freq=False`` is nodig omdat Parquet het ``freq``-attribuut van een
    DatetimeIndex niet bewaart: een index die met ``date_range(freq='D')`` is
    gemaakt, komt terug zonder frequentielabel. De datums en waarden zijn
    identiek, alleen het metadata-label verdwijnt.

    Dat raakt dit project niet: echte koersreeksen staan op handelsdagen en
    hebben dus sowieso ``freq is None``. Wel iets om te weten voordat je in
    fase 2 een resample-stap bouwt die op ``index.freq`` vertrouwt — dat
    attribuut overleeft de cache niet.
    """
    cache = ParquetCache(tmp_path)
    cache.save("test_key", sample_frame, source="fred", code="TEST")

    loaded = cache.load("test_key")
    assert loaded is not None
    pd.testing.assert_frame_equal(loaded, sample_frame, check_freq=False)


def test_cache_reports_freshness(tmp_path: Path, sample_frame: pd.DataFrame) -> None:
    """Een net weggeschreven entry is vers; met TTL 0 is niets vers."""
    cache = ParquetCache(tmp_path)
    cache.save("test_key", sample_frame, source="fred", code="TEST")

    assert cache.is_fresh("test_key", ttl_hours=12)
    assert not cache.is_fresh("test_key", ttl_hours=0)
    assert not cache.is_fresh("bestaat_niet", ttl_hours=12)


def test_cache_survives_corrupt_manifest(tmp_path: Path) -> None:
    """Een onleesbaar manifest maakt de cache leeg, niet stuk."""
    (tmp_path / "_manifest.json").write_text("{dit is geen json", encoding="utf-8")
    cache = ParquetCache(tmp_path)
    assert cache.summary().empty


def test_cache_records_metadata(tmp_path: Path, sample_frame: pd.DataFrame) -> None:
    """Het manifest legt bron, code en bereik vast."""
    cache = ParquetCache(tmp_path)
    cache.save("test_key", sample_frame, source="yfinance", code="GC=F", note="test")

    entry = cache.entry_for("test_key")
    assert entry is not None
    assert entry.source == "yfinance"
    assert entry.code == "GC=F"
    assert entry.row_count == 10
    assert entry.start_date == "2024-01-01"
    assert entry.end_date == "2024-01-10"
    assert entry.age_hours() < 1


def test_cache_clear(tmp_path: Path, sample_frame: pd.DataFrame) -> None:
    """Legen verwijdert bestanden en manifest-entries."""
    cache = ParquetCache(tmp_path)
    cache.save("a", sample_frame, source="fred", code="A")
    cache.save("b", sample_frame, source="fred", code="B")

    assert cache.clear("a") == 1
    assert not cache.exists("a")
    assert cache.exists("b")
    assert cache.clear() == 1


# -- vintage --------------------------------------------------------------


def test_as_known_on_returns_contemporaneous_value() -> None:
    """as_known_on geeft de versie die op de peildatum gepubliceerd was."""
    vintage = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-01"]),
            "realtime_start": pd.to_datetime(["2020-04-29", "2020-05-28", "2020-09-30"]),
            "realtime_end": pd.to_datetime(["2020-05-27", "2020-09-29", "9999-12-31"]),
            "value": [-4.8, -5.0, -5.1],
        }
    )

    # Halverwege mei kende je alleen de eerste schatting.
    early = as_known_on(vintage, "2020-05-15")
    assert early.loc[pd.Timestamp("2020-01-01"), "value"] == pytest.approx(-4.8)

    # In juni de tweede.
    mid = as_known_on(vintage, "2020-06-15")
    assert mid.loc[pd.Timestamp("2020-01-01"), "value"] == pytest.approx(-5.0)

    # Vandaag de laatste.
    latest = as_known_on(vintage, "2025-01-01")
    assert latest.loc[pd.Timestamp("2020-01-01"), "value"] == pytest.approx(-5.1)


def test_as_known_on_hides_unpublished_observations() -> None:
    """Observaties die op de peildatum nog niet bestonden, ontbreken."""
    vintage = pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-01", "2020-04-01"]),
            "realtime_start": pd.to_datetime(["2020-04-29", "2020-07-30"]),
            "realtime_end": pd.to_datetime(["9999-12-31", "9999-12-31"]),
            "value": [-4.8, -31.4],
        }
    )

    # Op 1 mei 2020 was het Q2-cijfer er nog niet.
    known = as_known_on(vintage, "2020-05-01")
    assert pd.Timestamp("2020-01-01") in known.index
    assert pd.Timestamp("2020-04-01") not in known.index


# -- loader ---------------------------------------------------------------


def test_cache_key_is_filesystem_safe() -> None:
    """Tickers met =, ^ en . leveren bruikbare bestandsnamen op."""
    for spec in ALL_SERIES:
        key = DataLoader.cache_key(spec)
        assert not any(ch in key for ch in '=^<>:"/\\|?*')


def test_cache_keys_are_unique() -> None:
    """Geen twee reeksen delen een cachesleutel."""
    keys = [DataLoader.cache_key(spec) for spec in ALL_SERIES]
    assert len(keys) == len(set(keys))


def test_build_panel_joins_on_date(sample_frame: pd.DataFrame) -> None:
    """Het paneel voegt reeksen samen op datum met een outer join."""
    spec_a, spec_b = ALL_SERIES[0], ALL_SERIES[1]

    other = sample_frame.copy()
    other.index = other.index + pd.Timedelta(days=5)

    report = LoadReport(
        results=[
            LoadResult(spec_a, LoadStatus.DOWNLOADED, sample_frame),
            LoadResult(spec_b, LoadStatus.DOWNLOADED, other),
        ]
    )
    panel = DataLoader.build_panel(report)

    assert list(panel.columns) == [spec_a.name, spec_b.name]
    # 10 dagen + 5 dagen verschoven = 15 unieke data.
    assert len(panel) == 15
    # De gaten blijven staan; de datalaag vult niets op.
    assert panel[spec_a.name].isna().sum() == 5


def test_build_panel_skips_failed_series(sample_frame: pd.DataFrame) -> None:
    """Een mislukte reeks komt niet als lege kolom in het paneel."""
    report = LoadReport(
        results=[
            LoadResult(ALL_SERIES[0], LoadStatus.DOWNLOADED, sample_frame),
            LoadResult(ALL_SERIES[1], LoadStatus.FAILED, None, "netwerkfout"),
        ]
    )
    panel = DataLoader.build_panel(report)
    assert list(panel.columns) == [ALL_SERIES[0].name]


def test_build_panel_empty_when_nothing_loaded() -> None:
    """Zonder geslaagde reeksen komt er een leeg dataframe uit."""
    report = LoadReport(results=[LoadResult(ALL_SERIES[0], LoadStatus.FAILED, None, "fout")])
    assert DataLoader.build_panel(report).empty


def test_loader_uses_fresh_cache_without_network(
    tmp_path: Path, sample_frame: pd.DataFrame
) -> None:
    """Bij een verse cache wordt de bron niet aangeroepen."""
    cache = ParquetCache(tmp_path)
    spec = ALL_SERIES[0]
    cache.save(DataLoader.cache_key(spec), sample_frame, source="fred", code=spec.code)

    loader = DataLoader(cache=cache, fred_api_key="dummy-key-niet-gebruikt")
    result = loader.load_series(spec)

    assert result.status is LoadStatus.FRESH_CACHE
    assert result.ok


def test_loader_falls_back_to_stale_cache(tmp_path: Path, sample_frame: pd.DataFrame) -> None:
    """Bij een onbereikbare bron wordt een verlopen cache alsnog gebruikt."""
    from goldmodel.config import FetchSettings

    cache = ParquetCache(tmp_path)
    spec = ALL_SERIES[0]
    key = DataLoader.cache_key(spec)
    cache.save(key, sample_frame, source="fred", code=spec.code)

    # Zet de ophaaltijd kunstmatig ver terug zodat de entry verlopen is.
    entry = cache.entry_for(key)
    assert entry is not None
    entry.fetched_at = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # Zonder API-sleutel faalt het ophalen gegarandeerd zonder netwerkcall.
    loader = DataLoader(
        FetchSettings(stale_fallback=True), cache=cache, fred_api_key=""
    )
    result = loader.load_series(spec)

    assert result.status is LoadStatus.STALE_CACHE
    assert result.ok
    assert "cache" in result.message


def test_loader_fails_cleanly_without_fallback(tmp_path: Path) -> None:
    """Zonder cache en zonder bron faalt alleen die reeks, zonder exception."""
    from goldmodel.config import FetchSettings

    loader = DataLoader(
        FetchSettings(stale_fallback=False),
        cache=ParquetCache(tmp_path),
        fred_api_key="",
    )
    result = loader.load_series(ALL_SERIES[0])

    assert result.status is LoadStatus.FAILED
    assert not result.ok


# -- configuratie ---------------------------------------------------------


def test_every_series_documents_its_rationale() -> None:
    """Elke reeks heeft een economische motivatie en een verwacht teken.

    Dit is geen codetest maar een disciplinetest: een driver toevoegen zonder
    op te schrijven waarom hij er zou moeten toe doen, is precies hoe je aan
    datamining begint.
    """
    for spec in ALL_SERIES:
        assert len(spec.rationale) > 100, f"{spec.name} mist een serieuze motivatie"
        assert spec.expected_sign, f"{spec.name} mist een verwacht teken"
        assert spec.description, f"{spec.name} mist een beschrijving"


def test_market_series_are_marked_never_revised() -> None:
    """Rentenoteringen zijn niet-gereviseerd; de dollarindex WEL.

    Deze test is aangepast nadat een ALFRED-meting de oorspronkelijke aanname
    weerlegde. Van DTWEXBGS bleken 249 van de 261 observaties uit 2015 een
    andere waarde te hebben in een latere vintage — de Fed heeft de index in
    maart 2019 herbaseerd.

    Rentes en spreads zijn wél zuivere marktnoteringen: die liggen vast zodra
    de markt sluit. Het onderscheid loopt dus niet langs "marktnotering of
    niet" maar langs "kan het niveau opnieuw vastgesteld worden".
    """
    never_revised = {"DFII10", "T10YIE", "DFF", "T10Y2Y", "BAMLH0A0HYM2"}
    for spec in ALL_SERIES:
        if spec.code in never_revised:
            assert spec.revision is RevisionBehaviour.NEVER_REVISED, (
                f"{spec.code} is een rentenotering en wordt niet herzien"
            )


def test_dollar_index_is_marked_as_revised() -> None:
    """De dollarindex staat als herzien gemarkeerd, met de meting erbij.

    Legt de correctie vast zodat niemand hem terugdraait zonder opnieuw te
    meten. De herbasering valt op log-rendementen grotendeels weg, maar
    "valt weg" is iets anders dan "gebeurt niet".
    """
    spec = series_by_name("usd_broad_index")

    assert spec.revision is not RevisionBehaviour.NEVER_REVISED
    assert spec.revision is RevisionBehaviour.REVISED_MILD


def test_core_series_excludes_optional() -> None:
    """De kernset bevat geen optionele reeksen."""
    assert all(not spec.optional for spec in core_series())
    assert len(core_series()) < len(ALL_SERIES)


def test_gold_is_in_core_series() -> None:
    """De afhankelijke variabele moet altijd in de kernset zitten."""
    assert any(spec.name == "gold_futures" for spec in core_series())


def test_publication_lag_is_set_for_fred_series() -> None:
    """FRED-reeksen hebben een publicatievertraging van minstens één dag."""
    for spec in ALL_SERIES:
        if spec.source is Source.FRED:
            assert spec.publication_lag_days >= 1, (
                f"{spec.name}: FRED publiceert nooit op de observatiedag zelf"
            )
