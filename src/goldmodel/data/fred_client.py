"""Client voor FRED en ALFRED (de vintage-variant van FRED).

Het verschil tussen FRED en ALFRED in één alinea
------------------------------------------------
FRED geeft je de reeks *zoals die nu is*. ALFRED (Archival FRED) geeft je de
reeks *zoals die op een gekozen datum in het verleden was*. Elke observatie in
ALFRED heeft naast een observatiedatum ook een ``realtime_start`` en
``realtime_end``: het venster waarin díe waarde de officieel gepubliceerde
waarde was. Wordt een cijfer herzien, dan sluit ALFRED het oude venster af en
opent een nieuw record met dezelfde observatiedatum maar een latere
``realtime_start``.

Concreet: het Amerikaanse BBP over Q1 2020 heeft in ALFRED meerdere records
met observatiedatum 2020-01-01 — de eerste schatting van eind april, de
tweede van eind mei, de derde van eind juni, plus latere benchmarkherzieningen.
Vraag je FRED om die waarde, dan krijg je de laatste; vraag je ALFRED om de
waarde "zoals bekend op 2020-05-15", dan krijg je de eerste schatting. Dat
laatste is wat een backtest nodig heeft.

Waarom dit hier maar beperkt speelt
-----------------------------------
De kernreeksen in dit project (DFII10, DTWEXBGS, T10YIE, DFF, T10Y2Y,
BAMLH0A0HYM2) zijn dagelijkse marktnoteringen. Die worden niet herzien: het
TIPS-rendement van 3 maart 2020 was toen wat het nu is. Voor die reeksen
levert 'huidige data' geen vertekening in de waarden op.

Wat wél speelt, ook bij niet-gereviseerde reeksen, is de *publicatievertraging*.
FRED publiceert de waarde van een handelsdag pas de volgende werkdag. Wie in
een backtest de waarde van dag t gebruikt om het rendement van dag t te
verklaren, gebruikt informatie die pas op dag t+1 beschikbaar was. Dat is een
vorm van look-ahead bias die losstaat van revisies, en de reden dat elke
``SeriesSpec`` een ``publication_lag_days`` heeft.

Deze module ondersteunt beide modi. ``fetch_series`` haalt de huidige waarden
op; ``fetch_vintage_series`` haalt het volledige vintage-panel op. Zodra we
een gereviseerde reeks toevoegen (CPI, industriële productie, werkgelegenheid)
schakelen we voor die reeks over op de tweede.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

ALFRED_ENDPOINT = "https://api.stlouisfed.org/fred/series/observations"


class FredDataError(RuntimeError):
    """Ophalen bij FRED is mislukt."""


class FredClient:
    """Dunne wrapper om de FRED/ALFRED REST-API.

    We gebruiken ``requests`` direct in plaats van uitsluitend ``fredapi``,
    omdat de vintage-parameters (``realtime_start``, ``realtime_end``,
    ``output_type``) niet allemaal via die wrapper bereikbaar zijn. Voor de
    gewone reeksen zou ``fredapi`` volstaan, maar één codepad is
    overzichtelijker dan twee.
    """

    def __init__(
        self,
        api_key: str,
        *,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.5,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialiseert de client.

        Argumenten:
            api_key: FRED API-sleutel.
            max_retries: Aantal nieuwe pogingen bij een netwerkfout.
            retry_backoff_seconds: Basiswachttijd, exponentieel oplopend.
            timeout_seconds: Timeout per HTTP-request.
        """
        if not api_key:
            raise ValueError("FRED API-sleutel ontbreekt.")
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.timeout_seconds = timeout_seconds
        self._session = requests.Session()

    # -- laag niveau ------------------------------------------------------

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        """Voert een API-call uit met retries en exponentiële backoff.

        Retryen doen we alleen bij netwerkfouten en serverfouten (5xx). Een
        4xx betekent dat het verzoek zelf fout is — een onbekende reekscode
        of een ongeldige sleutel — en dan heeft opnieuw proberen geen zin.
        """
        payload = {**params, "api_key": self.api_key, "file_type": "json"}
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = self._session.get(
                    ALFRED_ENDPOINT, params=payload, timeout=self.timeout_seconds
                )
                if 400 <= response.status_code < 500:
                    raise FredDataError(
                        f"FRED wees het verzoek af (HTTP {response.status_code}): "
                        f"{response.text[:200]}"
                    )
                response.raise_for_status()
                return response.json()
            except FredDataError:
                raise
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    wait = self.retry_backoff_seconds * (2**attempt)
                    logger.warning(
                        "FRED-call mislukt (poging %d/%d): %s — opnieuw over %.1fs",
                        attempt + 1,
                        self.max_retries,
                        exc,
                        wait,
                    )
                    time.sleep(wait)

        raise FredDataError(f"FRED onbereikbaar na {self.max_retries} pogingen: {last_error}")

    # -- huidige waarden --------------------------------------------------

    def fetch_series(
        self,
        code: str,
        *,
        start_date: str,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Haalt een FRED-reeks op met de huidige (meest recente) waarden.

        Argumenten:
            code: FRED-reekscode, bijvoorbeeld 'DFII10'.
            start_date: Vroegste observatiedatum, ISO-formaat.
            end_date: Laatste observatiedatum; None betekent tot vandaag.

        Geeft terug:
            Dataframe met een DatetimeIndex ``date`` en één kolom ``value``.
            Ontbrekende waarden (FRED codeert die als '.') worden NaN.

        Let op:
            Dit zijn de waarden zoals ze nú in de database staan. Voor
            reeksen die gereviseerd worden is dat niet wat op het moment
            zelf bekend was — gebruik dan ``fetch_vintage_series``.
        """
        params: dict[str, Any] = {
            "series_id": code,
            "observation_start": start_date,
        }
        if end_date:
            params["observation_end"] = end_date

        data = self._request(params)
        observations = data.get("observations", [])
        if not observations:
            raise FredDataError(f"FRED gaf geen observaties terug voor {code!r}.")

        frame = pd.DataFrame(observations)
        frame["date"] = pd.to_datetime(frame["date"])
        # FRED codeert ontbrekende waarden als de string '.'; errors="coerce"
        # zet die om naar NaN in plaats van te crashen.
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        result = frame.set_index("date")[["value"]].sort_index()
        result.index.name = "date"
        return result

    # -- vintage ----------------------------------------------------------

    def fetch_vintage_series(
        self,
        code: str,
        *,
        start_date: str,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Haalt het volledige vintage-panel van een reeks op via ALFRED.

        Met ``realtime_start=1776-07-04`` en ``realtime_end=9999-12-31`` vraagt
        de API alle bekende versies van elke observatie op. Die twee data zijn
        de sentinelwaarden die FRED zelf gebruikt voor 'vanaf het begin' en
        'tot het einde der tijden'.

        Geeft terug:
            Dataframe met kolommen ``date`` (observatiedatum),
            ``realtime_start`` (vanaf wanneer deze waarde gepubliceerd was),
            ``realtime_end`` (tot wanneer) en ``value``. Eén observatiedatum
            kan meerdere rijen hebben: één per revisie.

        Gebruik hiervan:
            Om te weten wat op datum D bekend was, filter je op
            ``realtime_start <= D <= realtime_end``. De helper
            ``as_known_on`` hieronder doet dat.

        Waarschuwing:
            Voor lange dagelijkse reeksen kan dit veel rijen opleveren en is
            de call traag. Roep dit alleen aan voor reeksen die daadwerkelijk
            gereviseerd worden.
        """
        params: dict[str, Any] = {
            "series_id": code,
            "observation_start": start_date,
            "realtime_start": "1776-07-04",
            "realtime_end": "9999-12-31",
        }
        if end_date:
            params["observation_end"] = end_date

        try:
            data = self._request(params)
        except FredDataError as error:
            # FRED weigert een verzoek als er te veel vintage-datums in het
            # gevraagde venster vallen. Bij een DAGELIJKSE reeks is dat snel
            # het geval: elke werkdag levert een nieuwe vintage op, dus een
            # paar jaar historie loopt al tegen de limiet aan.
            #
            # Dat is geen randgeval maar de normale situatie voor de
            # kernreeksen van dit project. We vertalen het naar een
            # begrijpelijke fout in plaats van een rauwe HTTP 400.
            if "vintage dates" in str(error):
                raise FredDataError(
                    f"ALFRED weigert het volledige vintage-panel voor {code!r}: "
                    "het gevraagde venster bevat te veel vintage-datums. "
                    "Beperk de periode met start_date/end_date, of gebruik "
                    "fetch_as_known_on() voor een enkele peildatum — dat is "
                    "wat een backtest nodig heeft."
                ) from error
            raise

        observations = data.get("observations", [])
        if not observations:
            raise FredDataError(f"ALFRED gaf geen observaties terug voor {code!r}.")

        frame = pd.DataFrame(observations)
        for col in ("date", "realtime_start", "realtime_end"):
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        return frame.sort_values(["date", "realtime_start"]).reset_index(drop=True)


    def fetch_as_known_on(
        self,
        code: str,
        known_on: str | pd.Timestamp,
        *,
        start_date: str,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Haalt de reeks op zoals die op één peildatum gepubliceerd was.

        Dit is de functie die een backtest nodig heeft, en de praktische
        tegenhanger van ``fetch_vintage_series``: in plaats van het hele
        vintage-panel vraagt hij ALFRED om één momentopname.

        Waarom dat belangrijk is: het volledige panel van een dagelijkse
        reeks overschrijdt de limiet van FRED op het aantal vintage-datums.
        Per peildatum ophalen blijft daar ruim onder, en het is precies wat
        je op elk voorspelmoment wilt weten.

        Argumenten:
            code: FRED-reekscode.
            known_on: De datum waarop je 'staat' in de backtest. ALFRED geeft
                de waarden terug zoals ze op die dag gepubliceerd waren.
            start_date: Vroegste observatiedatum.
            end_date: Laatste observatiedatum; None betekent tot ``known_on``.

        Geeft terug:
            Dataframe met DatetimeIndex ``date`` en kolom ``value``, met
            alleen wat op ``known_on`` bekend was. Observaties die toen nog
            niet gepubliceerd waren, ontbreken — en dat hoort zo.
        """
        as_of = pd.Timestamp(known_on).strftime("%Y-%m-%d")
        params: dict[str, Any] = {
            "series_id": code,
            "observation_start": start_date,
            "observation_end": end_date or as_of,
            # Beide gelijk: geef de stand van zaken op exact deze dag.
            "realtime_start": as_of,
            "realtime_end": as_of,
        }

        data = self._request(params)
        observations = data.get("observations", [])
        if not observations:
            raise FredDataError(
                f"ALFRED gaf geen observaties terug voor {code!r} op {as_of}."
            )

        frame = pd.DataFrame(observations)
        frame["date"] = pd.to_datetime(frame["date"])
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        result = frame.set_index("date")[["value"]].sort_index()
        result.index.name = "date"
        return result

    def count_revisions(
        self, code: str, *, start_date: str, end_date: str
    ) -> dict:
        """Telt hoe vaak een reeks in een periode herzien is.

        Beantwoordt de vraag die de hele vintage-discussie beslist: wordt
        deze reeks eigenlijk wel herzien? Voor marktnoteringen is het
        antwoord nee, en dan is werken met de huidige reeks verdedigbaar.

        Houd de periode kort (een jaar of minder), anders loopt het verzoek
        tegen de vintage-limiet van FRED aan.
        """
        vintages = self.fetch_vintage_series(
            code, start_date=start_date, end_date=end_date
        )
        per_observation = vintages.groupby("date").size()
        revised = per_observation[per_observation > 1]

        return {
            "code": code,
            "n_observations": int(len(per_observation)),
            "n_records": int(len(vintages)),
            "n_revised": int(len(revised)),
            "share_revised": float(len(revised) / max(len(per_observation), 1)),
        }


def as_known_on(vintage_frame: pd.DataFrame, known_on: str | pd.Timestamp) -> pd.DataFrame:
    """Reconstrueert de reeks zoals die op een gegeven datum bekend was.

    Argumenten:
        vintage_frame: Output van ``FredClient.fetch_vintage_series``.
        known_on: De datum waarop je 'staat' in de backtest.

    Geeft terug:
        Dataframe met DatetimeIndex ``date`` en kolom ``value``, met per
        observatiedatum de waarde die op ``known_on`` gepubliceerd was.
        Observaties die op dat moment nog niet gepubliceerd waren, ontbreken
        volledig — en dat hoort zo: die kende je toen niet.

    Dit is de functie die look-ahead bias uit een backtest haalt. Draai je de
    walk-forward loop, dan roep je hem aan met de datum van elk voorspelmoment
    in plaats van één keer met vandaag.
    """
    cutoff = pd.Timestamp(known_on)
    mask = (vintage_frame["realtime_start"] <= cutoff) & (
        vintage_frame["realtime_end"] >= cutoff
    )
    visible = vintage_frame.loc[mask]
    # Bij overlappende vensters (komt zelden voor) nemen we de laatst
    # gepubliceerde versie die op de peildatum al gold.
    visible = visible.sort_values("realtime_start").drop_duplicates("date", keep="last")
    result = visible.set_index("date")[["value"]].sort_index()
    result.index.name = "date"
    return result
