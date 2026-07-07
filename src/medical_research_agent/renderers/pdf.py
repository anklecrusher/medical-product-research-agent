"""Minimal ReportLab PDF rendering for MVP Markdown reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen.canvas import Canvas


BODY_FONT_SIZE: Final = 10
TITLE_FONT_SIZE: Final = 14
LEADING: Final = 14
TOP_MARGIN: Final = 18 * mm
BOTTOM_MARGIN: Final = 16 * mm
LEFT_MARGIN: Final = 18 * mm
RIGHT_MARGIN: Final = 18 * mm
DEFAULT_FONT: Final = "Helvetica"
CID_FALLBACK_FONT: Final = "STSong-Light"
WINDOWS_FONT_CANDIDATES: Final = (
    ("MicrosoftYaHei", Path("C:/Windows/Fonts/msyh.ttc")),
    ("MicrosoftYaHei", Path("C:/Windows/Fonts/msyh.ttf")),
    ("SimSun", Path("C:/Windows/Fonts/simsun.ttc")),
    ("SimSun", Path("C:/Windows/Fonts/simsun.ttf")),
)


@dataclass(frozen=True, slots=True)
class PdfRenderResult:
    """Metadata returned after a PDF artifact has been rendered."""

    path: Path
    font_name: str
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class FontSelection:
    """A chosen ReportLab font and any non-blocking font warnings."""

    name: str
    warnings: list[str]


def render_markdown_pdf(markdown: str, output_path: Path, title: str | None = None) -> PdfRenderResult:
    """Render Markdown-ish text into a simple, real PDF file."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    font = _select_font()
    lines = _normalise_markdown_lines(markdown, title)
    pdf = Canvas(str(output_path), pagesize=A4, pageCompression=1)
    width, height = A4
    text_width = width - LEFT_MARGIN - RIGHT_MARGIN
    y = height - TOP_MARGIN

    pdf.setTitle(title or "medical-product-research-report")
    pdf.setFont(font.name, TITLE_FONT_SIZE)
    y = _draw_line(pdf, lines[0], font.name, TITLE_FONT_SIZE, y, text_width)
    pdf.setFont(font.name, BODY_FONT_SIZE)

    for line in lines[1:]:
        if y < BOTTOM_MARGIN:
            pdf.showPage()
            pdf.setFont(font.name, BODY_FONT_SIZE)
            y = height - TOP_MARGIN
        y = _draw_line(pdf, line, font.name, BODY_FONT_SIZE, y, text_width)

    pdf.save()
    return PdfRenderResult(path=output_path, font_name=font.name, warnings=font.warnings)


def _select_font() -> FontSelection:
    warnings: list[str] = []
    for font_name, font_path in WINDOWS_FONT_CANDIDATES:
        if not font_path.exists():
            warnings.append(f"Font not found: {font_path}")
            continue
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        except (OSError, TTFError) as exc:
            warnings.append(f"Font registration failed for {font_path}: {exc}")
            continue
        return FontSelection(name=font_name, warnings=warnings)

    try:
        pdfmetrics.registerFont(UnicodeCIDFont(CID_FALLBACK_FONT))
    except KeyError as exc:
        warnings.append(f"CID fallback font unavailable: {CID_FALLBACK_FONT}: {exc}")
        warnings.append(f"Using ReportLab built-in font: {DEFAULT_FONT}")
        return FontSelection(name=DEFAULT_FONT, warnings=warnings)

    warnings.append(f"Using ReportLab CID fallback font: {CID_FALLBACK_FONT}")
    return FontSelection(name=CID_FALLBACK_FONT, warnings=warnings)


def _normalise_markdown_lines(markdown: str, title: str | None) -> list[str]:
    lines: list[str] = []
    heading = title or "医疗产品调研报告"
    lines.append(_clean_markdown_line(heading))
    for raw_line in markdown.splitlines():
        line = _clean_markdown_line(raw_line)
        if line:
            lines.append(line)
        else:
            lines.append(" ")
    return lines


def _clean_markdown_line(line: str) -> str:
    return line.strip().lstrip("#").replace("**", "").replace("`", "").strip()


def _draw_line(pdf: Canvas, line: str, font_name: str, font_size: int, y: float, text_width: float) -> float:
    wrapped_lines = simpleSplit(line, font_name, font_size, text_width) or [" "]
    for wrapped_line in wrapped_lines:
        if y < BOTTOM_MARGIN:
            pdf.showPage()
            pdf.setFont(font_name, font_size)
            y = A4[1] - TOP_MARGIN
        pdf.drawString(LEFT_MARGIN, y, wrapped_line)
        y -= LEADING
    return y
