"""Configuratie: paden, reeksdefinities en de economische motivatie daarachter.

Dit bestand is bewust de enige plek waar staat *welke* reeksen we ophalen en
*waarom*. De ophaallogica in ``data/`` kent geen enkele reeks bij naam; die
werkt uitsluitend op de definities hieronder. Zo blijft het toevoegen van een
driver een configuratiewijziging in plaats van een codewijziging.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

# --------------------------------------------------------------------------
# Paden
# --------------------------------------------------------------------------

# Projectwortel: dit bestand zit in src/goldmodel/, dus drie niveaus omhoog.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def get_cache_dir() -> Path:
    """Geeft de cachemap terug en maakt hem aan als hij nog niet bestaat.

    Standaard ``data/cache`` in de projectmap; te overschrijven met de
    omgevingsvariabele ``CACHE_DIR``. Die override bestaat omdat de projectmap
    hier onder OneDrive staat: wie sync-ruis wil vermijden kan de cache
    buiten de gesynchroniseerde map zetten zonder code aan te passen.
    """
    override = os.getenv("CACHE_DIR")
    cache_dir = Path(override) if override else PROJECT_ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_fred_api_key() -> str | None:
    """Leest de FRED-sleutel uit de omgeving.

    Geeft ``None`` terug in plaats van een exception te gooien: de datalaag
    moet graceful degraderen. Zonder sleutel zijn de yfinance-reeksen nog
    steeds bruikbaar, en een gevulde cache blijft ook zonder sleutel leesbaar.
    """
    key = os.getenv("FRED_API_KEY")
    return key.strip() if key and key.strip() else None


# --------------------------------------------------------------------------
# Revisiegedrag — de kern van de look-ahead-vraag
# --------------------------------------------------------------------------


class RevisionBehaviour(str, Enum):
    """Hoe sterk een reeks achteraf herzien wordt.

    Dit bepaalt of vintage-data (ALFRED) nodig is om look-ahead bias te
    vermijden. Zie ``docs/vintage_data.md`` voor de volledige uitleg.

    NEVER_REVISED
        Marktgenoteerde reeksen. De waarde van een handelsdag ligt vast zodra
        de markt sluit en verandert daarna niet meer. Wat je vandaag ophaalt
        voor 3 maart 2020 is exact wat op 4 maart 2020 bekend was. Voor deze
        reeksen introduceert 'huidige data' geen look-ahead bias in de waarden
        zelf — alleen de publicatievertraging (één werkdag) moet je respecteren.

    REVISED
        Statistische aggregaten die het bureau achteraf bijstelt: eerste
        schatting, tweede schatting, jaarlijkse benchmarkherziening,
        seizoensherziening. Het BBP-cijfer over Q1 dat je vandaag ophaalt kan
        substantieel afwijken van wat er in april van dat jaar gepubliceerd
        werd. Backtesten met de huidige waarde betekent dan handelen op
        informatie die pas maanden later bestond.

    REVISED_MILD
        Reeksen die formeel gereviseerd kunnen worden maar in de praktijk
        nauwelijks bewegen na de eerste publicatie.
    """

    NEVER_REVISED = "never_revised"
    REVISED = "revised"
    REVISED_MILD = "revised_mild"


class Source(str, Enum):
    """Databron van een reeks."""

    FRED = "fred"
    YFINANCE = "yfinance"


@dataclass(frozen=True)
class SeriesSpec:
    """Definitie van één tijdreeks.

    Attributen:
        code: Identifier bij de bron (FRED-reekscode of Yahoo-ticker).
        name: Korte, leesbare naam die we in kolomkoppen gebruiken.
        source: Waar de reeks vandaan komt.
        description: Wat de reeks meet, in gewone taal.
        rationale: Waarom deze reeks in een goudmodel thuishoort — de
            economische motivatie. Dit is het antwoord op de vraag "waarom
            deze variabele?" in een sollicitatiegesprek.
        expected_sign: Verwachte richting van het verband met goudrendementen
            ('+', '-' of '?'). Vooraf opschrijven is een discipline tegen
            achteraf-rationalisatie: als het model het omgekeerde teken vindt,
            moet je dat verklaren in plaats van het weg te redeneren.
        revision: Revisiegedrag, zie ``RevisionBehaviour``.
        publication_lag_days: Aantal kalenderdagen tussen de observatiedatum
            en het moment waarop de waarde publiek beschikbaar is. Gebruikt
            om de reeks te lagen bij het bouwen van de modelmatrix.
        units: Eenheid van de ruwe reeks, voor de leesbaarheid van output.
        transform_hint: Voorgestelde transformatie naar een (waarschijnlijk)
            stationaire reeks. Dit is een hint voor fase 2, geen automatisme:
            de stationariteitstoetsen bepalen uiteindelijk wat we doen.
    """

    code: str
    name: str
    source: Source
    description: str
    rationale: str
    expected_sign: str
    revision: RevisionBehaviour
    publication_lag_days: int
    units: str
    transform_hint: str
    optional: bool = False


# --------------------------------------------------------------------------
# FRED-reeksen
# --------------------------------------------------------------------------

FRED_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec(
        code="DFII10",
        name="real_rate_10y",
        source=Source.FRED,
        description="Rendement op 10-jaars inflatiegeïndexeerde Treasuries (TIPS), dagelijks.",
        rationale=(
            "Dit is theoretisch de belangrijkste driver van de goudprijs. Goud "
            "betaalt geen rente en geen dividend, dus de kosten van het aanhouden "
            "ervan zijn de reële rente die je misloopt op een veilig alternatief. "
            "Stijgt de reële rente, dan wordt goud aanhouden duurder ten opzichte "
            "van TIPS en daalt de vraag. Dit is geen empirisch gevonden verband "
            "maar een arbitrage-argument, wat het sterker maakt dan een gevonden "
            "correlatie: je kunt uitleggen waarom het zou moeten gelden."
        ),
        expected_sign="-",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=1,
        units="procent per jaar",
        transform_hint="eerste verschil (niveau is vrijwel zeker niet-stationair)",
    ),
    SeriesSpec(
        code="DTWEXBGS",
        name="usd_broad_index",
        source=Source.FRED,
        description="Handelsgewogen dollarindex tegenover een brede korf valuta's, dagelijks.",
        rationale=(
            "Goud wordt in dollars genoteerd, maar wordt wereldwijd gekocht. Als "
            "de dollar sterker wordt, wordt goud duurder in euro's, yen en yuan, "
            "waardoor de vraag buiten de VS daalt en de dollarprijs onder druk "
            "komt. Er zit ook een puur mechanisch effect in: bij een constante "
            "waarde in een valutamandje daalt de dollarnotering automatisch als "
            "de dollar stijgt. Let op dat dit verband deels een identiteit is en "
            "niet volledig als causaal 'signaal' mag worden gelezen."
        ),
        expected_sign="-",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=1,
        units="index (jan 2006 = 100)",
        transform_hint="log-rendement",
    ),
    SeriesSpec(
        code="T10YIE",
        name="breakeven_inflation_10y",
        source=Source.FRED,
        description=(
            "10-jaars break-even inflatie: het verschil tussen het nominale "
            "Treasury-rendement en het TIPS-rendement, dagelijks."
        ),
        rationale=(
            "Dit is de inflatieverwachting die de markt inprijst. Goud geldt "
            "als inflatiehedge, dus stijgende inflatieverwachtingen zouden de "
            "vraag moeten opdrijven. Belangrijke kanttekening voor het model: "
            "break-even is per constructie het nominale rendement min het reële "
            "rendement, en DFII10 zit al als aparte driver in het model. Er zit "
            "dus een definitorisch verband tussen deze twee regressoren, wat tot "
            "multicollineariteit leidt. Dat is precies waarom we in fase 3 naar "
            "de VIF's kijken en regularisatie overwegen."
        ),
        expected_sign="+",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=1,
        units="procentpunt",
        transform_hint="eerste verschil",
    ),
    SeriesSpec(
        code="DFF",
        name="fed_funds_rate",
        source=Source.FRED,
        description="Effectieve Federal Funds Rate, dagelijks.",
        rationale=(
            "De beleidsrente aan de korte kant van de curve. Grotendeels "
            "overlappend met de reële rente, maar vangt iets anders: het "
            "actuele beleidsstandpunt in plaats van de marktverwachting op "
            "lange termijn. Verwacht weinig eigenstandige verklaringskracht "
            "bovenop DFII10; we nemen hem mee om dat expliciet te kunnen "
            "laten zien in plaats van het aan te nemen. Als de coëfficiënt "
            "insignificant blijkt, is dat een resultaat om te rapporteren."
        ),
        expected_sign="-",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=1,
        units="procent per jaar",
        transform_hint="eerste verschil",
    ),
    # ---------------------------------------------------------------
    # Aanvullende reeksen — mijn eigen keuzes, met motivatie
    # ---------------------------------------------------------------
    SeriesSpec(
        code="T10Y2Y",
        name="term_spread_10y2y",
        source=Source.FRED,
        description="Renteverschil tussen 10-jaars en 2-jaars Treasuries, dagelijks.",
        rationale=(
            "De helling van de rentecurve is een klassieke voorlopende indicator "
            "voor recessies: een inversie (negatieve spread) gaat historisch "
            "vooraf aan economische krimp. Goud presteert doorgaans goed in de "
            "aanloop naar en tijdens recessies, deels als veilige haven en deels "
            "omdat de Fed dan gaat verruimen. Dit voegt een dimensie toe die de "
            "niveaus van DFII10 en DFF niet vangen: niet hoe hoog de rente is, "
            "maar wat de markt verwacht over de richting."
        ),
        expected_sign="+",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=1,
        units="procentpunt",
        transform_hint="eerste verschil",
    ),
    SeriesSpec(
        code="BAMLH0A0HYM2",
        name="high_yield_spread",
        source=Source.FRED,
        description="ICE BofA US High Yield Option-Adjusted Spread, dagelijks.",
        rationale=(
            "Een marktgebaseerde maatstaf voor kredietstress: hoeveel extra "
            "rendement eisen beleggers voor risicovolle bedrijfsobligaties. "
            "Loopt sterk op in periodes van financiële stress. Dit is een "
            "alternatieve stress-indicator naast de VIX, en ze meten niet "
            "hetzelfde: de VIX meet verwachte aandelenvolatiliteit, deze spread "
            "meet gepercipieerd wanbetalingsrisico. In 2008 liepen ze uiteen in "
            "timing, wat ze complementair maakt."
        ),
        expected_sign="+",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=1,
        units="procentpunt",
        transform_hint="eerste verschil of log-niveau",
        # LET OP: FRED levert via de observations-endpoint maar circa drie jaar
        # historie voor deze reeks (vanaf ~2023), terwijl de andere drivers tot
        # 2003 teruggaan. Een regressor die pas in 2023 begint, kort het hele
        # model in tot dat venster. Daarom optioneel: bruikbaar voor een
        # deelperiode-analyse, niet voor het basismodel. De VIX vervult de rol
        # van stressindicator over de volledige periode.
        optional=True,
    ),
    SeriesSpec(
        code="WALCL",
        name="fed_balance_sheet",
        source=Source.FRED,
        description="Totale activa op de balans van de Federal Reserve, wekelijks (woensdag).",
        rationale=(
            "Een directe maatstaf voor kwantitatieve verruiming en verkrapping. "
            "Het monetaire-debasement-argument voor goud gaat over "
            "balansuitbreiding, niet over de rente. Twee waarschuwingen: de "
            "reeks is wekelijks terwijl de rest dagelijks is, dus we moeten "
            "expliciet kiezen hoe we die mengen (forward-fill introduceert "
            "kunstmatige autocorrelatie), en de balans groeide vrijwel monotoon "
            "van 2008 tot 2022, wat een schijnverband met elke andere stijgende "
            "reeks oplevert. Dit is een reeks waar spurious regression op de "
            "loer ligt; in eerste verschillen is dat risico veel kleiner."
        ),
        expected_sign="+",
        revision=RevisionBehaviour.REVISED_MILD,
        publication_lag_days=2,
        units="miljoen USD",
        transform_hint="log-rendement (wekelijks)",
        optional=True,
    ),
)


# --------------------------------------------------------------------------
# yfinance-reeksen
# --------------------------------------------------------------------------

YFINANCE_SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec(
        code="GC=F",
        name="gold_futures",
        source=Source.YFINANCE,
        description="COMEX goud-futures, front-month continu contract, dagelijkse slotkoers.",
        rationale=(
            "De afhankelijke variabele. We gebruiken futures in plaats van een "
            "spotprijs of een ETF omdat de brug naar je hedge-tool over "
            "margeverplichtingen op een short futures-positie gaat: dan wil je "
            "de volatiliteit van precies dat instrument modelleren. "
            "Belangrijke kanttekening: een continu front-month contract bevat "
            "roll-effecten. Bij elke doorrol springt de prijs naar het volgende "
            "contract, en dat is geen echt rendement. Dit moeten we in fase 2 "
            "controleren op uitschieters rond rolldata."
        ),
        expected_sign="n.v.t. (afhankelijke variabele)",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=0,
        units="USD per troy ounce",
        transform_hint="log-rendement",
    ),
    SeriesSpec(
        code="SI=F",
        name="silver_futures",
        source=Source.YFINANCE,
        description="COMEX zilver-futures, front-month continu contract.",
        rationale=(
            "Zilver is deels een edelmetaal en deels een industrieel metaal. Het "
            "verschil tussen goud- en zilverrendementen scheidt daarmee de "
            "'monetaire vraag' van de 'industriële vraag'. Vooral nuttig als "
            "diagnostiek: beweegt goud omdat beleggers naar veilige havens "
            "vluchten, of beweegt de hele edelmetaalcomplex mee met de "
            "industriële cyclus?"
        ),
        expected_sign="+",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=0,
        units="USD per troy ounce",
        transform_hint="log-rendement",
        optional=True,
    ),
    SeriesSpec(
        code="^VIX",
        name="vix",
        source=Source.YFINANCE,
        description="CBOE Volatility Index: impliciete 30-daags volatiliteit op de S&P 500.",
        rationale=(
            "De standaardmaat voor marktangst. Goud wordt vaak als veilige haven "
            "gekocht tijdens aandelenstress. Kanttekening die je moet kunnen "
            "maken: dat veilige-havenverband is niet stabiel. In een acute "
            "liquiditeitscrisis (maart 2020, oktober 2008) wordt goud juist "
            "verkocht omdat het liquide is en beleggers cash nodig hebben om "
            "margestortingen te doen. De rolling correlaties in fase 2 zouden "
            "dat zichtbaar moeten maken — en dat is precies waarom we ze doen."
        ),
        expected_sign="+",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=0,
        units="index (jaarlijkse volatiliteit in procenten)",
        transform_hint="log-niveau of eerste verschil",
    ),
    SeriesSpec(
        code="^GSPC",
        name="sp500",
        source=Source.YFINANCE,
        description="S&P 500 index, dagelijkse slotkoers.",
        rationale=(
            "De brede aandelenmarkt, als maat voor de risicobereidheid. Dient "
            "ook als benchmark: de correlatie tussen goud en aandelen bepaalt "
            "hoeveel diversificatiewaarde goud in een portefeuille heeft. Die "
            "correlatie schommelt historisch rond nul, wat het interessanter "
            "maakt dan een stabiel verband: het gemiddelde verbergt periodes "
            "van sterk positieve en sterk negatieve samenhang."
        ),
        expected_sign="?",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=0,
        units="indexpunten",
        transform_hint="log-rendement",
    ),
    SeriesSpec(
        code="DX-Y.NYB",
        name="dxy",
        source=Source.YFINANCE,
        description="ICE US Dollar Index (DXY).",
        rationale=(
            "Een tweede dollarmaatstaf naast DTWEXBGS. De DXY weegt zwaar naar "
            "de euro (circa 58%) en bevat geen enkele opkomende markt, terwijl "
            "DTWEXBGS handelsgewogen is en China wel meeneemt. We halen beide "
            "op om te kunnen laten zien dat de keuze van dollarmaatstaf "
            "uitmaakt — een robuustheidscheck, geen tweede regressor. Ze samen "
            "in één regressie stoppen is een multicollineariteitsfout."
        ),
        expected_sign="-",
        revision=RevisionBehaviour.NEVER_REVISED,
        publication_lag_days=0,
        units="index",
        transform_hint="log-rendement",
        optional=True,
    ),
)


ALL_SERIES: tuple[SeriesSpec, ...] = FRED_SERIES + YFINANCE_SERIES


def series_by_name(name: str) -> SeriesSpec:
    """Zoekt een reeksdefinitie op via de leesbare naam."""
    for spec in ALL_SERIES:
        if spec.name == name:
            return spec
    raise KeyError(f"Onbekende reeks: {name!r}")


def core_series() -> tuple[SeriesSpec, ...]:
    """Geeft alleen de niet-optionele reeksen terug.

    De kernset is wat het basismodel gebruikt; optionele reeksen zijn er voor
    robuustheidschecks en uitbreidingen.
    """
    return tuple(spec for spec in ALL_SERIES if not spec.optional)


# --------------------------------------------------------------------------
# Standaardinstellingen voor het ophalen
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FetchSettings:
    """Instellingen voor de ophaallaag.

    Attributen:
        start_date: Vroegste observatiedatum die we opvragen. 2003-01-01 is
            gekozen omdat DFII10 (10-jaars TIPS) pas vanaf begin 2003 een
            betrouwbare doorlopende reeks is. Eerder beginnen levert een
            paneel op waarin de belangrijkste driver ontbreekt.
        cache_ttl_hours: Hoe lang een gecachet bestand als vers geldt. 12 uur
            betekent in de praktijk: één keer ophalen per werkdag.
        stale_fallback: Bij een netwerkfout of API-storing een verlopen
            cachebestand alsnog gebruiken in plaats van falen. Dit is de
            graceful degradation uit je hedging-tool.
        max_retries: Aantal nieuwe pogingen bij een mislukte netwerkcall.
        retry_backoff_seconds: Basiswachttijd, exponentieel oplopend.
    """

    start_date: str = "2003-01-01"
    end_date: str | None = None  # None = tot vandaag
    cache_ttl_hours: float = 12.0
    stale_fallback: bool = True
    max_retries: int = 3
    retry_backoff_seconds: float = 1.5


DEFAULT_FETCH_SETTINGS = FetchSettings()
