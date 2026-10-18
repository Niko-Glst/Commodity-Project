"""Tests voor de paperfiguren in results/figures.

Deze tests kijken niet naar hoe de figuren eruitzien, maar naar wat bij het
uploaden naar Overleaf stilletjes mis kan gaan: een figuur die ontbreekt, een
naam in de paper die niet bestaat, een font dat niet is ingebed, of een PNG
op schermresolutie.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from make_figures import (  # noqa: E402
    FIGSIZES,
    FIGURE_NAMES,
    FIGURES,
    autocorrelations,
    highlight_path,
)

# Waar de paper kan staan; de test van de \safefig-namen slaat over als hij
# er niet is.
PAPER_CANDIDATES = (
    PROJECT_ROOT / "gold_margin_paper.tex",
    PROJECT_ROOT / "paper" / "gold_margin_paper.tex",
)


@pytest.mark.parametrize("name", FIGURE_NAMES)
def test_figure_exists_as_pdf_and_png(name: str) -> None:
    """Elke paperfiguur bestaat als vector-PDF en als PNG."""
    assert (FIGURES / f"{name}.pdf").is_file(), f"{name}.pdf ontbreekt"
    assert (FIGURES / f"{name}.png").is_file(), f"{name}.png ontbreekt"


@pytest.mark.parametrize("name", FIGURE_NAMES)
def test_pdf_embeds_truetype_fonts(name: str) -> None:
    """Fonts zijn als TrueType ingebed (fonttype 42), niet als Type 3.

    Type 3-fonts renderen slecht in sommige PDF-viewers en worden door
    tijdschriften geweigerd.
    """
    data = (FIGURES / f"{name}.pdf").read_bytes()
    assert b"/FontFile2" in data, "geen ingebed TrueType-font"
    assert b"/Type3" not in data, "Type 3-font gevonden"


@pytest.mark.parametrize("name", FIGURE_NAMES)
def test_png_is_300_dpi_at_paper_size(name: str) -> None:
    """De PNG is 300 dpi op exact het afgesproken formaat."""
    with Image.open(FIGURES / f"{name}.png") as image:
        dpi_x, dpi_y = image.info["dpi"]
        assert dpi_x == pytest.approx(300, abs=1)
        assert dpi_y == pytest.approx(300, abs=1)
        width, height = FIGSIZES[name]
        assert image.size == (round(width * 300), round(height * 300))


def test_every_safefig_in_the_paper_has_a_file() -> None:
    """Elke \\safefig{naam} in de paper heeft een bijbehorende PDF.

    Faalt als de paper een figuur laadt die niet bestaat; Overleaf toont dan
    alleen een placeholder en dat valt pas op bij het lezen.
    """
    paper = next((path for path in PAPER_CANDIDATES if path.is_file()), None)
    if paper is None:
        pytest.skip("gold_margin_paper.tex staat niet in het project")

    names = re.findall(r"\\safefig\{([^}]+)\}", paper.read_text(encoding="utf-8"))
    assert names, "geen \\safefig-aanroepen gevonden in de paper"
    missing = [name for name in names if not (FIGURES / f"{name}.pdf").is_file()]
    assert not missing, f"figuren zonder bestand: {missing}"


# -- de autocorrelatie achter fig2 ------------------------------------------


def test_autocorrelation_band_holds_for_white_noise() -> None:
    """Op witte ruis vallen rendementen en absolute rendementen in de band.

    De band is 1,96/wortel(n); onder witte ruis verwacht je ongeveer 5% van de
    lags erbuiten. Ruim genomen: hoogstens 10 van de 100.
    """
    rng = np.random.default_rng(42)
    noise = pd.Series(rng.normal(0.0, 0.01, 5000))
    lags, returns_acf, absolute_acf, band = autocorrelations(noise, 100)

    assert band == pytest.approx(1.96 / np.sqrt(5000))
    assert list(lags) == list(range(1, 101))
    assert int((np.abs(returns_acf) >= band).sum()) <= 10
    assert int((np.abs(absolute_acf) >= band).sum()) <= 10


def test_autocorrelation_detects_volatility_clustering() -> None:
    """Bij GARCH-achtige data liggen absolute rendementen ver boven de band.

    Het positieve controlegeval: als de figuur volatiliteitsclustering moet
    laten zien, moet de berekening die ook vinden waar hij aanwezig is.

    De rendementen zelf zijn hier ongecorreleerd gesimuleerd, maar we toetsen
    NIET dat hun ACF binnen de band valt. Bij volatiliteitsclustering is de
    witte-ruisband te smal voor de ACF van rendementen: met deze data valt
    lag 1 er net buiten (0,033 tegen 0,028). We toetsen alleen dat ze veel
    kleiner is dan die van de absolute rendementen.
    """
    rng = np.random.default_rng(42)
    n, omega, alpha, beta = 5000, 1e-6, 0.10, 0.88
    variance, returns = omega / (1 - alpha - beta), np.empty(n)
    for t in range(n):
        returns[t] = np.sqrt(variance) * rng.standard_normal()
        variance = omega + alpha * returns[t] ** 2 + beta * variance
    lags, returns_acf, absolute_acf, band = autocorrelations(pd.Series(returns), 20)

    assert absolute_acf[0] > 3 * band
    assert np.all(absolute_acf > band)
    assert np.mean(np.abs(returns_acf)) < np.mean(absolute_acf) / 3


# -- het uitgelichte pad in fig7 ---------------------------------------------


def test_highlight_path_picks_largest_gap_within_range() -> None:
    """Het gekozen pad heeft het grootste verschil tussen maximum en eind.

    Alleen paden met een maximum tussen 10% en 30% tellen mee: een pad dat
    hoger piekt, valt buiten de band, en een pad dat lager blijft, laat de
    vuistregels niet zien.
    """
    losses = np.array(
        [
            [0.0, 20.0, 18.0],   # verschil 2
            [0.0, 15.0, -5.0],   # verschil 20  <- verwacht
            [0.0, 40.0, -10.0],  # verschil 50, maar maximum boven 30%
            [0.0, 5.0, -20.0],   # verschil 25, maar maximum onder 10%
        ]
    )
    assert highlight_path(losses) == 1


def test_highlight_path_refuses_when_no_path_qualifies() -> None:
    """Zonder geschikt pad een duidelijke fout, geen stille willekeurige keuze."""
    with pytest.raises(ValueError):
        highlight_path(np.array([[0.0, 2.0, 1.0], [0.0, 45.0, 0.0]]))
