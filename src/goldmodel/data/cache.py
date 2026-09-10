"""Bestandscache op basis van Parquet met een JSON-manifest.

Waarom Parquet en niet SQLite of CSV?

- **CSV** verliest typen. Een datumkolom komt terug als string, een
  ontbrekende waarde als lege string, en je moet bij elke inleesactie
  opnieuw parseren. Bij dagelijkse reeksen over twintig jaar is dat traag
  en foutgevoelig.
- **SQLite** is uitstekend als je wilt *queryen* — filteren, joinen,
  aggregeren binnen de opslaglaag. Dat doen we hier niet: we lezen vrijwel
  altijd een hele reeks in en werken er daarna in pandas mee. Dan betaal je
  wel de complexiteit (schema's, connecties, SQL) zonder het voordeel.
- **Parquet** bewaart dtypes exact (inclusief datetime en NaN), is
  kolomgeoriënteerd en gecomprimeerd, en ``pd.read_parquet`` geeft je in
  één regel een dataframe terug dat identiek is aan wat je wegschreef.

De keuze kan later kantelen. Zodra we vintage-panels opslaan (elke
observatiedatum × elke publicatiedatum) wordt de data veel groter en gaan we
er wél selectief in filteren — "geef me de waarden zoals bekend op
2015-06-30". Dat is een queryprobleem en daar wint SQLite. De cache-interface
hieronder is daarom bewust smal (``load``/``save``/``is_fresh``), zodat er
later een SQLite-implementatie naast kan zonder de aanroepende code te raken.

Elk gecachet bestand krijgt een naamgenoot in ``_manifest.json`` met
ophaaltijd, bron en rijaantal. Die metadata in het Parquet-bestand zelf
stoppen kan wel, maar dan moet je het bestand openen om te weten of het vers
is; een apart manifest maakt de TTL-check één JSON-read voor de hele cache.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

MANIFEST_NAME = "_manifest.json"


@dataclass
class CacheEntry:
    """Metadata over één gecachet bestand.

    Attributen:
        key: Cachesleutel, gelijk aan de bestandsnaam zonder extensie.
        source: Bron waar de data vandaan komt ('fred' of 'yfinance').
        code: Reekscode bij de bron.
        fetched_at: UTC-tijdstempel van het moment van ophalen, ISO-formaat.
        row_count: Aantal rijen, als snelle sanity check.
        start_date: Eerste observatiedatum in de data.
        end_date: Laatste observatiedatum in de data.
        note: Vrije tekst, bijvoorbeeld over vintage-status.
    """

    key: str
    source: str
    code: str
    fetched_at: str
    row_count: int
    start_date: str | None = None
    end_date: str | None = None
    note: str = ""

    @property
    def fetched_at_dt(self) -> datetime:
        """Ophaaltijd als timezone-bewuste datetime."""
        return datetime.fromisoformat(self.fetched_at)

    def age_hours(self) -> float:
        """Leeftijd van de cache-entry in uren."""
        delta = datetime.now(timezone.utc) - self.fetched_at_dt
        return delta.total_seconds() / 3600.0


class ParquetCache:
    """Eenvoudige bestandscache met TTL en stale-fallback.

    Gebruik:
        >>> cache = ParquetCache(Path("data/cache"))
        >>> if cache.is_fresh("fred_DFII10", ttl_hours=12):
        ...     df = cache.load("fred_DFII10")
    """

    def __init__(self, cache_dir: Path) -> None:
        """Initialiseert de cache en maakt de map aan als die ontbreekt."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.cache_dir / MANIFEST_NAME
        self._manifest: dict[str, CacheEntry] = self._read_manifest()

    # -- manifest ---------------------------------------------------------

    def _read_manifest(self) -> dict[str, CacheEntry]:
        """Leest het manifest van schijf; geeft een lege dict bij problemen."""
        if not self._manifest_path.exists():
            return {}
        try:
            raw = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # Een corrupt manifest mag de hele run niet blokkeren: we
            # behandelen de cache dan als leeg en halen opnieuw op.
            logger.warning("Manifest onleesbaar (%s); cache wordt genegeerd.", exc)
            return {}
        entries: dict[str, CacheEntry] = {}
        for key, payload in raw.items():
            try:
                entries[key] = CacheEntry(**payload)
            except TypeError:
                logger.warning("Manifest-entry %r heeft een onbekend formaat.", key)
        return entries

    def _write_manifest(self) -> None:
        """Schrijft het manifest atomair weg.

        Eerst naar een tijdelijk bestand, dan hernoemen. Dat voorkomt een
        half geschreven manifest als het proces halverwege afgebroken wordt —
        relevant omdat deze map onder OneDrive kan staan en tijdens het
        schrijven gesynchroniseerd kan worden.
        """
        payload = {key: asdict(entry) for key, entry in self._manifest.items()}
        tmp_path = self._manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        tmp_path.replace(self._manifest_path)

    # -- paden ------------------------------------------------------------

    def path_for(self, key: str) -> Path:
        """Geeft het pad naar het Parquet-bestand voor een cachesleutel."""
        return self.cache_dir / f"{key}.parquet"

    def entry_for(self, key: str) -> CacheEntry | None:
        """Geeft de manifest-entry voor een sleutel, of None."""
        return self._manifest.get(key)

    # -- lezen en schrijven -----------------------------------------------

    def exists(self, key: str) -> bool:
        """Bestaat er een gecachet bestand voor deze sleutel?"""
        return self.path_for(key).exists() and key in self._manifest

    def is_fresh(self, key: str, ttl_hours: float) -> bool:
        """Is het gecachete bestand jonger dan de TTL?"""
        if not self.exists(key):
            return False
        entry = self._manifest[key]
        return entry.age_hours() < ttl_hours

    def load(self, key: str) -> pd.DataFrame | None:
        """Leest een gecachet dataframe in; None als dat niet lukt."""
        path = self.path_for(key)
        if not path.exists():
            return None
        try:
            return pd.read_parquet(path)
        except (OSError, ValueError) as exc:
            logger.warning("Kon cachebestand %s niet lezen: %s", path.name, exc)
            return None

    def save(
        self,
        key: str,
        frame: pd.DataFrame,
        *,
        source: str,
        code: str,
        note: str = "",
    ) -> None:
        """Schrijft een dataframe naar de cache en werkt het manifest bij."""
        path = self.path_for(key)
        try:
            frame.to_parquet(path, index=True)
        except (OSError, ValueError, ImportError) as exc:
            logger.error("Kon %s niet naar cache schrijven: %s", key, exc)
            return

        index_is_datetime = isinstance(frame.index, pd.DatetimeIndex)
        self._manifest[key] = CacheEntry(
            key=key,
            source=source,
            code=code,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            row_count=int(len(frame)),
            start_date=str(frame.index.min().date()) if index_is_datetime and len(frame) else None,
            end_date=str(frame.index.max().date()) if index_is_datetime and len(frame) else None,
            note=note,
        )
        self._write_manifest()

    # -- inspectie --------------------------------------------------------

    def summary(self) -> pd.DataFrame:
        """Geeft een overzicht van alles in de cache, als dataframe."""
        if not self._manifest:
            return pd.DataFrame(
                columns=["key", "source", "code", "rows", "start", "end", "age_hours"]
            )
        rows = []
        for entry in self._manifest.values():
            rows.append(
                {
                    "key": entry.key,
                    "source": entry.source,
                    "code": entry.code,
                    "rows": entry.row_count,
                    "start": entry.start_date,
                    "end": entry.end_date,
                    "age_hours": round(entry.age_hours(), 1),
                }
            )
        return pd.DataFrame(rows).sort_values("key").reset_index(drop=True)

    def clear(self, key: str | None = None) -> int:
        """Verwijdert één sleutel of de hele cache; geeft het aantal terug."""
        keys = [key] if key else list(self._manifest.keys())
        removed = 0
        for k in keys:
            path = self.path_for(k)
            if path.exists():
                path.unlink()
                removed += 1
            self._manifest.pop(k, None)
        self._write_manifest()
        return removed
