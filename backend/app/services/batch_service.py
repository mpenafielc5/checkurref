"""Casos de uso: auditar un lote de documentos (CU-06, HU-08 y HU-09).

Un docente solo ve sus lotes: uno ajeno responde igual que uno inexistente, para
no revelar que existe. Los trabajos del lote son del docente que los subió, así
que su informe se abre con la misma ruta y la misma regla que el del estudiante.

El riesgo solo mira el índice de veracidad y las contradicciones: el formato no
cuenta (HU-21 CA04).
"""

import math
from collections import Counter
from uuid import UUID

from app.repositories.batches import (
    BatchOverview,
    BatchRepository,
    StoredBatch,
    StoredBatchAnalysis,
    StoredWork,
)
from app.schemas.batch import BatchDetail, BatchesPage, BatchSummary, BatchWork
from app.schemas.report import FieldDifference, VerdictCounts
from app.services.upload_service import UploadRejectedError, UploadResult, UploadService

BATCHES_PAGE_SIZE = 20
MAX_WORKS_PER_BATCH = 40  # HU-08 CA02
COMPLETED = "completado"
FAILED = "error"
CONTRADICTION = "contradiccion"
DISCREPANCY = "discrepancia"

# Índices que separan el riesgo de un trabajo (RF20-CA02).
HIGH_RISK_BELOW = 60.0
LOW_RISK_FROM = 85.0
HIGH = "alto"
MEDIUM = "medio"
LOW = "bajo"

BATCH_FULL = f"El lote ya tiene el máximo de {MAX_WORKS_PER_BATCH} trabajos."


class BatchNotFoundError(Exception):
    """El lote no existe o no es del docente."""


def risk_of(index: float | None, contradictions: int) -> str | None:
    """Riesgo de un trabajo; None si aún no hay referencias que permitan calcularlo."""
    if contradictions > 0:
        return HIGH
    if index is None:
        return None
    if index < HIGH_RISK_BELOW:
        return HIGH
    return LOW if index >= LOW_RISK_FROM else MEDIUM


class BatchService:
    def __init__(self, batches: BatchRepository, uploads: UploadService | None = None) -> None:
        self._batches = batches
        self._uploads = uploads

    def create(self, teacher_id: UUID, name: str, period: str) -> BatchSummary:
        return _summary(BatchOverview(self._batches.create(teacher_id, name, period), ()))

    def list_batches(self, teacher_id: UUID, page: int) -> BatchesPage:
        page = max(page, 1)
        result = self._batches.list_batches(
            teacher_id, (page - 1) * BATCHES_PAGE_SIZE, BATCHES_PAGE_SIZE
        )
        return BatchesPage(
            items=[_summary(item) for item in result.items],
            page=page,
            page_size=BATCHES_PAGE_SIZE,
            total=result.total,
            total_pages=max(1, math.ceil(result.total / BATCHES_PAGE_SIZE)),
        )

    def detail(self, teacher_id: UUID, batch_id: UUID) -> BatchDetail:
        batch = self._owned(teacher_id, batch_id)
        stored = self._batches.works(batch_id)
        works = [_work(item) for item in stored]
        # Un análisis en curso aún no tiene veredictos: contarlo parecería un error de consulta.
        finished = [item for item in stored if item.status == COMPLETED]
        analyses = tuple(
            StoredBatchAnalysis(item.status, item.index, _count(item, CONTRADICTION))
            for item in stored
        )
        return BatchDetail(
            **_summary(BatchOverview(batch, analyses)).model_dump(),
            references=sum(len(item.verdicts) for item in finished),
            counts=_counts(finished),
            most_different_fields=_most_different(finished),
            works=works,
        )

    def submit_work(
        self, teacher_id: UUID, batch_id: UUID, file_name: str, content: bytes
    ) -> UploadResult:
        """Sube un PDF al lote. Se llama una vez por archivo: el estado de cada uno es
        independiente y un error no detiene a los demás (RNF09)."""
        if self._uploads is None:
            raise RuntimeError("BatchService sin servicio de subida")
        self._owned(teacher_id, batch_id)
        if self._batches.count_works(batch_id) >= MAX_WORKS_PER_BATCH:
            raise UploadRejectedError(BATCH_FULL)
        return self._uploads.submit(teacher_id, file_name, content, batch_id)

    def _owned(self, teacher_id: UUID, batch_id: UUID) -> StoredBatch:
        batch = self._batches.get(batch_id)
        if batch is None or batch.teacher_id != teacher_id:
            raise BatchNotFoundError(str(batch_id))
        return batch


def _summary(overview: BatchOverview) -> BatchSummary:
    batch, analyses = overview.batch, overview.analyses
    finished = [item for item in analyses if item.status == COMPLETED]
    failed = sum(item.status == FAILED for item in analyses)
    return BatchSummary(
        id=batch.id,
        name=batch.name,
        period=batch.period,
        created_at=batch.created_at,
        total_works=len(analyses),
        finished=len(finished),
        failed=failed,
        in_progress=len(analyses) - len(finished) - failed,
        high_risk=sum(risk_of(item.index, item.contradictions) == HIGH for item in finished),
    )


def _work(work: StoredWork) -> BatchWork:
    finished = work.status == COMPLETED
    contradictions = _count(work, CONTRADICTION)
    return BatchWork(
        analysis_id=work.analysis_id,
        document_id=work.document_id,
        file_name=work.file_name,
        created_at=work.created_at,
        status=work.status,
        progress=work.progress,
        total_references=work.total_references,
        norm=work.norm,
        index=work.index,
        contradictions=contradictions if finished else 0,
        alerts=contradictions + _count(work, DISCREPANCY) if finished else 0,
        risk=risk_of(work.index, contradictions) if finished else None,
        error_message=work.error_message,
    )


def _count(work: StoredWork, verdict: str) -> int:
    return sum(item == verdict for item in work.verdicts)


def _counts(works: list[StoredWork]) -> VerdictCounts:
    tally = Counter(verdict or "error_consulta" for work in works for verdict in work.verdicts)
    return VerdictCounts(**tally)


def _most_different(works: list[StoredWork]) -> list[FieldDifference]:
    tally = Counter(field for work in works for field in work.different_fields)
    return [
        FieldDifference(field=field, references=count)
        for field, count in sorted(tally.items(), key=lambda item: (-item[1], item[0]))
    ]
