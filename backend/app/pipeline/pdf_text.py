"""Lectura del texto del PDF con PyMuPDF, línea por línea.

Se conserva el orden en que el documento guarda sus bloques de texto, que en
los PDF exportados desde Word o LaTeX es el orden de lectura. De cada línea se
guarda también su posición horizontal: la separación de referencias APA la
usa para reconocer la sangría francesa.
"""

from dataclasses import dataclass
from typing import Any

import pymupdf

from app.pipeline.errors import EncryptedPdfError, ScannedPdfError, UnreadablePdfError

TEXT_BLOCK = 0
# Por debajo de este promedio de caracteres por página se considera escaneado.
MIN_CHARS_PER_PAGE = 25


@dataclass(frozen=True)
class TextLine:
    page: int  # número de página, desde 1
    x0: float  # borde izquierdo de la línea, en puntos
    text: str


def extract_pages(pdf_bytes: bytes) -> list[list[TextLine]]:
    """Líneas no vacías de cada página, en orden de lectura."""
    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except (pymupdf.FileDataError, pymupdf.EmptyFileError) as error:
        raise UnreadablePdfError from error

    with document:
        if document.needs_pass:
            raise EncryptedPdfError
        if document.page_count == 0:
            raise UnreadablePdfError
        pages = [_page_lines(page, number) for number, page in enumerate(document, start=1)]

    visible_chars = sum(len(line.text.replace(" ", "")) for page in pages for line in page)
    if visible_chars < MIN_CHARS_PER_PAGE * len(pages):
        raise ScannedPdfError
    return pages


def _page_lines(page: pymupdf.Page, number: int) -> list[TextLine]:
    lines: list[TextLine] = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != TEXT_BLOCK:
            continue
        for row in _rows(block["lines"]):
            row.sort(key=lambda piece: piece[0])
            text = " ".join(" ".join(piece[1] for piece in row).split())
            if text:
                lines.append(TextLine(page=number, x0=round(row[0][0], 1), text=text))
    return lines


def _rows(block_lines: list[dict[str, Any]]) -> list[list[tuple[float, str]]]:
    """Agrupa los trozos de un bloque que están en el mismo renglón.

    En el texto justificado, PyMuPDF a veces entrega un renglón partido en
    varias "líneas" por los espacios anchos. Se unen solo dentro de un mismo
    bloque, para no mezclar las columnas de un documento a dos columnas.
    """
    rows: list[list[tuple[float, str]]] = []
    previous_middle: float | None = None
    for line in block_lines:
        x0, y0, _x1, y1 = line["bbox"]
        middle = (y0 + y1) / 2
        piece = (x0, "".join(span["text"] for span in line["spans"]))
        if previous_middle is not None and abs(middle - previous_middle) < (y1 - y0) / 2:
            rows[-1].append(piece)
        else:
            rows.append([piece])
            previous_middle = middle
    return rows
