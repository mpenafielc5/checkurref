"""Caso de uso: eliminar un trabajo con todos sus resultados.

El estudiante elimina los suyos y el docente los de sus lotes, o el lote completo: en
todos los casos, quien subió el PDF es su dueño. Se borra primero el PDF y luego el
documento, del que la base borra en cascada sus análisis, referencias, verificaciones y
hallazgos. Si algo falla a mitad, repetir la operación termina el trabajo.
"""

from uuid import UUID

from app.repositories.batches import BatchRepository
from app.repositories.documents import DocumentRepository
from app.repositories.pdf_storage import PdfStorage

# Un análisis en curso todavía escribe en la base: se espera a que termine.
FINISHED = frozenset({"completado", "error"})


class WorkNotFoundError(Exception):
    """El análisis no existe o es de otra cuenta: para quien pregunta, es lo mismo."""


class WorkInProgressError(Exception):
    """El trabajo tiene un análisis que aún no termina."""


class BatchNotFoundError(Exception):
    """El lote no existe o es de otro docente: para quien pregunta, es lo mismo."""


class WorkService:
    def __init__(
        self,
        documents: DocumentRepository,
        storage: PdfStorage,
        batches: BatchRepository | None = None,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._batches = batches

    def delete(self, owner_id: UUID, analysis_id: UUID) -> None:
        work = self._documents.find_owned_work(owner_id, analysis_id)
        if work is None:
            raise WorkNotFoundError(str(analysis_id))
        if any(status not in FINISHED for status in work.statuses):
            raise WorkInProgressError(str(analysis_id))
        self._storage.remove([work.storage_path])
        self._documents.delete_document(work.document_id)

    def delete_batch(self, teacher_id: UUID, batch_id: UUID) -> None:
        """Elimina el lote con todos sus trabajos. Los documentos se borran antes que el
        lote: si fuera al revés, la base los dejaría como trabajos sueltos."""
        if self._batches is None:
            raise RuntimeError("WorkService sin repositorio de lotes")
        batch = self._batches.get(batch_id)
        if batch is None or batch.teacher_id != teacher_id:
            raise BatchNotFoundError(str(batch_id))
        works = self._documents.batch_works(batch_id)
        if any(status not in FINISHED for work in works for status in work.statuses):
            raise WorkInProgressError(str(batch_id))
        self._storage.remove([work.storage_path for work in works])
        self._documents.delete_batch_documents(batch_id)
        self._batches.delete(batch_id)
