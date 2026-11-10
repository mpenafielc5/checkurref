"""Estándar de oro en la base de datos (tabla m_referencias_oro)."""

from typing import Any

import httpx

from app.benchmark.gold_set import GoldReference, from_database_row
from app.repositories.supabase_http import send


class SupabaseGoldSetRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/m_referencias_oro"
        self._client = client

    def load_all(self) -> list[GoldReference]:
        """Todas las referencias, siempre en el mismo orden: así dos mediciones son comparables."""
        rows = send(
            self._client,
            "GET",
            self._url,
            params={
                "select": "texto,norma,campos_anotados,es_alterada,tipo_alteracion",
                "order": "id.asc",
            },
        )
        return [from_database_row(row) for row in rows]

    def replace_all(self, rows: list[dict[str, Any]]) -> None:
        """Reemplaza el estándar de oro completo: así la tabla siempre coincide con el CSV final."""
        # PostgREST exige un filtro para borrar: este abarca todas las filas.
        send(self._client, "DELETE", self._url, params={"id": "not.is.null"})
        if rows:
            send(self._client, "POST", self._url, json=rows)
