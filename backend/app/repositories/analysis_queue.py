"""Cola de análisis sobre la tabla analisis (patrón Productor-Consumidor).

La API produce: crea el análisis "en_cola". El worker consume: toma el más
antiguo con una actualización condicionada (solo si sigue "en_cola"), así dos
procesos nunca toman el mismo análisis.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

import httpx

from app.extraction.base import Engine
from app.repositories.supabase_http import send

QUEUED = "en_cola"
IN_PROGRESS = ("extrayendo", "segmentando", "verificando")
# Análisis que se revisan por vuelta: si otro proceso tomó uno, se intenta el siguiente.
CANDIDATES = 5


@dataclass(frozen=True)
class QueuedAnalysis:
    analysis_id: UUID
    document_id: UUID
    storage_path: str


class AnalysisQueue(Protocol):
    def claim_next(self) -> QueuedAnalysis | None: ...

    def report(self, analysis_id: UUID, status: str, progress: int) -> None: ...

    def complete(self, analysis_id: UUID, engine: Engine, duration_ms: int) -> None: ...

    def fail(self, analysis_id: UUID, message: str, duration_ms: int | None = None) -> None: ...

    def requeue_interrupted(self) -> int: ...


class SupabaseAnalysisQueue:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/analisis"
        self._client = client

    def claim_next(self) -> QueuedAnalysis | None:
        candidates = self._send(
            "GET",
            params={
                "select": "id,documento_id,documentos(ruta_storage)",
                "estado": f"eq.{QUEUED}",
                "order": "creado_en.asc",
                "limit": str(CANDIDATES),
            },
        )
        for row in candidates:
            claimed = self._send(
                "PATCH",
                params={"id": f"eq.{row['id']}", "estado": f"eq.{QUEUED}"},
                json={"estado": IN_PROGRESS[0], "progreso": 5, "iniciado_en": _now()},
                headers={"Prefer": "return=representation"},
            )
            if claimed:
                return QueuedAnalysis(
                    analysis_id=UUID(row["id"]),
                    document_id=UUID(row["documento_id"]),
                    storage_path=row["documentos"]["ruta_storage"],
                )
        return None

    def report(self, analysis_id: UUID, status: str, progress: int) -> None:
        self._update(analysis_id, {"estado": status, "progreso": progress})

    def complete(self, analysis_id: UUID, engine: Engine, duration_ms: int) -> None:
        self._update(
            analysis_id,
            {
                "estado": "completado",
                "progreso": 100,
                "extractor_principal": engine.value,
                "mensaje_error": None,
                "finalizado_en": _now(),
                "duracion_ms": duration_ms,
            },
        )

    def fail(self, analysis_id: UUID, message: str, duration_ms: int | None = None) -> None:
        self._update(
            analysis_id,
            {
                "estado": "error",
                "mensaje_error": message,
                "finalizado_en": _now(),
                "duracion_ms": duration_ms,
            },
        )

    def requeue_interrupted(self) -> int:
        """Devuelve a la cola los análisis que quedaron a medias (el servidor se reinició)."""
        rows = self._send(
            "PATCH",
            params={"estado": f"in.({','.join(IN_PROGRESS)})"},
            json={"estado": QUEUED, "progreso": 0},
            headers={"Prefer": "return=representation"},
        )
        return len(rows)

    def _update(self, analysis_id: UUID, values: dict[str, Any]) -> None:
        self._send("PATCH", params={"id": f"eq.{analysis_id}"}, json=values)

    def _send(self, method: str, **options: Any) -> list[dict[str, Any]]:
        return send(self._client, method, self._url, **options)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
