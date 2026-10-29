"""Worker de análisis (T11, patrón Productor-Consumidor).

Corre dentro del proceso de la API: toma de la cola el análisis más antiguo, lo
procesa en un hilo aparte para no bloquear la API y, si no hay trabajo, espera
unos segundos. Un error en un documento lo marca como error y sigue con el
siguiente: nunca detiene la cola.
"""

import asyncio
import logging
from contextlib import suppress

from app.core.config import Settings
from app.extraction.base import Engine
from app.extraction.factory import create_extractor
from app.repositories.analysis_queue import AnalysisQueue, SupabaseAnalysisQueue
from app.repositories.extractions import SupabaseExtractionRepository
from app.repositories.pdf_storage import SupabasePdfStorage
from app.repositories.references import SupabaseReferenceRepository
from app.repositories.supabase_http import SupabaseUnavailableError, shared_client
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

# Mensaje para el usuario cuando falla algo que no es el PDF: la causa es del sistema.
INTERNAL_ERROR = (
    "El sistema no pudo completar el análisis por un error interno. "
    "Intenta subir el trabajo de nuevo en unos minutos."
)


class AnalysisWorker:
    def __init__(
        self, queue: AnalysisQueue, service: AnalysisService, poll_seconds: float = 3.0
    ) -> None:
        self._queue = queue
        self._service = service
        self._poll_seconds = poll_seconds

    async def run(self, stop: asyncio.Event) -> None:
        """Procesa la cola hasta que se active `stop`."""
        try:
            requeued = await asyncio.to_thread(self._queue.requeue_interrupted)
        except SupabaseUnavailableError as error:
            logger.warning("No se pudo revisar la cola al iniciar: %s", error)
        else:
            if requeued:
                logger.info("%d análisis interrumpidos volvieron a la cola", requeued)

        while not stop.is_set():
            processed = await asyncio.to_thread(self.process_next)
            if not processed:
                with suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=self._poll_seconds)

    def process_next(self) -> bool:
        """Procesa un análisis de la cola. False si no había ninguno o no hubo conexión."""
        try:
            job = self._queue.claim_next()
        except SupabaseUnavailableError as error:
            logger.warning("No se pudo consultar la cola: %s", error)
            return False
        if job is None:
            return False
        try:
            self._service.run(job)
        except Exception:  # un documento nunca detiene la cola
            logger.exception("El análisis %s falló", job.analysis_id)
            with suppress(SupabaseUnavailableError):
                self._queue.fail(job.analysis_id, INTERNAL_ERROR)
        return True


def create_worker(settings: Settings) -> AnalysisWorker:
    client = shared_client(settings.supabase_service_role_key)
    queue = SupabaseAnalysisQueue(settings.supabase_rest_url, client)
    service = AnalysisService(
        queue=queue,
        storage=SupabasePdfStorage(settings.supabase_storage_url, settings.storage_bucket, client),
        references=SupabaseReferenceRepository(settings.supabase_rest_url, client),
        extractions=SupabaseExtractionRepository(settings.supabase_rest_url, client),
        extractor=create_extractor(Engine(settings.extraction_engine), settings.anystyle_command),
    )
    return AnalysisWorker(queue, service, settings.worker_poll_seconds)
