"""Gedeelde opmaak voor alle figuren.

Eén plek voor kleuren, lettergroottes en het wegschrijven van bestanden, zodat
alle figuren in het project er hetzelfde uitzien. Dat is niet alleen esthetiek:
als je in een sollicitatiegesprek een reeks grafieken laat zien, telt het
wanneer ze duidelijk uit één systeem komen.

Kleurkeuze
----------
De categorische kleuren zijn gekozen uit een gevalideerd palet dat ook voor
mensen met kleurenblindheid onderscheidbaar blijft (getoetst op voldoende
afstand in de OKLab-kleurruimte). Ze worden altijd in vaste volgorde
toegekend, nooit willekeurig doorgeroteerd, zodat dezelfde reeks in elke
figuur dezelfde kleur heeft.

Belangrijker nog: kleur is nooit de enige drager van informatie. Elke lijn
krijgt ook een label of een verschillende lijnstijl, zodat de figuur ook in
zwart-wit en voor kleurenblinde lezers leesbaar blijft.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

# Categorische kleuren in vaste volgorde. Nooit doorroteren: reeks 9 krijgt
# geen nieuwe kleur maar wordt samengevoegd of in een aparte figuur gezet.
COLORS = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "green": "#008300",
    "violet": "#4a3aa7",
    "red": "#e34948",
}

# Rolgebonden kleuren: welke kleur waarvoor staat, consequent door het project.
ROLE = {
    "empirical": COLORS["blue"],     # wat we waarnemen in de data
    "theoretical": COLORS["orange"],  # wat een model voorspelt
    "reference": "#8a8a85",           # hulplijnen, nullijn
    "highlight": COLORS["red"],       # waar het misgaat, staarten
    "secondary": COLORS["aqua"],      # tweede vergelijking (t-verdeling)
    "surface": "#fcfcfb",
    "ink": "#0b0b0b",
    "ink_soft": "#52514e",
    "grid": "#e3e3e0",
}


def apply_style() -> None:
    """Zet de matplotlib-instellingen voor dit project.

    Kern van de keuzes: assen en raster zijn terughoudend (dun, grijs), de
    data springt eruit. Een raster hoort een hulpmiddel te zijn, geen
    onderdeel van het beeld.
    """
    mpl.rcParams.update(
        {
            # Achtergrond
            "figure.facecolor": ROLE["surface"],
            "axes.facecolor": ROLE["surface"],
            "savefig.facecolor": ROLE["surface"],
            # Tekst
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlepad": 12,
            "axes.labelsize": 10,
            "axes.labelcolor": ROLE["ink_soft"],
            "text.color": ROLE["ink"],
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "xtick.color": ROLE["ink_soft"],
            "ytick.color": ROLE["ink_soft"],
            # Assen: alleen links en onder, dun en grijs
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": True,
            "axes.spines.bottom": True,
            "axes.edgecolor": ROLE["grid"],
            "axes.linewidth": 1.0,
            # Raster: terughoudend
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": ROLE["grid"],
            "grid.linewidth": 0.8,
            "grid.alpha": 0.7,
            "axes.axisbelow": True,
            # Lijnen
            "lines.linewidth": 2.0,
            "lines.markersize": 5,
            # Legenda: geen kader, die voegt niets toe
            "legend.frameon": False,
            "legend.fontsize": 9,
            # Opslaan
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "figure.autolayout": False,
        }
    )


def get_output_dir() -> Path:
    """Geeft de map voor figuren terug en maakt hem aan indien nodig."""
    project_root = Path(__file__).resolve().parents[3]
    output_dir = project_root / "output" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_figure(fig: plt.Figure, filename: str, *, quiet: bool = False) -> Path:
    """Schrijft een figuur weg als PNG en geeft het pad terug."""
    path = get_output_dir() / filename
    fig.savefig(path)
    plt.close(fig)
    if not quiet:
        print(f"  opgeslagen: {path.name}")
    return path


def annotate(ax: plt.Axes, text: str, *, loc: str = "upper right") -> None:
    """Zet een toelichtend tekstblok in een grafiek.

    Gebruikt voor het benoemen van de kernboodschap in de figuur zelf, zodat
    een grafiek ook los van de omringende tekst te begrijpen is.
    """
    positions = {
        "upper right": (0.97, 0.97, "right", "top"),
        "upper left": (0.03, 0.97, "left", "top"),
        "lower right": (0.97, 0.03, "right", "bottom"),
        "lower left": (0.03, 0.03, "left", "bottom"),
    }
    x, y, ha, va = positions[loc]
    ax.text(
        x,
        y,
        text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=9,
        color=ROLE["ink_soft"],
        linespacing=1.5,
        bbox={
            "boxstyle": "round,pad=0.6",
            "facecolor": ROLE["surface"],
            "edgecolor": ROLE["grid"],
            "linewidth": 1.0,
        },
    )
