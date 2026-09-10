"""Haalt alle geconfigureerde reeksen op en toont basisstatistieken.

Dit is het controlescript voor fase 1: als dit draait en er redelijke
getallen uitkomen, werkt de datalaag.

Gebruik:
    python scripts/fetch_data.py                 # cache-eerst
    python scripts/fetch_data.py --refresh       # negeer de cache
    python scripts/fetch_data.py --core          # alleen de kernreeksen
    python scripts/fetch_data.py --cache-info    # toon alleen de cache-inhoud
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Zorg dat 'src' op het pad staat, zodat het script zonder installatie werkt.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from goldmodel.config import (  # noqa: E402
    ALL_SERIES,
    DEFAULT_FETCH_SETTINGS,
    core_series,
    get_cache_dir,
    get_fred_api_key,
)
from goldmodel.data.loader import DataLoader  # noqa: E402

SEPARATOR = "=" * 78


def configure_output() -> None:
    """Zet logging en pandas-weergave zo dat de output leesbaar blijft."""
    logging.basicConfig(
        level=logging.WARNING,
        format="[%(levelname)s] %(message)s",
    )
    pd.set_option("display.width", 140)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.float_format", lambda v: f"{v:,.4f}")


def header(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{SEPARATOR}\n{title}\n{SEPARATOR}")


def show_load_report(report) -> None:
    """Toont per reeks hoe die geladen is."""
    header("1. LAADRAPPORT")
    print(report.to_frame().to_string(index=False))

    stale = [r for r in report.results if r.status.value.startswith("verlopen")]
    if stale:
        print(
            "\nLET OP: de volgende reeksen komen uit een verlopen cache omdat de "
            "bron onbereikbaar was:"
        )
        for r in stale:
            print(f"  - {r.spec.name}: {r.message}")

    if report.failed:
        print("\nNIET GELADEN:")
        for r in report.failed:
            print(f"  - {r.spec.name} ({r.spec.code}): {r.message}")


def show_coverage(panel: pd.DataFrame) -> None:
    """Toont per reeks de dekking: bereik, aantal waarnemingen, gaten."""
    header("2. DEKKING PER REEKS")
    rows = []
    for column in panel.columns:
        series = panel[column].dropna()
        if series.empty:
            continue
        span_days = (series.index.max() - series.index.min()).days
        # Verwacht aantal handelsdagen als ruwe referentie: ~252 per jaar.
        expected = span_days / 365.25 * 252
        rows.append(
            {
                "reeks": column,
                "van": series.index.min().date(),
                "tot": series.index.max().date(),
                "n": len(series),
                "dekking_vs_handelsdagen": f"{len(series) / expected:>6.1%}" if expected > 0 else "n.v.t.",
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))
    print(
        "\nEen dekking rond 100% wijst op een dagelijkse reeks; ~20% op een "
        "wekelijkse. Sterk onder 100% bij een dagelijkse reeks betekent gaten "
        "(feestdagen verschillen per bron)."
    )


def show_levels(panel: pd.DataFrame) -> None:
    """Toont beschrijvende statistieken van de niveaus."""
    header("3. NIVEAUS — BESCHRIJVENDE STATISTIEK")
    print(panel.describe().T.to_string())
    print(
        "\nDeze getallen zijn vooral een sanity check op de eenheden: staat de "
        "goudprijs in dollars per ounce, de reële rente in procenten, de VIX "
        "rond de 15-20? Statistisch zeggen gemiddelde en standaardafwijking van "
        "een niet-stationaire reeks weinig — het 'gemiddelde niveau' van de "
        "goudprijs over twintig jaar is geen grootheid waar je iets mee kunt. "
        "Dat is precies wat de stationariteitstoetsen in fase 2 gaan aantonen."
    )


def show_returns(panel: pd.DataFrame) -> None:
    """Toont rendementsstatistieken voor de prijsreeksen."""
    header("4. DAGELIJKSE LOG-RENDEMENTEN — EERSTE BLIK OP DE STAARTEN")

    price_columns = [
        c for c in ("gold_futures", "silver_futures", "sp500", "dxy") if c in panel.columns
    ]
    if not price_columns:
        print("Geen prijsreeksen geladen.")
        return

    # Log-rendementen: ln(P_t / P_{t-1}). We gebruiken die in plaats van
    # procentuele veranderingen omdat ze optelbaar zijn over de tijd (het
    # rendement over een week is de som van de dagrendementen) en omdat de
    # verdeling symmetrischer is. Bij kleine bewegingen zijn ze vrijwel
    # gelijk aan procentuele rendementen.
    import numpy as np

    returns = np.log(panel[price_columns] / panel[price_columns].shift(1)).dropna(how="all")

    stats = pd.DataFrame(
        {
            "n": returns.count(),
            "gem_dag_%": returns.mean() * 100,
            "std_dag_%": returns.std() * 100,
            "std_jaar_%": returns.std() * (252**0.5) * 100,
            "scheefheid": returns.skew(),
            "kurtosis_exces": returns.kurtosis(),
            "min_%": returns.min() * 100,
            "max_%": returns.max() * 100,
        }
    )
    print(stats.to_string())

    print(
        "\nHoe je dit leest:\n"
        "  scheefheid      0 bij een symmetrische verdeling. Negatief betekent\n"
        "                  dat grote dalingen extremer zijn dan grote stijgingen.\n"
        "  kurtosis_exces  0 bij een normale verdeling. Positief betekent dikke\n"
        "                  staarten: extreme dagen komen vaker voor dan de\n"
        "                  normale verdeling voorspelt. Bij financiële data is\n"
        "                  3 tot 10 gebruikelijk; dat is niet 'een beetje\n"
        "                  afwijkend' maar een fundamenteel andere verdeling.\n"
        "\n"
        "Waarom dit er nu al toe doet: als de kurtosis hier duidelijk boven 0 "
        "ligt, is de aanname van normaal verdeelde schokken in een standaard-GBM "
        "onhoudbaar, en onderschat een VaR-berekening op basis van de normale "
        "verdeling het staartrisico systematisch. Dat is de rechtvaardiging voor "
        "de t-verdeelde schokken in fase 4 — dan is het een onderbouwde keuze "
        "in plaats van een trucje."
    )

    _show_tail_check(returns)


def _show_tail_check(returns: pd.DataFrame) -> None:
    """Vergelijkt waargenomen extreme dagen met wat normaal zou voorspellen."""
    from scipy import stats as sps

    print("\n  Staarttoets: hoe vaak komen bewegingen groter dan 3 standaardafwijkingen voor?")
    rows = []
    for column in returns.columns:
        series = returns[column].dropna()
        if len(series) < 100:
            continue
        standardised = (series - series.mean()) / series.std()
        observed = int((standardised.abs() > 3).sum())
        # Onder normaliteit: P(|Z| > 3) = 0,27%.
        expected = len(series) * 2 * (1 - sps.norm.cdf(3))
        jb_stat, jb_p = sps.jarque_bera(series)
        rows.append(
            {
                "reeks": column,
                "n": len(series),
                "waargenomen_>3sd": observed,
                "verwacht_normaal": round(expected, 1),
                "ratio": round(observed / expected, 1) if expected > 0 else float("nan"),
                "jarque_bera_p": f"{jb_p:.2e}",
            }
        )
    print("  " + pd.DataFrame(rows).to_string(index=False).replace("\n", "\n  "))
    print(
        "\n  De Jarque-Bera-toets toetst of scheefheid en kurtosis samen "
        "verenigbaar zijn met\n  een normale verdeling. Een p-waarde onder 0,05 "
        "verwerpt normaliteit. Bij dagelijkse\n  financiële rendementen is een "
        "p-waarde van vrijwel nul de norm, niet de uitzondering —\n  de toets is "
        "hier dus meer een bevestiging dan een ontdekking."
    )


def show_correlations(panel: pd.DataFrame) -> None:
    """Toont de correlatiematrix van dagelijkse veranderingen."""
    header("5. CORRELATIES TUSSEN DAGELIJKSE VERANDERINGEN")

    changes = panel.diff().dropna(how="all")
    # Alleen kolommen met voldoende overlap meenemen.
    usable = [c for c in changes.columns if changes[c].notna().sum() > 250]
    corr = changes[usable].corr()
    print(corr.to_string())
    print(
        "\nBelangrijk: dit zijn correlaties tussen *veranderingen*, niet tussen "
        "niveaus. Correlaties tussen niveaus van niet-stationaire reeksen zijn "
        "misleidend hoog — twee reeksen die allebei een trend hebben, correleren "
        "sterk zonder enig onderliggend verband (spurious correlation). Dit is "
        "dezelfde reden waarom we in fase 3 regressies op rendementen draaien en "
        "niet op prijsniveaus."
    )

    if {"real_rate_10y", "breakeven_inflation_10y"} <= set(corr.columns):
        print(
            "\nLet op de correlatie tussen real_rate_10y en "
            "breakeven_inflation_10y: die zijn per constructie verbonden "
            "(nominaal = reëel + breakeven), dus een sterke samenhang daar is "
            "een definitie, geen bevinding."
        )
    if {"dxy", "usd_broad_index"} <= set(corr.columns):
        print(
            "\nDXY en usd_broad_index meten allebei de dollar. Een hoge "
            "correlatie is te verwachten; ze samen in één regressie stoppen is "
            "een multicollineariteitsfout. Ze zijn er als robuustheidscheck op "
            "elkaar, niet als twee drivers."
        )


def show_cache_info() -> None:
    """Toont wat er in de cache staat."""
    from goldmodel.data.cache import ParquetCache

    header("CACHE-INHOUD")
    cache = ParquetCache(get_cache_dir())
    summary = cache.summary()
    print(f"Locatie: {get_cache_dir()}")
    if summary.empty:
        print("Cache is leeg.")
    else:
        print(summary.to_string(index=False))


def main() -> int:
    """Voert het ophalen en de rapportage uit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="negeer de cache")
    parser.add_argument("--core", action="store_true", help="alleen kernreeksen")
    parser.add_argument("--cache-info", action="store_true", help="toon cache en stop")
    args = parser.parse_args()

    configure_output()

    if args.cache_info:
        show_cache_info()
        return 0

    header("GOUDPRIJSMODEL — DATALAAG")
    print(f"Cachelocatie : {get_cache_dir()}")
    print(f"FRED-sleutel : {'gevonden' if get_fred_api_key() else 'ONTBREEKT (.env)'}")
    print(f"Periode      : vanaf {DEFAULT_FETCH_SETTINGS.start_date}")
    print(f"Cache-TTL    : {DEFAULT_FETCH_SETTINGS.cache_ttl_hours} uur")

    specs = core_series() if args.core else ALL_SERIES
    print(f"Reeksen      : {len(specs)}")

    loader = DataLoader()
    report = loader.load_all(specs, force_refresh=args.refresh)
    show_load_report(report)

    panel = DataLoader.build_panel(report)
    if panel.empty:
        print("\nGeen data geladen — kan geen statistieken tonen.")
        return 1

    show_coverage(panel)
    show_levels(panel)
    show_returns(panel)
    show_correlations(panel)

    header("KLAAR")
    print(
        f"Paneel: {panel.shape[0]} rijen x {panel.shape[1]} kolommen, "
        f"{panel.index.min().date()} tot {panel.index.max().date()}."
    )
    print(
        "\nDe gaten in het paneel (NaN) zijn bewust niet opgevuld. Hoe we "
        "verschillende frequenties samenvoegen is een modelleerbeslissing voor "
        "fase 2, niet iets wat de datalaag stilzwijgend moet doen."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
