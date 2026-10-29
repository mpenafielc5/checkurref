"""Caso de uso: analizar un documento de la cola (CU-03, patrón Pipeline).

Etapas, cada una informa su avance para la pantalla de progreso:

1. extrayendo: descarga el PDF y ubica la sección de referencias.
2. segmentando: separa las referencias, detecta la norma (T06) y extrae los
   campos de cada una (T07).
3. verificando: consulta las fuentes y decide el veredicto (T13, pendiente).

Un PDF que no se puede leer termina el análisis con un mensaje para el usuario.
"""

import logging
import time

from app.extraction.base import ReferenceExtractor, elapsed_ms
from app.pipeline.errors import PdfProcessingError
from app.pipeline.references_section import extract_reference_section
from app.pipeline.segmentation import segment_references
from app.repositories.analysis_queue import AnalysisQueue, QueuedAnalysis
from app.repositories.extractions import ExtractionRepository
from app.repositories.pdf_storage import PdfStorage
from app.repositories.references import ReferenceRepository

logger = logging.getLogger(__name__)

# Avance (0-100) al terminar cada etapa.
PROGRESS_TEXT = 20
PROGRESS_SEGMENTS = 40
PROGRESS_FIELDS = 90


class AnalysisService:
    def __init__(
        self,
        queue: AnalysisQueue,
        storage: PdfStorage,
        references: ReferenceRepository,
        extractions: ExtractionRepository,
        extractor: ReferenceExtractor,
    ) -> None:
        self._queue = queue
        self._storage = storage
        self._references = references
        self._extractions = extractions
        self._extractor = extractor

    def run(self, job: QueuedAnalysis) -> None:
        start = time.perf_counter()
        try:
            section = extract_reference_section(self._storage.download(job.storage_path))
        except PdfProcessingError as error:
            logger.info("Análisis %s sin procesar: %s", job.analysis_id, error.message)
            self._queue.fail(job.analysis_id, error.message, elapsed_ms(start))
            return
        self._queue.report(job.analysis_id, "segmentando", PROGRESS_TEXT)

        segmentation = segment_references(section)
        ids = self._references.save_segmentation(job.analysis_id, segmentation)
        self._queue.report(job.analysis_id, "segmentando", PROGRESS_SEGMENTS)

        results = self._extractor.extract_all([ref.text for ref in segmentation.references])
        self._extractions.save(
            self._extractor.engine,
            {
                ids[reference.order]: result
                for reference, result in zip(segmentation.references, results, strict=True)
            },
        )
        self._queue.report(job.analysis_id, "segmentando", PROGRESS_FIELDS)

        self._queue.complete(job.analysis_id, self._extractor.engine, elapsed_ms(start))
        logger.info(
            "Análisis %s completado: %d referencias, norma %s",
            job.analysis_id,
            len(segmentation.references),
            segmentation.norm.value,
        )
