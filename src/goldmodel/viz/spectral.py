"""Spectraalanalyse: zit er periodiciteit in de volatiliteit?

De vraag die dit beantwoordt
----------------------------
In figuur 5 zie je dat rustige en onrustige periodes in blokken komen. De
natuurlijke vervolgvraag is: zit daar een *ritme* in? Als onrust elke zoveel
maanden terugkomt, kun je hem voorspellen met een sinusfunctie of met een
Fourier-reeks.

Wat een Fourier-transformatie doet
----------------------------------
Elke tijdreeks is te schrijven als een som van sinussen en cosinussen met
verschillende frequenties. De Fourier-transformatie berekent hoeveel van elke
frequentie erin zit. Het resultaat heet het **spectrum** of **periodogram**:
op de horizontale as staat de frequentie (of de periode: 1/frequentie), op de
verticale as hoeveel "energie" de reeks op die frequentie heeft.

Bevat je reeks een echte cyclus van bijvoorbeeld 60 dagen, dan zie je een
scherpe piek bij periode 60. Geen cyclus betekent geen piek — dan is het
spectrum een dalende curve zonder structuur.

De valkuil die dit bestand expliciet adresseert
-----------------------------------------------
Een periodogram van ruis is NIET vlak. Het schommelt fors, en de hoogste
waarde in zo'n schommeling ziet er altijd uit als "een piek". Wie zonder
referentie naar een periodogram kijkt, vindt gegarandeerd cycli die er niet
zijn. Dat is een van de oudste valkuilen in de tijdreeksanalyse — Slutsky
beschreef in 1927 al hoe het optellen van willekeurige getallen
golfachtige patronen oplevert die je ten onrechte als cyclus leest.

Daarom vergelijken we het waargenomen spectrum altijd met een
referentieverdeling die we genereren uit data zonder cyclus. Pas als een piek
daar significant bovenuit steekt, is er iets aan de hand.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy import signal as sps_signal

from goldmodel.viz.style import ROLE, annotate, save_figure


def realised_volatility(
    returns: pd.Series, *, window: int = 21, annualise: bool = True
) -> pd.Series:
    """Berekent de voortschrijdende gerealiseerde volatiliteit.

    Argumenten:
        returns: Dagelijkse log-rendementen.
        window: Aantal handelsdagen in het venster. 21 is ongeveer een
            kalendermaand.
        annualise: Vermenigvuldig met √252 zodat het getal leesbaar is als
            jaarvolatiliteit in procenten.

    Let op de keuze van het venster: die bepaalt wat je kunt zien. Met een
    venster van 21 dagen zijn cycli korter dan ongeveer 42 dagen per
    constructie uitgesmeerd — het voortschrijdend gemiddelde werkt als een
    laagdoorlaatfilter. Wie een cyclus van 10 dagen zoekt, moet een korter
    venster nemen. Dat is geen detail: het venster kan een cyclus wegpoetsen
    én er een creëren (zie ``spurious_cycle_from_smoothing``).
    """
    vol = returns.rolling(window).std()
    if annualise:
        # Maal 100 zodat de uitkomst in procentpunten staat (18,3 = 18,3%)
        # en niet als fractie. Anders lijkt een RMSE van 0,074 klein terwijl
        # het in werkelijkheid 7,4 volatiliteitspunten is.
        vol = vol * np.sqrt(252) * 100
    return vol.dropna()


def compute_periodogram(
    series: pd.Series, *, detrend: str = "constant"
) -> tuple[np.ndarray, np.ndarray]:
    """Berekent het periodogram van een reeks.

    Geeft terug:
        (periods, power) — de periodes in dagen en de bijbehorende energie.
        De frequentie nul (het gemiddelde) is weggelaten, want die zegt niets
        over cycliciteit.

    We gebruiken Welch's methode niet maar het gewone periodogram, omdat we
    de ruwe schattingsonzekerheid juist willen laten zien: die is het punt.
    """
    values = series.values.astype(float)
    frequencies, power = sps_signal.periodogram(values, detrend=detrend, scaling="density")

    # Frequentie 0 weglaten: dat is het gemiddelde, geen cyclus.
    mask = frequencies > 0
    frequencies, power = frequencies[mask], power[mask]
    periods = 1.0 / frequencies
    return periods, power


def null_distribution(
    series: pd.Series,
    *,
    n_simulations: int = 400,
    seed: int = 42,
    method: str = "ar1",
) -> np.ndarray:
    """Genereert de verdeling van periodogrammen onder 'geen cyclus'.

    De keuze van deze referentie is de belangrijkste beslissing in de hele
    analyse, en het is waar de meeste cyclus-'ontdekkingen' stuklopen.

    ``method="shuffle"`` — permutatie
        Schudt de waarnemingen door elkaar. Behoudt de verdeling exact, maar
        vernietigt *alle* volgorde-informatie: zowel de cyclus die we zoeken
        als de persistentie die we al kennen.

        **Dit is een stroman.** De volatiliteit is sterk persistent
        (autocorrelatie boven 0,98). Een persistente reeks heeft van nature
        veel energie op lage frequenties — niet omdat er een cyclus is, maar
        omdat hij traag beweegt. Tegen een geschudde referentie steekt die
        energie er altijd bovenuit, en dan "vind" je een cyclus met een
        periode van duizenden dagen die niets anders is dan de trage drift
        van de reeks. Deze optie zit erin om dat te kunnen laten zien.

    ``method="ar1"`` — persistente referentie (standaard)
        Simuleert een AR(1)-proces met dezelfde eerste-orde autocorrelatie,
        hetzelfde gemiddelde en dezelfde residuele spreiding als de echte
        reeks. Een AR(1) is per constructie persistent maar heeft *geen*
        cyclus: de autocorrelatie daalt exponentieel en wordt nooit negatief.

        Zo toetsen we precies de goede vraag: heeft de volatiliteit méér
        structuur op een bepaalde frequentie dan een traag maar ritmeloos
        proces zou hebben?

    Geeft terug:
        Array van vorm (n_simulations, n_frequenties) met de energie per
        simulatie.
    """
    rng = np.random.default_rng(seed)
    values = series.values.astype(float)
    n = len(values)
    simulated = []

    if method == "shuffle":
        for _ in range(n_simulations):
            shuffled = rng.permutation(values)
            _, power = sps_signal.periodogram(
                shuffled, detrend="constant", scaling="density"
            )
            simulated.append(power[1:])
        return np.array(simulated)

    if method != "ar1":
        raise ValueError(f"Onbekende methode: {method!r}. Kies 'ar1' of 'shuffle'.")

    # AR(1) schatten: x_t - mu = phi * (x_{t-1} - mu) + e_t
    mean = float(values.mean())
    centred = values - mean
    phi = float(np.dot(centred[1:], centred[:-1]) / np.dot(centred[:-1], centred[:-1]))
    residual_std = float(np.std(centred[1:] - phi * centred[:-1]))

    # Vectoriseer over de simulaties: alle paden tegelijk opbouwen scheelt
    # een factor honderd ten opzichte van een Python-lus per pad. De
    # recursie over de tijd blijft (die is inherent sequentieel), maar draait
    # nu op arrays van n_simulations in plaats van op losse getallen.
    shocks = rng.normal(0.0, residual_std, size=(n_simulations, n))
    paths = np.empty((n_simulations, n))
    paths[:, 0] = centred[0]
    for t in range(1, n):
        paths[:, t] = phi * paths[:, t - 1] + shocks[:, t]

    _, power = sps_signal.periodogram(
        paths + mean, detrend="constant", scaling="density", axis=-1
    )
    return power[:, 1:]


def fit_sine(series: pd.Series, period_days: float) -> tuple[np.ndarray, float]:
    """Past een sinus met vaste periode op de reeks en geeft de R² terug.

    We doen dit met lineaire regressie op sin(2πt/T) en cos(2πt/T). Die
    combinatie kan elke fase aannemen, dus we hoeven de fase niet apart te
    schatten — dat is de standaardtruc bij harmonische regressie.

    Geeft terug:
        (voorspelling, r_squared)
    """
    values = series.values.astype(float)
    t = np.arange(len(values), dtype=float)

    design = np.column_stack(
        [
            np.ones_like(t),
            np.sin(2 * np.pi * t / period_days),
            np.cos(2 * np.pi * t / period_days),
        ]
    )
    coefficients, *_ = np.linalg.lstsq(design, values, rcond=None)
    fitted = design @ coefficients

    ss_residual = float(np.sum((values - fitted) ** 2))
    ss_total = float(np.sum((values - values.mean()) ** 2))
    r_squared = 1.0 - ss_residual / ss_total
    return fitted, r_squared


def spurious_cycle_from_smoothing(
    *, n: int = 6000, window: int = 21, seed: int = 7
) -> tuple[np.ndarray, np.ndarray]:
    """Toont dat een voortschrijdend gemiddelde een cyclus *creëert*.

    Dit is het Slutsky-Yule-effect. Neem volstrekt onafhankelijke ruis —
    geen enkele structuur — en pas er een voortschrijdend gemiddelde op toe.
    Het resultaat vertoont golven met een karakteristieke lengte, en een
    periodogram van die gladgestreken reeks laat een piek zien.

    Die piek komt niet uit de data maar uit het filter. Dat is direct
    relevant voor ons: de volatiliteitsreeks is zélf een voortschrijdend
    gemiddelde (van kwadraten), dus elke piek moet je tegen dit effect
    afzetten voordat je hem als bevinding presenteert.
    """
    rng = np.random.default_rng(seed)
    pure_noise = rng.standard_normal(n)
    smoothed = pd.Series(pure_noise).rolling(window).mean().dropna().values
    return pure_noise, smoothed


# --------------------------------------------------------------------------
# Figuren
# --------------------------------------------------------------------------


def plot_volatility_spectrum(
    returns: pd.Series,
    *,
    window: int = 21,
    filename: str = "07_volatiliteit_spectrum.png",
) -> tuple[object, dict]:
    """Periodogram van de gerealiseerde volatiliteit met een referentieband.

    Links: het spectrum met de 95%-band onder 'geen cyclus'. Rechts: de
    volatiliteitsreeks zelf met de best passende sinus erover.
    """
    vol = realised_volatility(returns, window=window)
    periods, power = compute_periodogram(vol)
    null_power = null_distribution(vol, method="ar1")
    shuffled_power = null_distribution(vol, method="shuffle", n_simulations=200)

    # 95e percentiel per frequentie: de grens waarboven 5% van de
    # cyclusloze simulaties uitkomt.
    upper_band = np.percentile(null_power, 95, axis=0)
    median_band = np.percentile(null_power, 50, axis=0)
    shuffled_band = np.percentile(shuffled_power, 95, axis=0)

    # Zoek de piek binnen een zinvol bereik: tussen 10 dagen en een kwart
    # van de reekslengte. Langere periodes zijn niet te schatten omdat er
    # te weinig herhalingen in de data zitten.
    valid = (periods >= 10) & (periods <= len(vol) / 4)

    # Selecteer op de VERHOUDING tot de referentieband, niet op ruwe energie.
    # Dat is essentieel: bij een persistente reeks is de ruwe energie altijd
    # het hoogst op de laagste frequentie, dus "de sterkste piek" zou dan
    # niets anders zijn dan de trage drift van de reeks. Wat we zoeken is een
    # frequentie waar de data méér energie heeft dan een ritmeloos persistent
    # proces daar zou hebben.
    excess_ratio = power[valid] / upper_band[valid]
    peak_index = int(np.argmax(excess_ratio))
    peak_period = float(periods[valid][peak_index])
    peak_power = float(power[valid][peak_index])
    peak_threshold = float(upper_band[valid][peak_index])
    peak_ratio = float(excess_ratio[peak_index])

    fitted, r_squared = fit_sine(vol, peak_period)

    fig, (ax_spec, ax_fit) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    # -- links: het spectrum --------------------------------------------
    plot_mask = (periods >= 5) & (periods <= 2000)
    ax_spec.fill_between(
        periods[plot_mask],
        0,
        upper_band[plot_mask],
        color=ROLE["reference"],
        alpha=0.25,
        label="95%-band als er GEEN cyclus is",
    )
    ax_spec.plot(
        periods[plot_mask],
        median_band[plot_mask],
        color=ROLE["reference"],
        linewidth=1.2,
        linestyle="--",
        label="mediaan zonder cyclus",
    )
    ax_spec.plot(
        periods[plot_mask],
        shuffled_band[plot_mask],
        color=ROLE["theoretical"],
        linewidth=1.3,
        linestyle=":",
        label="95%-band van een NAÏEVE referentie (geschud)",
    )
    ax_spec.plot(
        periods[plot_mask],
        power[plot_mask],
        color=ROLE["empirical"],
        linewidth=1.1,
        label="waargenomen spectrum",
    )
    ax_spec.scatter(
        [peak_period],
        [peak_power],
        s=70,
        color=ROLE["highlight"],
        zorder=5,
        label=f"sterkste piek: {peak_period:.0f} dagen",
    )

    ax_spec.set_xscale("log")
    ax_spec.set_yscale("log")
    ax_spec.set_xlabel("Periode in handelsdagen (logaritmisch)")
    ax_spec.set_ylabel("Energie (logaritmisch)")
    ax_spec.set_title("Periodogram van de volatiliteit", fontsize=11)
    # Onderkant afkappen: de diepe dalen van het periodogram zijn ruis en
    # rekken de as over zeven ordes van grootte, waardoor de referentieband
    # onleesbaar wordt. Boven de band blijft alles zichtbaar.
    visible = power[plot_mask]
    ax_spec.set_ylim(bottom=max(float(np.percentile(visible, 2)), 1e-2))
    ax_spec.legend(loc="upper left", fontsize=7.5, ncol=1)

    annotate(
        ax_spec,
        f"Sterkste afwijking: {peak_period:.0f} dagen\n"
        f"({peak_ratio:.1f}x de grijze band)\n\n"
        "Tegen de stippellijn steekt de\n"
        "data overal bovenuit. Dat komt\n"
        "niet door een cyclus maar door\n"
        "persistentie — daarom is de\n"
        "grijze band de juiste maatstaf.",
        loc="lower right",
    )

    # -- rechts: de sinus op de data ------------------------------------
    ax_fit.plot(
        vol.index,
        vol.values,
        color=ROLE["empirical"],
        linewidth=0.8,
        alpha=0.8,
        label="gerealiseerde volatiliteit",
    )
    ax_fit.plot(
        vol.index,
        fitted,
        color=ROLE["theoretical"],
        linewidth=2.2,
        label=f"sinus met periode {peak_period:.0f} dagen",
    )
    ax_fit.set_ylabel(f"Volatiliteit ({window}d, jaarbasis, %)")
    ax_fit.set_title("De best passende sinus op de echte reeks", fontsize=11)
    ax_fit.legend(loc="upper right", fontsize=8.5)

    annotate(
        ax_fit,
        f"R² = {r_squared:.4f}\n\n"
        f"De sinus verklaart {r_squared * 100:.1f}% van\n"
        "de beweging in de volatiliteit.\n"
        "De rest is geen ritme.",
        loc="upper left",
    )

    fig.suptitle(
        "Zit er een cyclus in de volatiliteit van goud?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = save_figure(fig, filename)

    diagnostics = {
        "peak_period": peak_period,
        "peak_power": peak_power,
        "peak_threshold": peak_threshold,
        "peak_ratio": peak_ratio,
        "peak_significant": bool(peak_power > peak_threshold),
        "sine_r_squared": r_squared,
        "n_observations": int(len(vol)),
        "n_above_band": int(np.sum(power[valid] > upper_band[valid])),
        "n_above_shuffled": int(np.sum(power[valid] > shuffled_band[valid])),
        "n_frequencies_tested": int(valid.sum()),
    }
    return path, diagnostics


def plot_slutsky_effect(
    *,
    window: int = 21,
    filename: str = "08_slutsky_effect.png",
):
    """Laat zien dat gladstrijken zelf golven maakt.

    Dit is de belangrijkste waarschuwing bij spectraalanalyse van een
    voortschrijdend gemiddelde, en de reden dat we het hier expliciet
    aantonen in plaats van alleen te noemen.
    """
    raw_noise, smoothed = spurious_cycle_from_smoothing(window=window)

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8))
    ax_raw, ax_smooth = axes[0]
    ax_spec_raw, ax_spec_smooth = axes[1]

    # -- boven: de reeksen ----------------------------------------------
    ax_raw.plot(raw_noise[:800], color=ROLE["empirical"], linewidth=0.6)
    ax_raw.set_title("Pure ruis: geen enkele structuur", fontsize=11)
    ax_raw.set_ylabel("Waarde")
    ax_raw.grid(axis="y", alpha=0.4)

    ax_smooth.plot(smoothed[:800], color=ROLE["theoretical"], linewidth=1.4)
    ax_smooth.set_title(
        f"Dezelfde ruis, {window}-daags voortschrijdend gemiddelde", fontsize=11
    )
    ax_smooth.grid(axis="y", alpha=0.4)
    annotate(
        ax_smooth,
        "Hier zie je golven.\n"
        "Die zitten NIET in de data —\n"
        "ze komen uit het gladstrijken.",
        loc="upper right",
    )

    # -- onder: de spectra ----------------------------------------------
    for ax, data, color, title in (
        (ax_spec_raw, raw_noise, ROLE["empirical"], "Spectrum van de ruis"),
        (
            ax_spec_smooth,
            smoothed,
            ROLE["theoretical"],
            "Spectrum na gladstrijken",
        ),
    ):
        periods, power = compute_periodogram(pd.Series(data))
        mask = (periods >= 5) & (periods <= 500)
        ax.plot(periods[mask], power[mask], color=color, linewidth=1.1)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Periode in stappen (logaritmisch)")
        ax.set_ylabel("Energie (logaritmisch)")
        ax.set_title(title, fontsize=11)

    annotate(
        ax_spec_smooth,
        "Het filter drukt de korte periodes weg\n"
        "en laat de lange staan. Dat maakt een\n"
        "helling die op een cyclus lijkt.",
        loc="lower left",
    )

    fig.suptitle(
        "Het Slutsky-Yule-effect: gladstrijken maakt golven die er niet waren",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)


def plot_persistence_vs_cycle(
    returns: pd.Series,
    *,
    window: int = 21,
    filename: str = "09_persistentie_vs_cyclus.png",
):
    """Zet 'persistentie' tegenover 'cyclus' — twee verschillende dingen.

    Volatiliteitsclustering is **persistentie**: hoog blijft hoog, en zakt
    daarna geleidelijk terug. Een **cyclus** is iets anders: hoog wordt laag
    wordt hoog met een vaste tussenpoos.

    Je ziet het verschil in de autocorrelatie. Persistentie geeft een
    langzaam dalende curve die positief blijft. Een cyclus geeft een curve
    die door nul gaat en negatief wordt, om daarna weer positief te worden —
    een golf.
    """
    from statsmodels.tsa.stattools import acf

    vol = realised_volatility(returns, window=window)
    n_lags = 250
    acf_vol = acf(vol.values, nlags=n_lags, fft=True)

    # Referentie: hoe ziet de ACF eruit bij een zuiver persistent proces
    # zonder cyclus? Een AR(1) met dezelfde eerste-orde autocorrelatie.
    phi = acf_vol[1]
    lags = np.arange(n_lags + 1)
    ar1_reference = phi**lags

    # En hoe ziet hij eruit als er wél een cyclus is? De demping moet traag
    # zijn, anders is de golf uitgedoofd voordat je hem ziet — met 0,85 per
    # dag is de amplitude na tien dagen al onder de 20%.
    cycle_period = 120
    cyclical = np.exp(-lags / 400.0) * np.cos(2 * np.pi * lags / cycle_period)

    fig, (ax_real, ax_compare) = plt.subplots(1, 2, figsize=(13.5, 5))

    ax_real.plot(lags, acf_vol, color=ROLE["empirical"], linewidth=2.0, label="goud")
    ax_real.plot(
        lags,
        ar1_reference,
        color=ROLE["reference"],
        linewidth=1.6,
        linestyle="--",
        label=f"zuivere persistentie (AR1, φ={phi:.3f})",
    )
    ax_real.axhline(0, color=ROLE["ink_soft"], linewidth=0.9)
    ax_real.set_xlabel("Vertraging in handelsdagen")
    ax_real.set_ylabel("Autocorrelatie van de volatiliteit")
    ax_real.set_title("Wat de data laat zien", fontsize=11)
    ax_real.legend(loc="upper right", fontsize=8.5)

    annotate(
        ax_real,
        "De curve daalt en blijft positief.\n"
        "Hij gaat niet door nul en komt\n"
        "niet terug omhoog: persistentie.\n\n"
        "De kleine bulten waar goud boven\n"
        "de AR(1)-lijn uitkomt zijn de 64-\n"
        "daagse structuur. Zichtbaar, maar\n"
        "veel te zwak om op te sturen.",
        loc="lower left" if acf_vol[-1] > 0 else "upper left",
    )

    ax_compare.plot(
        lags,
        ar1_reference,
        color=ROLE["theoretical"],
        linewidth=2.0,
        label="persistentie: daalt naar nul",
    )
    ax_compare.plot(
        lags,
        cyclical,
        color=ROLE["secondary"],
        linewidth=2.0,
        label=f"cyclus van {cycle_period} dagen: golft",
    )
    ax_compare.axhline(0, color=ROLE["ink_soft"], linewidth=0.9)
    ax_compare.set_xlabel("Vertraging in handelsdagen")
    ax_compare.set_ylabel("Autocorrelatie")
    ax_compare.set_title("Hoe de twee er in theorie uitzien", fontsize=11)
    ax_compare.legend(loc="upper right", fontsize=8.5)

    annotate(
        ax_compare,
        "Zoek je een cyclus, dan moet de\n"
        "autocorrelatie NEGATIEF worden\n"
        "en weer terugkomen.\n\n"
        "Vergelijk dit met de linkerfiguur.",
        loc="lower left",
    )

    fig.suptitle(
        "Persistentie en cycliciteit zijn niet hetzelfde",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return save_figure(fig, filename), {"phi": float(phi), "acf_at_250": float(acf_vol[-1])}
