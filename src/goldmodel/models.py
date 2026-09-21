"""Fase 3: regressiemodellen met eerlijke validatie.

De vraag van fase 3
-------------------
Fase 2 leverde een nulhypothese op: goudrendementen zijn nauwelijks te
verklaren uit macro-data. Fase 3 toetst dat formeel, en de toets die telt is
niet de R-kwadraat maar de **out-of-sample** vergelijking met een naïeve
benchmark.

Waarom in-sample R-kwadraat niet genoeg is
------------------------------------------
Een model met genoeg variabelen past altijd wel iets. Voeg een driver toe en
de R-kwadraat stijgt, ook als die driver niets betekent — dat is een
rekenkundige eigenschap van OLS, geen bevinding. De enige eerlijke test is:
schat het model op data tot tijdstip t, voorspel t+1, en vergelijk met een
benchmark die niets weet.

De benchmark is de random walk: "morgen is als vandaag", oftewel een
voorspelling van nul voor het rendement. Dat klinkt triviaal, maar op
financiële data is het ontzettend moeilijk te verslaan — en een model dat het
niet lukt, voegt niets toe.

Newey-West standaardfouten
--------------------------
Gewone OLS-standaardfouten maken twee aannames die in deze data geschonden
worden:

1. **Homoskedasticiteit** — constante variantie van de fouten. Fase 1 liet
   zien dat volatiliteit clustert: in onrustige periodes zijn de fouten groter.
2. **Geen autocorrelatie** in de fouten.

Bij overtreding zijn de standaardfouten te klein, en lijkt alles significanter
dan het is. Newey-West corrigeert daarvoor door de covariantiematrix te
berekenen met een venster over naburige waarnemingen.

Belangrijk: Newey-West repareert de *standaardfouten*, niet de coëfficiënten.
Die blijven precies hetzelfde. Het model wordt er niet beter van; je krijgt
alleen een eerlijker beeld van de onzekerheid.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import Ridge


@dataclass
class RegressionResult:
    """Uitkomst van één regressie, met en zonder correctie.

    Attributen:
        coefficients: Geschatte coëfficiënten per driver.
        standard_errors_ols: Gewone OLS-standaardfouten.
        standard_errors_nw: Newey-West gecorrigeerde standaardfouten.
        t_values_nw: t-waarden op basis van de gecorrigeerde fouten.
        p_values_nw: p-waarden idem.
        r_squared: In-sample verklaarde variantie.
        r_squared_adj: Idem, gecorrigeerd voor het aantal variabelen.
        n_observations: Aantal gebruikte waarnemingen.
        vif: Variance Inflation Factor per driver, als maat voor
            multicollineariteit.
    """

    coefficients: pd.Series
    standard_errors_ols: pd.Series
    standard_errors_nw: pd.Series
    t_values_nw: pd.Series
    p_values_nw: pd.Series
    r_squared: float
    r_squared_adj: float
    n_observations: int
    vif: pd.Series

    def to_frame(self) -> pd.DataFrame:
        """Tabel met de coëfficiënten en hun betrouwbaarheid."""
        return pd.DataFrame(
            {
                "coefficient": self.coefficients,
                "se_ols": self.standard_errors_ols,
                "se_newey_west": self.standard_errors_nw,
                "t_nw": self.t_values_nw,
                "p_nw": self.p_values_nw,
                "vif": self.vif,
            }
        )

    @property
    def se_inflation(self) -> pd.Series:
        """Hoeveel groter de Newey-West fouten zijn dan de gewone.

        Een waarde van 1,5 betekent: de gewone standaardfout onderschatte de
        onzekerheid met een factor 1,5. Dat is precies het bedrag waarmee je
        jezelf voor de gek zou houden zonder correctie.
        """
        return self.standard_errors_nw / self.standard_errors_ols


def compute_vif(design: pd.DataFrame) -> pd.Series:
    """Berekent de Variance Inflation Factor per variabele.

    De VIF meet hoeveel de onzekerheid over een coëfficiënt wordt opgeblazen
    doordat de variabele samenhangt met de andere. Je berekent hem door elke
    driver op alle andere te regresseren: VIF = 1 / (1 - R²).

    Vuistregels:
        VIF < 5   geen probleem
        5 - 10    let op
        > 10      de losse coëfficiënt is niet te interpreteren

    Bij een VIF van 10 is de standaardfout ruim drie keer zo groot als bij
    onafhankelijke drivers (√10 ≈ 3,2).
    """
    values = {}
    for column in design.columns:
        others = design.drop(columns=[column])
        model = sm.OLS(design[column], sm.add_constant(others)).fit()
        values[column] = 1.0 / max(1.0 - model.rsquared, 1e-12)
    return pd.Series(values)


def fit_ols_newey_west(
    target: pd.Series, drivers: pd.DataFrame, *, max_lags: int | None = None
) -> RegressionResult:
    """Schat een OLS-regressie met Newey-West standaardfouten.

    Argumenten:
        target: Afhankelijke variabele (het goudrendement).
        drivers: Verklarende variabelen, al getransformeerd naar stationaire
            veranderingen.
        max_lags: Aantal vertragingen voor de Newey-West correctie. None
            gebruikt de vuistregel 4·(n/100)^(2/9) van Newey en West, die de
            bandbreedte met de steekproefgrootte laat meegroeien.

    Geeft terug:
        ``RegressionResult`` met beide soorten standaardfouten, zodat je het
        verschil kunt zien.
    """
    data = pd.concat([target, drivers], axis=1).dropna()
    y = data.iloc[:, 0]
    X = sm.add_constant(data.iloc[:, 1:])

    if max_lags is None:
        max_lags = int(np.ceil(4 * (len(data) / 100) ** (2 / 9)))

    plain = sm.OLS(y, X).fit()
    robust = sm.OLS(y, X).fit(
        cov_type="HAC", cov_kwds={"maxlags": max_lags, "use_correction": True}
    )

    driver_names = list(drivers.columns)
    vif = compute_vif(data.iloc[:, 1:])

    return RegressionResult(
        coefficients=robust.params[driver_names],
        standard_errors_ols=plain.bse[driver_names],
        standard_errors_nw=robust.bse[driver_names],
        t_values_nw=robust.tvalues[driver_names],
        p_values_nw=robust.pvalues[driver_names],
        r_squared=float(robust.rsquared),
        r_squared_adj=float(robust.rsquared_adj),
        n_observations=int(len(data)),
        vif=vif,
    )


# --------------------------------------------------------------------------
# Walk-forward validatie
# --------------------------------------------------------------------------


@dataclass
class WalkForwardResult:
    """Uitkomst van een walk-forward backtest.

    Attributen:
        predictions: Voorspellingen per model, op de testdata.
        actuals: De werkelijke uitkomsten.
        metrics: Per model de RMSE, directional accuracy en R² out-of-sample.
        n_folds: Aantal keer dat het model opnieuw geschat is.
        horizon: Aantal dagen dat per keer vooruit voorspeld werd.
    """

    predictions: pd.DataFrame
    actuals: pd.Series
    metrics: pd.DataFrame
    n_folds: int
    horizon: int


def _directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Aandeel van de keren dat het teken van de voorspelling klopte.

    Geeft NaN terug als het model geen richting voorspelt. Dat is het geval
    bij de random walk, die altijd nul voorspelt: nul heeft geen teken, dus
    "0% correct" zou misleidend zijn — het model doet simpelweg geen uitspraak
    over de richting.

    Gevallen waarin de werkelijke verandering exact nul is, laten we ook weg:
    die hebben geen richting om te voorspellen.
    """
    if np.all(predicted == 0):
        return float("nan")
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.sign(predicted[mask]) == np.sign(actual[mask])))


def _out_of_sample_r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    """R² tegen de benchmark 'voorspel altijd nul'.

    Dit is niet de gewone R². De noemer is de som van gekwadrateerde
    werkelijke waarden, niet de afwijking van hun gemiddelde. Zo meet je
    direct of het model beter is dan "geen verandering voorspellen" — de
    random walk.

    Een negatieve waarde betekent: het model is SLECHTER dan niets doen.
    """
    numerator = float(np.sum((actual - predicted) ** 2))
    denominator = float(np.sum(actual**2))
    if denominator == 0:
        return float("nan")
    return 1.0 - numerator / denominator


def walk_forward_validate(
    target: pd.Series,
    drivers: pd.DataFrame,
    *,
    min_train: int = 1000,
    horizon: int = 1,
    step: int = 21,
    ridge_alpha: float = 1.0,
) -> WalkForwardResult:
    """Valideert de modellen out-of-sample, zonder look-ahead.

    Werkwijze: begin met ``min_train`` waarnemingen, schat de modellen,
    voorspel de volgende ``horizon`` dagen, schuif ``step`` dagen op, herhaal.
    Op elk moment gebruikt het model alleen data van vóór de voorspelde
    periode.

    De drivers worden met één dag gelagd voordat ze het model in gaan. Dat is
    essentieel en volgt uit fase 1: FRED publiceert de waarde van dag t pas op
    werkdag t+1, dus het rendement van vandaag verklaren uit de rente van
    vandaag zou look-ahead bias zijn.

    De modellen die we vergelijken:
        random_walk  voorspelt altijd nul (geen verandering)
        historisch   voorspelt het gemiddelde rendement uit de trainingsdata
        ols          gewone regressie op alle drivers
        ridge        geregulariseerde regressie, tegen multicollineariteit

    Argumenten:
        target: Het goudrendement.
        drivers: De verklarende variabelen, ONGELAGD; deze functie lagt ze.
        min_train: Minimale trainingsperiode in dagen.
        horizon: Hoeveel dagen vooruit per keer.
        step: Hoeveel dagen de vensters opschuiven.
        ridge_alpha: Regularisatiesterkte voor ridge.
    """
    # Lag de drivers: informatie van dag t-1 verklaart het rendement van dag t.
    lagged = drivers.shift(1)
    data = pd.concat([target, lagged], axis=1).dropna()
    y = data.iloc[:, 0]
    X = data.iloc[:, 1:]

    n = len(data)
    records: list[dict] = []
    n_folds = 0

    for train_end in range(min_train, n - horizon + 1, step):
        train_y = y.iloc[:train_end]
        train_X = X.iloc[:train_end]
        test_y = y.iloc[train_end : train_end + horizon]
        test_X = X.iloc[train_end : train_end + horizon]

        if len(test_y) == 0:
            break

        # OLS, geschat op alleen de trainingsdata.
        ols_model = sm.OLS(train_y, sm.add_constant(train_X)).fit()
        ols_prediction = ols_model.predict(sm.add_constant(test_X, has_constant="add"))

        # Ridge, met gestandaardiseerde drivers. Standaardiseren gebeurt op
        # de TRAININGSDATA; de testdata wordt met diezelfde schaling
        # omgezet. Anders lekt informatie uit de testperiode naar binnen.
        train_mean = train_X.mean()
        train_std = train_X.std().replace(0.0, 1.0)
        ridge = Ridge(alpha=ridge_alpha)
        ridge.fit((train_X - train_mean) / train_std, train_y)
        ridge_prediction = ridge.predict((test_X - train_mean) / train_std)

        for index, date in enumerate(test_y.index):
            records.append(
                {
                    "date": date,
                    "actual": float(test_y.iloc[index]),
                    "random_walk": 0.0,
                    "historisch": float(train_y.mean()),
                    "ols": float(np.asarray(ols_prediction)[index]),
                    "ridge": float(np.asarray(ridge_prediction)[index]),
                }
            )
        n_folds += 1

    frame = pd.DataFrame(records).set_index("date")
    actuals = frame["actual"]
    model_names = ["random_walk", "historisch", "ols", "ridge"]
    predictions = frame[model_names]

    metric_rows = []
    for name in model_names:
        predicted = predictions[name].to_numpy()
        actual = actuals.to_numpy()
        metric_rows.append(
            {
                "model": name,
                "rmse": float(np.sqrt(np.mean((actual - predicted) ** 2))),
                "mae": float(np.mean(np.abs(actual - predicted))),
                "directional_accuracy": _directional_accuracy(actual, predicted),
                "r2_oos": _out_of_sample_r2(actual, predicted),
            }
        )

    metrics = pd.DataFrame(metric_rows).set_index("model")
    baseline_rmse = float(metrics.loc["random_walk", "rmse"])
    metrics["rmse_vs_benchmark_pct"] = (
        metrics["rmse"] / baseline_rmse - 1.0
    ) * 100

    return WalkForwardResult(
        predictions=predictions,
        actuals=actuals,
        metrics=metrics,
        n_folds=n_folds,
        horizon=horizon,
    )


def diebold_mariano(
    actual: pd.Series, first: pd.Series, second: pd.Series, *, max_lags: int = 5
) -> dict:
    """Toetst of twee modellen significant verschillend presteren.

    Het probleem dat dit oplost: model A kan een lagere RMSE hebben dan model
    B door toeval. De Diebold-Mariano-toets kijkt of het verschil in
    voorspelfouten systematisch is.

    Werkwijze: bereken per dag het verschil in gekwadrateerde fout tussen de
    twee modellen, en toets of het gemiddelde daarvan nul is — met
    Newey-West standaardfouten, want die verschilreeks is zelf
    geautocorreleerd.

    Geeft terug:
        Dict met de toetsingsgrootheid, de p-waarde, en welk model beter was.
        Een negatieve statistiek betekent dat ``first`` beter is.
    """
    loss_difference = (actual - first) ** 2 - (actual - second) ** 2
    loss_difference = loss_difference.dropna()

    if len(loss_difference) < 20:
        return {
            "statistic": float("nan"),
            "p_value": float("nan"),
            "better": "onbepaald",
            "n": len(loss_difference),
        }

    model = sm.OLS(
        loss_difference.to_numpy(), np.ones(len(loss_difference))
    ).fit(cov_type="HAC", cov_kwds={"maxlags": max_lags, "use_correction": True})

    statistic = float(model.tvalues[0])
    p_value = float(model.pvalues[0])

    if p_value >= 0.05:
        better = "geen significant verschil"
    elif statistic < 0:
        better = "eerste model"
    else:
        better = "tweede model"

    return {
        "statistic": statistic,
        "p_value": p_value,
        "better": better,
        "n": int(len(loss_difference)),
        "mean_loss_difference": float(loss_difference.mean()),
    }


def horizon_comparison(
    target_prices: pd.Series,
    drivers: pd.DataFrame,
    *,
    horizons: tuple[int, ...] = (1, 5, 21, 63),
    min_train: int = 750,
) -> pd.DataFrame:
    """Vergelijkt de voorspelbaarheid over verschillende horizonnen.

    Fase 2 vond zwakke dagcorrelaties, maar dat sluit sterkere verbanden op
    maand- of kwartaalbasis niet uit: ruis dempt uit bij aggregatie terwijl
    een echt signaal blijft staan.

    Per horizon aggregeren we de rendementen over die periode en toetsen we
    of de drivers ze voorspellen. Let op de kanttekening bij de uitkomst:
    langere horizonnen betekenen minder onafhankelijke waarnemingen, dus meer
    onzekerheid over elke schatting.
    """
    rows = []
    for horizon in horizons:
        # Rendement over de komende `horizon` dagen, uit de prijsreeks.
        forward_return = (
            np.log(target_prices.shift(-horizon) / target_prices)
        ).dropna()

        # Steekproef verdunnen tot niet-overlappende vensters, zodat de
        # waarnemingen onafhankelijk zijn.
        thinned = forward_return.iloc[::horizon]
        thinned_drivers = drivers.reindex(thinned.index)

        aligned = pd.concat([thinned, thinned_drivers], axis=1).dropna()
        if len(aligned) < min_train // horizon + 30:
            rows.append(
                {
                    "horizon_dagen": horizon,
                    "n": len(aligned),
                    "r2_in_sample": float("nan"),
                    "r2_oos": float("nan"),
                    "opmerking": "te weinig waarnemingen",
                }
            )
            continue

        result = fit_ols_newey_west(aligned.iloc[:, 0], aligned.iloc[:, 1:])

        # Simpele out-of-sample check: eerste 70% trainen, rest testen.
        split = int(len(aligned) * 0.7)
        train = aligned.iloc[:split]
        test = aligned.iloc[split:]
        model = sm.OLS(
            train.iloc[:, 0], sm.add_constant(train.iloc[:, 1:])
        ).fit()
        predicted = model.predict(
            sm.add_constant(test.iloc[:, 1:], has_constant="add")
        )

        rows.append(
            {
                "horizon_dagen": horizon,
                "n": result.n_observations,
                "r2_in_sample": result.r_squared,
                "r2_oos": _out_of_sample_r2(
                    test.iloc[:, 0].to_numpy(), np.asarray(predicted)
                ),
                "opmerking": "",
            }
        )

    return pd.DataFrame(rows)
