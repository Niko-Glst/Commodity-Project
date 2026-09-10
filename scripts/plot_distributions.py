"""Maakt de figuren over de verdeling van goudrendementen.

Elke figuur beantwoordt één vraag en wordt weggeschreven naar output/figures/.
Het script drukt bij elke figuur af wat erop te zien is, zodat je de uitleg
naast de grafiek hebt.

Gebruik:
    python scripts/plot_distributions.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
from scipy import stats as sps  # noqa: E402

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.viz.distributions import (  # noqa: E402
    compute_returns,
    plot_distribution_vs_normal,
    plot_kurtosis_explained,
    plot_qq,
    plot_series_comparison,
    plot_skewness_explained,
    plot_volatility_clustering,
)
from goldmodel.viz.style import apply_style, get_output_dir  # noqa: E402

LINE = "=" * 78


def section(number: int, title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\nFIGUUR {number}: {title}\n{LINE}")


def main() -> int:
    """Genereert alle verdelingsfiguren."""
    apply_style()

    print(LINE)
    print("FIGUREN OVER DE VERDELING VAN GOUDRENDEMENTEN")
    print(LINE)

    print("\nData laden uit de cache...")
    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)

    if "gold_futures" not in panel.columns:
        print("FOUT: geen goudprijzen geladen. Draai eerst scripts/fetch_data.py")
        return 1

    gold = compute_returns(panel, "gold_futures")
    print(
        f"{len(gold):,} handelsdagen, "
        f"{gold.index.min().date()} tot {gold.index.max().date()}"
    )

    # De kerngetallen, zodat je ze naast de figuren hebt.
    mean = gold.mean()
    std = gold.std()
    skew = gold.skew()
    kurt = gold.kurtosis()
    z = (gold - mean) / std
    observed_3sd = int((z.abs() > 3).sum())
    expected_3sd = len(gold) * 2 * (1 - sps.norm.cdf(3))

    print("\nKerngetallen:")
    print(f"  gemiddelde per dag       {mean * 100:+.4f}%")
    print(f"  standaardafwijking       {std * 100:.4f}%  (jaarbasis {std * np.sqrt(252) * 100:.1f}%)")
    print(f"  scheefheid               {skew:+.3f}")
    print(f"  exces-kurtosis           {kurt:+.3f}")
    print(f"  dagen buiten 3 sd        {observed_3sd} (normaal verwacht: {expected_3sd:.0f})")

    # ------------------------------------------------------------------
    section(1, "De verdeling tegenover de normale verdeling")
    print(
        "Het histogram is wat er echt gebeurde; de oranje lijn is wat een\n"
        "normale verdeling met hetzelfde gemiddelde en dezelfde spreiding\n"
        "voorspelt. Let op twee dingen:\n"
        "\n"
        "  1. De piek in het midden is HOGER dan de kromme. Er zijn meer\n"
        "     rustige dagen dan normaal voorspelt.\n"
        "  2. De staarten steken BUITEN de kromme. Er zijn meer extreme\n"
        "     dagen dan normaal voorspelt.\n"
        "\n"
        "Waar zit dan het tekort? In het middengebied, rond 1 tot 2\n"
        "standaardafwijkingen. Financiele markten kennen weinig 'gewoon\n"
        "matig bewegende' dagen: het is meestal rustig, en af en toe knalt\n"
        "het. De rechterhelft toont hetzelfde met een logaritmische y-as,\n"
        "waardoor je de staarten pas echt ziet."
    )
    plot_distribution_vs_normal(gold)

    # ------------------------------------------------------------------
    section(2, "Wat kurtosis is en hoe je het uitrekent")
    print(
        "Kurtosis in vier stappen:\n"
        "\n"
        "  Stap 1  Neem elk dagrendement en trek het gemiddelde eraf.\n"
        "  Stap 2  Deel door de standaardafwijking. Je hebt nu voor elke dag\n"
        "          een getal z: hoeveel standaardafwijkingen week die dag af.\n"
        "  Stap 3  Verhef elke z tot de VIERDE macht.\n"
        "  Stap 4  Neem het gemiddelde van al die vierde machten.\n"
        "\n"
        "Voor een normale verdeling komt daar precies 3 uit. Daarom trekt\n"
        "vrijwel iedereen er 3 vanaf en rapporteert 'exces-kurtosis', waarbij\n"
        "0 dus normaal betekent. Pandas doet dat automatisch: .kurtosis()\n"
        f"geeft exces-kurtosis. Voor goud is dat {kurt:.2f}.\n"
        "\n"
        "Waarom de vierde macht? Omdat die extreme waarnemingen enorm zwaar\n"
        "laat wegen. Een dag van 1 standaardafwijking telt als 1. Een dag van\n"
        "4 standaardafwijkingen telt als 4^4 = 256. Kurtosis is daardoor geen\n"
        "maat voor 'hoe breed' de verdeling is, maar voor 'hoe extreem de\n"
        "uitschieters zijn'. Dat is een veelgemaakte fout: kurtosis meet niet\n"
        "de piek maar de staarten.\n"
        "\n"
        "De rechterhelft van de figuur laat zien hoe geconcentreerd dat is."
    )
    plot_kurtosis_explained(gold)

    # ------------------------------------------------------------------
    section(3, "Scheefheid: valt goud harder dan het stijgt?")
    print(
        "Scheefheid werkt hetzelfde als kurtosis, maar met de DERDE macht.\n"
        "Dat verschil is essentieel: een oneven macht behoudt het teken.\n"
        "\n"
        "  (-2)^3 = -8    negatieve afwijkingen tellen negatief\n"
        "  (+2)^3 = +8    positieve afwijkingen tellen positief\n"
        "  (-2)^4 = +16   bij de vierde macht valt het teken weg\n"
        "\n"
        "Daarom meet scheefheid de RICHTING van de uitschieters en kurtosis\n"
        "alleen de GROOTTE. Bij een symmetrische verdeling heffen positieve\n"
        "en negatieve bijdragen elkaar op en komt er 0 uit.\n"
        "\n"
        f"Goud heeft {skew:.2f}: negatief, dus scheef naar links. De grote\n"
        "dalingen zijn extremer dan de grote stijgingen.\n"
        "\n"
        "De linkerhelft van de figuur klapt de dalingen over de stijgingen\n"
        "heen. Bij een symmetrische verdeling zouden ze samenvallen."
    )
    plot_skewness_explained(gold)

    # ------------------------------------------------------------------
    section(4, "QQ-plot: de scherpste toets op staartgedrag")
    print(
        "Een QQ-plot vergelijkt twee verdelingen door hun kwantielen tegen\n"
        "elkaar uit te zetten. Een kwantiel is een grenswaarde: het 5%-\n"
        "kwantiel is de waarde waar 5% van de waarnemingen onder ligt.\n"
        "\n"
        "Op de horizontale as staat wat de theorie voorspelt, op de\n"
        "verticale as wat je waarneemt. Klopt de verdeling, dan liggen alle\n"
        "punten op een rechte lijn. Afwijkingen aan de uiteinden betekenen\n"
        "dat de staarten niet kloppen.\n"
        "\n"
        "Dit is scherper dan een histogram, want in een histogram zijn de\n"
        "staarten bijna onzichtbaar - daar zitten immers weinig waarnemingen.\n"
        "In een QQ-plot krijgt elke waarneming een eigen punt, dus de\n"
        "extreme dagen zijn juist het best zichtbaar.\n"
        "\n"
        "Rechts staat dezelfde plot tegen een t-verdeling. Die heeft een\n"
        "parameter (vrijheidsgraden) die bepaalt hoe dik de staarten zijn:\n"
        "weinig vrijheidsgraden = dikke staarten, boven ongeveer 30 lijkt hij\n"
        "op de normale verdeling."
    )
    _, df = plot_qq(gold)
    print(
        f"\nGeschatte vrijheidsgraden voor goud: {df:.1f}\n"
        "Dat is laag, en het bevestigt de dikke staarten. Deze t-verdeling\n"
        "is precies wat we in fase 4 als schokverdeling gaan gebruiken."
    )

    # ------------------------------------------------------------------
    section(5, "Volatiliteitsclustering: waarom GARCH nodig is")
    print(
        "Dit is een tweede verschijnsel, los van de dikke staarten, en het\n"
        "is de reden dat we in fase 4 GARCH gebruiken.\n"
        "\n"
        "De onderste grafiek zet twee autocorrelaties naast elkaar.\n"
        "Autocorrelatie meet of de waarde van vandaag iets zegt over de\n"
        "waarde van morgen.\n"
        "\n"
        "  BLAUW  autocorrelatie van de rendementen zelf. Deze blijft binnen\n"
        "         de stippellijnen, wat betekent: niet te onderscheiden van\n"
        "         toeval. Of goud morgen stijgt of daalt, kun je niet\n"
        "         afleiden uit vandaag. Dat is de efficiente-markthypothese\n"
        "         in beeld, en het is precies wat je verwacht.\n"
        "\n"
        "  ORANJE autocorrelatie van de ABSOLUTE rendementen, dus van de\n"
        "         grootte zonder richting. Deze steekt er ver bovenuit en\n"
        "         blijft weken doorlopen. Of morgen een onrustige dag wordt,\n"
        "         weet je vandaag wel degelijk.\n"
        "\n"
        "Dat contrast is de kern: de RICHTING is onvoorspelbaar, de GROOTTE\n"
        "niet. Een simulatie met een vaste volatiliteit negeert dat en\n"
        "onderschat het risico in onrustige periodes systematisch - juist\n"
        "wanneer een margin call dreigt."
    )
    plot_volatility_clustering(gold)

    # ------------------------------------------------------------------
    section(6, "Zijn dikke staarten uniek voor goud?")
    print(
        "Nee, en dat is geruststellend. Zou alleen goud dit patroon tonen,\n"
        "dan zou je eerder aan de data twijfelen dan aan de normale\n"
        "verdeling. Dikke staarten zijn een van de best gedocumenteerde\n"
        "feiten in de financiele economie (bekend sinds Mandelbrot, 1963).\n"
        "\n"
        "De rechterhelft zet scheefheid tegen kurtosis uit. De ster op (0,0)\n"
        "is waar een normale verdeling zou liggen. Geen enkele reeks komt in\n"
        "de buurt."
    )
    plot_series_comparison(
        panel, ["gold_futures", "silver_futures", "sp500", "dxy"]
    )

    # ------------------------------------------------------------------
    print(f"\n{LINE}\nKLAAR\n{LINE}")
    print(f"Alle figuren staan in: {get_output_dir()}")
    print("\nWat dit betekent voor de rest van het project:")
    print(
        f"  - Exces-kurtosis {kurt:.2f} en scheefheid {skew:.2f} sluiten een\n"
        "    normale verdeling uit. Een Monte Carlo met normale schokken\n"
        "    onderschat het staartrisico, en dat is precies het risico waar\n"
        "    je margeberekening over gaat.\n"
        f"  - De t-verdeling met {df:.1f} vrijheidsgraden past duidelijk beter.\n"
        "  - Volatiliteit clustert, dus een vaste sigma volstaat niet. GARCH\n"
        "    modelleert dat."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
