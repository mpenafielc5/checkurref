"""Interfaz común de los extractores de campos (patrón Strategy).

Cada extractor recibe el texto de una referencia y devuelve sus campos. El
resto del pipeline solo conoce esta interfaz: puede usar AnyStyle o spaCy, y el
Laboratorio puede compararlos, sin saber cómo trabaja cada uno.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from enum import Enum

from app.extraction.editors import drop_editors

logger = logging.getLogger(__name__)

EXTRACTION_FAILED = "No se pudieron extraer los campos de esta referencia."


class Engine(str, Enum):
    """Valores del tipo motor_extraccion de la base de datos."""

    ANYSTYLE = "anystyle"
    SPACY = "spacy"


@dataclass(frozen=True)
class Author:
    family: str  # apellido, o el nombre completo de una organización
    given: str = ""  # nombres o iniciales; vacío en una organización


@dataclass(frozen=True)
class ExtractedFields:
    authors: tuple[Author, ...] = ()
    year: int | None = None
    title: str | None = None
    container: str | None = None  # revista, libro, congreso o sitio que contiene la obra
    publisher: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None


@dataclass(frozen=True)
class Extraction:
    """Resultado de extraer una referencia: sus campos o el motivo del fallo."""

    fields: ExtractedFields | None
    elapsed_ms: int
    error: str | None = None


class ExtractionError(Exception):
    """El extractor no pudo procesar una o varias referencias."""


class ReferenceExtractor(ABC):
    engine: Engine

    @abstractmethod
    def extract(self, reference: str) -> ExtractedFields:
        """Campos de una referencia. Lanza ExtractionError si no puede procesarla."""

    def available(self) -> bool:
        """Si el motor se puede usar en esta máquina."""
        return True

    def version(self) -> str | None:
        """Versión del motor, para guardarla con cada medición; None si no se conoce."""
        return None

    def extract_all(self, references: list[str]) -> list[Extraction]:
        """Campos de cada referencia, en el mismo orden.

        Si falla con una referencia, se registra, se marca solo esa y se sigue
        con las demás: un error nunca detiene el documento.
        """
        return [self._extract_one(position, text) for position, text in enumerate(references, 1)]

    def _extract_one(self, position: int, reference: str) -> Extraction:
        start = time.perf_counter()
        try:
            fields = self.extract(reference)
        except Exception:  # cualquier fallo afecta solo a esta referencia
            logger.exception("%s no pudo extraer la referencia %d", self.engine.value, position)
            return Extraction(None, elapsed_ms(start), EXTRACTION_FAILED)
        return Extraction(tidy_fields(reference, fields), elapsed_ms(start))


def tidy_fields(reference: str, fields: ExtractedFields) -> ExtractedFields:
    """Arreglos comunes a los dos motores, antes de guardar los campos."""
    return close_title_parenthesis(reference, drop_editors(reference, fields))


def close_title_parenthesis(reference: str, fields: ExtractedFields) -> ExtractedFields:
    """Devuelve al título el paréntesis de cierre que el extractor dejó fuera.

    El número de informe va entre paréntesis tras el título ("Marco de
    autorización (Informe n.° 12)") y el extractor a veces corta el título antes
    del cierre. Solo se cierra si la referencia trae el título con su paréntesis.
    """
    title = fields.title
    if not title or title.count("(") <= title.count(")"):
        return fields
    closed = f"{title.rstrip()})"
    return replace(fields, title=closed) if closed in reference else fields


def elapsed_ms(start: float) -> int:
    """Milisegundos desde `start` (un valor de time.perf_counter)."""
    return round((time.perf_counter() - start) * 1000)
