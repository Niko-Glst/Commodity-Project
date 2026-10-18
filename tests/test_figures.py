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

import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from make_figures import FIGSIZES, FIGURE_NAMES, FIGURES  # noqa: E402

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
