"""Dekkingstoetsen: doet een bufferregel wat hij belooft?

De vraag
--------
Een buffer die "99% dekking" belooft, moet in ongeveer 1% van de perioden
doorbroken worden. Twee dingen kunnen misgaan:

1. **Het aantal klopt niet.** Te veel overschrijdingen betekent een te
   optimistisch model; te weinig betekent onnodig vastgelegd kapitaal. Dat
   toetst Kupiec.

2. **Het aantal klopt maar de timing niet.** Vijf overschrijdingen verspreid
   over twintig jaar is iets anders dan vijf in dezelfde maand. Clustering
   betekent dat het model de dynamiek mist, ook als het gemiddelde klopt. Dat
   toetst Christoffersen.

Beide toetsen samen heten de *conditional coverage* toets. Je hebt ze allebei
nodig: een model kan de ene halen en de andere niet.

De waarschuwing die overal bij hoort
------------------------------------
Bij 94 kwartalen en een drempel van 99% verwacht je **0,94** overschrijdingen.
Met zulke aantallen heeft geen enkele toets kracht: je kunt vrijwel niets
afwijzen. Elke uitkomst in deze module krijgt daarom zijn N mee, en een
expliciet label UNDERPOWERED zodra dat telt.

Dat is geen tekortkoming van de opzet maar van de hoeveelheid data. 23 jaar
levert nu eenmaal 94 onafhankelijke kwartalen op.

Twee getallen, en waarom ze verschillen
---------------------------------------
- **94** = 5.959 handelsdagen / 63. Het rekenkundige maximum aan
  niet-overlappende kwartalen dat in de data past.
- **78** = wat er overblijft om te TOETSEN. De eerste 1.000 dagen gaan op aan
  het schatten van het model vóór het eerste beslismoment (januari 2007). Die
  dagen kun je niet ook nog als uitkomst gebruiken; dat zou look-ahead zijn.

Waar deze module een dekkingstoets uitvoert is N dus 78, niet 94. Het getal
94 staat in de projectdocumentatie als maat voor de onafhankelijke
steekproefomvang van de data zelf. Beide kloppen, ze beantwoorden een andere
vraag. ``n_periods`` in ``CoverageResult`` is altijd het getoetste aantal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats as sps

# Onder dit aantal waarnemingen noemen we een resultaat onderbemeten.
UNDERPOWERED_THRESHOLD = 30


@dataclass
class CoverageResult:
    """Uitkomst van de dekkingstoetsen voor één bufferregel.

    Attributen:
        label: Naam van de regel.
        n_periods: Aantal getoetste perioden. **Altijd rapporteren.**
        n_breaches: Aantal keer dat de buffer doorbroken werd.
        expected_breaches: Hoeveel er verwacht werden bij het beloofde niveau.
        kupiec_lr: Likelihood-ratio van de Kupiec-toets.
        kupiec_p: Bijbehorende p-waarde.
        christoffersen_lr: Likelihood-ratio van de onafhankelijkheidstoets.
        christoffersen_p: Bijbehorende p-waarde.
        mean_buffer: Gemiddelde buffergrootte — de maat voor kapitaalefficiëntie.
        max_buffer: Grootste buffer die de regel ooit vroeg.
        breach_dates: Wanneer de overschrijdingen plaatsvonden.
    """

    label: str
    n_periods: int
    n_breaches: int
    expected_breaches: float
    confidence: float
    kupiec_lr: float
    kupiec_p: float
    christoffersen_lr: float
    christoffersen_p: float
    mean_buffer: float
    max_buffer: float
    breach_dates: list = field(default_factory=list)

    @property
    def is_underpowered(self) -> bool:
        """Heeft de toets genoeg waarnemingen om iets te kunnen afwijzen?

        We kijken naar het aantal VERWACHTE overschrijdingen, niet naar het
        aantal perioden. Bij 94 kwartalen op 99% verwacht je er 0,94 — en met
        minder dan een handvol verwachte gebeurtenissen kan geen enkele toets
        onderscheid maken.
        """
        return (
            self.n_periods < UNDERPOWERED_THRESHOLD
            or self.expected_breaches < 5.0
        )

    @property
    def kupiec_rejects(self) -> bool:
        """Verwerpt Kupiec het model op 5%?"""
        return bool(self.kupiec_p < 0.05)

    @property
    def christoffersen_rejects(self) -> bool:
        """Verwerpt Christoffersen onafhankelijkheid op 5%?"""
        return bool(self.christoffersen_p < 0.05)

    def as_row(self) -> dict:
        """Rij voor een vergelijkingstabel."""
        return {
            "model": self.label,
            "N": self.n_periods,
            "breaches": self.n_breaches,
            "expected": round(self.expected_breaches, 2),
            "kupiec_p": round(self.kupiec_p, 4),
            "christoffersen_p": round(self.christoffersen_p, 4),
            "mean_buffer": round(self.mean_buffer * 100, 1),
            "max_buffer": round(self.max_buffer * 100, 1),
            "underpowered": "JA" if self.is_underpowered else "nee",
        }


def kupiec_pof_test(
    n_periods: int, n_breaches: int, confidence: float = 0.99
) -> tuple[float, float]:
    """Kupiec proportion-of-failures toets (onconditionele dekking).

    Toetst of het aandeel overschrijdingen overeenkomt met 1 − confidence.
    De likelihood-ratio volgt onder de nulhypothese een chi-kwadraatverdeling
    met één vrijheidsgraad.

    Geeft terug:
        (LR-statistiek, p-waarde)
    """
    expected_rate = 1.0 - confidence
    if n_periods == 0:
        return float("nan"), float("nan")

    if n_breaches == 0:
        # Randgeval: log(0) bestaat niet, de formule vereenvoudigt.
        statistic = -2.0 * n_periods * np.log(1.0 - expected_rate)
    elif n_breaches == n_periods:
        statistic = -2.0 * n_periods * np.log(expected_rate)
    else:
        observed_rate = n_breaches / n_periods
        log_null = (n_periods - n_breaches) * np.log(1.0 - expected_rate) + (
            n_breaches * np.log(expected_rate)
        )
        log_alternative = (n_periods - n_breaches) * np.log(
            1.0 - observed_rate
        ) + n_breaches * np.log(observed_rate)
        statistic = -2.0 * (log_null - log_alternative)

    p_value = float(1.0 - sps.chi2.cdf(statistic, df=1))
    return float(statistic), p_value


def christoffersen_independence_test(
    breaches: np.ndarray,
) -> tuple[float, float]:
    """Christoffersen-toets op onafhankelijkheid van overschrijdingen.

    Het idee: als het model klopt, is de kans op een overschrijding morgen
    onafhankelijk van of er vandaag een was. Clusteren de overschrijdingen,
    dan mist het model de dynamiek — precies wat je verwacht als je
    volatiliteitsclustering negeert.

    De toets vergelijkt twee modellen voor de overgangskansen:
        nul:       P(breach | vorige breach) = P(breach | geen vorige breach)
        alternatief: die twee kansen verschillen

    Geeft terug:
        (LR-statistiek, p-waarde). NaN als er te weinig overgangen zijn om
        de kansen te schatten.
    """
    indicators = np.asarray(breaches).astype(int)
    if len(indicators) < 2:
        return float("nan"), float("nan")

    # Tel de overgangen: n_ij = van toestand i naar toestand j.
    previous = indicators[:-1]
    current = indicators[1:]
    n_00 = int(np.sum((previous == 0) & (current == 0)))
    n_01 = int(np.sum((previous == 0) & (current == 1)))
    n_10 = int(np.sum((previous == 1) & (current == 0)))
    n_11 = int(np.sum((previous == 1) & (current == 1)))

    # Zonder overschrijdingen valt er niets te toetsen.
    if (n_01 + n_11) == 0:
        return float("nan"), float("nan")

    # Overgangskansen onder het alternatief.
    pi_01 = n_01 / (n_00 + n_01) if (n_00 + n_01) > 0 else 0.0
    pi_11 = n_11 / (n_10 + n_11) if (n_10 + n_11) > 0 else 0.0
    # Gezamenlijke kans onder de nulhypothese.
    pi = (n_01 + n_11) / (n_00 + n_01 + n_10 + n_11)

    # Als een van de kansen op de rand ligt, is de log-likelihood ongedefinieerd.
    if pi in (0.0, 1.0):
        return float("nan"), float("nan")

    def _safe_log(value: float) -> float:
        """log met 0·log(0) = 0, zoals de conventie in likelihoods."""
        return float(np.log(value)) if value > 0 else 0.0

    log_null = (n_00 + n_10) * _safe_log(1.0 - pi) + (n_01 + n_11) * _safe_log(pi)
    log_alternative = (
        n_00 * _safe_log(1.0 - pi_01)
        + n_01 * _safe_log(pi_01)
        + n_10 * _safe_log(1.0 - pi_11)
        + n_11 * _safe_log(pi_11)
    )

    statistic = -2.0 * (log_null - log_alternative)
    p_value = float(1.0 - sps.chi2.cdf(statistic, df=1))
    return float(statistic), p_value


def evaluate_coverage(
    buffers: pd.Series,
    realised: pd.Series,
    *,
    label: str,
    confidence: float = 0.99,
) -> CoverageResult:
    """Toetst één bufferregel op dekking en onafhankelijkheid.

    Argumenten:
        buffers: De buffer die de regel voor elke periode voorschreef.
        realised: De werkelijk opgetreden tegenbeweging in die periode.
        label: Naam van de regel, voor de tabel.
        confidence: Het beloofde dekkingsniveau.

    Geeft terug:
        ``CoverageResult`` met beide toetsen, N, en de buffergrootte.
    """
    aligned = pd.concat(
        [buffers.rename("buffer"), realised.rename("realised")], axis=1
    ).dropna()

    breaches = (aligned["realised"] > aligned["buffer"]).to_numpy()
    n_periods = int(len(aligned))
    n_breaches = int(breaches.sum())
    expected = n_periods * (1.0 - confidence)

    kupiec_lr, kupiec_p = kupiec_pof_test(n_periods, n_breaches, confidence)
    christoffersen_lr, christoffersen_p = christoffersen_independence_test(breaches)

    return CoverageResult(
        label=label,
        n_periods=n_periods,
        n_breaches=n_breaches,
        expected_breaches=float(expected),
        confidence=confidence,
        kupiec_lr=kupiec_lr,
        kupiec_p=kupiec_p,
        christoffersen_lr=christoffersen_lr,
        christoffersen_p=christoffersen_p,
        mean_buffer=float(aligned["buffer"].mean()),
        max_buffer=float(aligned["buffer"].max()),
        breach_dates=[str(d.date()) for d in aligned.index[breaches]],
    )


# --------------------------------------------------------------------------
# De naïeve alternatieven
# --------------------------------------------------------------------------


def fixed_buffer(index: pd.Index, level: float = 0.25) -> pd.Series:
    """Een vaste buffer, ongeacht de markt.

    De simpelste regel die er is, en de eerlijke benchmark voor een model dat
    zegt mee te bewegen met de omstandigheden. Als een vaste 25% dezelfde
    dekking haalt met minder kapitaal, voegt het model niets toe.
    """
    return pd.Series(level, index=index, name="fixed")


def rolling_percentile_buffer(
    returns: pd.Series,
    period_starts: pd.Index,
    *,
    horizon_days: int,
    lookback_days: int = 504,
    confidence: float = 0.99,
) -> pd.Series:
    """Het historische percentiel over een voortschrijdend venster.

    Op elk beslismoment: kijk naar de afgelopen twee jaar, bereken de
    tegenbewegingen die zich daarin voordeden over dezelfde horizon, en neem
    het gevraagde percentiel.

    Puur historisch, geen modelaanname. Dat maakt het een sterke benchmark:
    het is wat een voorzichtige handelaar zonder model zou doen.

    Belangrijk: alleen data van VOOR het beslismoment wordt gebruikt.
    """
    values = returns.dropna()
    buffers = {}

    for start in period_starts:
        history = values.loc[values.index < start]
        if len(history) < lookback_days:
            continue
        window = history.iloc[-lookback_days:]

        # Alle tegenbewegingen over `horizon_days` binnen dat venster.
        excursions = []
        array = window.to_numpy()
        for offset in range(len(array) - horizon_days):
            path = np.concatenate([[0.0], np.cumsum(array[offset : offset + horizon_days])])
            excursions.append(float(np.expm1(path.max())))
        if excursions:
            buffers[start] = float(np.percentile(excursions, confidence * 100))

    return pd.Series(buffers, name="rolling_pct").sort_index()


def ewma_buffer(
    returns: pd.Series,
    period_starts: pd.Index,
    *,
    horizon_days: int,
    lambda_: float = 0.94,
    confidence: float = 0.99,
) -> pd.Series:
    """RiskMetrics: exponentieel gewogen volatiliteit, normale staarten.

    De industriestandaard van J.P. Morgan uit de jaren negentig, en nog steeds
    de meest gebruikte eenvoudige volatiliteitsschatter:

        sigma^2_t = lambda * sigma^2_{t-1} + (1 - lambda) * r^2_{t-1}

    Met lambda = 0,94 voor dagelijkse data. Dit is GARCH's directe voorganger
    en de eerlijkste vergelijking: het beweegt ook mee met de markt, maar
    gebruikt een normale verdeling en schat geen parameters.

    De buffer schaalt met de wortel van de horizon, en gebruikt het normale
    kwantiel — precies de twee aannames die fase 1 weerlegde. Als GARCH-t niet
    van deze benchmark wint, voegen die correcties niets toe.

    De buffer dekt het MAXIMUM van het pad, niet het eindpunt; zie
    ``max_excursion_buffer``. Zo meet deze regel hetzelfde als de GARCH-buffer
    en als de werkelijke uitkomst waartegen alle regels getoetst worden.
    """
    values = returns.dropna()
    buffers = {}

    for start in period_starts:
        history = values.loc[values.index < start]
        if len(history) < 100:
            continue

        array = history.to_numpy()
        variance = float(np.var(array[:100]))
        for observation in array[100:]:
            variance = lambda_ * variance + (1.0 - lambda_) * observation**2

        buffers[start] = max_excursion_buffer(
            float(np.sqrt(variance)), horizon_days, confidence
        )

    return pd.Series(buffers, name="ewma").sort_index()


def max_excursion_buffer(
    daily_sigma: float, horizon_days: int, confidence: float = 0.99
) -> float:
    """Buffer die het maximum van een normaal pad zonder drift dekt.

    Waarom niet z_0,99 * sigma * wortel(h)
    --------------------------------------
    Dat is het kwantiel van de beweging aan het EIND van de horizon. Een
    margin call komt onderweg, dus elke regel wordt getoetst tegen de
    grootste beweging TIJDENS het kwartaal, en die is nooit kleiner dan het
    eindpunt. Met z_0,99 dekt deze regel het maximum maar in ongeveer 98% van
    de paden: een nadeel dat niets met de volatiliteitsschatting te maken heeft.

    Het reflectieprincipe: voor een random walk zonder drift geldt
    P(max >= b) = 2 * P(eind >= b). Voor 99% dekking van het maximum moet
    P(eind >= b) dus 0,5% zijn, en het kwantiel wordt z_0,995 = 2,576.

    Dat is exact voor een continu pad. Bij 63 dagslotkoersen mist de reeks de
    pieken tussen twee slotkoersen, zodat de dekking iets hoger uitkomt:
    ongeveer 99,2% in plaats van 99,0%.

    Argumenten:
        daily_sigma: Volatiliteit per dag, als log-rendement.
        horizon_days: Lengte van de horizon in handelsdagen.
        confidence: Gewenste dekking van het maximum.

    Geeft terug:
        De buffer als fractie van de notionele waarde: exp(z * sigma * wortel(h)) - 1.
    """
    z_score = float(sps.norm.ppf(1.0 - (1.0 - confidence) / 2.0))
    return float(np.expm1(z_score * daily_sigma * np.sqrt(horizon_days)))


def compare_buffer_rules(
    rules: dict[str, pd.Series],
    realised: pd.Series,
    *,
    confidence: float = 0.99,
) -> tuple[pd.DataFrame, dict[str, CoverageResult]]:
    """Vergelijkt meerdere bufferregels op dezelfde perioden.

    De winnaar moet op TWEE dingen winnen:
      1. dekking — de toetsen niet verwerpen
      2. kapitaalefficiëntie — een lagere gemiddelde buffer

    Een regel die de dekking haalt met een enorme buffer is geen winnaar; die
    legt onnodig kapitaal vast. Een regel met een kleine buffer die de dekking
    mist, ook niet.

    Geeft terug:
        (vergelijkingstabel, resultaten per regel)
    """
    results = {}
    for label, buffers in rules.items():
        results[label] = evaluate_coverage(
            buffers, realised, label=label, confidence=confidence
        )

    table = pd.DataFrame([r.as_row() for r in results.values()])
    return table, results
