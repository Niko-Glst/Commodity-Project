"""Van positie naar rendement na kosten.

Wat dit doet
------------
Een positie is nog geen rendement. Deze module rekent door wat een strategie
werkelijk oplevert, met drie dingen die de meeste backtests verkeerd doen:

1. **Executie-lag.** Je handelt op informatie van dag t, maar je positie gaat
   pas in op dag t+1. Zonder die verschuiving handel je op de slotkoers van
   een dag waarvan je de slotkoers nog niet kent. Dat is de meest voorkomende
   vorm van look-ahead bias in backtests, en hij maakt elk resultaat waardeloos.

2. **Transactiekosten.** Elke verandering in de positie kost geld: commissie,
   en het verschil tussen bied- en laatprijs.

3. **Slippage.** De prijs waartegen je werkelijk handelt wijkt af van de
   slotkoers die je in je data ziet. Bij een liquide contract als goud is dat
   klein, maar niet nul.

Waarom de kosten apart staan
----------------------------
Omdat het brutoresultaat en het nettoresultaat verschillende dingen zeggen.
Een strategie die bruto nét positief is en netto negatief, heeft geen signaal
gevonden maar een kostenpost. Door beide te rapporteren is dat zichtbaar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from goldmodel.signal import turnover

TRADING_DAYS_PER_YEAR = 252


@dataclass
class CostModel:
    """Transactiekosten voor één handelsinstrument.

    Attributen:
        commission_bps: Commissie per transactie, in basispunten van de
            notionele waarde. Bij COMEX-goudfutures is dit laag; een
            institutionele partij betaalt enkele dollars per contract op een
            notionele waarde van ruim $400.000.
        half_spread_bps: De helft van het verschil tussen bied- en laatprijs.
            Je betaalt dit bij elke transactie, want je koopt op de laatprijs
            en verkoopt op de biedprijs.
        slippage_bps: Extra afwijking van de slotkoers. Bij grote orders of
            in onrustige markten loopt dit op.

    Realistische waarden voor goudfutures (GC=F)
    --------------------------------------------
    Goud is een van de liquidste futurescontracten ter wereld. De spread is
    doorgaans 10 cent op een prijs van ruim $4.000, dus ongeveer 0,25
    basispunten. Commissie is verwaarloosbaar op institutionele schaal.

    De standaardwaarden hieronder zijn daarom BEWUST CONSERVATIEF gekozen
    (hoger dan wat een grote partij betaalt): 1 basispunt totaal per
    transactie. Wie de strategie afwijst op basis van deze kosten, wijst hem
    ook af bij realistischere kosten.
    """

    commission_bps: float = 0.2
    half_spread_bps: float = 0.3
    slippage_bps: float = 0.5

    @property
    def total_bps(self) -> float:
        """Totale kosten per eenheid omzet, in basispunten."""
        return self.commission_bps + self.half_spread_bps + self.slippage_bps

    @property
    def total_fraction(self) -> float:
        """Idem, als fractie."""
        return self.total_bps / 10_000.0


@dataclass
class BacktestResult:
    """Uitkomst van een backtest.

    Attributen:
        gross_returns: Rendement per dag vóór kosten.
        net_returns: Rendement per dag ná kosten.
        costs: Kosten per dag.
        positions: De GEWENSTE positie per dag (op basis van informatie
            van die dag).
        executed_positions: De WERKELIJKE positie, één dag later.
        settings: Wat er gebruikt is.
    """

    gross_returns: pd.Series
    net_returns: pd.Series
    costs: pd.Series
    positions: pd.Series
    executed_positions: pd.Series
    cost_model: CostModel
    execution_lag: int
    metrics: dict = field(default_factory=dict)

    def equity_curve(self, *, net: bool = True) -> pd.Series:
        """Cumulatieve waardeontwikkeling, startend op 1."""
        returns = self.net_returns if net else self.gross_returns
        return (1.0 + returns).cumprod()


def _performance_metrics(returns: pd.Series, *, label: str = "") -> dict:
    """Berekent de standaardmaten voor een rendementsreeks.

    Let op de Sharpe-ratio: die wordt hier zonder risicovrije rente berekend
    (dus strikt genomen een information ratio ten opzichte van nul). Bij een
    futures-positie is dat verdedigbaar, want je legt geen kapitaal vast
    behalve de marge.

    Belangrijker: bij een strategie zonder signaal is de Sharpe-ratio een
    ruisgetal. De standaardfout van een Sharpe over n jaar is ongeveer
    1/sqrt(n), dus bij 20 jaar data is alles onder 0,22 niet van nul te
    onderscheiden. Dat rapporteren we expliciet.
    """
    clean = returns.dropna()
    n = len(clean)
    if n == 0:
        return {"n": 0}

    mean_daily = float(clean.mean())
    std_daily = float(clean.std())
    years = n / TRADING_DAYS_PER_YEAR

    annual_return = mean_daily * TRADING_DAYS_PER_YEAR
    annual_volatility = std_daily * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = annual_return / annual_volatility if annual_volatility > 0 else 0.0

    # Standaardfout van de Sharpe-ratio, eerste orde: 1/sqrt(jaren).
    sharpe_standard_error = 1.0 / np.sqrt(years) if years > 0 else float("inf")

    equity = (1.0 + clean).cumprod()
    drawdown = equity / equity.cummax() - 1.0

    return {
        "label": label,
        "n": n,
        "years": float(years),
        "total_return": float(equity.iloc[-1] - 1.0),
        "annual_return": float(annual_return),
        "annual_volatility": float(annual_volatility),
        "sharpe": float(sharpe),
        "sharpe_standard_error": float(sharpe_standard_error),
        "sharpe_t_statistic": float(sharpe / sharpe_standard_error)
        if sharpe_standard_error > 0
        else 0.0,
        "max_drawdown": float(drawdown.min()),
        "hit_rate": float((clean > 0).mean()),
        "worst_day": float(clean.min()),
        "best_day": float(clean.max()),
    }


def run_backtest(
    positions: pd.Series,
    asset_returns: pd.Series,
    *,
    cost_model: CostModel | None = None,
    execution_lag: int = 1,
) -> BacktestResult:
    """Rekent een positiereeks door naar rendement na kosten.

    Argumenten:
        positions: De gewenste positie per dag, gebaseerd op informatie die op
            die dag beschikbaar is.
        asset_returns: Het rendement van het onderliggende instrument per dag.
        cost_model: Transactiekosten; None gebruikt de conservatieve standaard.
        execution_lag: Aantal dagen tussen signaal en uitvoering. **Moet
            minstens 1 zijn.** Zie de uitleg hieronder.

    Geeft terug:
        ``BacktestResult`` met bruto- en nettorendement.

    Waarom de executie-lag verplicht is
    -----------------------------------
    Je berekent je signaal uit de slotkoers van dag t. Die ken je pas als de
    markt gesloten is. Je kunt dus niet meer op dag t handelen — je positie
    gaat in op dag t+1, en verdient het rendement van dag t+1.

    Zonder die verschuiving vermenigvuldig je de positie van dag t met het
    rendement van dag t, en dat rendement zit al in het signaal. Dan meet je
    hoe goed je de koers van vandaag kunt "voorspellen" met de koers van
    vandaag. Het resultaat is altijd prachtig en altijd onzin.

    Deze functie weigert daarom een lag van nul.
    """
    if execution_lag < 1:
        raise ValueError(
            "execution_lag moet minstens 1 zijn. Een lag van nul betekent "
            "handelen op de slotkoers van een dag die nog niet gesloten is — "
            "dat is look-ahead bias en maakt elk resultaat waardeloos."
        )

    cost_model = cost_model or CostModel()

    # De positie van vandaag wordt morgen uitgevoerd.
    executed = positions.shift(execution_lag)

    aligned = pd.concat(
        [executed.rename("position"), asset_returns.rename("asset")], axis=1
    ).dropna()

    gross = aligned["position"] * aligned["asset"]

    # Kosten volgen de VERANDERING in de uitgevoerde positie, niet in de
    # gewenste: je betaalt op het moment dat je daadwerkelijk handelt.
    traded = turnover(aligned["position"])
    costs = traded * cost_model.total_fraction

    net = gross - costs

    metrics = {
        "gross": _performance_metrics(gross, label="bruto"),
        "net": _performance_metrics(net, label="netto"),
        "total_costs": float(costs.sum()),
        "cost_drag_annual": float(costs.mean() * TRADING_DAYS_PER_YEAR),
        "execution_lag": execution_lag,
        "cost_bps_per_trade": cost_model.total_bps,
    }

    return BacktestResult(
        gross_returns=gross,
        net_returns=net,
        costs=costs,
        positions=positions,
        executed_positions=executed,
        cost_model=cost_model,
        execution_lag=execution_lag,
        metrics=metrics,
    )


def compare_to_benchmarks(
    result: BacktestResult, asset_returns: pd.Series
) -> pd.DataFrame:
    """Zet de strategie naast passieve alternatieven.

    De benchmarks:
        buy & hold      altijd voluit long
        altijd short    altijd voluit short
        niets doen      nul rendement, nul kosten

    Die laatste lijkt flauw maar is de belangrijkste: een strategie die "niets
    doen" niet verslaat, heeft geld gekost om tot stilstand te komen.
    """
    common = result.net_returns.index

    rows = [
        _performance_metrics(result.gross_returns, label="strategie (bruto)"),
        _performance_metrics(result.net_returns, label="strategie (netto)"),
        _performance_metrics(asset_returns.reindex(common).dropna(), label="buy & hold"),
        _performance_metrics(
            -asset_returns.reindex(common).dropna(), label="altijd short"
        ),
        _performance_metrics(
            pd.Series(0.0, index=common), label="niets doen"
        ),
    ]
    return pd.DataFrame(rows).set_index("label")


def sharpe_significance(returns: pd.Series) -> dict:
    """Is de Sharpe-ratio te onderscheiden van nul?

    De vraag die bij elke gerapporteerde Sharpe hoort. Met n jaar data is de
    standaardfout ongeveer 1/sqrt(n): bij 20 jaar is dat 0,22, dus een Sharpe
    van 0,3 is niet significant.

    Dit wordt in de praktijk zelden gerapporteerd, en dat is precies waarom
    zoveel backtests een "goede" Sharpe laten zien die uit ruis bestaat.
    """
    clean = returns.dropna()
    n = len(clean)
    if n < 30:
        return {"n": n, "sharpe": float("nan"), "significant": False}

    years = n / TRADING_DAYS_PER_YEAR
    mean_daily = float(clean.mean())
    std_daily = float(clean.std())
    sharpe = (
        mean_daily * TRADING_DAYS_PER_YEAR / (std_daily * np.sqrt(TRADING_DAYS_PER_YEAR))
        if std_daily > 0
        else 0.0
    )
    standard_error = 1.0 / np.sqrt(years)
    t_statistic = sharpe / standard_error

    return {
        "n": n,
        "years": float(years),
        "sharpe": float(sharpe),
        "standard_error": float(standard_error),
        "t_statistic": float(t_statistic),
        # Tweezijdig op 5%: |t| > 1,96.
        "significant": bool(abs(t_statistic) > 1.96),
        "sharpe_needed_for_significance": float(1.96 * standard_error),
    }


def placebo_backtest(
    positions: pd.Series,
    asset_returns: pd.Series,
    *,
    n_trials: int = 200,
    seed: int = 42,
    cost_model: CostModel | None = None,
) -> dict:
    """Draait de backtest op geschudde datums.

    De vraag: als ik mijn positiereeks willekeurig door de tijd husselt, haal
    ik dan een vergelijkbaar resultaat? Zo ja, dan komt mijn rendement niet
    uit de koppeling tussen signaal en koers.

    Dit is de placebo die bij elke backtest hoort en die bijna nooit
    gerapporteerd wordt.
    """
    rng = np.random.default_rng(seed)
    cost_model = cost_model or CostModel()

    real = run_backtest(positions, asset_returns, cost_model=cost_model)
    real_sharpe = float(real.metrics["net"]["sharpe"])

    placebo_sharpes = np.empty(n_trials)
    for trial in range(n_trials):
        shuffled = pd.Series(
            rng.permutation(positions.to_numpy()), index=positions.index
        )
        outcome = run_backtest(shuffled, asset_returns, cost_model=cost_model)
        placebo_sharpes[trial] = float(outcome.metrics["net"]["sharpe"])

    percentile = float((placebo_sharpes < real_sharpe).mean() * 100)

    return {
        "real_sharpe": real_sharpe,
        "placebo_median": float(np.median(placebo_sharpes)),
        "placebo_p95": float(np.percentile(placebo_sharpes, 95)),
        "placebo_max": float(placebo_sharpes.max()),
        "percentile_of_real": percentile,
        "distinguishable": bool(percentile >= 95.0),
        "n_trials": n_trials,
    }
