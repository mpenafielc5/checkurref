"""Hallazgos de veracidad de una referencia verificada (tabla hallazgos, tipo veracidad).

Cada campo que no coincide con el registro se guarda con el valor de la
referencia y el oficial, para que el informe muestre qué cambiar. Los mensajes
describen la diferencia sin culpar al estudiante: el dato pudo leerse mal del PDF.
"""

from dataclasses import dataclass
from enum import Enum

from app.sources.lookup import Strategy
from app.verification.decision import CheckedField, FieldCheck, Verdict, Verification

QUERY_ERROR_CODE = "ERROR_CONSULTA"
INTERNAL_ERROR_CODE = "ERROR_VERIFICACION"
OTHER_WORK_CODE = "OTRA_OBRA"

QUERY_ERROR = (
    "No se pudo consultar Crossref ni OpenAlex para esta referencia. No cuenta en el "
    "índice de veracidad; el resultado puede cambiar si se repite el análisis más tarde."
)
INTERNAL_ERROR = (
    "El sistema no pudo completar la verificación de esta referencia. No cuenta en el "
    "índice de veracidad."
)

SOURCE_NAMES = {"crossref": "Crossref", "openalex": "OpenAlex"}

# Código y mensaje de cada campo distinto; {fuente} es Crossref u OpenAlex.
MISMATCH = {
    CheckedField.TITLE: ("TITULO_DISTINTO", "El título no coincide con el registro de {fuente}."),
    CheckedField.AUTHORS: (
        "AUTORES_DISTINTOS",
        "Uno o más autores citados no figuran en el registro de {fuente}.",
    ),
    CheckedField.YEAR: (
        "ANIO_DISTINTO",
        "El año de publicación no coincide con el registro de {fuente}.",
    ),
    CheckedField.DOI: ("DOI_DISTINTO", "El DOI no coincide con el registro de {fuente}."),
    CheckedField.CONTAINER: (
        "CONTENEDOR_DISTINTO",
        "La revista, el libro o el congreso no coincide con el registro de {fuente}.",
    ),
    CheckedField.VOLUME: (
        "VOLUMEN_DISTINTO",
        "El volumen no coincide con el registro de {fuente}.",
    ),
    CheckedField.PAGES: (
        "PAGINAS_DISTINTAS",
        "Las páginas no coinciden con el registro de {fuente}.",
    ),
}
UNREGISTERED_DOI = (
    "DOI_NO_REGISTRADO",
    "Ninguna fuente registra el DOI citado; la obra se encontró en {fuente} por su título.",
)
# Códigos de un campo que difiere del registro (los demás son avisos sobre la referencia).
MISMATCH_CODES = frozenset(code for code, _ in MISMATCH.values()) | {UNREGISTERED_DOI[0]}


class Severity(str, Enum):
    """Valores del tipo severidad de la base de datos."""

    INFO = "info"
    WARNING = "advertencia"
    CRITICAL = "critico"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str
    field: CheckedField | None = None
    given: str | None = None
    official: str | None = None


def findings_for(verification: Verification | None) -> list[Finding]:
    """Hallazgos de una referencia; `None` es una verificación que falló por un error interno."""
    if verification is None:
        return [Finding(INTERNAL_ERROR_CODE, Severity.INFO, INTERNAL_ERROR)]
    if verification.query_failed:
        return [Finding(QUERY_ERROR_CODE, Severity.INFO, QUERY_ERROR)]
    record = verification.record
    if record is None:  # Sin respaldo o No verificable: el veredicto lo dice todo
        return []
    source = SOURCE_NAMES.get(record.source.value, record.source.value)
    found: list[Finding] = []
    if verification.verdict is Verdict.CONTRADICTION:
        doi = verification.check(CheckedField.DOI)
        found.append(
            Finding(
                OTHER_WORK_CODE,
                Severity.CRITICAL,
                f"El DOI citado corresponde a otra obra en {source}.",
                CheckedField.DOI,
                doi.given if doi else None,
                record.title,
            )
        )
    searched = verification.strategy is Strategy.BIBLIOGRAPHIC_SEARCH
    found.extend(_mismatch(check, source, searched) for check in verification.mismatches)
    return found


def _mismatch(check: FieldCheck, source: str, searched: bool) -> Finding:
    # Con la búsqueda por título, el DOI citado no lo tiene ninguna fuente (si no,
    # se habría encontrado por DOI); el oficial, si hay, es el de la obra hallada.
    unregistered = check.field is CheckedField.DOI and searched
    code, message = UNREGISTERED_DOI if unregistered else MISMATCH[check.field]
    return Finding(
        code,
        Severity.WARNING,
        message.format(fuente=source),
        check.field,
        check.given,
        check.official,
    )
