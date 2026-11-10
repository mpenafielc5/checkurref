"""Lotes de auditoría del docente y el resultado de sus trabajos (PostgREST de Supabase)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import TypeAdapter

from app.repositories.supabase_http import get_counted, send
from app.verification.findings import MISMATCH_CODES

BATCH_COLUMNS = "id,docente_id,nombre,periodo_academico,creado_en"
DATETIME = TypeAdapter(datetime)


@dataclass(frozen=True)
class StoredBatch:
    id: UUID
    teacher_id: UUID
    name: str
    period: str | None
    created_at: datetime


@dataclass(frozen=True)
class StoredBatchAnalysis:
    """Lo que se necesita de un análisis para saber su estado y su riesgo."""

    status: str
    index: float | None
    contradictions: int


@dataclass(frozen=True)
class BatchOverview:
    batch: StoredBatch
    analyses: tuple[StoredBatchAnalysis, ...]


@dataclass(frozen=True)
class BatchPage:
    items: list[BatchOverview]
    total: int


@dataclass(frozen=True)
class StoredWork:
    analysis_id: UUID
    document_id: UUID
    file_name: str
    created_at: datetime
    status: str
    progress: int
    total_references: int | None
    norm: str | None
    index: float | None
    error_message: str | None
    # Una por referencia; None si no tiene veredicto (error de consulta o interno).
    verdicts: tuple[str | None, ...] = ()
    # Campo de cada hallazgo de veracidad que dice que un dato difiere del registro.
    different_fields: tuple[str, ...] = ()


class BatchRepository(Protocol):
    def create(self, teacher_id: UUID, name: str, period: str) -> StoredBatch: ...

    def get(self, batch_id: UUID) -> StoredBatch | None: ...

    def list_batches(self, teacher_id: UUID, offset: int, limit: int) -> BatchPage:
        """Lotes del docente, del más reciente al más antiguo."""
        ...

    def count_works(self, batch_id: UUID) -> int: ...

    def works(self, batch_id: UUID) -> list[StoredWork]:
        """Trabajos del lote con el análisis más reciente de cada uno."""
        ...


class SupabaseBatchRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._rest_url = rest_url
        self._client = client

    def create(self, teacher_id: UUID, name: str, period: str) -> StoredBatch:
        rows = send(
            self._client,
            "POST",
            f"{self._rest_url}/t_lotes_auditoria",
            params={"select": BATCH_COLUMNS},
            json={"docente_id": str(teacher_id), "nombre": name, "periodo_academico": period},
            headers={"Prefer": "return=representation"},
        )
        return _batch(rows[0])

    def get(self, batch_id: UUID) -> StoredBatch | None:
        rows = send(
            self._client,
            "GET",
            f"{self._rest_url}/t_lotes_auditoria",
            params={"select": BATCH_COLUMNS, "id": f"eq.{batch_id}"},
        )
        return _batch(rows[0]) if rows else None

    def list_batches(self, teacher_id: UUID, offset: int, limit: int) -> BatchPage:
        # De cada referencia solo interesan las contradicciones: deciden el riesgo alto.
        references = "t_referencias(id,t_verificaciones!inner(veredicto))"
        contradictions = "t_documentos.t_analisis.t_referencias.t_verificaciones.veredicto"
        rows, total = get_counted(
            self._client,
            f"{self._rest_url}/t_lotes_auditoria",
            {
                "select": (
                    f"{BATCH_COLUMNS},"
                    f"t_documentos(t_analisis(estado,indice_veracidad,creado_en,{references}))"
                ),
                "docente_id": f"eq.{teacher_id}",
                contradictions: "eq.contradiccion",
                "t_documentos.t_analisis.order": "creado_en.desc",
                "order": "creado_en.desc",
                "offset": str(offset),
                "limit": str(limit),
            },
        )
        return BatchPage([_overview(row) for row in rows], total)

    def count_works(self, batch_id: UUID) -> int:
        return get_counted(
            self._client,
            f"{self._rest_url}/t_documentos",
            {"select": "id", "lote_id": f"eq.{batch_id}", "limit": "1"},
        )[1]

    def works(self, batch_id: UUID) -> list[StoredWork]:
        references = "t_referencias(t_verificaciones(veredicto),t_hallazgos(tipo,codigo,campo))"
        rows = send(
            self._client,
            "GET",
            f"{self._rest_url}/t_documentos",
            params={
                "select": (
                    "id,nombre_archivo,creado_en,t_analisis(id,estado,progreso,total_referencias,"
                    f"norma_detectada,indice_veracidad,mensaje_error,creado_en,{references})"
                ),
                "lote_id": f"eq.{batch_id}",
                "t_analisis.order": "creado_en.desc",
                "order": "creado_en.asc",
            },
        )
        return [work for work in map(_work, rows) if work]


def _batch(row: dict[str, Any]) -> StoredBatch:
    return StoredBatch(
        id=UUID(row["id"]),
        teacher_id=UUID(row["docente_id"]),
        name=row["nombre"],
        period=row.get("periodo_academico"),
        created_at=DATETIME.validate_python(row["creado_en"]),
    )


def _overview(row: dict[str, Any]) -> BatchOverview:
    latest = (
        document["t_analisis"][0]
        for document in row.get("t_documentos") or []
        if document.get("t_analisis")
    )
    return BatchOverview(
        batch=_batch(row),
        analyses=tuple(
            StoredBatchAnalysis(
                status=analysis["estado"],
                index=_number(analysis.get("indice_veracidad")),
                contradictions=len(analysis.get("t_referencias") or []),
            )
            for analysis in latest
        ),
    )


def _work(row: dict[str, Any]) -> StoredWork | None:
    analyses = row.get("t_analisis") or []
    if not analyses:
        return None
    analysis = analyses[0]
    references = analysis.get("t_referencias") or []
    return StoredWork(
        analysis_id=UUID(analysis["id"]),
        document_id=UUID(row["id"]),
        file_name=row["nombre_archivo"],
        created_at=DATETIME.validate_python(analysis["creado_en"]),
        status=analysis["estado"],
        progress=analysis["progreso"],
        total_references=analysis.get("total_referencias"),
        norm=analysis.get("norma_detectada"),
        index=_number(analysis.get("indice_veracidad")),
        error_message=analysis.get("mensaje_error"),
        verdicts=tuple(_verdict(reference) for reference in references),
        different_fields=tuple(
            finding["campo"]
            for reference in references
            for finding in reference.get("t_hallazgos") or []
            if finding["tipo"] == "veracidad"
            and finding.get("campo")
            and finding["codigo"] in MISMATCH_CODES
        ),
    )


def _verdict(reference: dict[str, Any]) -> str | None:
    """t_verificaciones es uno a uno: PostgREST lo devuelve como objeto (o como lista)."""
    verification = reference.get("t_verificaciones")
    if isinstance(verification, list):
        verification = verification[0] if verification else None
    return verification["veredicto"] if verification else None


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None
