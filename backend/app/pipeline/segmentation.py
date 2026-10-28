"""Separa la sección de referencias en entradas individuales (T06).

Una línea empieza una referencia nueva cuando:

- lleva su número entre corchetes, [1], [2]... (IEEE);
- la lista usa sangría francesa y la línea está en el margen: las líneas que
  siguen a la primera de cada referencia llevan sangría;
- la lista usa sangría de primera línea (frecuente en los trabajos, aunque APA
  pide la francesa) y la línea tiene sangría;
- la línea empieza con el patrón autor-año, "Apellido, I. (2020)" u
  "Organización. (2020)", y la anterior cerraba una referencia. Es la única
  señal cuando la lista no tiene sangría.

Una entrada cuya separación no se puede confirmar no detiene el análisis: se
registra, se marca con el motivo y se sigue con las demás.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

from app.pipeline.norm_detection import Norm, detect_document_norm, detect_reference_norm
from app.pipeline.patterns import IEEE_NUMBER, SURNAME_FIRST, UPPER, YEAR_IN_PARENS
from app.pipeline.pdf_text import TextLine
from app.pipeline.references_section import ReferenceSection

logger = logging.getLogger(__name__)

IEEE_START = re.compile(rf"^{IEEE_NUMBER}")
AUTHOR_YEAR_START = re.compile(rf"^[{UPPER}][^()]{{0,250}}?{YEAR_IN_PARENS}")
# "Apellido, I." al inicio: en una lista de autores larga, el año queda más abajo.
AUTHOR_START = re.compile(rf"^{SURNAME_FIRST}")
# Una línea que termina así sigue en la siguiente: lista de autores o apellido partidos.
OPEN_ENDING = re.compile(r"(?:[,;:&-]|\s(?:y|e|and))$")
# Una línea que termina así cierra una referencia: en punto o en su DOI o URL.
CLOSED_ENDING = re.compile(r"(?:\.|(?:https?://|doi:)\S*)$", re.IGNORECASE)
# Otra referencia pegada dentro de la entrada, después de un punto o de un DOI o URL.
GLUED_START = re.compile(
    rf"(?:[.)]|(?:https?://|doi:)\S+)\s(?:{IEEE_NUMBER}\s"
    rf"|{SURNAME_FIRST}[^()]{{0,150}}?{YEAR_IN_PARENS})"
)

# Sangría francesa, en puntos (Word usa 1,27 cm = 36 pt).
MIN_INDENT = 10.0
MAX_INDENT = 90.0
# A partir de esta distancia, dos líneas están en columnas distintas.
COLUMN_GAP = 150.0
# Una referencia rara vez pasa de este largo: más suele ser dos unidas.
MAX_ENTRY_CHARS = 900

# El sistema no pudo confirmar la separación: el motivo puede ser la escritura de
# la lista o la lectura del PDF, así que el mensaje no culpa al estudiante.
NOT_A_REFERENCE = (
    "El sistema no pudo confirmar que este texto sea una referencia completa: "
    "puede ser parte de otra o un texto fuera de la lista."
)
GLUED = (
    "El sistema no pudo confirmar dónde termina esta referencia: podría contener más de una. "
    "Revisa que cada referencia empiece en su propia línea."
)
TOO_LONG = "El sistema no pudo confirmar que sea una sola referencia: es más larga de lo habitual."


class Layout(Enum):
    """Distribución de la lista: en qué nivel empieza cada referencia."""

    HANGING = "sangría francesa"  # empieza en el margen
    FIRST_LINE = "sangría de primera línea"  # empieza con sangría
    FLAT = "sin sangría"  # solo el patrón autor-año o [n] marcan el inicio


@dataclass(frozen=True)
class SplitEntry:
    page: int
    text: str
    issue: str | None = None  # motivo por el que la separación es dudosa


@dataclass(frozen=True)
class SegmentedReference:
    order: int  # posición en la lista, desde 1
    page: int
    text: str
    norm: Norm  # APA, IEEE o DESCONOCIDA
    issue: str | None


@dataclass(frozen=True)
class Segmentation:
    references: list[SegmentedReference]
    norm: Norm  # norma de la lista completa: APA, IEEE, MIXTA o DESCONOCIDA


def segment_references(section: ReferenceSection) -> Segmentation:
    """Entradas de la sección con la norma de cada una y la de la lista."""
    references = [
        SegmentedReference(
            order=order,
            page=entry.page,
            text=entry.text,
            norm=detect_reference_norm(entry.text),
            issue=entry.issue,
        )
        for order, entry in enumerate(split_entries(section.lines), start=1)
    ]
    for reference in references:
        if reference.issue:
            logger.warning(
                "Referencia %d (página %d): %s", reference.order, reference.page, reference.issue
            )
    return Segmentation(
        references=references,
        norm=detect_document_norm([reference.norm for reference in references]),
    )


def split_entries(lines: list[TextLine]) -> list[SplitEntry]:
    indents = _indents(lines)
    layout = _layout(lines, indents)

    groups: list[list[TextLine]] = []
    for index, line in enumerate(lines):
        following = lines[index + 1].text if index + 1 < len(lines) else None
        if not groups or _starts_entry(
            line, lines[index - 1].text, following, indents[index], layout
        ):
            groups.append([line])
        else:
            groups[-1].append(line)

    entries: list[SplitEntry] = []
    for position, group in enumerate(groups):
        text = group[0].text
        for line in group[1:]:
            text = _join(text, line.text)
        # Sin sangría, todas las entradas empiezan con un patrón reconocible
        # salvo, quizá, la primera: el texto que precede a la lista.
        leading_text = position == 0 and layout is Layout.FLAT and not _looks_like_start(text)
        for piece in _split_inline_numbers(text):
            entries.append(SplitEntry(group[0].page, piece, _issue(piece, leading_text)))
    return entries


def _indents(lines: list[TextLine]) -> list[float]:
    """Sangría de cada línea respecto del margen de su columna en la página."""
    page_x0: dict[int, list[float]] = {}
    for line in lines:
        page_x0.setdefault(line.page, []).append(line.x0)
    return [
        line.x0 - min(x0 for x0 in page_x0[line.page] if line.x0 - COLUMN_GAP < x0 <= line.x0)
        for line in lines
    ]


def _layout(lines: list[TextLine], indents: list[float]) -> Layout:
    """Las referencias empiezan en el nivel (margen o sangría) donde más se reconoce su inicio."""
    at_margin = [line for line, indent in zip(lines, indents, strict=True) if indent < MIN_INDENT]
    indented = [
        line
        for line, indent in zip(lines, indents, strict=True)
        if MIN_INDENT <= indent <= MAX_INDENT
    ]
    if not at_margin or not indented:
        return Layout.FLAT
    margin_share, indented_share = _start_share(at_margin), _start_share(indented)
    if margin_share == indented_share:
        return Layout.FLAT
    return Layout.HANGING if margin_share > indented_share else Layout.FIRST_LINE


def _start_share(lines: list[TextLine]) -> float:
    starts = sum(
        _looks_like_start(line.text) or bool(AUTHOR_START.match(line.text)) for line in lines
    )
    return starts / len(lines)


def _looks_like_start(text: str) -> bool:
    return bool(IEEE_START.match(text) or AUTHOR_YEAR_START.match(text))


def _starts_entry(
    line: TextLine, previous: str, following: str | None, indent: float, layout: Layout
) -> bool:
    if IEEE_START.match(line.text):
        return True
    if layout is not Layout.FLAT:
        if (indent < MIN_INDENT) == (layout is Layout.HANGING):
            return True
        # Fuera de su nivel, solo si la anterior cerraba y esta empieza como referencia.
        if not CLOSED_ENDING.search(previous):
            return False
    if OPEN_ENDING.search(previous):
        return False
    # Una lista de autores larga deja el año en la línea siguiente.
    text = line.text
    if following and OPEN_ENDING.search(text):
        text = _join(text, following)
    return bool(AUTHOR_YEAR_START.match(text))


def _join(text: str, continuation: str) -> str:
    # Un apellido compuesto o una URL partidos al final de la línea se unen sin espacio.
    if text.endswith(("-", "/")):
        return text + continuation
    return f"{text} {continuation}"


def _split_inline_numbers(text: str) -> list[str]:
    """Separa las referencias IEEE que quedaron en una misma línea: "... [3] ... [4] ..."."""
    match = IEEE_START.match(text)
    if not match:
        return [text]
    pieces: list[str] = []
    number = int(match.group(1))
    while marker := re.search(rf"\s\[{number + 1}\]\s", text):
        pieces.append(text[: marker.start()])
        text = text[marker.start() + 1 :]
        number += 1
    pieces.append(text)
    return pieces


def _issue(text: str, leading_text: bool) -> str | None:
    if leading_text:
        return NOT_A_REFERENCE
    if GLUED_START.search(text):
        return GLUED
    if len(text) > MAX_ENTRY_CHARS:
        return TOO_LONG
    return None
