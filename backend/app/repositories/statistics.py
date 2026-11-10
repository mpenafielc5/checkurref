"""Lecturas para las estadísticas de cada rol (PostgREST de Supabase).

Un estudiante o un docente tiene pocos trabajos: se leen y se resumen en el
servicio. Las cifras globales abarcan todo el sistema, así que se piden a la base
como conteos y nunca se traen sus filas.
"""

from typing import Protocol
from uuid import UUID

import httpx

from app.repositories.batches import WORK_SELECT, StoredWork, work_from_row
from app.repositories.supabase_http import get_counted, send

COMPLETED = "completado"
# Una sola fila basta: el total llega en la cabecera de la respuesta.
COUNT_ONLY = {"limit": "1"}


class StatisticsRepository(Protocol):
    def works_of(self, owner_id: UUID, in_batches: bool) -> list[StoredWork]:
        """Trabajos del usuario, con su análisis más reciente."""
        ...

    def count_batches(self, teacher_id: UUID) -> int: ...

    def count_documents(self) -> int:
        """Documentos con al menos un análisis terminado."""
        ...

    def count_references(self) -> int:
        """Referencias de los análisis terminados."""
        ...

    def count_verdict(self, verdict: str) -> int:
        """Referencias de los análisis terminados con ese veredicto."""
        ...


class SupabaseStatisticsRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._rest_url = rest_url
        self._client = client

    def works_of(self, owner_id: UUID, in_batches: bool) -> list[StoredWork]:
        rows = send(
            self._client,
            "GET",
            f"{self._rest_url}/t_documentos",
            params={
                "select": WORK_SELECT,
                "propietario_id": f"eq.{owner_id}",
                "lote_id": "not.is.null" if in_batches else "is.null",
                "t_analisis.order": "creado_en.desc",
            },
        )
        return [work for work in map(work_from_row, rows) if work]

    def count_batches(self, teacher_id: UUID) -> int:
        return self._count("t_lotes_auditoria", {"select": "id", "docente_id": f"eq.{teacher_id}"})

    def count_documents(self) -> int:
        return self._count(
            "t_documentos",
            {"select": "id,t_analisis!inner(id)", "t_analisis.estado": f"eq.{COMPLETED}"},
        )

    def count_references(self) -> int:
        return self._count(
            "t_referencias",
            {"select": "id,t_analisis!inner(id)", "t_analisis.estado": f"eq.{COMPLETED}"},
        )

    def count_verdict(self, verdict: str) -> int:
        return self._count(
            "t_verificaciones",
            {
                "select": "id,t_referencias!inner(t_analisis!inner(id))",
                "veredicto": f"eq.{verdict}",
                "t_referencias.t_analisis.estado": f"eq.{COMPLETED}",
            },
        )

    def _count(self, table: str, params: dict[str, str]) -> int:
        return get_counted(self._client, f"{self._rest_url}/{table}", {**params, **COUNT_ONLY})[1]
