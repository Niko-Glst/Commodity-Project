"""Fase 4: Monte Carlo-simulatie van goudprijspaden.

Wat dit doet
------------
In plaats van te voorspellen WAAR de goudprijs heen gaat, simuleren we
duizenden mogelijke paden en kijken we naar de verdeling van de uitkomsten.
De output is expliciet geen puntvoorspelling maar een kansverdeling.

Waarom dat mag terwijl fase 3 concludeerde dat goud onvoorspelbaar is
-------------------------------------------------------------------
Dat is precies het punt. Fase 3 toonde dat de RICHTING niet te voorspellen is.
Een simulatie voorspelt de richting ook niet: elk pad is toeval. Wat we wel
gebruiken is de GROOTTE van de bewegingen, en die is aantoonbaar voorspelbaar
(autocorrelatie van de volatiliteit 0,98).

Voor de margevraag is dat genoeg. Je hoeft niet te weten of goud stijgt of
daalt; je moet weten hoe groot de tegenbeweging kan zijn.

De drie modellen, van simpel naar realistisch
---------------------------------------------
1. **GBM met normale schokken** — het standaardmodel (Black-Scholes). Twee
   aannames die fase 1 weerlegde: normaal verdeelde schokken (kurtosis 6,5
   zegt nee) en constante volatiliteit (clustering zegt nee). We beginnen
   ermee als referentie, zodat we kunnen laten zien wat de verbeteringen
   opleveren.

2. **GBM met t-verdeelde schokken** — onderbouwd met de QQ-plot uit fase 1:
   een t-verdeling met ongeveer 3,6 vrijheidsgraden past de data veel beter.
   Dit repareert aanname 1.

3. **GARCH met t-schokken** — onderbouwd met bevinding 3 uit fase 1:
   volatiliteit clustert, dus is voorspelbaar. Dit repareert aanname 2, en
   het maakt de simulatie afhankelijk van de HUIDIGE marktomstandigheden in
   plaats van het langjarig gemiddelde.

Wat we meten per pad
--------------------
Voor een margevraag is de eindwaarde niet interessant. Wat telt is de grootste
TUSSENTIJDSE tegenbeweging: de piek van het verlies onderweg, want dáár komt de
margin call. Dat heet de maximum adverse excursion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats as sps

TRADING_DAYS_PER_YEAR = 252


@dataclass
class SimulationSettings:
    """Instellingen voor een simulatie.

    Attributen:
        n_paths: Aantal gesimuleerde paden. Meer paden geven een stabielere
            schatting van de staartpercentielen; bij 10.000 paden zit de
            99%-grens op ongeveer 100 waarnemingen, wat de minimale
            hoeveelheid is om hem zinvol te schatten.
        horizon_days: Aantal handelsdagen vooruit. 63 is ongeveer een
            kwartaal.
        seed: Toevalszaad, zodat een run reproduceerbaar is. Zonder vast zaad
            krijg je elke keer andere getallen en kun je een resultaat niet
            natrekken.
        is_short: True voor een short positie. Bepaalt welke kant van de
            verdeling het verlies is.
        include_drift: Of het historische gemiddelde rendement meegenomen
            wordt. Zie de uitleg hieronder — dit is een inhoudelijke keuze,
            geen technisch detail.

    Over de drift
    -------------
    Het gemiddelde dagrendement van goud was +0,043%, oftewel +2,7% over een
    kwartaal. Neem je dat mee in de simulatie, dan drijft elke prijs gemiddeld
    omhoog — en bij een SHORT positie is omhoog precies de verkeerde kant. De
    99%-VaR stijgt daardoor met ruim 3 procentpunt.

    Waarom we de drift standaard WEGLATEN:

    1. **Fase 3 toonde dat de richting onvoorspelbaar is.** Een historisch
       gemiddelde van 23 jaar als voorspelling voor het komende kwartaal
       gebruiken, is precies de aanname die daar weerlegd werd.
    2. **Het gemiddelde is zeer onnauwkeurig geschat.** Met een dagelijkse
       standaardafwijking van 1,15% en 5.957 waarnemingen is de standaardfout
       van het gemiddelde 0,015% — een derde van de schatting zelf. Het
       95%-betrouwbaarheidsinterval loopt van ongeveer +0,013% tot +0,072%,
       dus zelfs het teken is beter bepaald dan de grootte.
    3. **Het is een uitspraak over de toekomst die we niet willen doen.** Het
       project belooft expliciet geen puntvoorspelling; een drift van +2,7%
       per kwartaal inbouwen is er stilletjes toch een.

    Zet ``include_drift=True`` om het effect te zien. Voor een risicomaat is
    nul de conservatieve en verdedigbare keuze.
    """

    n_paths: int = 10_000
    horizon_days: int = 63
    seed: int = 42
    is_short: bool = True
    include_drift: bool = False


@dataclass
class PathStatistics:
    """Samenvattende statistieken van een set gesimuleerde paden.

    Attributen:
        final_returns: Het cumulatieve rendement aan het eind van elk pad.
        max_adverse: Per pad de grootste tussentijdse beweging TEGEN de
            positie in. Dit is het getal dat de margebehoefte bepaalt.
        model_name: Welk model de paden genereerde.
        settings: De gebruikte instellingen.
    """

    final_returns: np.ndarray
    max_adverse: np.ndarray
    model_name: str
    settings: SimulationSettings
    # Een steekproef van de cumulatieve paden, voor de fan chart. We bewaren
    # niet alle paden: bij 20.000 paden x 64 dagen is dat onnodig veel
    # geheugen voor een figuur die maar een paar honderd lijnen toont.
    path_sample: np.ndarray | None = None
    percentile_bands: dict[str, np.ndarray] = field(default_factory=dict)

    def percentiles(self, levels: tuple[float, ...] = (50, 90, 95, 99, 99.9)) -> pd.DataFrame:
        """Percentielen van de eindwaarde en van de tussentijdse tegenbeweging."""
        rows = []
        for level in levels:
            rows.append(
                {
                    "percentiel": level,
                    "eindrendement_pct": float(
                        np.percentile(self.final_returns, level) * 100
                    ),
                    "max_tegenbeweging_pct": float(
                        np.percentile(self.max_adverse, level) * 100
                    ),
                }
            )
        return pd.DataFrame(rows)

    def value_at_risk(self, confidence: float = 0.99) -> float:
        """Value-at-Risk: de grens die met ``confidence`` niet overschreden wordt.

        Voor een short positie is het verlies een prijsSTIJGING, dus nemen we
        het bovenste percentiel van de tegenbeweging.
        """
        return float(np.percentile(self.max_adverse, confidence * 100))

    def expected_shortfall(self, confidence: float = 0.99) -> float:
        """Expected Shortfall: het gemiddelde verlies ALS je de VaR overschrijdt.

        Dit repareert de bekende zwakte van VaR. Een 99%-VaR van 10% is
        verenigbaar met een verlies van 11% in het slechtste procent, maar ook
        met 40%. ES vertelt je welke van de twee het is.

        Sinds Basel III de voorkeursmaat voor banken, om precies die reden.
        """
        threshold = self.value_at_risk(confidence)
        beyond = self.max_adverse[self.max_adverse >= threshold]
        if beyond.size == 0:
            return threshold
        return float(beyond.mean())


def _summarise_paths(
    cumulative: np.ndarray, *, n_sample: int = 200
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Bewaart een steekproef van de paden plus de percentielband per dag.

    De fan chart heeft twee dingen nodig: een paar honderd individuele paden
    om de spreiding te laten zien, en de percentielen per dag om de band te
    tekenen. Alle paden bewaren is zonde van het geheugen.
    """
    sample = cumulative[: min(n_sample, cumulative.shape[0])]
    bands = {
        f"p{level:g}": np.percentile(cumulative, level, axis=0)
        for level in (1, 5, 25, 50, 75, 95, 99)
    }
    return sample, bands


def _effective_drift(daily_mean: float, settings: SimulationSettings) -> float:
    """Geeft de te gebruiken drift terug, afhankelijk van de instelling.

    Zie de uitleg bij ``SimulationSettings.include_drift``: standaard nul,
    omdat fase 3 aantoonde dat de richting niet voorspelbaar is en het
    historische gemiddelde te onnauwkeurig geschat is om als voorspelling te
    dienen.
    """
    return daily_mean if settings.include_drift else 0.0


def _adverse_excursion(paths: np.ndarray, *, is_short: bool) -> np.ndarray:
    """Berekent per pad de grootste tussentijdse beweging tegen de positie in.

    ``paths`` heeft vorm (n_paths, horizon+1) en bevat cumulatieve
    log-rendementen, beginnend bij nul.

    Voor een SHORT positie is een prijsstijging ongunstig, dus zoeken we het
    maximum van het cumulatieve rendement. Voor een LONG het minimum, en dan
    geven we de absolute waarde terug zodat "meer is erger" altijd geldt.

    We werken met het cumulatieve pad en niet met de eindwaarde, omdat een
    margin call onderweg komt. Een pad dat halverwege 30% tegen je in staat en
    daarna terugkomt, heeft je wel degelijk uitgestopt.
    """
    if is_short:
        worst_log = np.max(paths, axis=1)
        return np.expm1(worst_log)
    worst_log = np.min(paths, axis=1)
    return np.abs(np.expm1(worst_log))


def simulate_gbm_normal(
    daily_mean: float,
    daily_volatility: float,
    settings: SimulationSettings | None = None,
) -> PathStatistics:
    """Geometrisch Brownse beweging met normaal verdeelde schokken.

    Het standaardmodel, en de referentie waartegen we de verbeteringen meten.

    Elke dag is het log-rendement:
        r_t = mu + sigma * z_t,   z_t ~ normaal(0, 1)

    De aanname die hier fout is: fase 1 vond een exces-kurtosis van 6,5 en 78
    dagen buiten drie standaardafwijkingen waar de normale verdeling er 16
    voorspelt. Dit model onderschat het staartrisico dus systematisch — en
    precies dat risico bepaalt de margebehoefte.
    """
    settings = settings or SimulationSettings()
    rng = np.random.default_rng(settings.seed)

    shocks = rng.standard_normal((settings.n_paths, settings.horizon_days))
    daily_returns = _effective_drift(daily_mean, settings) + daily_volatility * shocks

    cumulative = np.concatenate(
        [np.zeros((settings.n_paths, 1)), np.cumsum(daily_returns, axis=1)], axis=1
    )

    sample, bands = _summarise_paths(cumulative)
    return PathStatistics(
        final_returns=np.expm1(cumulative[:, -1]),
        max_adverse=_adverse_excursion(cumulative, is_short=settings.is_short),
        model_name="GBM normaal",
        settings=settings,
        path_sample=sample,
        percentile_bands=bands,
    )


def simulate_gbm_student_t(
    daily_mean: float,
    daily_volatility: float,
    degrees_of_freedom: float,
    settings: SimulationSettings | None = None,
) -> PathStatistics:
    """GBM met t-verdeelde schokken: dikke staarten.

    Zelfde opzet als hierboven, maar de schokken komen uit een t-verdeling in
    plaats van een normale.

    Belangrijk detail: een t-verdeling met ``df`` vrijheidsgraden heeft
    variantie df/(df-2), dus GROTER dan 1. Zouden we hem ongeschaald
    gebruiken, dan simuleren we een hogere volatiliteit dan we hebben gemeten
    en is de vergelijking met het normale model niet eerlijk. We schalen hem
    daarom terug naar variantie 1.

    Dat vereist df > 2. Bij de geschatte 3,6 vrijheidsgraden gaat dat net
    goed, maar het is een grens om te kennen: onder 2 bestaat de variantie
    niet en is deze hele aanpak zinloos.
    """
    settings = settings or SimulationSettings()
    if degrees_of_freedom <= 2:
        raise ValueError(
            f"Vrijheidsgraden moeten boven 2 liggen voor een eindige variantie; "
            f"kreeg {degrees_of_freedom}."
        )

    rng = np.random.default_rng(settings.seed)
    raw = rng.standard_t(degrees_of_freedom, (settings.n_paths, settings.horizon_days))
    # Terugschalen naar variantie 1, zodat sigma betekent wat het zegt.
    scaled = raw / np.sqrt(degrees_of_freedom / (degrees_of_freedom - 2))
    daily_returns = (
        _effective_drift(daily_mean, settings) + daily_volatility * scaled
    )

    cumulative = np.concatenate(
        [np.zeros((settings.n_paths, 1)), np.cumsum(daily_returns, axis=1)], axis=1
    )

    sample, bands = _summarise_paths(cumulative)
    return PathStatistics(
        final_returns=np.expm1(cumulative[:, -1]),
        max_adverse=_adverse_excursion(cumulative, is_short=settings.is_short),
        model_name=f"GBM t (df={degrees_of_freedom:.1f})",
        settings=settings,
        path_sample=sample,
        percentile_bands=bands,
    )


@dataclass
class GarchParameters:
    """Geschatte GARCH(1,1)-parameters.

    Het model:
        sigma^2_t = omega + alpha * eps^2_{t-1} + beta * sigma^2_{t-1}

    In woorden: de verwachte onrust van morgen is een basisniveau (omega),
    plus een deel van de klap van gisteren (alpha), plus een deel van de
    onrust van gisteren (beta).

    Attributen:
        omega: Basisniveau van de variantie.
        alpha: Gewicht van de schok van gisteren.
        beta: Gewicht van de volatiliteit van gisteren.
        degrees_of_freedom: Vrijheidsgraden van de t-verdeling voor de schokken.
        last_variance: De geschatte variantie op de laatste dag van de
            steekproef. Dit is het startpunt van de simulatie, en het is wat
            de simulatie afhankelijk maakt van de HUIDIGE markt.
        long_run_variance: Het niveau waar de variantie naartoe terugkeert:
            omega / (1 - alpha - beta).
    """

    omega: float
    alpha: float
    beta: float
    degrees_of_freedom: float
    last_variance: float
    long_run_variance: float

    @property
    def persistence(self) -> float:
        """Alpha plus beta: hoe traag een schok uitdooft.

        Bij financiële data ligt dit doorgaans tussen 0,95 en 0,99. Boven 1
        is het model niet-stationair: een schok dooft dan nooit uit en de
        variantie loopt weg. Dat is een teken dat het model of de data niet
        klopt.
        """
        return self.alpha + self.beta

    @property
    def half_life_days(self) -> float:
        """Na hoeveel dagen is de helft van een schok weggeëbd?

        Dit maakt de persistentie concreet: een halfwaardetijd van 30 dagen
        betekent dat een volatiliteitspiek een maand later nog half zo groot
        is.
        """
        if self.persistence >= 1.0:
            return float("inf")
        return float(np.log(0.5) / np.log(self.persistence))


def fit_garch(returns: pd.Series, *, distribution: str = "t") -> GarchParameters:
    """Schat een GARCH(1,1)-model op de rendementen.

    We gebruiken de ``arch``-bibliotheek. De rendementen worden met 100
    vermenigvuldigd omdat die bibliotheek numeriek stabieler is op
    percentages dan op fracties; we schalen de uitkomst terug.

    Argumenten:
        returns: Dagelijkse log-rendementen (als fractie, niet als procent).
        distribution: 't' voor Student-t schokken, 'normal' voor normale.
            De t is hier de juiste keuze, om dezelfde reden als in fase 1.
    """
    from arch import arch_model

    scaled = returns.dropna() * 100.0
    model = arch_model(
        scaled, vol="GARCH", p=1, q=1, dist=distribution, mean="Constant"
    )
    fitted = model.fit(disp="off", show_warning=False)

    parameters = fitted.params
    omega = float(parameters["omega"]) / 10_000.0
    alpha = float(parameters["alpha[1]"])
    beta = float(parameters["beta[1]"])

    if distribution == "t":
        degrees_of_freedom = float(parameters["nu"])
    else:
        degrees_of_freedom = float("inf")

    last_variance = float(fitted.conditional_volatility.iloc[-1] ** 2) / 10_000.0
    persistence = alpha + beta
    long_run = omega / (1.0 - persistence) if persistence < 1.0 else float("nan")

    return GarchParameters(
        omega=omega,
        alpha=alpha,
        beta=beta,
        degrees_of_freedom=degrees_of_freedom,
        last_variance=last_variance,
        long_run_variance=long_run,
    )


def simulate_garch(
    daily_mean: float,
    parameters: GarchParameters,
    settings: SimulationSettings | None = None,
    *,
    start_variance: float | None = None,
) -> PathStatistics:
    """Simuleert paden met tijdsvariërende volatiliteit volgens GARCH.

    Het verschil met de vorige twee modellen: de volatiliteit is niet
    constant maar evolueert per dag volgens de GARCH-vergelijking. Een grote
    schok verhoogt de volatiliteit van de volgende dag, die daarna langzaam
    terugzakt naar het langetermijnniveau.

    Dat levert twee dingen op die de andere modellen missen:

    1. **Volatiliteitsclustering** in de gesimuleerde paden, zoals in de
       echte data.
    2. **Afhankelijkheid van de startsituatie.** Begin je in een onrustige
       periode, dan zijn de eerste weken onrustiger. Dat maakt de
       margebehoefte conditioneel op de markt van vandaag in plaats van op
       het gemiddelde van 23 jaar — en dat is precies het probleem met een
       vaste vuistregel.

    Argumenten:
        start_variance: Beginvariantie. None gebruikt de laatst geschatte
            waarde uit de data (de huidige markt). Geef de
            langetermijnvariantie mee om een 'gemiddelde markt' te simuleren.
    """
    settings = settings or SimulationSettings()
    rng = np.random.default_rng(settings.seed)

    degrees_of_freedom = parameters.degrees_of_freedom
    if degrees_of_freedom <= 2:
        raise ValueError(
            "GARCH met t-schokken vereist meer dan 2 vrijheidsgraden."
        )

    variance = np.full(
        settings.n_paths,
        parameters.last_variance if start_variance is None else start_variance,
    )

    scale = np.sqrt(degrees_of_freedom / (degrees_of_freedom - 2))
    drift = _effective_drift(daily_mean, settings)
    cumulative = np.zeros((settings.n_paths, settings.horizon_days + 1))

    for day in range(settings.horizon_days):
        shocks = rng.standard_t(degrees_of_freedom, settings.n_paths) / scale
        innovations = np.sqrt(variance) * shocks
        returns_today = drift + innovations
        cumulative[:, day + 1] = cumulative[:, day] + returns_today

        # Werk de variantie bij voor morgen.
        variance = (
            parameters.omega
            + parameters.alpha * innovations**2
            + parameters.beta * variance
        )

    sample, bands = _summarise_paths(cumulative)
    return PathStatistics(
        final_returns=np.expm1(cumulative[:, -1]),
        max_adverse=_adverse_excursion(cumulative, is_short=settings.is_short),
        model_name=f"GARCH t (df={degrees_of_freedom:.1f})",
        settings=settings,
        path_sample=sample,
        percentile_bands=bands,
    )


# --------------------------------------------------------------------------
# Validatie: klopt de simulatie?
# --------------------------------------------------------------------------


def kupiec_test(
    n_observations: int, n_exceedances: int, confidence: float = 0.99
) -> dict:
    """Kupiec-toets: klopt het aantal VaR-overschrijdingen?

    Het idee: zeg je "99% VaR", dan verwacht je dat 1% van de waarnemingen de
    grens doorbreekt. Zie je er veel meer, dan is je model te optimistisch;
    veel minder, dan is het te conservatief en houd je onnodig kapitaal aan.

    De toetsingsgrootheid is een likelihood-ratio die onder de nulhypothese
    (het model klopt) een chi-kwadraatverdeling met 1 vrijheidsgraad volgt.

    Waarom dit de belangrijkste validatie van fase 4 is: een simulatie
    produceert altijd wel getallen. Deze toets is het enige dat vaststelt of
    die getallen ergens op gebaseerd zijn.
    """
    expected_rate = 1.0 - confidence
    expected_count = n_observations * expected_rate

    if n_exceedances == 0:
        # Randgeval: log(0) bestaat niet. De formule vereenvoudigt.
        statistic = -2.0 * n_observations * np.log(1.0 - expected_rate)
    else:
        observed_rate = n_exceedances / n_observations
        statistic = -2.0 * (
            (n_observations - n_exceedances) * np.log(1.0 - expected_rate)
            + n_exceedances * np.log(expected_rate)
        ) + 2.0 * (
            (n_observations - n_exceedances) * np.log(1.0 - observed_rate)
            + n_exceedances * np.log(observed_rate)
        )

    p_value = float(1.0 - sps.chi2.cdf(statistic, df=1))

    return {
        "n_observations": n_observations,
        "n_exceedances": n_exceedances,
        "expected_exceedances": float(expected_count),
        "observed_rate": n_exceedances / n_observations,
        "expected_rate": expected_rate,
        "statistic": float(statistic),
        "p_value": p_value,
        "model_accepted": p_value >= 0.05,
    }


def backtest_var(
    returns: pd.Series,
    *,
    horizon_days: int = 63,
    confidence: float = 0.99,
    window: int = 1000,
    step: int = 21,
    model: str = "garch_t",
    n_paths: int = 2000,
    seed: int = 7,
) -> dict:
    """Backtest de VaR-voorspelling walk-forward, en toets hem met Kupiec.

    Dit is de eerlijke test van fase 4, en hij volgt dezelfde discipline als
    fase 3: schat het model op data tot dag t, voorspel de VaR voor de
    volgende ``horizon_days``, en kijk achteraf of de werkelijke
    tegenbeweging binnen die grens bleef.

    Let op een beperking die je moet benoemen: de testvensters OVERLAPPEN
    elkaar (elke 21 dagen een nieuw venster van 63 dagen), dus de
    overschrijdingen zijn niet volledig onafhankelijk. De Kupiec-toets neemt
    onafhankelijkheid aan, dus de p-waarde is indicatief en niet exact. Niet
    overlappen zou betekenen dat je maar een handvol vensters overhoudt.
    """
    returns = returns.dropna()
    exceedances = 0
    tested = 0
    details = []

    for train_end in range(window, len(returns) - horizon_days, step):
        train = returns.iloc[:train_end]
        future = returns.iloc[train_end : train_end + horizon_days]

        settings = SimulationSettings(
            n_paths=n_paths, horizon_days=horizon_days, seed=seed + tested
        )
        daily_mean = float(train.mean())

        if model == "garch_t":
            try:
                parameters = fit_garch(train)
                simulated = simulate_garch(daily_mean, parameters, settings)
            except Exception:
                # GARCH convergeert niet altijd; sla dat venster over in
                # plaats van de hele backtest te laten falen.
                continue
        elif model == "gbm_t":
            degrees = float(sps.t.fit(train.values)[0])
            simulated = simulate_gbm_student_t(
                daily_mean, float(train.std()), max(degrees, 2.5), settings
            )
        else:
            simulated = simulate_gbm_normal(daily_mean, float(train.std()), settings)

        predicted_var = simulated.value_at_risk(confidence)

        # Werkelijke grootste tegenbeweging in de testperiode.
        cumulative = future.cumsum().to_numpy()
        actual_adverse = float(np.expm1(np.max(np.concatenate([[0.0], cumulative]))))

        breached = actual_adverse > predicted_var
        exceedances += int(breached)
        tested += 1
        details.append(
            {
                "datum": returns.index[train_end],
                "voorspelde_var_pct": predicted_var * 100,
                "werkelijk_pct": actual_adverse * 100,
                "overschreden": breached,
            }
        )

    kupiec = kupiec_test(tested, exceedances, confidence)
    return {
        "model": model,
        "n_windows": tested,
        "n_exceedances": exceedances,
        "kupiec": kupiec,
        "details": pd.DataFrame(details),
    }

def historical_adverse_excursion(
    returns: pd.Series, *, horizon_days: int = 63, is_short: bool = True, step: int = 5
) -> np.ndarray:
    """De werkelijk waargenomen tegenbeweging per venster, uit de echte data.

    Dit is de ijkmaat voor de simulatie. Een model dat een 99%-VaR oplevert
    die ver boven of onder de historische waarde ligt, moet dat kunnen
    verantwoorden — anders simuleer je een markt die niet bestaat.

    Let op dat de vensters overlappen (``step`` kleiner dan ``horizon_days``),
    dus de waarnemingen zijn niet onafhankelijk. Voor een ijkpunt is dat
    acceptabel; voor een formele toets niet.
    """
    values = returns.dropna().to_numpy()
    outcomes = []
    for start in range(0, len(values) - horizon_days, step):
        window = values[start : start + horizon_days]
        cumulative = np.concatenate([[0.0], np.cumsum(window)])
        if is_short:
            outcomes.append(np.expm1(cumulative.max()))
        else:
            outcomes.append(abs(np.expm1(cumulative.min())))
    return np.array(outcomes)


def compare_to_history(
    simulations: dict[str, PathStatistics],
    returns: pd.Series,
    *,
    horizon_days: int = 63,
    is_short: bool = True,
) -> pd.DataFrame:
    """Zet elke simulatie naast de werkelijk waargenomen verdeling.

    Dit is de eerlijkheidscheck van fase 4. Een simulatie produceert altijd
    getallen; deze vergelijking laat zien of ze in de buurt liggen van wat er
    echt gebeurd is.

    Een model dat te hoge waarden geeft is niet "veilig" maar duur: je houdt
    kapitaal vast dat niets doet. Een model dat te lage waarden geeft, stopt
    je uit op het verkeerde moment. Beide zijn fouten.
    """
    historical = historical_adverse_excursion(
        returns, horizon_days=horizon_days, is_short=is_short
    )
    rows = [
        {
            "bron": "historisch (echte data)",
            "n": len(historical),
            "p50": float(np.percentile(historical, 50)) * 100,
            "p95": float(np.percentile(historical, 95)) * 100,
            "p99": float(np.percentile(historical, 99)) * 100,
            "afwijking_p99_pp": 0.0,
        }
    ]
    historical_p99 = float(np.percentile(historical, 99)) * 100
    for name, result in simulations.items():
        p99 = result.value_at_risk(0.99) * 100
        rows.append(
            {
                "bron": name,
                "n": len(result.max_adverse),
                "p50": float(np.percentile(result.max_adverse, 50)) * 100,
                "p95": result.value_at_risk(0.95) * 100,
                "p99": p99,
                "afwijking_p99_pp": p99 - historical_p99,
            }
        )
    return pd.DataFrame(rows)
