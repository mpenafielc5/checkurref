"""Cola de análisis, worker y etapas del análisis (T11). Sin Supabase real."""

import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from app.extraction.base import Author, Engine, ExtractedFields, Extraction, ReferenceExtractor
from app.pipeline.errors import ReferencesNotFoundError
from app.pipeline.segmentation import Segmentation
from app.repositories.analysis_queue import QueuedAnalysis, SupabaseAnalysisQueue
from app.repositories.extractions import SupabaseExtractionRepository
from app.repositories.pdf_storage import SupabasePdfStorage
from app.repositories.supabase_http import SupabaseUnavailableError
from app.services.analysis_service import AnalysisService
from app.workers.analysis_worker import INTERNAL_ERROR, AnalysisWorker
from tests.pdf_factory import PageSpec, make_pdf

REST_URL = "https://proyecto.supabase.co/rest/v1"
APA_1 = "Pérez, M. y López, J. (2021). Redes neuronales en la educación superior."
APA_2 = "Rivas, A. (2020). Aprendizaje automático aplicado. Editorial UNEMI."
PDF = make_pdf(
    [PageSpec(["Conclusiones del trabajo con texto suficiente.", "Referencias", APA_1, APA_2])]
)
JOB = QueuedAnalysis(uuid4(), uuid4(), "usuario/documento.pdf")


# --- Dobles de prueba -----------------------------------------------------------------------


class FakeQueue:
    def __init__(self, jobs: list[QueuedAnalysis] | None = None, down: bool = False) -> None:
        self.jobs = list(jobs or [])
        self.down = down
        self.events: list[tuple[Any, ...]] = []

    def claim_next(self) -> QueuedAnalysis | None:
        if self.down:
            raise SupabaseUnavailableError("caída")
        return self.jobs.pop(0) if self.jobs else None

    def report(self, analysis_id: UUID, status: str, progress: int) -> None:
        self.events.append(("avance", status, progress))

    def complete(self, analysis_id: UUID, engine: Engine, duration_ms: int) -> None:
        self.events.append(("completado", analysis_id, engine))

    def fail(self, analysis_id: UUID, message: str, duration_ms: int | None = None) -> None:
        self.events.append(("error", analysis_id, message))

    def requeue_interrupted(self) -> int:
        return 0


class FakeStorage:
    def __init__(self, content: bytes = PDF) -> None:
        self.content = content

    def upload(self, path: str, content: bytes) -> None: ...

    def download(self, path: str) -> bytes:
        return self.content

    def delete(self, path: str) -> None: ...


class FakeReferences:
    def __init__(self) -> None:
        self.saved: list[Segmentation] = []

    def save_segmentation(self, analysis_id: UUID, segmentation: Segmentation) -> dict[int, str]:
        self.saved.append(segmentation)
        return {reference.order: f"ref-{reference.order}" for reference in segmentation.references}


class FakeExtractions:
    def __init__(self) -> None:
        self.saved: dict[str, Extraction] = {}

    def save(self, engine: Engine, extractions: dict[str, Extraction]) -> None:
        self.saved.update(extractions)


class TitleExtractor(ReferenceExtractor):
    engine = Engine.SPACY

    def extract(self, reference: str) -> ExtractedFields:
        return ExtractedFields(title=reference[:20])


def service(
    queue: FakeQueue, storage: FakeStorage | None = None
) -> tuple[AnalysisService, FakeReferences, FakeExtractions]:
    references, extractions = FakeReferences(), FakeExtractions()
    analysis = AnalysisService(
        queue, storage or FakeStorage(), references, extractions, TitleExtractor()
    )
    return analysis, references, extractions


# --- Servicio: etapas -----------------------------------------------------------------------


def test_un_analisis_recorre_sus_etapas_y_termina_completado() -> None:
    queue = FakeQueue()
    analysis, references, extractions = service(queue)

    analysis.run(JOB)

    [segmentation] = references.saved
    assert [reference.text for reference in segmentation.references] == [APA_1, APA_2]
    assert set(extractions.saved) == {"ref-1", "ref-2"}  # una extracción por referencia
    assert queue.events == [
        ("avance", "segmentando", 20),
        ("avance", "segmentando", 40),
        ("avance", "segmentando", 90),
        ("completado", JOB.analysis_id, Engine.SPACY),
    ]


def test_un_pdf_sin_referencias_termina_con_su_mensaje() -> None:
    queue = FakeQueue()
    sin_referencias = make_pdf([PageSpec(["Un trabajo sin la sección final, solo texto."])])
    analysis, references, _ = service(queue, FakeStorage(sin_referencias))

    analysis.run(JOB)

    assert queue.events == [("error", JOB.analysis_id, ReferencesNotFoundError.message)]
    assert references.saved == []


# --- Worker ---------------------------------------------------------------------------------


def test_un_error_en_un_documento_no_detiene_la_cola() -> None:
    broken, good = QueuedAnalysis(uuid4(), uuid4(), "roto.pdf"), JOB
    queue = FakeQueue([broken, good])

    class BrokenOnce(FakeStorage):
        def download(self, path: str) -> bytes:
            if path == "roto.pdf":
                raise RuntimeError("fallo inesperado")
            return super().download(path)

    analysis, _, _ = service(queue, BrokenOnce())
    worker = AnalysisWorker(queue, analysis)

    assert worker.process_next() is True
    assert worker.process_next() is True
    assert worker.process_next() is False  # cola vacía

    assert ("error", broken.analysis_id, INTERNAL_ERROR) in queue.events
    assert ("completado", good.analysis_id, Engine.SPACY) in queue.events


def test_sin_conexion_el_worker_espera_y_no_se_cae() -> None:
    worker = AnalysisWorker(FakeQueue(down=True), service(FakeQueue())[0])

    assert worker.process_next() is False


def test_el_worker_procesa_la_cola_y_se_detiene_al_pedirlo() -> None:
    queue = FakeQueue([JOB])
    worker = AnalysisWorker(queue, service(queue)[0], poll_seconds=0.01)

    async def run() -> None:
        stop = asyncio.Event()
        task = asyncio.create_task(worker.run(stop))
        await asyncio.sleep(0.5)
        stop.set()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(run())

    assert ("completado", JOB.analysis_id, Engine.SPACY) in queue.events


# --- Repositorios ---------------------------------------------------------------------------


def mock(handler: Any) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_la_cola_toma_el_analisis_solo_si_sigue_en_cola() -> None:
    first, second = str(uuid4()), str(uuid4())
    patches: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            rows = [
                {"id": id_, "documento_id": str(uuid4()), "documentos": {"ruta_storage": "a.pdf"}}
                for id_ in (first, second)
            ]
            return httpx.Response(200, json=rows)
        patches.append(request)
        # Otro proceso ya tomó el primero: la actualización condicionada no devuelve filas.
        taken = request.url.params["id"] == f"eq.{first}"
        return httpx.Response(200, json=[] if taken else [{"id": second}])

    job = SupabaseAnalysisQueue(REST_URL, mock(handler)).claim_next()

    assert job is not None and str(job.analysis_id) == second
    assert all(request.url.params["estado"] == "eq.en_cola" for request in patches)
    assert json.loads(patches[0].content)["estado"] == "extrayendo"


def test_la_cola_devuelve_los_analisis_interrumpidos() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"id": "a"}, {"id": "b"}])

    assert SupabaseAnalysisQueue(REST_URL, mock(handler)).requeue_interrupted() == 2
    assert seen[0].url.params["estado"] == "in.(extrayendo,segmentando,verificando)"
    assert json.loads(seen[0].content) == {"estado": "en_cola", "progreso": 0}


def test_la_cola_marca_el_error_con_su_mensaje() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(204)

    SupabaseAnalysisQueue(REST_URL, mock(handler)).fail(JOB.analysis_id, "PDF dañado", 120)

    assert bodies[0]["estado"] == "error"
    assert bodies[0]["mensaje_error"] == "PDF dañado"
    assert bodies[0]["duracion_ms"] == 120


def test_guarda_cada_extraccion_y_recorta_lo_que_no_cabe() -> None:
    bodies: list[list[dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(201)

    fields = ExtractedFields(authors=(Author("Pérez", "M."),), year=2021, volume="8" * 40)
    SupabaseExtractionRepository(REST_URL, mock(handler)).save(
        Engine.SPACY,
        {"ref-1": Extraction(fields, 12), "ref-2": Extraction(None, 3, "falló")},
    )

    first, failed = bodies[0]
    assert first["motor"] == "spacy" and first["anio"] == 2021 and first["tiempo_ms"] == 12
    assert first["autores"] == [{"family": "Pérez", "given": "M."}]
    assert len(first["volumen"]) == 20  # el largo de la columna
    assert failed["titulo"] is None and failed["autores"] is None  # se intentó, sin campos


def test_descarga_el_pdf_de_storage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/object/documentos/usuario/doc.pdf")
        return httpx.Response(200, content=PDF)

    storage = SupabasePdfStorage(
        "https://proyecto.supabase.co/storage/v1", "documentos", mock(handler)
    )

    assert storage.download("usuario/doc.pdf") == PDF


@pytest.mark.parametrize("status", [404, 503])
def test_si_storage_falla_la_descarga_avisa(status: int) -> None:
    storage = SupabasePdfStorage(
        "https://proyecto.supabase.co/storage/v1",
        "documentos",
        mock(lambda _: httpx.Response(status)),
    )

    with pytest.raises(SupabaseUnavailableError):
        storage.download("usuario/doc.pdf")
