"""Estándar de oro en la base de datos (tabla referencias_oro)."""

from typing import Any

import httpx

from app.repositories.supabase_http import SupabaseUnavailableError, ensure_ok


class SupabaseGoldSetRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/referencias_oro"
        self._client = client

    def replace_all(self, rows: list[dict[str, Any]]) -> None:
        """Reemplaza el estándar de oro completo: así la tabla siempre coincide con el CSV final."""
        try:
            # PostgREST exige un filtro para borrar: este abarca todas las filas.
            ensure_ok(self._client.delete(self._url, params={"id": "not.is.null"}))
            if rows:
                ensure_ok(self._client.post(self._url, json=rows))
        except httpx.HTTPError as error:
            raise SupabaseUnavailableError(str(error)) from error
