"""Detección de la norma (APA o IEEE) de cada referencia y de la lista completa.

Nadie elige la norma al subir el trabajo: se reconoce por los rasgos que cada
una deja en el texto plano del PDF. Cada rasgo suma puntos a su norma y gana la
que tenga más, siempre que llegue al mínimo.

- IEEE: [n] al inicio, iniciales antes del apellido (J. Pérez), título entre
  comillas, vol., no. y pp., y el año al final.
- APA: año entre paréntesis después de los autores, apellido antes de las
  iniciales (Pérez, J.) y volumen(número).
"""

import re
from collections import Counter
from enum import Enum

from app.pipeline.patterns import (
    IEEE_NUMBER,
    INITIALS,
    LOWER,
    SURNAME_FIRST,
    UPPER,
    YEAR_IN_PARENS,
)

IEEE_FEATURES: list[tuple[re.Pattern[str], int]] = [
    (re.compile(rf"^{IEEE_NUMBER}"), 3),
    (re.compile(rf"^(?:{IEEE_NUMBER}\s*)?{INITIALS}\s?[{UPPER}][{LOWER}]"), 2),
    (re.compile(r"[“\"][^”\"]{8,}[”\"]"), 2),
    (re.compile(r"\bvol\.\s?\d", re.IGNORECASE), 1),
    (re.compile(r"\bno\.\s?\d", re.IGNORECASE), 1),
    # "(pp. 10-25)" entre paréntesis es de un capítulo en APA: no cuenta.
    (re.compile(r"(?<!\()\bpp\.\s?\d"), 1),
    # El año va al final, a veces seguido del DOI: ", 2021." o ", Mar. 2021, doi: ...".
    (re.compile(r",\s(?:[A-Z][a-z]{2,4}\.?\s)?(?:19|20)\d{2}(?:[.,]|$)"), 1),
]
APA_FEATURES: list[tuple[re.Pattern[str], int]] = [
    (re.compile(rf"^[^\[\d][^()]{{0,250}}?{YEAR_IN_PARENS}"), 3),
    (re.compile(rf"^{SURNAME_FIRST}"), 2),
    (re.compile(r"\b\d+\(\d+(?:[-–]\d+)?\)"), 1),
]
# Puntos mínimos para reconocer una norma: el rasgo más fuerte de cada una basta.
MIN_SCORE = 3
# La lista es MIXTA si la norma minoritaria aparece al menos en estas referencias
# o en esta fracción; así una sola referencia confusa en una lista larga no basta.
MIN_MIXED_COUNT = 2
MIN_MIXED_SHARE = 0.2


class Norm(str, Enum):
    """Valores del tipo norma_bibliografica de la base de datos."""

    APA = "APA"
    IEEE = "IEEE"
    MIXED = "MIXTA"
    UNKNOWN = "DESCONOCIDA"


def detect_reference_norm(text: str) -> Norm:
    """Norma de una referencia: APA, IEEE o DESCONOCIDA (nunca MIXTA)."""
    apa = _score(text, APA_FEATURES)
    ieee = _score(text, IEEE_FEATURES)
    if max(apa, ieee) < MIN_SCORE or apa == ieee:
        return Norm.UNKNOWN
    return Norm.APA if apa > ieee else Norm.IEEE


def detect_document_norm(norms: list[Norm]) -> Norm:
    """Norma de la lista completa a partir de la de cada referencia."""
    counts = Counter(norm for norm in norms if norm in (Norm.APA, Norm.IEEE))
    if not counts:
        return Norm.UNKNOWN
    (majority, _), *rest = counts.most_common()
    if not rest:
        return majority
    minority = rest[0][1]
    if minority >= MIN_MIXED_COUNT or minority / counts.total() >= MIN_MIXED_SHARE:
        return Norm.MIXED
    return majority


def _score(text: str, features: list[tuple[re.Pattern[str], int]]) -> int:
    return sum(points for pattern, points in features if pattern.search(text))
