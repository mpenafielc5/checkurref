"""DTO de los lotes de auditoría (HU-08, HU-09, HU-10)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.schemas.report import FieldDifference, VerdictCounts

# Los mismos límites que las columnas de t_lotes_auditoria.
BatchName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
BatchPeriod = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class BatchCreate(BaseModel):
    """El lote requiere un nombre y un periodo académico (HU-08 CA01)."""

    name: BatchName
    period: BatchPeriod


class BatchSummary(BaseModel):
    id: UUID
    name: str
    period: str | None
    created_at: datetime
    total_works: int
    finished: int
    in_progress: int
    failed: int
    high_risk: int


class BatchesPage(BaseModel):
    items: list[BatchSummary]
    page: int
    page_size: int
    total: int
    total_pages: int


class BatchWork(BaseModel):
    analysis_id: UUID
    document_id: UUID
    file_name: str
    # Leídos de la portada; vacío: se muestra el archivo y "Portada no reconocida" (RF19-CA03).
    authors: list[str]
    created_at: datetime
    # en_cola, extrayendo, segmentando, verificando, completado o error.
    status: str
    progress: int
    total_references: int | None
    norm: str | None
    index: float | None
    contradictions: int
    # Referencias con Contradicción o Discrepancia. Sin respaldo no es una alerta: no
    # significa que la obra sea falsa.
    alerts: int
    # alto, medio o bajo; None mientras se analiza o si no hay con qué calcularlo.
    risk: str | None
    error_message: str | None


class BatchDetail(BatchSummary):
    """El tablero completo: el navegador ordena y pagina, porque un lote tiene 40 trabajos."""

    references: int
    counts: VerdictCounts
    most_different_fields: list[FieldDifference]
    works: list[BatchWork]


class ExportReference(BaseModel):
    order: int
    text: str
    # None: sin veredicto, porque una fuente no respondió.
    verdict: str | None
    # Códigos de campo; el navegador les pone el nombre que ve el usuario.
    different_fields: list[str]


class ExportWork(BaseModel):
    file_name: str
    authors: list[str]
    status: str
    error_message: str | None
    # Vacía si el análisis no terminó.
    references: list[ExportReference]


class BatchExport(BaseModel):
    """Datos del CSV del lote (HU-10). El navegador arma el archivo con los nombres de la
    interfaz, los mismos de la pantalla."""

    name: str
    works: list[ExportWork]
