"""Mediciones de los motores contra el estándar de oro (tabla t_corridas_benchmark)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

import httpx
from pydantic import TypeAdapter

from app.repositories.supabase_http import send

DATETIME = TypeAdapter(datetime)
VERSION_LENGTH = 60  # el largo de version_modelo


@dataclass(frozen=True)
class StoredScore:
    """Una fila de la tabla: un motor y un campo en una medición."""

    engine: str
    field: str
    precision: float
    recall: float
    f1: float
    samples: int
    version: str | None
    executed_at: datetime


class BenchmarkRunRepository(Protocol):
    def save(self, scores: list[StoredScore]) -> None:
        """Guarda una medición completa: todas sus filas o ninguna."""
        ...

    def recent(self, limit: int) -> list[StoredScore]:
        """Las filas más recientes, de la medición más nueva a la más antigua."""
        ...


class SupabaseBenchmarkRunRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/t_corridas_benchmark"
        self._client = client

    def save(self, scores: list[StoredScore]) -> None:
        # Un solo POST con todas las filas: PostgREST lo aplica en una transacción.
        send(self._client, "POST", self._url, json=[_row(score) for score in scores])

    def recent(self, limit: int) -> list[StoredScore]:
        rows = send(
            self._client,
            "GET",
            self._url,
            params={
                "select": (
                    "motor,campo,precision_score,recall_score,f1_score,"
                    "total_muestras,version_modelo,ejecutado_en"
                ),
                "order": "ejecutado_en.desc",
                "limit": str(limit),
            },
        )
        return [_score(row) for row in rows]


def _row(score: StoredScore) -> dict[str, Any]:
    return {
        "motor": score.engine,
        "campo": score.field,
        "precision_score": round(score.precision, 4),
        "recall_score": round(score.recall, 4),
        "f1_score": round(score.f1, 4),
        "total_muestras": score.samples,
        "version_modelo": score.version[:VERSION_LENGTH] if score.version else None,
        "ejecutado_en": score.executed_at.isoformat(),
    }


def _score(row: dict[str, Any]) -> StoredScore:
    return StoredScore(
        engine=row["motor"],
        field=row["campo"],
        precision=float(row.get("precision_score") or 0),
        recall=float(row.get("recall_score") or 0),
        f1=float(row.get("f1_score") or 0),
        samples=row["total_muestras"],
        version=row.get("version_modelo"),
        executed_at=DATETIME.validate_python(row["ejecutado_en"]),
    )
