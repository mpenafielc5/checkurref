"""Ubica la sección de referencias del documento (primera etapa del análisis)."""

import re
import unicodedata
from dataclasses import dataclass

from app.pipeline.errors import ReferencesNotFoundError
from app.pipeline.pdf_text import TextLine, extract_pages
from app.pipeline.text_cleanup import join_broken_lines, remove_page_furniture

HEADINGS = {
    "referencias",
    "referencias bibliograficas",
    "lista de referencias",
    "bibliografia",
    "bibliografias",
    "bibliografia consultada",
    "fuentes bibliograficas",
    "references",
    "bibliography",
}
SECTION_END_PREFIXES = ("anexo", "apendice", "appendix", "annex")
# Numeración que puede preceder al título: "7.", "VII.", "5.2", "Capítulo 6".
NUMBERING = re.compile(r"^((capitulo|chapter)\s+)?(\d+(\.\d+)*|[ivxlc]+)[.)\-:]?\s+")


@dataclass(frozen=True)
class ReferenceSection:
    heading: str
    page: int
    lines: list[TextLine]


def extract_reference_section(pdf_bytes: bytes) -> ReferenceSection:
    """Lee el PDF, limpia el texto y devuelve solo la sección de referencias."""
    pages = remove_page_furniture(extract_pages(pdf_bytes))
    return find_reference_section(join_broken_lines([line for page in pages for line in page]))


def find_reference_section(lines: list[TextLine]) -> ReferenceSection:
    heading_index = _heading_index(lines)
    if heading_index is None:
        raise ReferencesNotFoundError

    body: list[TextLine] = []
    for line in lines[heading_index + 1 :]:
        if _is_section_end(line.text):
            break
        if not _is_heading(line.text):  # un encabezado repetido en la página siguiente
            body.append(line)

    if not body:
        raise ReferencesNotFoundError
    heading = lines[heading_index]
    return ReferenceSection(heading=heading.text, page=heading.page, lines=body)


def _heading_index(lines: list[TextLine]) -> int | None:
    """Índice del título de la sección.

    Se toma el último título que aparece en el documento: el índice general
    también puede nombrar la sección, pero siempre está antes. Se descartan los
    encabezados repetidos: un título al inicio de una página cuando el anterior
    estaba en la página inmediatamente anterior. Un capítulo que empieza en
    página nueva sí cuenta, porque el índice está varias páginas antes.
    """
    candidates = [index for index, line in enumerate(lines) if _is_heading(line.text)]
    real = [
        index
        for position, index in enumerate(candidates)
        if position == 0 or not _is_running_header(lines, candidates[position - 1], index)
    ]
    return real[-1] if real else None


def _is_running_header(lines: list[TextLine], previous: int, index: int) -> bool:
    starts_page = index > 0 and lines[index - 1].page != lines[index].page
    return starts_page and lines[previous].page == lines[index].page - 1


def _normalize(text: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )
    return NUMBERING.sub("", " ".join(without_accents.split())).rstrip(" :.")


def _is_heading(text: str) -> bool:
    return _normalize(text) in HEADINGS


def _is_section_end(text: str) -> bool:
    normalized = _normalize(text)
    return len(normalized.split()) <= 4 and normalized.startswith(SECTION_END_PREFIXES)
