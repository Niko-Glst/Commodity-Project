"""Orkestratie van de datalaag: cache-eerst ophalen en samenvoegen tot een paneel.

De loader is de enige plek die weet in welke volgorde we dingen proberen:

1. Verse cache? Gebruik die, ga niet het net op.
2. Anders ophalen bij de bron en wegschrijven naar de cache.
3. Mislukt dat en is er een verlopen cache? Gebruik die alsnog en waarschuw.
4. Mislukt alles? Sla de reeks over en ga door met de rest.

Stap 3 en 4 zijn de graceful degradation: een storing bij Yahoo mag je
werkdag niet slopen als je gisteren nog data hebt opgehaald. De loader
rapporteert per reeks wat er gebeurd is, zodat je in de output ziet of je
naar verse of naar oude data kijkt — stille fallback is gevaarlijker dan
falen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from goldmodel.config import (
    ALL_SERIES,
    DEFAULT_FETCH_SETTINGS,
    FetchSettings,
    SeriesSpec,
    Source,
    get_cache_dir,
    get_fred_api_key,
)
from goldmodel.data.cache import ParquetCache
from goldmodel.data.fred_client import FredClient
from goldmodel.data.yahoo_client import YahooClient

logger = logging.getLogger(__name__)


class LoadStatus(str, Enum):
    """Hoe een reeks uiteindelijk geladen is."""

    FRESH_CACHE = "verse cache"
    DOWNLOADED = "opgehaald"
    STALE_CACHE = "verlopen cache (fallback)"
    FAILED = "mislukt"


@dataclass
class LoadResult:
    """Uitkomst van het laden van één reeks.

    Attributen:
        spec: De reeksdefinitie.
        status: Hoe de data verkregen is.
        frame: De data, of None bij mislukking.
        message: Toelichting, vooral relevant bij fallback of mislukking.
    """

    spec: SeriesSpec
    status: LoadStatus
    frame: pd.DataFrame | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        """Is er bruikbare data?"""
        return self.frame is not None and not self.frame.empty


@dataclass
class LoadReport:
    """Verzamelde resultaten van een laadronde."""

    results: list[LoadResult] = field(default_factory=list)

    @property
    def successful(self) -> list[LoadResult]:
        """Reeksen waarvoor we data hebben."""
        return [r for r in self.results if r.ok]

    @property
    def failed(self) -> list[LoadResult]:
        """Reeksen zonder data."""
        return [r for r in self.results if not r.ok]

    def to_frame(self) -> pd.DataFrame:
        """Overzichtstabel van de laadronde."""
        return pd.DataFrame(
            [
                {
                    "reeks": r.spec.name,
                    "code": r.spec.code,
                    "bron": r.spec.source.value,
                    "status": r.status.value,
                    "rijen": len(r.frame) if r.frame is not None else 0,
                    "toelichting": r.message,
                }
                for r in self.results
            ]
        )


class DataLoader:
    """Haalt reeksen op met cache-eerst-strategie en bouwt het paneel."""

    def __init__(
        self,
        settings: FetchSettings | None = None,
        *,
        cache: ParquetCache | None = None,
        fred_api_key: str | None = None,
    ) -> None:
        """Initialiseert de loader.

        Argumenten:
            settings: Ophaalinstellingen; None gebruikt de standaard.
            cache: Cache-implementatie; None maakt er zelf een aan.
            fred_api_key: Sleutel; None leest hem uit .env. Zonder sleutel
                worden FRED-reeksen overgeslagen in plaats van dat de hele
                run faalt.
        """
        self.settings = settings or DEFAULT_FETCH_SETTINGS
        self.cache = cache or ParquetCache(get_cache_dir())

        key = fred_api_key if fred_api_key is not None else get_fred_api_key()
        self._fred: FredClient | None = None
        if key:
            self._fred = FredClient(
                key,
                max_retries=self.settings.max_retries,
                retry_backoff_seconds=self.settings.retry_backoff_seconds,
            )
        else:
            logger.warning(
                "Geen FRED_API_KEY gevonden. FRED-reeksen worden alleen uit de "
                "cache geladen. Zet de sleutel in .env om ze op te halen."
            )

        self._yahoo = YahooClient(
            max_retries=self.settings.max_retries,
            retry_backoff_seconds=self.settings.retry_backoff_seconds,
        )

    # -- één reeks --------------------------------------------------------

    @staticmethod
    def cache_key(spec: SeriesSpec) -> str:
        """Bouwt de cachesleutel voor een reeks.

        Tekens die niet in een bestandsnaam mogen (``=``, ``^``, ``.``)
        vervangen we; 'GC=F' wordt 'yfinance_GC_F'.
        """
        safe_code = spec.code.replace("=", "_").replace("^", "").replace(".", "_")
        return f"{spec.source.value}_{safe_code}"

    def load_series(self, spec: SeriesSpec, *, force_refresh: bool = False) -> LoadResult:
        """Laadt één reeks volgens de cache-eerst-strategie."""
        key = self.cache_key(spec)

        # 1. Verse cache
        if not force_refresh and self.cache.is_fresh(key, self.settings.cache_ttl_hours):
            frame = self.cache.load(key)
            if frame is not None and not frame.empty:
                entry = self.cache.entry_for(key)
                age = f"{entry.age_hours():.1f}u oud" if entry else ""
                return LoadResult(spec, LoadStatus.FRESH_CACHE, frame, age)

        # 2. Ophalen bij de bron
        try:
            frame = self._download(spec)
            note = f"revisiegedrag: {spec.revision.value}"
            self.cache.save(key, frame, source=spec.source.value, code=spec.code, note=note)
            return LoadResult(spec, LoadStatus.DOWNLOADED, frame, "")
        except Exception as exc:  # noqa: BLE001 - bewust breed: elke bronfout
            download_error = str(exc)
            logger.warning("Ophalen van %s mislukt: %s", spec.name, download_error)

        # 3. Verlopen cache als vangnet
        if self.settings.stale_fallback and self.cache.exists(key):
            frame = self.cache.load(key)
            if frame is not None and not frame.empty:
                entry = self.cache.entry_for(key)
                age = f"{entry.age_hours():.1f}u" if entry else "onbekend"
                return LoadResult(
                    spec,
                    LoadStatus.STALE_CACHE,
                    frame,
                    f"bron onbereikbaar, cache van {age} oud gebruikt",
                )

        # 4. Opgeven, maar alleen voor deze reeks
        return LoadResult(spec, LoadStatus.FAILED, None, download_error[:160])

    def _download(self, spec: SeriesSpec) -> pd.DataFrame:
        """Haalt één reeks op bij de juiste bron."""
        if spec.source is Source.FRED:
            if self._fred is None:
                raise RuntimeError("Geen FRED API-sleutel beschikbaar.")
            return self._fred.fetch_series(
                spec.code,
                start_date=self.settings.start_date,
                end_date=self.settings.end_date,
            )
        if spec.source is Source.YFINANCE:
            return self._yahoo.fetch_series(
                spec.code,
                start_date=self.settings.start_date,
                end_date=self.settings.end_date,
            )
        raise ValueError(f"Onbekende bron: {spec.source}")

    # -- meerdere reeksen -------------------------------------------------

    def load_all(
        self,
        specs: tuple[SeriesSpec, ...] | list[SeriesSpec] | None = None,
        *,
        force_refresh: bool = False,
    ) -> LoadReport:
        """Laadt een set reeksen en geeft een rapport terug."""
        selected = list(specs) if specs is not None else list(ALL_SERIES)
        report = LoadReport()
        for spec in selected:
            report.results.append(self.load_series(spec, force_refresh=force_refresh))
        return report

    # -- paneel bouwen ----------------------------------------------------

    @staticmethod
    def build_panel(report: LoadReport) -> pd.DataFrame:
        """Voegt de geladen reeksen samen tot één dataframe op datum.

        We gebruiken een outer join op de datumindex, zodat geen enkele
        observatie verloren gaat. Het resultaat bevat dus gaten: FRED-reeksen
        hebben geen waarde op Amerikaanse feestdagen, Yahoo-reeksen niet in
        het weekend, en de wekelijkse balansreeks heeft er per definitie maar
        één per week.

        Die gaten laten we hier expliciet staan. Ze opvullen is een
        modelleerbeslissing, geen laadbeslissing: forward-fill van een
        wekelijkse reeks naar dagelijkse frequentie creëert kunstmatige
        autocorrelatie (vijf identieke waarden op rij), wat de
        standaardfouten in een regressie te klein maakt en de Durbin-Watson-
        statistiek onbruikbaar. Dat besluit hoort in fase 2, met de gevolgen
        erbij, niet stilzwijgend in de datalaag.
        """
        columns: dict[str, pd.Series] = {}
        for result in report.successful:
            assert result.frame is not None
            columns[result.spec.name] = result.frame["value"]

        if not columns:
            return pd.DataFrame()

        panel = pd.concat(columns, axis=1)
        panel.index.name = "date"
        return panel.sort_index()
