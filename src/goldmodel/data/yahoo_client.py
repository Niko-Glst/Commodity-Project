"""Client voor prijsreeksen via yfinance.

Yahoo Finance is gratis en heeft geen sleutel nodig, maar het is een
onofficiële bron zonder garanties. Praktische aandachtspunten die we hier
afhandelen:

- Het kolomformaat van ``yf.download`` verschilt tussen versies en tussen
  één of meerdere tickers (MultiIndex-kolommen). We normaliseren dat.
- Bij een onbekende ticker geeft yfinance een leeg dataframe terug in plaats
  van een foutmelding. Dat vangen we expliciet af.
- ``auto_adjust`` past koersen aan voor splits en dividenden. Voor futures en
  indices maakt dat niets uit, voor aandelen wel. We zetten het expliciet aan
  zodat het gedrag niet afhangt van de standaardwaarde van de bibliotheek,
  die tussen versies veranderd is.

Een inhoudelijke waarschuwing over GC=F die in de analyse terugkomt: dat is
een continu front-month contract. Yahoo plakt opeenvolgende contractmaanden
aan elkaar zonder de prijssprong bij de doorrol te corrigeren. Zo'n sprong
verschijnt in de data als een rendement, terwijl je die als houder van de
positie niet realiseert. Bij goud is de sprong klein (de forwardcurve is
vlak omdat opslagkosten en rente laag zijn), maar het is een bekend gebrek
dat je in een gesprek moet kunnen benoemen.
"""

from __future__ import annotations

import logging
import time

import pandas as pd

logger = logging.getLogger(__name__)


class YahooDataError(RuntimeError):
    """Ophalen bij Yahoo Finance is mislukt."""


class YahooClient:
    """Wrapper om ``yfinance.download`` met normalisatie en retries."""

    def __init__(
        self,
        *,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.5,
    ) -> None:
        """Initialiseert de client."""
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds

    def fetch_series(
        self,
        code: str,
        *,
        start_date: str,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Haalt de dagelijkse slotkoers van één ticker op.

        Argumenten:
            code: Yahoo-ticker, bijvoorbeeld 'GC=F' of '^VIX'.
            start_date: Eerste datum, ISO-formaat.
            end_date: Laatste datum; None betekent tot vandaag.

        Geeft terug:
            Dataframe met DatetimeIndex ``date`` en kolommen ``value``
            (slotkoers) en ``volume`` waar beschikbaar. De kolom heet bewust
            ``value`` en niet ``close``, zodat FRED- en Yahoo-reeksen
            hetzelfde schema hebben en de loader ze uniform kan behandelen.
        """
        import yfinance as yf  # lokale import: yfinance is traag om te laden

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                raw = yf.download(
                    code,
                    start=start_date,
                    end=end_date,
                    auto_adjust=True,
                    progress=False,
                    # Eén ticker per call: dan is de kolomstructuur
                    # voorspelbaar en weten we zeker welke reeks faalt.
                    threads=False,
                )
                if raw is None or raw.empty:
                    raise YahooDataError(
                        f"Yahoo gaf geen data terug voor {code!r}. "
                        "Controleer of de ticker klopt."
                    )
                return self._normalise(raw, code)
            except YahooDataError:
                raise
            except Exception as exc:  # noqa: BLE001 - yfinance gooit van alles
                last_error = exc
                if attempt < self.max_retries - 1:
                    wait = self.retry_backoff_seconds * (2**attempt)
                    logger.warning(
                        "Yahoo-call voor %s mislukt (poging %d/%d): %s — opnieuw over %.1fs",
                        code,
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait,
                    )
                    time.sleep(wait)

        raise YahooDataError(
            f"Yahoo onbereikbaar voor {code!r} na {self.max_retries} pogingen: {last_error}"
        )

    @staticmethod
    def _normalise(raw: pd.DataFrame, code: str) -> pd.DataFrame:
        """Brengt de yfinance-output terug tot een uniform schema.

        yfinance geeft afhankelijk van versie en aanroep platte kolommen of
        een MultiIndex ``(veld, ticker)``. We plakken die plat en pakken
        alleen wat we nodig hebben.
        """
        frame = raw.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            # Neem het niveau met de veldnamen ('Close', 'Volume', ...).
            level_values = frame.columns.get_level_values(0)
            if "Close" in set(level_values):
                frame.columns = level_values
            else:
                frame.columns = frame.columns.get_level_values(-1)

        if "Close" not in frame.columns:
            raise YahooDataError(
                f"Onverwachte kolomstructuur voor {code!r}: {list(frame.columns)}"
            )

        # Bij dubbele kolomnamen na het platslaan houdt .loc de eerste.
        frame = frame.loc[:, ~frame.columns.duplicated()]

        result = pd.DataFrame(index=pd.to_datetime(frame.index))
        result["value"] = pd.to_numeric(frame["Close"], errors="coerce")
        if "Volume" in frame.columns:
            result["volume"] = pd.to_numeric(frame["Volume"], errors="coerce")

        # Yahoo levert soms een tijdzone-bewuste index; die strippen we zodat
        # de join met FRED-data (tijdzoneloos) niet op dtype-verschil faalt.
        if isinstance(result.index, pd.DatetimeIndex) and result.index.tz is not None:
            result.index = result.index.tz_localize(None)

        result.index.name = "date"
        return result.sort_index()
