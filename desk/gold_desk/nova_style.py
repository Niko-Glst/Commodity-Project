"""Nova Gold Weekly page template, added 27 Nov 2026.

Look: the desk's own landscape style (white slides, light Segoe UI titles with a gold bar, filled teal section bars,
grey text boxes, a teal key block), chosen by the user on 27 Nov 2026 over the blueprint's cream/blue palette.

Windows only: it embeds Segoe UI from C:/Windows/Fonts. It is imported by the edition build scripts, never by
gold_desk.report or the weekly routine, so the Linux cloud run does not depend on it.

Every string drawn on a page, and every text object of every chart, goes through a recorder so the build can check
the house rules after rendering: no em dashes and no en dashes used as dashes, exactly one key block, every chart
with a takeaway title and a plain subtitle, every font embedded.
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph, Table, TableStyle

TEAL, TEAL2, GOLDBAR, KEYTITLE, MINT = "#0b3a44", "#2f5d62", "#c9a227", "#e9c46a", "#7fd1b9"
BLUE, GOLD, INK, MUTED = "#1c5cab", "#b8860b", "#111111", "#8a8a86"
BORDER, BOX, ZEBRA, WHITE = "#e3e3df", "#f1f1f0", "#f6f5f2", "#ffffff"
CREAM = WHITE                       # page background (kept as a name for the edition scripts)
FONT_DIR = Path("C:/Windows/Fonts")
FONTS = {"NV-R": "segoeui.ttf", "NV-B": "segoeuib.ttf", "NV-I": "segoeuii.ttf", "NV-BI": "segoeuiz.ttf",
         "NV-H": "seguisb.ttf", "NV-L": "segoeuil.ttf"}
W, H = 960, 540
C = colors.HexColor
STANDARD_14 = ("Helvetica", "Times-Roman", "Times-Bold", "Courier", "Symbol", "ZapfDingbats")


def fonts_available() -> bool:
    return all((FONT_DIR / f).exists() for f in FONTS.values())


def register_fonts() -> None:
    if not fonts_available():
        raise FileNotFoundError("Segoe UI not found in C:/Windows/Fonts")
    for name, f in FONTS.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / f)))
    pdfmetrics.registerFontFamily("NV-R", normal="NV-R", bold="NV-B", italic="NV-I", boldItalic="NV-BI")


def has_glyph(font_name: str, char: str) -> bool:
    return ord(char) in pdfmetrics.getFont(font_name).face.charToGlyph


def style(name, **kw):
    base = {"fontName": "NV-R", "fontSize": 9.4, "leading": 12.2, "textColor": C(INK), "bulletFontName": "NV-R"}
    return ParagraphStyle(name, **{**base, **kw})


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", str(s)).replace("&amp;", "&")


def find_dashes(texts) -> list[str]:
    """Strings with an em dash, or an en dash used as a dash (with a space on either side). An en dash inside a
    number range ('3,298\u20133,751') or alone in an empty table cell is allowed."""
    out = []
    for t in texts:
        t = str(t)
        if "\u2014" in t or re.search(r"(\s\u2013|\u2013\s)", t.strip()) and t.strip() != "\u2013":
            out.append(t)
    return out


def figure_texts(fig) -> list[str]:
    import matplotlib.text
    return [t.get_text() for t in fig.findobj(matplotlib.text.Text) if t.get_text()]


def fonts_embedded(pdf_path) -> tuple[bool, str]:
    """Every font in the PDF is embedded: no standard-14 base font, and an embedded font file for each base font."""
    b = Path(pdf_path).read_bytes()
    base = set(re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-]+)", b))
    std = [x.decode() for x in base if any(x.decode().endswith(s) or x.decode() == s for s in STANDARD_14)]
    n_file = len(re.findall(rb"/FontFile2", b))
    ok = not std and n_file >= len(base)
    return ok, f"standard-14 fonts: {std or 'none'}; embedded font files: {n_file}; base fonts: {len(base)}"


class Deck:
    def __init__(self, path, title, edition_label, footer_label):
        register_fonts()
        self.path = str(path)
        self.cv = rl_canvas.Canvas(self.path, pagesize=(W, H), initialFontName="NV-R", initialFontSize=9)
        self.cv.setTitle(title)
        self.cv.setAuthor("Nova Capital")
        self.edition_label, self.footer_label = edition_label, footer_label
        self.page = 0
        self.texts: list[str] = []
        self.blue_blocks = 0
        self.charts: list[dict] = []
        self.tables: list[dict] = []

    # ---------------------------------------------------------------- primitives that record text
    def string(self, x, y, s, font="NV-R", size=9, color=INK, align="left"):
        self.texts.append(s)
        self.cv.setFont(font, size)
        self.cv.setFillColor(C(color))
        {"left": self.cv.drawString, "right": self.cv.drawRightString, "center": self.cv.drawCentredString}[align](x, y, s)

    def para(self, text, x, y_top, w, st):
        self.texts.append(strip_tags(text))
        p = Paragraph(text, st)
        _, ph = p.wrap(w, 2000)
        p.drawOn(self.cv, x, y_top - ph)
        return y_top - ph

    # ---------------------------------------------------------------- page frame
    def new_page(self, title, source="", section=""):
        if self.page:
            self.cv.showPage()
        self.page += 1
        cv = self.cv
        cv.setFillColor(C(WHITE))
        cv.rect(0, 0, W, H, stroke=0, fill=1)
        if title:
            cv.setFillColor(C(GOLDBAR))
            cv.rect(36, H - 62, 7, 30, stroke=0, fill=1)
            self.string(52, H - 58, title, font="NV-L", size=28, color=INK)
        if section:
            self.string(W - 36, H - 30, section, size=8, color=MUTED, align="right")
        cv.setStrokeColor(C(TEAL2))
        cv.setLineWidth(3)
        cv.line(36, 27, W - 36, 27)
        if source:
            source = re.sub(r"&(?!amp;|lt;|gt;)", "&amp;", source)
            self.para(source, 36, 44, W - 72, style("src", fontSize=6.6, leading=8, textColor=C(MUTED)))
        self.string(36, 15, self.footer_label, size=7, color=MUTED)
        self.string(W - 36, 15, str(self.page), font="NV-B", size=8, color=INK, align="right")

    def card(self, x, y_top, w, h, border=None, fill=BOX):
        """A grey text box; with a border colour it is drawn as an outlined white box instead."""
        self.cv.setFillColor(C(WHITE if border else fill))
        if border:
            self.cv.setStrokeColor(C(border))
            self.cv.setLineWidth(1.0)
        self.cv.roundRect(x, y_top - h, w, h, 8, stroke=1 if border else 0, fill=1)

    def heading(self, x, y, w, text, size=13):
        """Filled teal section bar with the text centred in white; content starts just below y - 8."""
        self.texts.append(text)
        self.cv.setFillColor(C(TEAL2))
        self.cv.roundRect(x, y - 7, w, 21, 5, stroke=0, fill=1)
        self.cv.setFillColor(C(WHITE))
        self.cv.setFont("NV-L", size)
        self.cv.drawCentredString(x + w / 2, y - 1, text)
        return y - 14

    def bullets(self, x, y_top, w, items, size=9.2, gap=4, bullet=True, color=INK):
        st = style("b", fontSize=size, leading=size * 1.3, leftIndent=9 if bullet else 0, textColor=C(color),
                   bulletColor=C(color))
        y = y_top
        for t in items:
            self.texts.append(strip_tags(t))
            p = Paragraph(t, st, bulletText="\u2022" if bullet else None)
            _, ph = p.wrap(w, 2000)
            p.drawOn(self.cv, x, y - ph)
            y -= ph + gap
        return y

    def table(self, rows, x, y_top, widths, size=8.2, styles=(), basis="none", align_right_from=None):
        """basis: what gold prices in the table are ('settlement', '16:00', 'none'); one per table."""
        assert basis in ("settlement", "16:00", "none")
        self.tables.append({"page": self.page, "basis": basis, "header": [strip_tags(c) for c in rows[0]]})
        esc = lambda v: str(v).replace("&amp;", "&").replace("&", "&amp;")  # noqa: E731
        hd = style("th", fontName="NV-B", fontSize=size, leading=size + 2, textColor=C(WHITE))
        cs = style("td", fontSize=size, leading=size + 2)
        cf = style("tf", fontName="NV-B", fontSize=size, leading=size + 2)
        data = []
        for i, r in enumerate(rows):
            self.texts.extend(strip_tags(v) for v in r)
            data.append([Paragraph(esc(v), hd if i == 0 else (cf if j == 0 else cs)) for j, v in enumerate(r)])
        t = Table(data, colWidths=widths)
        sty = [("FONT", (0, 0), (-1, -1), "NV-R", size), ("BACKGROUND", (0, 0), (-1, 0), C(TEAL2)),
               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.2),
               ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2), ("LEFTPADDING", (0, 0), (-1, -1), 4),
               ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("LINEBELOW", (0, 1), (-1, -1), 0.3, C(BORDER)),
               ("BACKGROUND", (0, 1), (-1, -1), C(WHITE))]
        sty += [("BACKGROUND", (0, i), (-1, i), C(ZEBRA)) for i in range(2, len(rows), 2)]
        t.setStyle(TableStyle(sty + list(styles)))
        _, th = t.wrapOn(self.cv, W, H)
        t.drawOn(self.cv, x, y_top - th)
        return y_top - th

    def chart(self, png, x, y_top, w, title, subtitle, fig_texts=(), h=None):
        """Every chart goes through here: takeaway title, plain subtitle, then the image."""
        assert title and subtitle
        self.charts.append({"page": self.page, "title": title, "subtitle": subtitle})
        self.texts.extend(fig_texts)
        y = self.para(title, x, y_top, w, style("ct", fontName="NV-H", fontSize=10.5, leading=12.5))
        y = self.para(subtitle, x, y - 1, w, style("cs", fontSize=7.8, leading=9.4, textColor=C(MUTED)))
        iw, ih = ImageReader(png).getSize()
        if h is None:
            h = w * ih / iw
        else:
            w = h * iw / ih
        self.cv.drawImage(png, x, y - 4 - h, w, h)
        return y - 4 - h

    def blue_block(self, x, y_top, w, h, title, items, size=9.8):
        """The one key block per document (teal, gold title, white text)."""
        self.blue_blocks += 1
        self.cv.setFillColor(C(TEAL))
        self.cv.roundRect(x, y_top - h, w, h, 10, stroke=0, fill=1)
        self.string(x + 16, y_top - 24, title, font="NV-H", size=11.5, color=KEYTITLE)
        return self.bullets(x + 16, y_top - 36, w - 32, items, size=size, color=WHITE)

    def save(self):
        self.cv.save()
        return self.path
