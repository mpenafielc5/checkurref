"""Ubica los campos extraídos dentro del texto original de la referencia.

El informe pinta cada campo de un color en el texto tal como aparece en el
trabajo (autores, año, título y revista). El extractor da los valores, no sus
posiciones, así que se buscan en el texto. Lo que no se encuentra queda sin
color: el texto nunca se altera.
"""

import re

from app.extraction.base import ExtractedFields
from app.pipeline.patterns import IEEE_NUMBER
from app.verification.corrected import Segment
from app.verification.decision import CheckedField

LEADING_NUMBER = re.compile(rf"^\s*{IEEE_NUMBER}\s*")
# Signos entre los autores y el campo siguiente que no forman parte de los autores.
AUTHORS_TAIL = ' .,(“"«'


def highlight(text: str, fields: ExtractedFields | None) -> list[Segment]:
    if fields is None:
        return [Segment(text)]
    spans: list[tuple[int, int, CheckedField]] = []

    def add(start: int, end: int, field: CheckedField) -> None:
        if start >= 0 and not any(s < end and start < e for s, e, _ in spans):
            spans.append((start, end, field))

    def find(value: str, after: int = 0) -> re.Match[str] | None:
        # Sin distinguir mayúsculas y con posiciones del texto original.
        return re.compile(re.escape(value), re.IGNORECASE).search(text, after)

    title = (fields.title or "").strip().rstrip(".")
    if title and (match := find(title)):
        add(match.start(), match.end(), CheckedField.TITLE)
    container = (fields.container or "").strip().rstrip(".,")
    if container:
        after_title = max((end for _, end, f in spans if f is CheckedField.TITLE), default=0)
        if match := find(container, after_title) or find(container):
            add(match.start(), match.end(), CheckedField.CONTAINER)
    if fields.year:
        for match in re.finditer(rf"\b{fields.year}\b", text):
            if not any(s < match.end() and match.start() < e for s, e, _ in spans):
                add(match.start(), match.end(), CheckedField.YEAR)
                break
    if fields.authors and spans:
        start = LEADING_NUMBER.match(text)
        begin = start.end() if start else 0
        end = min(s for s, _, _ in spans)
        while end > begin and text[end - 1] in AUTHORS_TAIL and not _closes_initial(text, end):
            end -= 1
        if end > begin:
            add(begin, end, CheckedField.AUTHORS)

    segments: list[Segment] = []
    cursor = 0
    for start, end, field in sorted(spans):
        if start > cursor:
            segments.append(Segment(text[cursor:start]))
        segments.append(Segment(text[start:end], field))
        cursor = end
    if cursor < len(text):
        segments.append(Segment(text[cursor:]))
    return segments


def _closes_initial(text: str, end: int) -> bool:
    """El punto en text[end - 1] cierra una inicial ("Vera, J."): es parte del autor."""
    if text[end - 1] != "." or end < 2 or not text[end - 2].isupper():
        return False
    return end < 3 or not text[end - 3].isalpha()
