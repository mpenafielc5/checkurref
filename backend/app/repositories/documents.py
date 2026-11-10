"""Documentos y análisis en la base de datos (PostgREST de Supabase)."""

import contextlib
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx

from app.repositories.supabase_http import SupabaseUnavailableError, send


@dataclass(frozen=True)
class NewDocument:
    id: UUID
    owner_id: UUID
    title: str
    file_name: str
    storage_path: str
    sha256: str
    size_bytes: int
    batch_id: UUID | None = None  # el lote del docente; None en un trabajo individual
    authors: tuple[str, ...] = ()  # leídos de la portada; solo se buscan en un lote


@dataclass(frozen=True)
class AnalysisRef:
    """Un análisis y el documento al que pertenece."""

    analysis_id: UUID
    document_id: UUID
    status: str


@dataclass(frozen=True)
class OwnedWork:
    """Un trabajo de su dueño: el documento, su PDF y el estado de cada análisis."""

    document_id: UUID
    storage_path: str
    statuses: tuple[str, ...]


class DocumentRepository(Protocol):
    def find_by_hash(
        self, owner_id: UUID, sha256: str, batch_id: UUID | None = None
    ) -> AnalysisRef | None:
        """Último análisis de un PDF idéntico del mismo usuario: en el mismo lote o, sin
        lote, entre sus trabajos individuales. El mismo PDF puede estar en dos lotes."""
        ...

    def create(self, document: NewDocument, model_version: str) -> AnalysisRef:
        """Crea el documento y su análisis en cola. La norma la detecta el pipeline."""
        ...

    def find_owned_work(self, owner_id: UUID, analysis_id: UUID) -> OwnedWork | None:
        """El trabajo al que pertenece el análisis, solo si es de ese usuario."""
        ...

    def delete_document(self, document_id: UUID) -> None:
        """Borra el documento; la base borra en cascada sus análisis y resultados."""
        ...

    def batch_works(self, batch_id: UUID) -> list[OwnedWork]:
        """Los trabajos del lote, con su PDF y el estado de cada análisis."""
        ...

    def delete_batch_documents(self, batch_id: UUID) -> None:
        """Borra los documentos del lote; la base borra en cascada sus resultados."""
        ...


class SupabaseDocumentRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._rest_url = rest_url
        self._client = client

    def find_by_hash(
        self, owner_id: UUID, sha256: str, batch_id: UUID | None = None
    ) -> AnalysisRef | None:
        rows = self._get(
            "t_documentos",
            {
                "select": "id,t_analisis(id,estado,creado_en)",
                "propietario_id": f"eq.{owner_id}",
                "sha256": f"eq.{sha256}",
                "lote_id": f"eq.{batch_id}" if batch_id else "is.null",
                "order": "creado_en.desc",
                "t_analisis.order": "creado_en.desc",
                "limit": "1",
            },
        )
        if not rows or not rows[0]["t_analisis"]:
            return None
        document, analysis = rows[0], rows[0]["t_analisis"][0]
        return AnalysisRef(
            analysis_id=UUID(analysis["id"]),
            document_id=UUID(document["id"]),
            status=analysis["estado"],
        )

    def create(self, document: NewDocument, model_version: str) -> AnalysisRef:
        row: dict[str, Any] = {
            "id": str(document.id),
            "propietario_id": str(document.owner_id),
            "titulo": document.title,
            "nombre_archivo": document.file_name,
            "ruta_storage": document.storage_path,
            "sha256": document.sha256,
            "tamano_bytes": document.size_bytes,
        }
        if document.batch_id:
            row["lote_id"] = str(document.batch_id)
        if document.authors:
            row["autores"] = list(document.authors)
        self._insert("t_documentos", row)
        try:
            analysis = self._insert(
                "t_analisis",
                {"documento_id": str(document.id), "version_modelo": model_version},
            )
        except SupabaseUnavailableError:
            # Sin análisis el documento quedaría huérfano: se borra y se avisa.
            self._delete("t_documentos", {"id": f"eq.{document.id}"})
            raise
        return AnalysisRef(
            analysis_id=UUID(analysis["id"]),
            document_id=document.id,
            status=analysis["estado"],
        )

    def find_owned_work(self, owner_id: UUID, analysis_id: UUID) -> OwnedWork | None:
        rows = self._get(
            "t_analisis",
            {
                "select": "t_documentos!inner(id,ruta_storage,t_analisis(estado))",
                "id": f"eq.{analysis_id}",
                "t_documentos.propietario_id": f"eq.{owner_id}",
            },
        )
        if not rows:
            return None
        document = rows[0]["t_documentos"]
        return OwnedWork(
            document_id=UUID(document["id"]),
            storage_path=document["ruta_storage"],
            statuses=tuple(analysis["estado"] for analysis in document["t_analisis"]),
        )

    def delete_document(self, document_id: UUID) -> None:
        url = f"{self._rest_url}/t_documentos"
        send(self._client, "DELETE", url, params={"id": f"eq.{document_id}"})

    def batch_works(self, batch_id: UUID) -> list[OwnedWork]:
        rows = self._get(
            "t_documentos",
            {"select": "id,ruta_storage,t_analisis(estado)", "lote_id": f"eq.{batch_id}"},
        )
        return [
            OwnedWork(
                document_id=UUID(row["id"]),
                storage_path=row["ruta_storage"],
                statuses=tuple(analysis["estado"] for analysis in row["t_analisis"]),
            )
            for row in rows
        ]

    def delete_batch_documents(self, batch_id: UUID) -> None:
        url = f"{self._rest_url}/t_documentos"
        send(self._client, "DELETE", url, params={"lote_id": f"eq.{batch_id}"})

    def _get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        return send(self._client, "GET", f"{self._rest_url}/{table}", params=params)

    def _insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._rest_url}/{table}"
        return send(
            self._client, "POST", url, json=row, headers={"Prefer": "return=representation"}
        )[0]

    def _delete(self, table: str, params: dict[str, str]) -> None:
        # La limpieza es lo último que se intenta: si falla, se informa el error original.
        with contextlib.suppress(httpx.HTTPError):
            self._client.delete(f"{self._rest_url}/{table}", params=params)
