"""Placebo-toetsen: hoe weet je dat een resultaat geen toeval is?

Het probleem
------------
Elk gevonden verband heeft een kans om er te zijn zonder dat er iets is. Een
p-waarde van 0,05 zegt dat die kans 5% is *voor één toets*. Maar een project
als dit doet er honderden: elf drivers, meerdere horizonnen, meerdere modellen,
meerdere subperiodes. Bij genoeg toetsen vind je gegarandeerd iets.

De oplossing is een **placebo**: draai exact dezelfde analyse op data waarin
per constructie GEEN verband zit, en kijk hoe vaak je dan toch "iets" vindt.
Dat getal is je werkelijke foutenpercentage, niet de nominale 5%.

Drie soorten placebo in dit bestand
-----------------------------------
1. **Nep-drivers** — vervang de macro-drivers door toevalsreeksen met dezelfde
   statistische eigenschappen (persistentie, volatiliteit) en kijk of het
   model dan óók iets vindt.

2. **Geschudde uitkomst** — houd de drivers intact maar schud het
   goudrendement door elkaar. Dat vernietigt elk verband in de tijd terwijl de
   verdeling identiek blijft.

3. **Nep-gebeurtenis** — toets een uitspraak over een periode waarin niets
   bijzonders gebeurde, en kijk of je "effect" daar ook uitkomt.

Wat een goede uitslag is
------------------------
Op placebodata hoort je toets ongeveer het nominale percentage te vinden: bij
een drempel van 5% ongeveer 5% "significante" uitkomsten. Vind je er veel
meer, dan is je opzet kapot — niet je data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass
class PlaceboResult:
    """Uitkomst van een placebo-experiment.

    Attributen:
        n_trials: Aantal herhalingen.
        n_significant: Hoe vaak de toets 'significant' zei.
        false_positive_rate: Aandeel daarvan.
        nominal_rate: Wat het had moeten zijn (meestal 0,05).
        real_statistic: De waarde op de ECHTE data, ter vergelijking.
        placebo_statistics: De verdeling van dezelfde grootheid op placebodata.
        label: Wat er getoetst werd.
    """

    n_trials: int
    n_significant: int
    false_positive_rate: float
    nominal_rate: float
    real_statistic: float
    placebo_statistics: np.ndarray
    label: str

    @property
    def percentile_of_real(self) -> float:
        """Waar de echte uitkomst ligt in de placeboverdeling.

        Dit is de eerlijkste maat: ligt je echte resultaat op het 50e
        percentiel van wat toeval oplevert, dan heb je niets gevonden. Ligt
        het op het 99e, dan is het opmerkelijk.
        """
        return float((self.placebo_statistics < self.real_statistic).mean() * 100)

    @property
    def is_distinguishable(self) -> bool:
        """Is het echte resultaat te onderscheiden van toeval?

        We hanteren het 95e percentiel als grens: het echte resultaat moet
        beter zijn dan 95% van wat pure toevalsdata oplevert.
        """
        return self.percentile_of_real >= 95.0


def _match_persistence(
    reference: pd.Series, rng: np.random.Generator
) -> np.ndarray:
    """Genereert een toevalsreeks met dezelfde persistentie en spreiding.

    Waarom niet gewoon witte ruis: de echte drivers zijn sterk persistent
    (renteniveaus, dollarindex). Een placebo van witte ruis zou een te
    makkelijke tegenstander zijn — je zou "significant" scoren puur doordat
    je echte driver traag beweegt en de placebo niet.

    Dit is dezelfde les als bij de spectraalanalyse in fase 1: de referentie
    moet alles delen met de echte data BEHALVE het verband dat je toetst.
    """
    values = reference.dropna().to_numpy()
    n = len(values)
    if n < 10:
        return rng.standard_normal(n)

    centred = values - values.mean()
    denominator = float(np.dot(centred[:-1], centred[:-1]))
    phi = (
        float(np.dot(centred[1:], centred[:-1]) / denominator)
        if denominator > 0
        else 0.0
    )
    phi = float(np.clip(phi, -0.999, 0.999))
    residual_std = float(np.std(centred[1:] - phi * centred[:-1]))

    path = np.empty(n)
    path[0] = centred[0]
    shocks = rng.normal(0.0, residual_std, n)
    for i in range(1, n):
        path[i] = phi * path[i - 1] + shocks[i]
    return path + values.mean()


def placebo_fake_drivers(
    target: pd.Series,
    drivers: pd.DataFrame,
    *,
    n_trials: int = 200,
    seed: int = 42,
    alpha: float = 0.05,
) -> PlaceboResult:
    """Vervangt de drivers door nepreeksen met dezelfde eigenschappen.

    De vraag: als ik mijn echte drivers vervang door toevalsreeksen die er
    statistisch hetzelfde uitzien, vindt mijn model dan óók een verband?

    Zo ja, dan meet mijn "gevonden verband" vooral de eigenschappen van de
    reeksen (persistentie, volatiliteit) en niet de economie.
    """
    rng = np.random.default_rng(seed)
    aligned = pd.concat([target, drivers], axis=1).dropna()
    y = aligned.iloc[:, 0]
    X_real = aligned.iloc[:, 1:]

    real_model = sm.OLS(y, sm.add_constant(X_real)).fit()
    real_r2 = float(real_model.rsquared)

    placebo_r2 = np.empty(n_trials)
    n_significant = 0

    for trial in range(n_trials):
        fake = pd.DataFrame(
            {
                column: _match_persistence(X_real[column], rng)
                for column in X_real.columns
            },
            index=X_real.index,
        )
        model = sm.OLS(y, sm.add_constant(fake)).fit()
        placebo_r2[trial] = float(model.rsquared)
        if float(model.f_pvalue) < alpha:
            n_significant += 1

    return PlaceboResult(
        n_trials=n_trials,
        n_significant=n_significant,
        false_positive_rate=n_significant / n_trials,
        nominal_rate=alpha,
        real_statistic=real_r2,
        placebo_statistics=placebo_r2,
        label="nep-drivers met dezelfde persistentie",
    )


def placebo_shuffled_target(
    target: pd.Series,
    drivers: pd.DataFrame,
    *,
    n_trials: int = 200,
    seed: int = 42,
    alpha: float = 0.05,
) -> PlaceboResult:
    """Schudt het goudrendement door elkaar, drivers blijven intact.

    Dit vernietigt elk verband in de TIJD terwijl de verdeling van de
    uitkomst exact hetzelfde blijft — zelfde gemiddelde, spreiding, dikke
    staarten.

    Vindt het model dan nog steeds iets, dan komt dat niet uit de koppeling
    tussen driver en uitkomst.
    """
    rng = np.random.default_rng(seed)
    aligned = pd.concat([target, drivers], axis=1).dropna()
    y = aligned.iloc[:, 0]
    X = aligned.iloc[:, 1:]

    real_r2 = float(sm.OLS(y, sm.add_constant(X)).fit().rsquared)

    placebo_r2 = np.empty(n_trials)
    n_significant = 0

    for trial in range(n_trials):
        shuffled = pd.Series(rng.permutation(y.to_numpy()), index=y.index)
        model = sm.OLS(shuffled, sm.add_constant(X)).fit()
        placebo_r2[trial] = float(model.rsquared)
        if float(model.f_pvalue) < alpha:
            n_significant += 1

    return PlaceboResult(
        n_trials=n_trials,
        n_significant=n_significant,
        false_positive_rate=n_significant / n_trials,
        nominal_rate=alpha,
        real_statistic=real_r2,
        placebo_statistics=placebo_r2,
        label="geschudde uitkomst",
    )


def effective_sample_size(series: pd.Series) -> dict:
    """Schat hoeveel ONAFHANKELIJKE waarnemingen een reeks eigenlijk bevat.

    De vraag "wat is je N?" heeft bij tijdreeksen een ongemakkelijk antwoord.
    Je hebt misschien 5.957 dagen, maar als opeenvolgende waarnemingen sterk
    samenhangen, dragen ze niet elk een volle waarneming aan informatie bij.

    De standaardcorrectie gebruikt de autocorrelaties:

        N_eff = N / (1 + 2 * som van de autocorrelaties)

    Voor rendementen (nauwelijks autocorrelatie) is N_eff bijna gelijk aan N.
    Voor niveaus of volatiliteit (sterk persistent) is hij dramatisch kleiner
    — en dat is precies waar de vraag pijnlijk wordt.
    """
    values = series.dropna().to_numpy()
    n = len(values)
    if n < 20:
        return {"n": n, "n_effective": float(n), "ratio": 1.0, "sum_acf": 0.0}

    centred = values - values.mean()
    variance = float(np.dot(centred, centred) / n)
    if variance == 0:
        return {"n": n, "n_effective": float(n), "ratio": 1.0, "sum_acf": 0.0}

    # Sommeer de autocorrelaties tot ze verwaarloosbaar worden. We kappen af
    # zodra een waarde onder de toevalsgrens zakt, want daarna is het ruis
    # optellen.
    bound = 1.96 / np.sqrt(n)
    total = 0.0
    for lag in range(1, min(n // 4, 500)):
        autocorrelation = float(
            np.dot(centred[lag:], centred[:-lag]) / (n * variance)
        )
        if abs(autocorrelation) < bound:
            break
        total += autocorrelation

    factor = 1.0 + 2.0 * total

    # Twee randgevallen afvangen.
    #
    # NEGATIEVE autocorrelatie maakt de factor kleiner dan 1, en dan komt
    # N_eff boven N uit. Wiskundig klopt dat — een reeks die systematisch
    # terugveert bevat meer informatie per waarneming dan witte ruis — maar
    # als antwoord op "wat is je N?" is het onbruikbaar: je kunt niet meer
    # onafhankelijke waarnemingen hebben dan waarnemingen. We kappen af op N.
    #
    # Een factor van nul of lager (sterke negatieve som) is een teken dat de
    # benadering niet opgaat; dan vallen we terug op N.
    if factor <= 0:
        n_effective = float(n)
    else:
        n_effective = min(n / factor, float(n))

    return {
        "n": n,
        "n_effective": float(n_effective),
        "ratio": float(n_effective / n),
        "sum_acf": float(total),
        # Bij een negatieve som is de schatting afgekapt; dat wil je weten
        # voordat je het getal citeert.
        "capped": bool(factor < 1.0),
    }


def independent_episodes(
    series: pd.Series, *, horizon_days: int
) -> dict:
    """Hoeveel NIET-OVERLAPPENDE vensters van deze lengte zitten er in?

    Bij een kwartaalhorizon is dit het getal dat telt, niet het aantal dagen.
    Overlappende vensters delen data en zijn dus niet onafhankelijk; een
    backtest die ze als los telt, overdrijft zijn eigen steekproef.
    """
    n = len(series.dropna())
    return {
        "n_days": n,
        "horizon_days": horizon_days,
        "n_non_overlapping": n // horizon_days,
        "n_overlapping": max(n - horizon_days, 0),
    }
