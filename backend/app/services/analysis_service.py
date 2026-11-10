"""Caso de uso: analizar un documento de la cola (CU-03, patrón Pipeline).

Etapas, cada una informa su avance para la pantalla de progreso:

1. extrayendo: descarga el PDF y ubica la sección de referencias.
2. segmentando: separa las referencias, detecta la norma (T06) y extrae los
   campos de cada una (T07).
3. verificando: busca cada referencia en Crossref y OpenAlex, decide su
   veredicto (T13), arma la referencia corregida (T26), revisa el formato (T25) y
   calcula el índice de veracidad. El formato no cambia el veredicto ni el índice.

Un PDF que no se puede leer termina el análisis con un mensaje para el usuario.
Un error al verificar una referencia solo afecta a esa referencia (RNF09).
"""

import asyncio
import logging
import time
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from app.extraction.base import ExtractedFields, ReferenceExtractor, elapsed_ms
from app.pipeline.errors import PdfProcessingError
from app.pipeline.references_section import extract_reference_section
from app.pipeline.segmentation import Segmentation, SegmentedReference, segment_references
from app.repositories.analysis_queue import AnalysisQueue, QueuedAnalysis
from app.repositories.extractions import ExtractionRepository
from app.repositories.pdf_storage import PdfStorage
from app.repositories.references import ReferenceRepository
from app.repositories.supabase_http import SupabaseUnavailableError
from app.repositories.verifications import VerificationRepository
from app.verification.corrected import CorrectedReference, corrected_reference
from app.verification.decision import Verification, truthfulness_index
from app.verification.findings import Finding
from app.verification.format_review import review_list, review_reference

logger = logging.getLogger(__name__)

# Avance (0-100) al terminar cada etapa. La verificación, la más lenta, avanza
# con cada referencia entre PROGRESS_FIELDS y PROGRESS_VERIFIED.
PROGRESS_TEXT = 10
PROGRESS_SEGMENTS = 20
PROGRESS_FIELDS = 30
PROGRESS_VERIFIED = 95


class Verifier(Protocol):
    async def verify(self, text: str, fields: ExtractedFields | None) -> Verification: ...


# Abre un verificador para un análisis (app/verification/factory.py).
OpenVerifier = Callable[[], AbstractAsyncContextManager[Verifier]]


class AnalysisService:
    def __init__(
        self,
        queue: AnalysisQueue,
        storage: PdfStorage,
        references: ReferenceRepository,
        extractions: ExtractionRepository,
        extractor: ReferenceExtractor,
        verifications: VerificationRepository,
        open_verifier: OpenVerifier,
    ) -> None:
        self._queue = queue
        self._storage = storage
        self._references = references
        self._extractions = extractions
        self._extractor = extractor
        self._verifications = verifications
        self._open_verifier = open_verifier

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

        texts = [reference.text for reference in segmentation.references]
        results = self._extractor.extract_all(texts)
        reference_ids = [ids[reference.order] for reference in segmentation.references]
        self._extractions.save(
            self._extractor.engine, dict(zip(reference_ids, results, strict=True))
        )
        self._queue.report(job.analysis_id, "verificando", PROGRESS_FIELDS)

        fields = [result.fields for result in results]
        verifications = asyncio.run(self._verify_all(job.analysis_id, texts, fields))
        corrected: dict[str, CorrectedReference] = {}
        for reference_id, reference, extracted, verification in zip(
            reference_ids, segmentation.references, fields, verifications, strict=True
        ):
            if item := _corrected(reference, extracted, verification):
                corrected[reference_id] = item
        index = truthfulness_index(item.verdict if item else None for item in verifications)
        self._verifications.save(
            job.analysis_id,
            dict(zip(reference_ids, verifications, strict=True)),
            corrected,
            index,
            _format_findings(segmentation, reference_ids, fields, verifications),
        )

        self._queue.complete(job.analysis_id, self._extractor.engine, elapsed_ms(start))
        logger.info(
            "Análisis %s completado: %d referencias, norma %s, índice %s",
            job.analysis_id,
            len(segmentation.references),
            segmentation.norm.value,
            index,
        )

    async def _verify_all(
        self,
        analysis_id: UUID,
        texts: Sequence[str],
        fields: Sequence[ExtractedFields | None],
    ) -> list[Verification | None]:
        """Verifica las referencias a la vez; las fuentes limitan su propia concurrencia.

        Devuelve None en la referencia cuya verificación falló por un error interno.
        """
        if not texts:
            return []
        progress = _Progress(self._report_verifying(analysis_id), len(texts))

        pending = enumerate(zip(texts, fields, strict=True), start=1)
        async with self._open_verifier() as verifier:
            verifications = await asyncio.gather(
                *(
                    _verify_one(verifier, progress, order, text, extracted)
                    for order, (text, extracted) in pending
                )
            )
        return list(verifications)

    def _report_verifying(self, analysis_id: UUID) -> Callable[[int], None]:
        def report(value: int) -> None:
            # El avance es informativo: si Supabase falla un momento, el análisis sigue.
            try:
                self._queue.report(analysis_id, "verificando", value)
            except SupabaseUnavailableError as error:
                logger.warning("No se pudo informar el avance de %s: %s", analysis_id, error)

        return report


def _corrected(
    reference: SegmentedReference,
    fields: ExtractedFields | None,
    verification: Verification | None,
) -> CorrectedReference | None:
    """Referencia corregida (T26). Si falla, la referencia solo se queda sin ella."""
    if fields is None or verification is None:
        return None
    try:
        return corrected_reference(reference.text, reference.norm, fields, verification)
    except Exception:  # una referencia nunca detiene el análisis (RNF09)
        logger.exception("Falló la referencia corregida de la referencia %d", reference.order)
        return None


def _format_findings(
    segmentation: Segmentation,
    reference_ids: Sequence[str],
    fields: Sequence[ExtractedFields | None],
    verifications: Sequence[Verification | None],
) -> dict[str, list[Finding]]:
    """Hallazgos de formato (T25) por referencia. Si la revisión falla en una, esa
    referencia solo se queda sin hallazgos."""
    found: dict[str, list[Finding]] = {}
    ids_by_order: dict[int, str] = {}
    for reference_id, reference, extracted, verification in zip(
        reference_ids, segmentation.references, fields, verifications, strict=True
    ):
        ids_by_order[reference.order] = reference_id
        try:
            items = review_reference(reference, segmentation.norm, extracted, verification)
        except Exception:  # una referencia nunca detiene el análisis (RNF09)
            logger.exception("Falló la revisión de formato de la referencia %d", reference.order)
            continue
        if items:
            found[reference_id] = items
    try:
        for order, items in review_list(segmentation).items():
            found.setdefault(ids_by_order[order], []).extend(items)
    except Exception:  # la lista completa tampoco detiene el análisis (RNF09)
        logger.exception("Falló la revisión de formato de la lista")
    return found


async def _verify_one(
    verifier: Verifier,
    progress: "_Progress",
    order: int,
    text: str,
    fields: ExtractedFields | None,
) -> Verification | None:
    try:
        return await verifier.verify(text, fields)
    except Exception:  # una referencia nunca detiene el análisis (RNF09)
        logger.exception("Falló la verificación de la referencia %d", order)
        return None
    finally:
        await progress.advance()


class _Progress:
    """Avance de la verificación: crece con cada referencia terminada y nunca retrocede,
    aunque las referencias terminen en otro orden."""

    def __init__(self, report: Callable[[int], None], total: int) -> None:
        self._report = report
        self._total = total
        self._done = 0
        self._reported = PROGRESS_FIELDS
        self._lock = asyncio.Lock()

    async def advance(self) -> None:
        async with self._lock:
            self._done += 1
            span = PROGRESS_VERIFIED - PROGRESS_FIELDS
            value = PROGRESS_FIELDS + span * self._done // self._total
            if value > self._reported:
                self._reported = value
                await asyncio.to_thread(self._report, value)
