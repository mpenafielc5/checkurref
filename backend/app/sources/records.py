"""Formato interno común de una obra registrada en Crossref u OpenAlex.

Cada fuente responde con su propio formato; su adaptador lo traduce a
SourceRecord, y el resto del análisis solo conoce este formato.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.extraction.base import Author

DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
VALID_DOI = re.compile(r"^10\.\d{4,9}/\S+$")


class Source(str, Enum):
    CROSSREF = "crossref"
    OPENALEX = "openalex"


@dataclass(frozen=True)
class SourceRecord:
    source: Source
    doi: str | None
    title: str | None
    authors: tuple[Author, ...] = ()
    year: int | None = None
    # Otros años válidos de la misma obra (versión impresa o en línea): la
    # verificación acepta cualquiera, porque APA cita el año del número impreso.
    other_years: tuple[int, ...] = ()
    container: str | None = None  # revista, libro o congreso
    publisher: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    work_type: str | None = None
    score: float | None = None  # relevancia que da la fuente en una búsqueda
    # Respuesta original de la fuente, para guardarla en la caché.
    raw: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)


def normalize_doi(value: str | None) -> str | None:
    """DOI sin prefijos ("doi:", "https://doi.org/"), en minúsculas; None si no es un DOI.

    Así un DOI real mal escrito se encuentra igual: la forma incorrecta es un
    hallazgo de formato (T25), no una Contradicción.
    """
    if not value:
        return None
    doi = value.strip()
    # Algunos trabajos repiten el prefijo: "doi:https://doi.org/10...".
    while (stripped := DOI_PREFIX.sub("", doi)) != doi:
        doi = stripped
    doi = doi.rstrip(".,;)").lower()
    return doi if VALID_DOI.match(doi) else None
