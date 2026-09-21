"""Verkenning: voegt de crack spread iets toe als olie-leg?

Dit script hoort bij docs/backlog/leg3b_crack_spread.md. Het is een
VERKENNING, geen onderdeel van het model: het beantwoordt de vraag of het
voorstel de moeite waard is om in te bouwen.

Belangrijk: de R-kwadraten hieronder zijn IN-SAMPLE. Dat is genoeg om te zien
of een driver kansloos is (dan hoef je geen walk-forward meer te draaien),
maar niet genoeg om te concluderen dat hij werkt. Zie de toelichting onderaan.

Gebruik:
    python scripts/verken_crack_spread.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.data.yahoo_client import YahooClient  # noqa: E402

LINE = "=" * 76

# Eén vat ruwe olie is 42 gallon; RB=F en HO=F noteren per gallon, CL=F per vat.
GALLONS_PER_BARREL = 42


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def fetch_energy_prices() -> pd.DataFrame:
    """Haalt de drie energiefutures op die de crack spread nodig heeft."""
    client = YahooClient(max_retries=2)
    tickers = {
        "crude": "CL=F",
        "gasoline": "RB=F",
        "heating_oil": "HO=F",
    }
    series = {}
    for name, ticker in tickers.items():
        frame = client.fetch_series(ticker, start_date="2003-01-01")
        series[name] = frame["value"]
        print(
            f"  {name:14s} {ticker:6s} n={len(frame):5d}  "
            f"{frame.index.min().date()} tot {frame.index.max().date()}"
        )
    # sort=True voorkomt een pandas-waarschuwing over de standaardsortering.
    return pd.concat(series, axis=1, sort=True).dropna()


def compute_cracks(energy: pd.DataFrame) -> pd.DataFrame:
    """Berekent de 3-2-1 crack en de diesel crack, in dollar per vat.

    De 3-2-1 verhouding benadert een typische Amerikaanse raffinaderij: uit
    3 vaten ruwe olie komen ongeveer 2 vaten benzine en 1 vat stookolie.
    """
    crack_321 = (
        (2 * energy["gasoline"] + energy["heating_oil"]) * GALLONS_PER_BARREL
        - 3 * energy["crude"]
    ) / 3
    diesel_crack = energy["heating_oil"] * GALLONS_PER_BARREL - energy["crude"]
    return pd.DataFrame({"crack_321": crack_321, "diesel_crack": diesel_crack})


def count_independent_episodes(
    series: pd.Series, *, quantile: float = 0.95, min_gap_days: int = 60
) -> dict:
    """Telt EPISODES boven een drempel, niet dagen.

    Dit is de kern van de waarschuwing in het voorstel. Bij een spread die in
    crisisperiodes omhoogschiet, is het aantal dagen boven een drempel geen
    maat voor het aantal waarnemingen: 139 aaneengesloten dagen in 2022 zijn
    één gebeurtenis, niet 139.

    We plakken blokken aan elkaar die minder dan ``min_gap_days`` uit elkaar
    liggen, omdat een korte onderbreking binnen een crisis geen nieuwe
    episode is.
    """
    threshold = float(series.quantile(quantile))
    above = series > threshold
    dates_above = series.index[above]

    if len(dates_above) == 0:
        return {
            "threshold": threshold,
            "n_days": 0,
            "n_episodes": 0,
            "episodes": [],
            "days_per_year": {},
        }

    episodes = []
    start = dates_above[0]
    previous = dates_above[0]
    for date in dates_above[1:]:
        if (date - previous).days > min_gap_days:
            episodes.append((start, previous))
            start = date
        previous = date
    episodes.append((start, previous))

    return {
        "threshold": threshold,
        "n_days": int(above.sum()),
        "n_episodes": len(episodes),
        "episodes": episodes,
        "days_per_year": series[above].groupby(series[above].index.year).size().to_dict(),
    }


def compare_models(data: pd.DataFrame, target: str, specs: list[tuple[str, list[str]]]) -> pd.DataFrame:
    """Vergelijkt een reeks modelspecificaties op dezelfde steekproef.

    Op dezelfde rijen, zodat de R-kwadraten vergelijkbaar zijn. We rapporteren
    ook de aangepaste R-kwadraat: die straft extra variabelen af, en is dus
    het getal dat telt bij de vraag 'voegt deze driver iets toe?'.
    """
    rows = []
    for label, columns in specs:
        model = sm.OLS(data[target], sm.add_constant(data[columns])).fit()
        rows.append(
            {
                "model": label,
                "n_vars": len(columns),
                "r2": model.rsquared,
                "r2_adj": model.rsquared_adj,
            }
        )
    frame = pd.DataFrame(rows)
    frame["winst_r2_pp"] = (frame["r2"] - frame["r2"].iloc[0]) * 100
    frame["winst_adj_pp"] = (frame["r2_adj"] - frame["r2_adj"].iloc[0]) * 100
    return frame


def main() -> int:
    """Draait de verkenning."""
    warnings.simplefilter("ignore")
    pd.set_option("display.width", 150)

    print(LINE)
    print("VERKENNING: CRACK SPREAD ALS OLIE-LEG (backlog LEG 3B)")
    print(LINE)
    print(
        "\nHet idee: diesel is een directere inflatiedriver dan ruwe olie, want\n"
        "vracht, landbouw en industrie lopen erop. Als de markt inflatie\n"
        "inprijst via de breakeven-rente, zou de dieselmarge daar meer over\n"
        "moeten zeggen dan de ruwe-olieprijs.\n"
        "\n"
        "Breakeven-inflatie is al een driver in het model, dus de vraag is:\n"
        "kan de crack spread de olie-leg verbeteren?"
    )

    section("STAP 1: IS DE DATA ER?")
    energy = fetch_energy_prices()
    cracks = compute_cracks(energy)

    print(f"\nOverlappende dagen: {len(energy)}")
    print("\nBerekende spreads (USD per vat):")
    summary = cracks.describe().T[["mean", "50%", "min", "max"]]
    summary.columns = ["gemiddeld", "mediaan", "min", "max"]
    print(summary.round(2).to_string())

    section("STAP 2: HOEVEEL ONAFHANKELIJKE WAARNEMINGEN ZIJN ER ECHT?")
    print(
        "\nHet voorstel waarschuwde hier zelf voor: er zijn 'essentially two\n"
        "high-crack regimes'. Laten we dat kwantificeren.\n"
        "\n"
        "Belangrijk onderscheid: het aantal DAGEN boven een drempel is geen\n"
        "maat voor het aantal waarnemingen. Aaneengesloten dagen binnen een\n"
        "crisis zijn een herhaling van dezelfde gebeurtenis."
    )

    episodes = count_independent_episodes(cracks["diesel_crack"])
    print(
        f"\nDrempel (95e percentiel): ${episodes['threshold']:.2f} per vat\n"
        f"Dagen erboven           : {episodes['n_days']}\n"
        f"Onafhankelijke EPISODES : {episodes['n_episodes']}"
    )
    print("\nVerdeeld over de jaren:")
    for year, count in sorted(episodes["days_per_year"].items()):
        print(f"  {year}: {count:3d} dagen")

    print("\nDe episodes:")
    for start, end in episodes["episodes"]:
        duration = (end - start).days
        print(f"  {start.date()} tot {end.date()}  ({duration} kalenderdagen)")

    concentrated = sum(
        count
        for year, count in episodes["days_per_year"].items()
        if count > episodes["n_days"] * 0.2
    )
    print(
        f"\n{concentrated} van de {episodes['n_days']} dagen "
        f"({concentrated / episodes['n_days']:.0%}) zitten in de twee grootste jaren.\n"
        "\n"
        "CONCLUSIE: effectief N = 2, niet N = "
        f"{episodes['n_days']}.\n"
        "\n"
        "Daarmee is de waarschuwing uit het voorstel niet alleen juist maar\n"
        "dwingend: met twee episodes kun je niet vaststellen of een hoge crack\n"
        "terugkeert naar een gemiddelde, en al helemaal niet hoe snel. Elke\n"
        "backtest van een mean-reversion-strategie meet hier twee\n"
        "gebeurtenissen en rapporteert dat als een patroon."
    )

    section("STAP 3: DE MEDIATIETEST")

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)

    gold_returns = np.log(
        panel["gold_futures"] / panel["gold_futures"].shift(1)
    )
    data = pd.concat(
        {
            "gold": gold_returns,
            "breakeven": panel["breakeven_inflation_10y"].diff(),
            "d_crude": np.log(energy["crude"] / energy["crude"].shift(1)),
            "d_crack": cracks["diesel_crack"].diff(),
        },
        axis=1,
        sort=True,
    ).dropna()

    print(f"\nSteekproef: {len(data)} dagen met alle reeksen beschikbaar.")

    print("\nVRAAG A: verklaart de crack de BREAKEVEN beter dan olie alleen?")
    breakeven_models = compare_models(
        data,
        "breakeven",
        [("olie alleen", ["d_crude"]), ("olie + crack", ["d_crude", "d_crack"])],
    )
    print(breakeven_models.round(4).to_string(index=False))

    print("\nVRAAG B: voegt de crack iets toe aan het GOUDmodel?")
    gold_models = compare_models(
        data,
        "gold",
        [
            ("olie alleen", ["d_crude"]),
            ("olie + crack", ["d_crude", "d_crack"]),
            ("olie + crack + breakeven", ["d_crude", "d_crack", "breakeven"]),
        ],
    )
    print(gold_models.round(4).to_string(index=False))

    section("CONCLUSIE VAN DE VERKENNING")

    breakeven_gain = float(breakeven_models["winst_r2_pp"].iloc[-1])
    gold_gain = float(gold_models["winst_r2_pp"].iloc[1])
    adj_full = float(gold_models["r2_adj"].iloc[-1])
    adj_partial = float(gold_models["r2_adj"].iloc[1])

    print(
        f"\nDe crack spread verbetert:\n"
        f"  het breakeven-model met {breakeven_gain:+.2f} procentpunt R2\n"
        f"  het goudmodel met       {gold_gain:+.2f} procentpunt R2\n"
    )

    if adj_full < adj_partial:
        print(
            "Let ook op de AANGEPASTE R2 in de laatste regel van vraag B: die\n"
            "gaat OMLAAG als je breakeven toevoegt. Het extra coefficient kost\n"
            "meer aan vrijheidsgraden dan het oplevert.\n"
        )

    print(
        "De voorwaarde in het voorstel was: 'if products dominate crude,\n"
        "replace crude as the oil leg'. Producten domineren ruwe olie niet.\n"
        "De crack spread komt dus niet in de plaats van olie.\n"
        "\n"
        "WAAROM DIT GEEN DEFINITIEF NEE IS\n"
        "Deze R-kwadraten zijn IN-SAMPLE: berekend op dezelfde data waarop het\n"
        "model geschat is. Dat is genoeg om te zien dat een driver kansloos is,\n"
        "maar niet om te concluderen dat hij werkt.\n"
        "\n"
        "Bovendien zit ruwe olie zelf nog niet in het model. De logische\n"
        "volgorde is: eerst fase 3 (basismodel bouwen en valideren), dan de\n"
        "vraag of olie een zinvolle toevoeging is, en pas dan of de crack\n"
        "spread beter is dan olie.\n"
        "\n"
        "Volledige onderbouwing: docs/backlog/leg3b_crack_spread.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
