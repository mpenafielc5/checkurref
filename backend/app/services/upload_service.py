"""Caso de uso: subir el PDF de un trabajo y dejar su análisis en cola (HU-04)."""

import hashlib
from dataclasses import dataclass
from pathlib import PurePath
from uuid import UUID, uuid4

from app.repositories.documents import AnalysisRef, DocumentRepository, NewDocument
from app.repositories.pdf_storage import PdfStorage
from app.repositories.supabase_http import SupabaseUnavailableError

MAX_PDF_BYTES = 10 * 1024 * 1024  # el mismo límite que el bucket y la tabla documentos
PDF_SIGNATURE = b"%PDF-"
MAX_NAME_LENGTH = 255


class UploadRejectedError(Exception):
    """El archivo no cumple las reglas de subida. El mensaje se muestra al usuario."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class UploadResult:
    analysis: AnalysisRef
    # True si el mismo usuario ya había subido un PDF idéntico: no se reanaliza.
    duplicate: bool


class UploadService:
    def __init__(
        self, documents: DocumentRepository, storage: PdfStorage, model_version: str
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._model_version = model_version

    def submit(self, owner_id: UUID, file_name: str, content: bytes) -> UploadResult:
        _validate(content)
        sha256 = hashlib.sha256(content).hexdigest()

        existing = self._documents.find_by_hash(owner_id, sha256)
        if existing:
            return UploadResult(analysis=existing, duplicate=True)

        document_id = uuid4()
        path = f"{owner_id}/{document_id}.pdf"
        self._storage.upload(path, content)
        document = NewDocument(
            id=document_id,
            owner_id=owner_id,
            title=_title_from(file_name),
            file_name=file_name[:MAX_NAME_LENGTH],
            storage_path=path,
            sha256=sha256,
            size_bytes=len(content),
        )
        try:
            analysis = self._documents.create(document, self._model_version)
        except SupabaseUnavailableError:
            # Sin registro en la base, el PDF guardado no serviría: se borra.
            self._storage.delete(path)
            raise
        return UploadResult(analysis=analysis, duplicate=False)


def _validate(content: bytes) -> None:
    if not content:
        raise UploadRejectedError("El archivo está vacío.")
    if len(content) > MAX_PDF_BYTES:
        raise UploadRejectedError("El archivo supera el máximo de 10 MB.")
    if not content.startswith(PDF_SIGNATURE):
        raise UploadRejectedError("Solo se aceptan archivos PDF.")


def _title_from(file_name: str) -> str:
    """Título provisional: el nombre del archivo sin la extensión."""
    stem = PurePath(file_name).stem.strip()
    return (stem or "Documento sin nombre")[:MAX_NAME_LENGTH]
