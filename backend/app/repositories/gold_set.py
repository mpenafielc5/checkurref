"""Estándar de oro en la base de datos (tabla referencias_oro)."""

from typing import Any

import httpx

from app.repositories.supabase_http import send


class SupabaseGoldSetRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/referencias_oro"
        self._client = client

    def replace_all(self, rows: list[dict[str, Any]]) -> None:
        """Reemplaza el estándar de oro completo: así la tabla siempre coincide con el CSV final."""
        # PostgREST exige un filtro para borrar: este abarca todas las filas.
        send(self._client, "DELETE", self._url, params={"id": "not.is.null"})
        if rows:
            send(self._client, "POST", self._url, json=rows)
