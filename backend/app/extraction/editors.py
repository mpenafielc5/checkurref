"""Separa a los editores de los autores.

En un capítulo de libro, la referencia nombra también a los editores del libro:
"Lara, A., & Prado, S. (2022). Título. En G. Salinas, … (Eds.), Libro". El
extractor reconoce el "In … (Eds.)" del inglés, pero con el "En" del español los
toma como autores del capítulo. En APA los autores van siempre antes del año; los
editores, después. Por eso, si la referencia marca editores, solo se conservan
los autores que aparecen antes del año.
"""

import re
import unicodedata
from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # solo para las anotaciones: base.py importa este módulo
    from app.extraction.base import ExtractedFields

# (Ed.), (Eds.), (Coord.), (Coords.), (Comp.), (Comps.), (Dir.), (Dirs.)
EDITORS_MARK = re.compile(r"\((?:eds?|coords?|comps?|dirs?)\.?\)", re.IGNORECASE)
# El año de APA entre paréntesis: (2022), (2022a) o (s. f.).
APA_YEAR = re.compile(r"\((?:\d{4}[a-z]?|s\.\s?f\.)", re.IGNORECASE)


def drop_editors(reference: str, fields: "ExtractedFields") -> "ExtractedFields":
    """Los campos sin los editores tomados como autores; sin cambios si no aplica."""
    if not EDITORS_MARK.search(reference):
        return fields
    year = APA_YEAR.search(reference)
    if year is None:
        return fields
    before_year = _fold(reference[: year.start()])
    authors = tuple(
        author for author in fields.authors if author.family and _fold(author.family) in before_year
    )
    # Si no quedara ninguno, la referencia no sigue el orden de APA: mejor no tocarla.
    if not authors or len(authors) == len(fields.authors):
        return fields
    return replace(fields, authors=authors)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()
