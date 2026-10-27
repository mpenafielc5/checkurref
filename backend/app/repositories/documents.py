"""Documentos y análisis en la base de datos (PostgREST de Supabase)."""

import contextlib
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx

from app.repositories.supabase_http import SupabaseUnavailableError, ensure_ok


@dataclass(frozen=True)
class NewDocument:
    id: UUID
    owner_id: UUID
    title: str
    file_name: str
    storage_path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class AnalysisRef:
    """Un análisis y el documento al que pertenece."""

    analysis_id: UUID
    document_id: UUID
    status: str


class DocumentRepository(Protocol):
    def find_by_hash(self, owner_id: UUID, sha256: str) -> AnalysisRef | None:
        """Último análisis de un PDF idéntico subido por el mismo usuario, fuera de lotes."""
        ...

    def create(self, document: NewDocument, model_version: str) -> AnalysisRef:
        """Crea el documento y su análisis en cola. La norma la detecta el pipeline."""
        ...


class SupabaseDocumentRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._rest_url = rest_url
        self._client = client

    def find_by_hash(self, owner_id: UUID, sha256: str) -> AnalysisRef | None:
        rows = self._get(
            "documentos",
            {
                "select": "id,analisis(id,estado,creado_en)",
                "propietario_id": f"eq.{owner_id}",
                "sha256": f"eq.{sha256}",
                "lote_id": "is.null",
                "order": "creado_en.desc",
                "analisis.order": "creado_en.desc",
                "limit": "1",
            },
        )
        if not rows or not rows[0]["analisis"]:
            return None
        document, analysis = rows[0], rows[0]["analisis"][0]
        return AnalysisRef(
            analysis_id=UUID(analysis["id"]),
            document_id=UUID(document["id"]),
            status=analysis["estado"],
        )

    def create(self, document: NewDocument, model_version: str) -> AnalysisRef:
        self._insert(
            "documentos",
            {
                "id": str(document.id),
                "propietario_id": str(document.owner_id),
                "titulo": document.title,
                "nombre_archivo": document.file_name,
                "ruta_storage": document.storage_path,
                "sha256": document.sha256,
                "tamano_bytes": document.size_bytes,
            },
        )
        try:
            analysis = self._insert(
                "analisis",
                {"documento_id": str(document.id), "version_modelo": model_version},
            )
        except SupabaseUnavailableError:
            # Sin análisis el documento quedaría huérfano: se borra y se avisa.
            self._delete("documentos", {"id": f"eq.{document.id}"})
            raise
        return AnalysisRef(
            analysis_id=UUID(analysis["id"]),
            document_id=document.id,
            status=analysis["estado"],
        )

    def _get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        try:
            response = self._client.get(f"{self._rest_url}/{table}", params=params)
        except httpx.HTTPError as error:
            raise SupabaseUnavailableError(str(error)) from error
        return ensure_ok(response).json()

    def _insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(
                f"{self._rest_url}/{table}",
                json=row,
                headers={"Prefer": "return=representation"},
            )
        except httpx.HTTPError as error:
            raise SupabaseUnavailableError(str(error)) from error
        return ensure_ok(response).json()[0]

    def _delete(self, table: str, params: dict[str, str]) -> None:
        # La limpieza es lo último que se intenta: si falla, se informa el error original.
        with contextlib.suppress(httpx.HTTPError):
            self._client.delete(f"{self._rest_url}/{table}", params=params)
