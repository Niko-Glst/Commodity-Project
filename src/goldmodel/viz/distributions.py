"""Figuren over de verdeling van rendementen.

Elke functie hier beantwoordt één vraag over de data. De grafieken zijn zo
opgezet dat ze los van de omringende tekst te begrijpen zijn: titel, uitleg
in de figuur, en waar mogelijk het getal er direct bij.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy import stats as sps

from goldmodel.viz.style import ROLE, annotate, save_figure


def compute_returns(panel: pd.DataFrame, column: str) -> pd.Series:
    """Berekent dagelijkse log-rendementen voor één prijsreeks.

    Log-rendement is ln(P_t / P_{t-1}). We gebruiken dat in plaats van de
    procentuele verandering om twee redenen:

    1. Ze zijn optelbaar over de tijd. Het rendement over een week is de som
       van de vijf dagrendementen. Bij procentuele rendementen moet je
       vermenigvuldigen, wat rekenen met horizonnen omslachtig maakt.
    2. De verdeling is symmetrischer. Een prijs die halveert en weer
       verdubbelt geeft -50% en +100% in procenten, maar -0,69 en +0,69 in
       logs. Dat laatste weerspiegelt beter dat het om dezelfde beweging gaat.

    Bij kleine dagelijkse bewegingen zijn de twee vrijwel gelijk: een
    log-rendement van 0,01 komt overeen met 1,005%.
    """
    prices = panel[column].dropna()
    return np.log(prices / prices.shift(1)).dropna()


# --------------------------------------------------------------------------
# 1. Histogram met normale verdeling erover
# --------------------------------------------------------------------------


def plot_distribution_vs_normal(
    returns: pd.Series,
    *,
    title: str = "Dagelijkse goudrendementen tegenover de normale verdeling",
    filename: str = "01_verdeling_vs_normaal.png",
):
    """Histogram van de rendementen met de passende normale verdeling erover.

    Dit is de basisfiguur. De blauwe balken zijn wat er echt gebeurde; de
    oranje lijn is wat een normale verdeling met hetzelfde gemiddelde en
    dezelfde standaardafwijking voorspelt.

    Waar je op moet letten: de piek in het midden is hoger dan de kromme, en
    de staarten liggen erbuiten. Dat is de handtekening van dikke staarten.
    Rustige dagen zijn *rustiger* dan normaal voorspelt, en extreme dagen zijn
    *extremer* — maar de gemiddelde dag daartussenin komt minder vaak voor.
    """
    mu = returns.mean()
    sigma = returns.std()

    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(13, 5.5))

    x_grid = np.linspace(returns.min(), returns.max(), 500)
    normal_pdf = sps.norm.pdf(x_grid, mu, sigma)

    for ax, log_scale in ((ax_lin, False), (ax_log, True)):
        ax.hist(
            returns,
            bins=140,
            density=True,
            color=ROLE["empirical"],
            alpha=0.75,
            label="Waargenomen rendementen",
        )
        ax.plot(
            x_grid,
            normal_pdf,
            color=ROLE["theoretical"],
            linewidth=2.2,
            label="Normale verdeling (zelfde gemiddelde en spreiding)",
        )
        ax.set_xlabel("Dagelijks log-rendement")
        if log_scale:
            ax.set_yscale("log")
            ax.set_ylim(bottom=1e-3)
            ax.set_ylabel("Dichtheid (logaritmische schaal)")
            ax.set_title("Zelfde figuur, logaritmische y-as", fontsize=11)
        else:
            ax.set_ylabel("Dichtheid")
            ax.set_title("Lineaire y-as", fontsize=11)

    ax_lin.legend(loc="upper left", fontsize=8.5)

    annotate(
        ax_lin,
        "De piek is hoger dan de kromme:\n"
        "rustige dagen komen vaker voor\n"
        "dan 'normaal' voorspelt.",
        loc="lower right",
    )
    annotate(
        ax_log,
        "Op deze schaal zie je de staarten.\n"
        "De blauwe balken lopen ver door\n"
        "waar de oranje lijn al bijna nul is.",
        loc="upper right",
    )

    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)


# --------------------------------------------------------------------------
# 2. Wat kurtosis meet, opgebouwd van de definitie
# --------------------------------------------------------------------------


def plot_kurtosis_explained(
    returns: pd.Series,
    *,
    filename: str = "02_kurtosis_uitgelegd.png",
):
    """Laat zien hoe kurtosis rekenkundig tot stand komt.

    Kurtosis is het gemiddelde van de vierde macht van de gestandaardiseerde
    afwijkingen. Deze figuur maakt zichtbaar waarom die vierde macht ervoor
    zorgt dat het getal vooral over de staarten gaat: een afwijking van 4
    standaardafwijkingen telt 256 keer zo zwaar als een afwijking van 1.

    Links: de bijdrage per waarneming aan de kurtosis, uitgezet tegen de
    afwijking. Rechts: welk deel van de totale kurtosis van hoeveel procent
    van de dagen komt.
    """
    z = ((returns - returns.mean()) / returns.std()).values
    contributions = z**4

    fig, (ax_curve, ax_share) = plt.subplots(1, 2, figsize=(13, 5))

    # -- links: de gewichtsfunctie -------------------------------------
    grid = np.linspace(-6, 6, 400)
    ax_curve.plot(
        grid,
        grid**4,
        color=ROLE["reference"],
        linewidth=1.6,
        linestyle="--",
        label="Gewicht = z⁴ (de formule)",
    )
    ax_curve.scatter(
        z,
        contributions,
        s=7,
        color=ROLE["empirical"],
        alpha=0.35,
        label="Elke handelsdag",
    )

    # Markeer de zwaarste dagen.
    heavy_idx = np.argsort(contributions)[-5:]
    ax_curve.scatter(
        z[heavy_idx],
        contributions[heavy_idx],
        s=55,
        color=ROLE["highlight"],
        zorder=5,
        label="De 5 zwaarstwegende dagen",
    )

    ax_curve.set_xlabel("Afwijking in standaardafwijkingen (z)")
    ax_curve.set_ylabel("Bijdrage aan kurtosis (z⁴, logaritmisch)")
    ax_curve.set_title("Waarom de vierde macht?", fontsize=11)
    ax_curve.set_xlim(-6.5, 6.5)
    # Logaritmische y-as: zonder dat drukt de zwaarste dag (z ≈ -6,5, gewicht
    # ruim 1.700) alle andere punten plat tegen de x-as en zie je de vorm van
    # de gewichtsfunctie niet meer.
    ax_curve.set_yscale("log")
    ax_curve.set_ylim(1e-4, 5e3)
    ax_curve.legend(loc="lower center", fontsize=8.5)

    annotate(
        ax_curve,
        "z = 1  telt als     1\n"
        "z = 2  telt als    16\n"
        "z = 3  telt als    81\n"
        "z = 4  telt als   256",
        loc="upper left",
    )

    # -- rechts: concentratie ------------------------------------------
    sorted_contrib = np.sort(contributions)[::-1]
    cumulative_share = np.cumsum(sorted_contrib) / sorted_contrib.sum() * 100
    day_share = np.arange(1, len(sorted_contrib) + 1) / len(sorted_contrib) * 100

    ax_share.plot(day_share, cumulative_share, color=ROLE["empirical"], linewidth=2.2)
    ax_share.plot(
        [0, 100],
        [0, 100],
        color=ROLE["reference"],
        linestyle="--",
        linewidth=1.4,
        label="Als elke dag evenveel bijdroeg",
    )

    # Markeer waar 1% en 5% van de dagen staan.
    for pct, color in ((1.0, ROLE["highlight"]), (5.0, ROLE["theoretical"])):
        idx = int(len(sorted_contrib) * pct / 100)
        share = cumulative_share[idx]
        ax_share.plot([pct, pct], [0, share], color=color, linewidth=1.4, linestyle=":")
        ax_share.plot([0, pct], [share, share], color=color, linewidth=1.4, linestyle=":")
        ax_share.scatter([pct], [share], s=45, color=color, zorder=5)
        ax_share.annotate(
            f"{pct:.0f}% van de dagen\nlevert {share:.0f}% van de kurtosis",
            xy=(pct, share),
            xytext=(pct + 12, share - 14),
            fontsize=8.5,
            color=color,
            arrowprops={"arrowstyle": "->", "color": color, "linewidth": 1.2},
        )

    ax_share.set_xlabel("Percentage van de handelsdagen (zwaarste eerst)")
    ax_share.set_ylabel("Cumulatief aandeel in de kurtosis (%)")
    ax_share.set_title("Kurtosis wordt bepaald door een handvol dagen", fontsize=11)
    ax_share.set_xlim(0, 100)
    ax_share.set_ylim(0, 101)
    ax_share.legend(loc="lower right", fontsize=8.5)

    excess = returns.kurtosis()
    fig.suptitle(
        f"Wat kurtosis meet — exces-kurtosis van goud: {excess:.2f}",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return save_figure(fig, filename)


# --------------------------------------------------------------------------
# 3. Scheefheid
# --------------------------------------------------------------------------


def plot_skewness_explained(
    returns: pd.Series,
    *,
    filename: str = "03_scheefheid.png",
):
    """Laat scheefheid zien door de linker- en rechterstaart te spiegelen.

    Scheefheid is de derde macht van de gestandaardiseerde afwijkingen. Anders
    dan bij de vierde macht behoudt een oneven macht het teken: negatieve
    afwijkingen leveren een negatieve bijdrage. Het getal meet dus of de
    grote uitschieters vooral aan de linker- of rechterkant zitten.

    De figuur klapt de linkerstaart over de rechterstaart heen. Zou de
    verdeling symmetrisch zijn, dan vielen ze samen.
    """
    z = (returns - returns.mean()) / returns.std()
    skew = returns.skew()

    fig, (ax_mirror, ax_extremes) = plt.subplots(1, 2, figsize=(13, 5))

    # -- links: gespiegelde staarten -----------------------------------
    bins = np.linspace(0, 6, 45)
    right_tail = z[z > 0]
    left_tail = -z[z < 0]  # spiegelen naar positief

    ax_mirror.hist(
        right_tail,
        bins=bins,
        color=ROLE["empirical"],
        alpha=0.6,
        label=f"Stijgingen (n={len(right_tail):,})",
    )
    ax_mirror.hist(
        left_tail,
        bins=bins,
        color=ROLE["highlight"],
        alpha=0.6,
        label=f"Dalingen, gespiegeld (n={len(left_tail):,})",
    )
    ax_mirror.set_yscale("log")
    ax_mirror.set_xlabel("Grootte van de beweging (standaardafwijkingen)")
    ax_mirror.set_ylabel("Aantal dagen (logaritmische schaal)")
    ax_mirror.set_title("Dalingen over stijgingen heen geklapt", fontsize=11)
    ax_mirror.legend(loc="upper right", fontsize=8.5)

    annotate(
        ax_mirror,
        "Rood steekt rechts boven blauw uit:\n"
        "de grootste dalingen zijn groter\n"
        "dan de grootste stijgingen.",
        loc="lower left",
    )

    # -- rechts: de tien extreemste dagen elke kant op ------------------
    worst = returns.nsmallest(10)
    best = returns.nlargest(10)

    positions = np.arange(10)
    ax_extremes.barh(
        positions + 0.2,
        best.values * 100,
        height=0.38,
        color=ROLE["empirical"],
        label="10 beste dagen",
    )
    ax_extremes.barh(
        positions - 0.2,
        worst.values * 100,
        height=0.38,
        color=ROLE["highlight"],
        label="10 slechtste dagen",
    )
    ax_extremes.axvline(0, color=ROLE["ink_soft"], linewidth=1.0)
    ax_extremes.set_yticks(positions)
    ax_extremes.set_yticklabels([f"#{i + 1}" for i in range(10)])
    ax_extremes.invert_yaxis()
    ax_extremes.set_xlabel("Dagrendement (%)")
    ax_extremes.set_title("De tien extreemste dagen elke kant op", fontsize=11)
    ax_extremes.legend(loc="lower right", fontsize=8.5)
    ax_extremes.grid(axis="x", alpha=0.5)
    ax_extremes.grid(axis="y", visible=False)

    # Label bij de zwaarste daling. De balk voor #1 staat op y = 0 - 0.2,
    # dus daar moet de pijl naartoe wijzen.
    ax_extremes.annotate(
        f"{worst.values[0] * 100:.1f}%  op {worst.index[0].date()}",
        xy=(worst.values[0] * 100, -0.2),
        xytext=(worst.values[0] * 100 * 0.75, -0.95),
        fontsize=8.5,
        color=ROLE["highlight"],
        ha="left",
        arrowprops={"arrowstyle": "->", "color": ROLE["highlight"], "linewidth": 1.1},
    )

    direction = "links" if skew < 0 else "rechts"
    fig.suptitle(
        f"Scheefheid van goudrendementen: {skew:.2f} (scheef naar {direction})",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return save_figure(fig, filename)


# --------------------------------------------------------------------------
# 4. QQ-plot
# --------------------------------------------------------------------------


def plot_qq(
    returns: pd.Series,
    *,
    filename: str = "04_qq_plot.png",
):
    """QQ-plot tegen de normale verdeling en tegen een t-verdeling.

    Een QQ-plot (quantile-quantile) zet de waargenomen kwantielen uit tegen
    de kwantielen die een theoretische verdeling voorspelt. Lagen de punten
    perfect op de diagonaal, dan volgde de data die verdeling exact.

    Dit is de scherpste diagnostiek voor staartgedrag die er is: afwijkingen
    aan de uiteinden vallen direct op, terwijl een histogram de staarten juist
    onzichtbaar maakt omdat er zo weinig waarnemingen zitten.

    Rechts staat dezelfde plot tegen een t-verdeling waarvan de vrijheidsgraden
    op de data zijn geschat. Dat is de verdeling die we in fase 4 gaan
    gebruiken; deze figuur laat zien of die keuze de data beter beschrijft.
    """
    fig, (ax_normal, ax_t) = plt.subplots(1, 2, figsize=(13, 5.5))

    # -- normaal --------------------------------------------------------
    sps.probplot(returns, dist="norm", plot=None, fit=False)
    theoretical_q, ordered = sps.probplot(returns, dist="norm", fit=False)

    ax_normal.scatter(
        theoretical_q, ordered * 100, s=9, color=ROLE["empirical"], alpha=0.55
    )
    line_range = np.array([theoretical_q.min(), theoretical_q.max()])
    ax_normal.plot(
        line_range,
        line_range * returns.std() * 100 + returns.mean() * 100,
        color=ROLE["reference"],
        linestyle="--",
        linewidth=1.6,
        label="Perfect normaal",
    )
    ax_normal.set_xlabel("Theoretische kwantielen (normale verdeling)")
    ax_normal.set_ylabel("Waargenomen rendement (%)")
    ax_normal.set_title("Tegen de normale verdeling", fontsize=11)
    ax_normal.legend(loc="upper left", fontsize=8.5)

    annotate(
        ax_normal,
        "De punten buigen aan beide\n"
        "uiteinden van de lijn weg.\n"
        "Dat is precies wat dikke\n"
        "staarten er uit laten zien.",
        loc="lower right",
    )

    # -- t-verdeling ----------------------------------------------------
    # Schat de vrijheidsgraden op de data. Weinig vrijheidsgraden betekent
    # dikkere staarten; boven ~30 nadert de t-verdeling de normale.
    df, loc_t, scale_t = sps.t.fit(returns.values)
    theoretical_qt, ordered_t = sps.probplot(
        returns, dist=sps.t, sparams=(df,), fit=False
    )

    ax_t.scatter(theoretical_qt, ordered_t * 100, s=9, color=ROLE["secondary"], alpha=0.55)
    line_range_t = np.array([theoretical_qt.min(), theoretical_qt.max()])
    ax_t.plot(
        line_range_t,
        line_range_t * scale_t * 100 + loc_t * 100,
        color=ROLE["reference"],
        linestyle="--",
        linewidth=1.6,
        label=f"Perfect t met {df:.1f} vrijheidsgraden",
    )
    ax_t.set_xlabel(f"Theoretische kwantielen (t-verdeling, df={df:.1f})")
    ax_t.set_ylabel("Waargenomen rendement (%)")
    ax_t.set_title("Tegen een t-verdeling", fontsize=11)
    ax_t.legend(loc="upper left", fontsize=8.5)

    annotate(
        ax_t,
        f"Met {df:.1f} vrijheidsgraden liggen\n"
        "de punten veel dichter bij de lijn.\n"
        "Dit is waarom fase 4 met de\n"
        "t-verdeling gaat werken.",
        loc="lower right",
    )

    fig.suptitle(
        "QQ-plot: past de data bij de verdeling?",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return save_figure(fig, filename), df


# --------------------------------------------------------------------------
# 5. Volatiliteitsclustering
# --------------------------------------------------------------------------


def plot_volatility_clustering(
    returns: pd.Series,
    *,
    filename: str = "05_volatiliteitsclustering.png",
):
    """Laat zien dat rustige en onrustige periodes zich groeperen.

    Dit is een apart verschijnsel van dikke staarten en het is de reden dat
    fase 4 GARCH gebruikt. De rendementen zelf zijn nauwelijks voorspelbaar
    (dat gaan we in fase 3 toetsen), maar de *grootte* van de bewegingen is
    dat wel degelijk: een onrustige dag wordt waarschijnlijk gevolgd door nog
    een onrustige dag.

    Boven: de rendementen door de tijd. Onder: de autocorrelatie van de
    rendementen zelf tegenover die van de absolute rendementen. Het contrast
    tussen die twee is het hele punt.
    """
    from statsmodels.tsa.stattools import acf

    fig, (ax_series, ax_acf) = plt.subplots(
        2, 1, figsize=(13, 8), gridspec_kw={"height_ratios": [1.3, 1]}
    )

    # -- boven: rendementen door de tijd --------------------------------
    ax_series.plot(
        returns.index,
        returns.values * 100,
        color=ROLE["empirical"],
        linewidth=0.6,
        alpha=0.85,
    )
    ax_series.axhline(0, color=ROLE["ink_soft"], linewidth=0.8)
    ax_series.set_ylabel("Dagrendement (%)")
    ax_series.set_title(
        "Rustige en onrustige periodes komen in blokken", fontsize=11
    )
    ax_series.grid(axis="y", alpha=0.5)

    # Markeer de meest onrustige periode.
    rolling_vol = returns.rolling(21).std()
    peak_date = rolling_vol.idxmax()
    ax_series.axvspan(
        peak_date - pd.Timedelta(days=45),
        peak_date + pd.Timedelta(days=45),
        color=ROLE["highlight"],
        alpha=0.12,
    )
    ax_series.annotate(
        f"onrustigste periode\n({peak_date.strftime('%b %Y')})",
        xy=(peak_date, returns.max() * 100 * 0.85),
        xytext=(peak_date + pd.Timedelta(days=500), returns.max() * 100 * 0.9),
        fontsize=8.5,
        color=ROLE["highlight"],
        arrowprops={"arrowstyle": "->", "color": ROLE["highlight"], "linewidth": 1.2},
    )

    # -- onder: autocorrelatie ------------------------------------------
    n_lags = 40
    acf_returns = acf(returns.values, nlags=n_lags, fft=True)
    acf_absolute = acf(np.abs(returns.values), nlags=n_lags, fft=True)

    lags = np.arange(1, n_lags + 1)
    width = 0.4
    ax_acf.bar(
        lags - width / 2,
        acf_returns[1:],
        width=width,
        color=ROLE["empirical"],
        label="Rendementen zelf (richting)",
    )
    ax_acf.bar(
        lags + width / 2,
        acf_absolute[1:],
        width=width,
        color=ROLE["theoretical"],
        label="Absolute rendementen (grootte)",
    )

    # Significantiegrens: ongeveer 2/sqrt(n).
    bound = 1.96 / np.sqrt(len(returns))
    ax_acf.axhline(bound, color=ROLE["reference"], linestyle="--", linewidth=1.2)
    ax_acf.axhline(-bound, color=ROLE["reference"], linestyle="--", linewidth=1.2)
    ax_acf.axhline(0, color=ROLE["ink_soft"], linewidth=0.8)
    ax_acf.text(
        n_lags * 0.99,
        bound * 1.5,
        "grens van toeval",
        fontsize=8,
        color=ROLE["ink_soft"],
        ha="right",
    )

    ax_acf.set_xlabel("Vertraging in handelsdagen")
    ax_acf.set_ylabel("Autocorrelatie")
    ax_acf.set_title(
        "De richting is onvoorspelbaar, de grootte niet", fontsize=11
    )
    ax_acf.legend(loc="upper right", fontsize=8.5)
    ax_acf.grid(axis="y", alpha=0.5)

    annotate(
        ax_acf,
        "Blauw blijft binnen de grenzen:\n"
        "of goud morgen stijgt of daalt is\n"
        "niet uit vandaag af te leiden.\n\n"
        "Oranje steekt er ver bovenuit:\n"
        "of morgen onrustig wordt, weet je\n"
        "vandaag wél. Dat is wat GARCH\n"
        "in fase 4 gaat modelleren.",
        loc="upper left",
    )

    fig.suptitle(
        "Volatiliteitsclustering: onrust komt in golven",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save_figure(fig, filename)


# --------------------------------------------------------------------------
# 6. Vergelijking van alle reeksen
# --------------------------------------------------------------------------


def plot_series_comparison(
    panel: pd.DataFrame,
    columns: list[str],
    *,
    filename: str = "06_reeksen_vergeleken.png",
):
    """Vergelijkt de verdelingskenmerken van meerdere prijsreeksen.

    Laat zien dat dikke staarten geen eigenaardigheid van goud zijn maar een
    algemeen kenmerk van financiële rendementen. Dat is relevant voor de
    verdedigbaarheid: als alleen goud dikke staarten had, zou je aan de data
    twijfelen.
    """
    available = [c for c in columns if c in panel.columns]
    if not available:
        return None

    returns_by_series = {c: compute_returns(panel, c) for c in available}

    fig, (ax_tail, ax_scatter) = plt.subplots(1, 2, figsize=(13, 5))

    # -- links: waargenomen versus verwachte extreme dagen --------------
    labels, observed_counts, expected_counts = [], [], []
    for name, series in returns_by_series.items():
        z = (series - series.mean()) / series.std()
        observed_counts.append(int((z.abs() > 3).sum()))
        expected_counts.append(len(series) * 2 * (1 - sps.norm.cdf(3)))
        labels.append(name.replace("_", " "))

    positions = np.arange(len(labels))
    width = 0.38
    bars_obs = ax_tail.bar(
        positions - width / 2,
        observed_counts,
        width,
        color=ROLE["empirical"],
        label="Werkelijk waargenomen",
    )
    bars_exp = ax_tail.bar(
        positions + width / 2,
        expected_counts,
        width,
        color=ROLE["theoretical"],
        label="Verwacht bij normale verdeling",
    )

    for bar in list(bars_obs) + list(bars_exp):
        ax_tail.annotate(
            f"{bar.get_height():.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8.5,
            color=ROLE["ink_soft"],
        )

    ax_tail.set_xticks(positions)
    ax_tail.set_xticklabels(labels, fontsize=9)
    ax_tail.set_ylabel("Aantal dagen met beweging > 3 standaardafwijkingen")
    ax_tail.set_title("Extreme dagen: werkelijkheid tegenover theorie", fontsize=11)
    ax_tail.legend(loc="upper right", fontsize=8.5)

    # -- rechts: scheefheid tegen kurtosis ------------------------------
    palette = [ROLE["empirical"], ROLE["theoretical"], ROLE["secondary"], ROLE["highlight"]]
    for i, (name, series) in enumerate(returns_by_series.items()):
        ax_scatter.scatter(
            series.skew(),
            series.kurtosis(),
            s=140,
            color=palette[i % len(palette)],
            zorder=5,
            edgecolor=ROLE["surface"],
            linewidth=2,
        )
        ax_scatter.annotate(
            name.replace("_", " "),
            xy=(series.skew(), series.kurtosis()),
            xytext=(8, 6),
            textcoords="offset points",
            fontsize=9,
            color=ROLE["ink_soft"],
        )

    # De normale verdeling als referentiepunt. We labelen hem direct in de
    # figuur in plaats van via een legenda: een legenda-item ver van het
    # punt zelf leest als een tweede ster.
    ax_scatter.scatter(
        [0], [0], s=200, marker="*", color=ROLE["reference"], zorder=6
    )
    # Label linksonder de ster: rechtsboven zit het punt van de dollarindex,
    # dat vlak bij de oorsprong ligt.
    ax_scatter.annotate(
        "normale verdeling\n(scheefheid 0, kurtosis 0)",
        xy=(0, 0),
        xytext=(-14, -26),
        textcoords="offset points",
        fontsize=8.5,
        color=ROLE["ink_soft"],
        ha="right",
        arrowprops={
            "arrowstyle": "-",
            "color": ROLE["reference"],
            "linewidth": 0.9,
        },
    )
    ax_scatter.axhline(0, color=ROLE["reference"], linewidth=1.0, linestyle="--")
    ax_scatter.axvline(0, color=ROLE["reference"], linewidth=1.0, linestyle="--")
    ax_scatter.set_xlabel("Scheefheid  (0 = symmetrisch)")
    ax_scatter.set_ylabel("Exces-kurtosis  (0 = normale staarten)")
    ax_scatter.set_title("Elke reeks wijkt af van normaal", fontsize=11)
    # Ruimte links en onder zodat de labels niet tegen de rand aanlopen.
    ax_scatter.margins(x=0.18, y=0.14)

    fig.suptitle(
        "Dikke staarten zijn niet uniek voor goud",
        fontsize=13,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return save_figure(fig, filename)
