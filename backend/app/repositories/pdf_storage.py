"""PDF en Supabase Storage (bucket privado "documentos")."""

import contextlib
from collections.abc import Sequence
from typing import Protocol

import httpx

from app.repositories.supabase_http import SupabaseUnavailableError, ensure_ok


class PdfStorage(Protocol):
    def upload(self, path: str, content: bytes) -> None: ...

    def download(self, path: str) -> bytes: ...

    def delete(self, path: str) -> None: ...

    def signed_url(self, path: str, seconds: int) -> str:
        """Enlace para ver el PDF que deja de servir a los `seconds` segundos."""
        ...

    def remove(self, paths: Sequence[str]) -> None:
        """Borra los PDF y avisa si no se pudo; si alguno ya no existe, no es un error."""
        ...


class SupabasePdfStorage:
    def __init__(self, storage_url: str, bucket: str, client: httpx.Client) -> None:
        self._storage_url = storage_url
        self._bucket = bucket
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

    def download(self, path: str) -> bytes:
        try:
            response = self._client.get(f"{self._objects_url}/{path}")
        except httpx.HTTPError as error:
            raise SupabaseUnavailableError(str(error)) from error
        return ensure_ok(response).content

    def remove(self, paths: Sequence[str]) -> None:
        # El borrado por lista responde lo mismo exista o no el archivo: repetirlo es seguro.
        if not paths:
            return
        try:
            response = self._client.request(
                "DELETE", self._objects_url, json={"prefixes": list(paths)}
            )
        except httpx.HTTPError as error:
            raise SupabaseUnavailableError(str(error)) from error
        ensure_ok(response)

    def signed_url(self, path: str, seconds: int) -> str:
        try:
            response = self._client.post(
                f"{self._storage_url}/object/sign/{self._bucket}/{path}",
                json={"expiresIn": seconds},
            )
        except httpx.HTTPError as error:
            raise SupabaseUnavailableError(str(error)) from error
        # Storage responde la ruta firmada relativa a su dirección: /object/sign/…
        return f"{self._storage_url}{ensure_ok(response).json()['signedURL']}"

    def delete(self, path: str) -> None:
        # Se usa solo para limpiar tras otro error; ese error es el que se informa.
        with contextlib.suppress(httpx.HTTPError):
            self._client.delete(f"{self._objects_url}/{path}")
