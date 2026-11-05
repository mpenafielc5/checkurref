"""DTO del historial de trabajos (HU-07), del estado de un análisis (HU-05) y del
informe de verificación (HU-06, HU-19).

Los campos de una referencia usan los valores de la base: titulo, autores, anio,
contenedor, doi, volumen, paginas, numero y editorial. Los nombres que ve el
usuario los pone el frontend.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AnalysisItem(BaseModel):
    """Un trabajo del historial, o el estado de un análisis para la pantalla de progreso."""

    analysis_id: UUID
    document_id: UUID
    file_name: str
    created_at: datetime
    # en_cola, extrayendo, segmentando, verificando, completado o error.
    status: str
    progress: int
    total_references: int | None
    # APA, IEEE, MIXTA o DESCONOCIDA; None mientras no se detecta.
    norm: str | None
    # Índice de veracidad de 0 a 100; None mientras se analiza o si no hay referencias que contar.
    index: float | None
    error_message: str | None


class HistoryPage(BaseModel):
    items: list[AnalysisItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class VerdictCounts(BaseModel):
    verificada: int = 0
    discrepancia: int = 0
    contradiccion: int = 0
    sin_respaldo: int = 0
    no_verificable: int = 0
    # Referencias sin veredicto: una fuente no respondió o falló el sistema. No
    # cuentan en el índice de veracidad.
    error_consulta: int = 0


class FieldDifference(BaseModel):
    field: str
    references: int  # referencias en las que ese campo difiere del registro


class TextSegment(BaseModel):
    text: str
    field: str | None = None  # titulo, autores, anio o contenedor; None: texto sin color


class CorrectedSegment(BaseModel):
    text: str
    field: str | None
    italic: bool
    changed: bool


class CorrectedReference(BaseModel):
    """Referencia corregida para copiar (HU-19): `text` es lo que va al portapapeles."""

    text: str
    changed_fields: list[str]
    segments: list[CorrectedSegment]


class FieldComparison(BaseModel):
    field: str
    given: str
    # Valor del registro. Si el campo coincide, es el mismo valor citado.
    official: str | None
    matches: bool
    # Nivel de confianza (0-1) de la comparación difusa; None en la directa.
    similarity: float | None


class NliResult(BaseModel):
    field: str
    entailment: float
    neutral: float
    contradiction: float


class Finding(BaseModel):
    code: str
    severity: str  # info, advertencia o critico
    message: str
    field: str | None
    given: str | None
    # En un hallazgo de veracidad, el valor del registro; en uno de formato, cómo debería ir.
    official: str | None


class ReferenceReport(BaseModel):
    order: int
    page: int | None
    norm: str | None
    text: str
    segments: list[TextSegment]
    # None: error de consulta o interno (el motivo está en veracity_findings).
    verdict: str | None
    # doi_directo, busqueda_bibliografica o sin_consulta; None sin veredicto.
    strategy: str | None
    comparisons: list[FieldComparison]
    nli: list[NliResult]
    veracity_findings: list[Finding]
    format_findings: list[Finding]
    corrected: CorrectedReference | None


class ReportResponse(BaseModel):
    """El informe completo. El filtro por veredicto y la paginación de 10 en 10 se
    hacen en el navegador: un trabajo tiene decenas de referencias, no miles."""

    analysis_id: UUID
    document_id: UUID
    file_name: str
    created_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    norm: str | None
    engine: str
    total_references: int
    index: float | None
    counts: VerdictCounts
    # Campos que más difieren del registro, de mayor a menor (HU-06 CA01).
    most_different_fields: list[FieldDifference]
    references: list[ReferenceReport]
