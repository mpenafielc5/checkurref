"""Lectura del texto del PDF con PyMuPDF, línea por línea.

Se conserva el orden en que el documento guarda sus bloques de texto, que en
los PDF exportados desde Word o LaTeX es el orden de lectura. De cada línea se
guarda también su posición horizontal: la separación de referencias APA la
usa para reconocer la sangría francesa.
"""

import re
from dataclasses import dataclass
from typing import Any

import pymupdf

from app.pipeline.errors import EncryptedPdfError, ScannedPdfError, UnreadablePdfError

TEXT_BLOCK = 0
# Sin los bytes de las imágenes: el análisis las descarta, y copiarlas hacía que leer una
# tesis de 126 páginas tardara 5 s en lugar de 0,1 s.
TEXT_ONLY = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
# Por debajo de este promedio de caracteres por página se considera escaneado.
MIN_CHARS_PER_PAGE = 25
# Caracteres de control que no son espacios. Algunos PDF exportados desde Word traen
# un carácter nulo (\x00) al final del texto: AnyStyle no lo lee y PostgreSQL no lo
# guarda, así que el análisis completo fallaba al guardar las referencias.
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")
# Páginas en las que se busca la portada con texto.
COVER_PAGES = 2


@dataclass(frozen=True)
class TextLine:
    page: int  # número de página, desde 1
    x0: float  # borde izquierdo de la línea, en puntos
    text: str


def extract_pages(pdf_bytes: bytes) -> list[list[TextLine]]:
    """Líneas no vacías de cada página, en orden de lectura."""
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.needs_pass:
                raise EncryptedPdfError
            if document.page_count == 0:
                raise UnreadablePdfError
            pages = [_page_lines(page, number) for number, page in enumerate(document, start=1)]
    except RuntimeError as error:
        # MuPDF señala con RuntimeError cualquier estructura dañada: no solo al abrir
        # (FileDataError), también al contar o leer las páginas de un PDF cortado.
        raise UnreadablePdfError from error

    visible_chars = sum(len(line.text.replace(" ", "")) for page in pages for line in page)
    if visible_chars < MIN_CHARS_PER_PAGE * len(pages):
        raise ScannedPdfError
    return pages


def cover_page_lines(pdf_bytes: bytes) -> list[str]:
    """Texto de las líneas de la portada; vacío si el PDF tiene clave, no tiene páginas o
    está dañado.

    La portada es la primera página con texto entre las primeras COVER_PAGES: algunos
    trabajos abren con una portada que es solo una imagen y llevan los datos en la
    página siguiente.
    """
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.needs_pass:
                return []
            for number in range(min(COVER_PAGES, document.page_count)):
                lines = [line.text for line in _page_lines(document[number], number + 1)]
                if lines:
                    return lines
            return []
    except RuntimeError:
        return []


def _page_lines(page: pymupdf.Page, number: int) -> list[TextLine]:
    lines: list[TextLine] = []
    for block in page.get_text("dict", flags=TEXT_ONLY)["blocks"]:
        if block["type"] != TEXT_BLOCK:
            continue
        for row in _rows(block["lines"]):
            row.sort(key=lambda piece: piece[0])
            text = clean_line(" ".join(piece[1] for piece in row))
            if text:
                lines.append(TextLine(page=number, x0=round(row[0][0], 1), text=text))
    return lines


def clean_line(text: str) -> str:
    """Texto de un renglón sin caracteres de control y con los espacios normalizados."""
    return " ".join(CONTROL_CHARS.sub("", text).split())


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
