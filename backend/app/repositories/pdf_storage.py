"""PDF en Supabase Storage (bucket privado "documentos")."""

import contextlib
from typing import Protocol

import httpx

from app.repositories.supabase_http import SupabaseUnavailableError, ensure_ok


class PdfStorage(Protocol):
    def upload(self, path: str, content: bytes) -> None: ...

    def delete(self, path: str) -> None: ...


class SupabasePdfStorage:
    def __init__(self, storage_url: str, bucket: str, client: httpx.Client) -> None:
        self._objects_url = f"{storage_url}/object/{bucket}"
        self._client = client

    def upload(self, path: str, content: bytes) -> None:
        try:
            response = self._client.post(
                f"{self._objects_url}/{path}",
                content=content,
                # Nunca reemplaza: cada documento tiene su propio nombre de archivo.
                headers={"Content-Type": "application/pdf", "x-upsert": "false"},
            )
        except httpx.HTTPError as error:
            raise SupabaseUnavailableError(str(error)) from error
        ensure_ok(response)

    def delete(self, path: str) -> None:
        # Se usa solo para limpiar tras otro error; ese error es el que se informa.
        with contextlib.suppress(httpx.HTTPError):
            self._client.delete(f"{self._objects_url}/{path}")
