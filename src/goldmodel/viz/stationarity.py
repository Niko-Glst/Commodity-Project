"""Figuren over stationariteit en schijnregressie.

Waarom dit het startpunt van fase 2 is
--------------------------------------
Voordat je twee reeksen tegen elkaar mag regresseren, moet je weten of ze
*stationair* zijn. Een reeks is stationair als zijn statistische eigenschappen
niet van de tijd afhangen: hetzelfde gemiddelde, dezelfde spreiding, dezelfde
samenhang met zijn eigen verleden — of je nu naar 2005 of naar 2025 kijkt.

Een prijsreeks is dat vrijwel nooit. De goudprijs schommelde rond $400 in 2003
en rond $4.300 in 2026; er is geen "gemiddelde goudprijs" waar hij naartoe
terugkeert.

Waarom dat een probleem is: regresseer je twee niet-stationaire reeksen op
elkaar, dan vind je vrijwel altijd een sterk, significant verband — ook als de
reeksen niets met elkaar te maken hebben. Dat heet **schijnregressie**
(spurious regression), beschreven door Granger en Newbold in 1974.

De oorzaak in één zin: twee reeksen die allebei een trend hebben, bewegen
allebei "omhoog over tijd", en dat alleen al levert een hoge correlatie op. De
regressie ziet gezamenlijke beweging, niet gezamenlijke oorzaak.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib import pyplot as plt
from statsmodels.tsa.stattools import adfuller, kpss

from goldmodel.viz.style import ROLE, annotate, save_figure


def generate_independent_walks(
    n: int = 1000, *, seed: int = 42
) -> tuple[pd.Series, pd.Series]:
    """Maakt twee volstrekt onafhankelijke random walks.

    Elke reeks is een cumulatieve som van eigen toevalsgetallen. Er is per
    constructie geen enkel verband: geen gedeelde schok, geen gedeelde trend,
    niets. Dat maakt ze de ideale controle — elk verband dat een regressie
    hier vindt, is per definitie schijn.
    """
    rng = np.random.default_rng(seed)
    first = pd.Series(100.0 + np.cumsum(rng.standard_normal(n)), name="reeks_a")
    second = pd.Series(100.0 + np.cumsum(rng.standard_normal(n)), name="reeks_b")
    return first, second


def spurious_regression_rate(
    *, n_simulations: int = 500, n_observations: int = 500, seed: int = 7
) -> dict:
    """Hoe vaak vindt een regressie op niveaus een 'significant' verband?

    We doen het experiment honderden keren met steeds nieuwe, onafhankelijke
    random walks en tellen hoe vaak de coëfficiënt significant lijkt (p < 0,05).

    Bij een correcte toets zou dat 5% van de tijd gebeuren — dat is wat een
    significantieniveau van 5% betekent. Op niveaus komt er iets heel anders
    uit, en dat verschil is de kern van het probleem.
    """
    rng = np.random.default_rng(seed)
    levels_significant = 0
    diffs_significant = 0
    r_squared_levels: list[float] = []

    for _ in range(n_simulations):
        a = np.cumsum(rng.standard_normal(n_observations))
        b = np.cumsum(rng.standard_normal(n_observations))

        model_levels = sm.OLS(a, sm.add_constant(b)).fit()
        if model_levels.pvalues[1] < 0.05:
            levels_significant += 1
        r_squared_levels.append(float(model_levels.rsquared))

        model_diffs = sm.OLS(np.diff(a), sm.add_constant(np.diff(b))).fit()
        if model_diffs.pvalues[1] < 0.05:
            diffs_significant += 1

    return {
        "levels_false_positive_rate": levels_significant / n_simulations,
        "diffs_false_positive_rate": diffs_significant / n_simulations,
        "median_r_squared_levels": float(np.median(r_squared_levels)),
        "n_simulations": n_simulations,
    }


def run_stationarity_tests(series: pd.Series, *, name: str = "") -> dict:
    """Voert de ADF- en KPSS-toets uit op één reeks.

    **ADF (Augmented Dickey-Fuller)**
        Nulhypothese: de reeks is NIET stationair (er zit een 'unit root' in).
        Een kleine p-waarde verwerpt dat, en is dus bewijs *voor*
        stationariteit.

    **KPSS**
        Nulhypothese: de reeks IS stationair — precies omgekeerd. Een kleine
        p-waarde verwerpt dat, en is dus bewijs *tegen* stationariteit.

    Waarom je ze samen gebruikt: de nulhypotheses staan tegenover elkaar, dus
    ze kunnen elkaar bevestigen of tegenspreken. Vier uitkomsten:

    ==================  ==================  ==============================
    ADF                 KPSS                Conclusie
    ==================  ==================  ==============================
    verwerpt (p<0,05)   verwerpt niet       stationair — eens
    verwerpt niet       verwerpt            niet-stationair — eens
    verwerpt            verwerpt            onduidelijk, mogelijk trend
    verwerpt niet       verwerpt niet       te weinig informatie
    ==================  ==================  ==============================

    Die laatste twee gevallen zijn geen mislukking van de toetsen maar een
    signaal dat je reeks ingewikkelder is dan "wel of niet stationair".
    """
    values = series.dropna().values

    # result_object=False houdt de tuple-vorm expliciet vast. Zonder deze
    # parameter waarschuwt statsmodels dat de standaard in een latere versie
    # verandert, wat deze code stil zou breken.
    adf_stat, adf_p, _, _, adf_crit, _ = adfuller(
        values, autolag="AIC", result_object=False
    )

    # KPSS waarschuwt bij p-waarden buiten de tabel; dat is informatief,
    # geen fout, dus we onderdrukken de waarschuwing bewust niet in de
    # berekening maar vangen hem wel op.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        kpss_stat, kpss_p, _, kpss_crit = kpss(values, regression="c", nlags="auto")

    adf_rejects = adf_p < 0.05
    kpss_rejects = kpss_p < 0.05

    if adf_rejects and not kpss_rejects:
        verdict = "stationair"
        explanation = "Beide toetsen wijzen dezelfde kant op."
    elif not adf_rejects and kpss_rejects:
        verdict = "NIET stationair"
        explanation = "Beide toetsen wijzen dezelfde kant op."
    elif adf_rejects and kpss_rejects:
        verdict = "onduidelijk"
        explanation = (
            "De toetsen spreken elkaar tegen. Kan wijzen op een "
            "deterministische trend of een structuurbreuk."
        )
    else:
        verdict = "onduidelijk"
        explanation = (
            "Geen van beide toetsen verwerpt; te weinig informatie om te "
            "beslissen."
        )

    return {
        "name": name or series.name or "reeks",
        "n": len(values),
        "adf_statistic": float(adf_stat),
        "adf_p": float(adf_p),
        "adf_critical_5pct": float(adf_crit["5%"]),
        "adf_rejects": bool(adf_rejects),
        "kpss_statistic": float(kpss_stat),
        "kpss_p": float(kpss_p),
        "kpss_critical_5pct": float(kpss_crit["5%"]),
        "kpss_rejects": bool(kpss_rejects),
        "verdict": verdict,
        "explanation": explanation,
    }


# --------------------------------------------------------------------------
# Figuren
# --------------------------------------------------------------------------


def plot_spurious_regression(filename: str = "13_schijnregressie.png"):
    """Toont hoe twee onafhankelijke reeksen een sterk verband lijken te hebben.

    Vier panelen: de twee reeksen door de tijd, de regressie op niveaus (die
    er overtuigend uitziet), dezelfde regressie op veranderingen (waar niets
    overblijft), en het resultaat van honderden herhalingen.
    """
    a, b = generate_independent_walks(1000, seed=42)

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9))
    ax_series, ax_levels = axes[0]
    ax_diffs, ax_repeat = axes[1]

    # -- 1. De twee reeksen ---------------------------------------------
    ax_series.plot(a.values, color=ROLE["empirical"], linewidth=1.4, label="reeks A")
    ax_series.plot(b.values, color=ROLE["theoretical"], linewidth=1.4, label="reeks B")
    ax_series.set_xlabel("Tijdstap")
    ax_series.set_ylabel("Niveau")
    ax_series.set_title("1. Twee reeksen uit een toevalsgenerator", fontsize=11)
    ax_series.legend(loc="upper left", fontsize=8.5)
    annotate(
        ax_series,
        "Deze twee hebben NIETS met\n"
        "elkaar te maken: elk is een\n"
        "aparte reeks toevalsgetallen.\n\n"
        "Toch lijken ze soms samen\n"
        "op en neer te gaan.",
        loc="lower right",
    )

    # -- 2. Regressie op niveaus ----------------------------------------
    model_levels = sm.OLS(a.values, sm.add_constant(b.values)).fit()
    ax_levels.scatter(b.values, a.values, s=8, color=ROLE["empirical"], alpha=0.45)
    x_line = np.array([b.min(), b.max()])
    ax_levels.plot(
        x_line,
        model_levels.params[0] + model_levels.params[1] * x_line,
        color=ROLE["highlight"],
        linewidth=2.2,
    )
    ax_levels.set_xlabel("Reeks B (niveau)")
    ax_levels.set_ylabel("Reeks A (niveau)")
    ax_levels.set_title("2. Regressie op NIVEAUS — ziet er sterk uit", fontsize=11)
    annotate(
        ax_levels,
        f"R² = {model_levels.rsquared:.3f}\n"
        f"t-waarde = {model_levels.tvalues[1]:.1f}\n"
        f"p-waarde = {model_levels.pvalues[1]:.1e}\n\n"
        "Dit zou je 'zeer significant'\n"
        "noemen. Het is volledig nep.",
        loc="upper left",
    )

    # -- 3. Regressie op verschillen ------------------------------------
    da, db = a.diff().dropna().values, b.diff().dropna().values
    model_diffs = sm.OLS(da, sm.add_constant(db)).fit()
    ax_diffs.scatter(db, da, s=8, color=ROLE["secondary"], alpha=0.45)
    x_line_d = np.array([db.min(), db.max()])
    ax_diffs.plot(
        x_line_d,
        model_diffs.params[0] + model_diffs.params[1] * x_line_d,
        color=ROLE["highlight"],
        linewidth=2.2,
    )
    ax_diffs.set_xlabel("Verandering in reeks B")
    ax_diffs.set_ylabel("Verandering in reeks A")
    ax_diffs.set_title("3. Regressie op VERANDERINGEN — niets over", fontsize=11)
    annotate(
        ax_diffs,
        f"R² = {model_diffs.rsquared:.4f}\n"
        f"t-waarde = {model_diffs.tvalues[1]:.2f}\n"
        f"p-waarde = {model_diffs.pvalues[1]:.2f}\n\n"
        "Geen verband. Dit is de\n"
        "waarheid: er is er ook geen.",
        loc="upper left",
    )

    # -- 4. Honderden herhalingen ---------------------------------------
    rates = spurious_regression_rate(n_simulations=400, n_observations=500)
    bars = ax_repeat.bar(
        ["op niveaus", "op veranderingen"],
        [
            rates["levels_false_positive_rate"] * 100,
            rates["diffs_false_positive_rate"] * 100,
        ],
        color=[ROLE["highlight"], ROLE["secondary"]],
        width=0.55,
    )
    for bar in bars:
        ax_repeat.annotate(
            f"{bar.get_height():.0f}%",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            fontsize=11,
            fontweight="bold",
            color=ROLE["ink_soft"],
        )
    ax_repeat.axhline(
        5,
        color=ROLE["reference"],
        linestyle="--",
        linewidth=1.6,
    )
    ax_repeat.text(
        1.45,
        7,
        "zo vaak hóórt het\n(5% bij toeval)",
        fontsize=8.5,
        color=ROLE["ink_soft"],
        ha="right",
    )
    ax_repeat.set_ylabel("Hoe vaak 'significant' (%)")
    ax_repeat.set_ylim(0, 105)
    ax_repeat.set_title(
        f"4. {rates['n_simulations']} keer herhaald met nieuwe toevalsreeksen",
        fontsize=11,
    )
    annotate(
        ax_repeat,
        "Op niveaus vind je bijna altijd\n"
        "een 'significant' verband in data\n"
        "waar er geen is.\n\n"
        "Op veranderingen klopt het\n"
        "foutenpercentage wel.",
        loc="upper right",
    )

    fig.suptitle(
        "Schijnregressie: waarom je niet op prijsniveaus mag regresseren",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename), rates


def plot_stationarity_comparison(
    panel: pd.DataFrame,
    *,
    filename: str = "14_stationariteit.png",
):
    """Zet de goudprijs naast de goudrendementen: niet-stationair versus wel.

    Het verschil is visueel meteen duidelijk, en dat is de bedoeling: je hoeft
    geen toets te doen om te zien dat de bovenste reeks geen vast gemiddelde
    heeft en de onderste wel.
    """
    prices = panel["gold_futures"].dropna()
    returns = np.log(prices / prices.shift(1)).dropna() * 100

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.5))
    ax_price, ax_price_mean = axes[0]
    ax_ret, ax_ret_mean = axes[1]

    # -- boven: de prijs ------------------------------------------------
    ax_price.plot(prices.index, prices.values, color=ROLE["empirical"], linewidth=1.1)
    ax_price.set_ylabel("Goudprijs (USD/ounce)")
    ax_price.set_title("De PRIJS: niet stationair", fontsize=11)
    ax_price.grid(axis="y", alpha=0.4)

    # Voortschrijdend gemiddelde over vijf jaar, om te laten zien dat het
    # gemiddelde zelf wegloopt.
    window = 252 * 5
    rolling_price_mean = prices.rolling(window).mean()
    ax_price_mean.plot(
        prices.index,
        rolling_price_mean.values,
        color=ROLE["highlight"],
        linewidth=2.2,
        label="gemiddelde over 5 jaar",
    )
    ax_price_mean.set_ylabel("Gemiddelde prijs (USD)")
    ax_price_mean.set_title("Het gemiddelde loopt weg", fontsize=11)
    ax_price_mean.legend(loc="upper left", fontsize=8.5)
    ax_price_mean.grid(axis="y", alpha=0.4)
    annotate(
        ax_price_mean,
        "Er is geen 'gemiddelde\n"
        "goudprijs' waar hij naar\n"
        "terugkeert. Het gemiddelde\n"
        "hangt af van welke periode\n"
        "je kiest.\n\n"
        "Dat is de definitie van\n"
        "niet-stationair.",
        loc="lower right",
    )

    # -- onder: de rendementen ------------------------------------------
    ax_ret.plot(
        returns.index, returns.values, color=ROLE["secondary"], linewidth=0.5, alpha=0.85
    )
    ax_ret.axhline(0, color=ROLE["ink_soft"], linewidth=0.9)
    ax_ret.set_ylabel("Dagrendement (%)")
    ax_ret.set_title("De RENDEMENTEN: wel stationair", fontsize=11)
    ax_ret.grid(axis="y", alpha=0.4)

    rolling_return_mean = returns.rolling(window).mean()
    ax_ret_mean.plot(
        returns.index,
        rolling_return_mean.values,
        color=ROLE["highlight"],
        linewidth=2.2,
        label="gemiddelde over 5 jaar",
    )
    ax_ret_mean.axhline(0, color=ROLE["ink_soft"], linewidth=0.9)
    ax_ret_mean.set_ylabel("Gemiddeld dagrendement (%)")
    ax_ret_mean.set_title("Het gemiddelde blijft rond nul", fontsize=11)
    ax_ret_mean.legend(loc="upper left", fontsize=8.5)
    ax_ret_mean.grid(axis="y", alpha=0.4)
    annotate(
        ax_ret_mean,
        "Let op de schaal: dit\n"
        "schommelt tussen ongeveer\n"
        "0 en 0,1 procent.\n\n"
        "Het gemiddelde blijft in\n"
        "dezelfde buurt, welke\n"
        "periode je ook pakt.",
        loc="lower right",
    )

    fig.suptitle(
        "Stationariteit: waarom we met rendementen werken en niet met prijzen",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)
