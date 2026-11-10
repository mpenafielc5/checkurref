"""Lotes de auditoría del docente (T16, HU-08, HU-09). Sin Supabase real."""

import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.analyses import get_upload_service
from app.api.routes.batches import get_batch_service
from app.main import create_app
from app.repositories.batches import (
    BatchOverview,
    BatchPage,
    StoredBatch,
    StoredBatchAnalysis,
    StoredWork,
    SupabaseBatchRepository,
)
from app.repositories.documents import AnalysisRef, NewDocument, SupabaseDocumentRepository
from app.services.batch_service import (
    MAX_WORKS_PER_BATCH,
    BatchNotFoundError,
    BatchService,
    risk_of,
)
from app.services.upload_service import UploadRejectedError, UploadService
from tests.pdf_factory import PageSpec, make_pdf
from tests.session_helpers import USER_ID, act_as, bearer, make_token, trust_test_tokens

TEACHER = UUID(USER_ID)
BATCH_ID = uuid4()
NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)
REST_URL = "https://proyecto.supabase.co/rest/v1"
PDF = make_pdf([PageSpec(lines=["Referencias", "Torres, A. (2020). Un título. Revista."])])
BATCH = StoredBatch(BATCH_ID, TEACHER, "Software 7A", "2026-2S", NOW)


def work(
    status: str = "completado",
    index: float | None = 90.0,
    verdicts: tuple[str | None, ...] = (),
    fields: tuple[str, ...] = (),
) -> StoredWork:
    return StoredWork(
        analysis_id=uuid4(),
        document_id=uuid4(),
        file_name="Avance.pdf",
        authors=("Ana Vera", "Luis Rojas"),
        created_at=NOW,
        status=status,
        progress=100 if status == "completado" else 40,
        total_references=len(verdicts),
        norm="APA",
        index=index,
        error_message=None,
        verdicts=verdicts,
        different_fields=fields,
    )


class FakeBatches:
    def __init__(self, stored: list[StoredWork] | None = None, count: int = 0) -> None:
        self.batch: StoredBatch | None = BATCH
        self.stored = stored or []
        self.total_works = count
        self.created: list[tuple[UUID, str, str]] = []

    def create(self, teacher_id: UUID, name: str, period: str) -> StoredBatch:
        self.created.append((teacher_id, name, period))
        return replace(BATCH, name=name, period=period, teacher_id=teacher_id)

    def get(self, batch_id: UUID) -> StoredBatch | None:
        return self.batch if self.batch and self.batch.id == batch_id else None

    def list_batches(self, teacher_id: UUID, offset: int, limit: int) -> BatchPage:
        if teacher_id != BATCH.teacher_id:
            return BatchPage([], 0)
        analyses = (
            StoredBatchAnalysis("completado", 50.0, 0),
            StoredBatchAnalysis("completado", 90.0, 2),
            StoredBatchAnalysis("completado", 90.0, 0),
            StoredBatchAnalysis("verificando", None, 0),
            StoredBatchAnalysis("error", None, 0),
        )
        return BatchPage([BatchOverview(BATCH, analyses)], 21)

    def count_works(self, batch_id: UUID) -> int:
        return self.total_works

    def works(self, batch_id: UUID) -> list[StoredWork]:
        return self.stored


class FakeDocuments:
    def __init__(self) -> None:
        self.created: list[NewDocument] = []
        self.searched: list[UUID | None] = []

    def find_by_hash(
        self, owner_id: UUID, sha256: str, batch_id: UUID | None = None
    ) -> AnalysisRef | None:
        self.searched.append(batch_id)
        return None

    def create(self, document: NewDocument, model_version: str) -> AnalysisRef:
        self.created.append(document)
        return AnalysisRef(uuid4(), document.id, "en_cola")


class FakeStorage:
    def upload(self, path: str, content: bytes) -> None:
        pass

    def delete(self, path: str) -> None:
        pass


def batch_service(
    batches: FakeBatches | None = None,
) -> tuple[BatchService, FakeBatches, FakeDocuments]:
    batches = batches or FakeBatches()
    documents = FakeDocuments()
    uploads = UploadService(documents, FakeStorage(), model_version="modelo-prueba")
    return BatchService(batches, uploads), batches, documents


# --- Riesgo (RF20-CA02) ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("index", "contradictions", "risk"),
    [
        (59.9, 0, "alto"),
        (60.0, 0, "medio"),
        (84.9, 0, "medio"),
        (85.0, 0, "bajo"),
        (100.0, 0, "bajo"),
        (100.0, 1, "alto"),  # una Contradicción basta, aunque el índice sea alto
        (None, 1, "alto"),
        (None, 0, None),
    ],
)
def test_riesgo_de_un_trabajo(index: float | None, contradictions: int, risk: str | None) -> None:
    assert risk_of(index, contradictions) == risk


# --- Crear y consultar ----------------------------------------------------------------------


def test_crea_un_lote_vacio() -> None:
    service, batches, _ = batch_service()

    created = service.create(TEACHER, "Metodología 5B", "2026-2S")

    assert batches.created == [(TEACHER, "Metodología 5B", "2026-2S")]
    assert (created.name, created.period, created.total_works) == ("Metodología 5B", "2026-2S", 0)


def test_la_lista_resume_el_estado_de_cada_lote() -> None:
    service, _, _ = batch_service()

    page = service.list_batches(TEACHER, 1)

    [summary] = page.items
    assert (page.total, page.total_pages) == (21, 2)
    assert summary.total_works == 5
    assert (summary.finished, summary.in_progress, summary.failed) == (3, 1, 1)
    assert summary.high_risk == 2  # índice bajo y una con contradicciones


def test_el_tablero_cuenta_solo_los_analisis_terminados() -> None:
    finished = work(
        index=50.0,
        verdicts=("verificada", "contradiccion", "discrepancia", "sin_respaldo", None),
        fields=("anio", "titulo", "anio"),
    )
    running = work(status="verificando", index=None, verdicts=(None, None))
    service, _, _ = batch_service(FakeBatches([finished, running]))

    detail = service.detail(TEACHER, BATCH_ID)

    assert detail.total_works == len(detail.works) == 2
    assert detail.references == 5
    assert detail.counts.model_dump() == {
        "verificada": 1,
        "discrepancia": 1,
        "contradiccion": 1,
        "sin_respaldo": 1,
        "no_verificable": 0,
        "error_consulta": 1,  # el análisis en curso no suma errores de consulta
    }
    assert [(f.field, f.references) for f in detail.most_different_fields] == [
        ("anio", 2),
        ("titulo", 1),
    ]
    assert (detail.finished, detail.in_progress) == (1, 1)


def test_cada_trabajo_trae_su_riesgo_y_sus_alertas() -> None:
    risky = work(index=95.0, verdicts=("verificada", "contradiccion", "discrepancia"))
    running = work(status="verificando", index=None, verdicts=("contradiccion",))
    service, _, _ = batch_service(FakeBatches([risky, running]))

    first, second = service.detail(TEACHER, BATCH_ID).works

    assert (first.risk, first.contradictions, first.alerts) == ("alto", 1, 2)
    assert first.authors == ["Ana Vera", "Luis Rojas"]
    assert (second.risk, second.contradictions, second.alerts) == (None, 0, 0)


def test_sin_respaldo_no_es_una_alerta() -> None:
    quiet = work(index=None, verdicts=("sin_respaldo", "no_verificable"))
    service, _, _ = batch_service(FakeBatches([quiet]))

    [item] = service.detail(TEACHER, BATCH_ID).works

    assert (item.alerts, item.risk) == (0, None)


# --- Solo lo propio -------------------------------------------------------------------------


def test_el_lote_de_otro_docente_no_existe_para_el() -> None:
    service, _, documents = batch_service()

    with pytest.raises(BatchNotFoundError):
        service.detail(uuid4(), BATCH_ID)
    with pytest.raises(BatchNotFoundError):
        service.submit_work(uuid4(), BATCH_ID, "a.pdf", PDF)
    assert documents.created == []


# --- Subir al lote --------------------------------------------------------------------------


def test_sube_un_trabajo_al_lote_con_la_misma_funcion_que_el_estudiante() -> None:
    service, _, documents = batch_service()

    result = service.submit_work(TEACHER, BATCH_ID, "Avance 2.pdf", PDF)

    [document] = documents.created
    assert (document.batch_id, document.owner_id) == (BATCH_ID, TEACHER)
    assert documents.searched == [BATCH_ID]  # el duplicado se busca solo en este lote
    assert result.analysis.status == "en_cola"


def test_al_subir_al_lote_se_leen_los_autores_de_la_portada() -> None:
    service, _, documents = batch_service()
    cover = make_pdf([PageSpec(lines=["Autores:", "Ana Vera", "Luis Rojas", "Tutor:", "Pablo"])])

    service.submit_work(TEACHER, BATCH_ID, "Avance 2.pdf", cover)

    assert documents.created[0].authors == ("Ana Vera", "Luis Rojas")


def test_el_trabajo_individual_no_lee_la_portada() -> None:
    documents = FakeDocuments()
    uploads = UploadService(documents, FakeStorage(), model_version="modelo-prueba")
    cover = make_pdf([PageSpec(lines=["Autores:", "Ana Vera", "Tutor:", "Pablo"])])

    uploads.submit(TEACHER, "Avance 2.pdf", cover)

    assert documents.created[0].authors == ()


def test_un_archivo_invalido_se_rechaza_con_su_motivo() -> None:
    service, _, documents = batch_service()

    with pytest.raises(UploadRejectedError, match="Solo se aceptan"):
        service.submit_work(TEACHER, BATCH_ID, "foto.png", b"no es un pdf")
    assert documents.created == []


def test_el_lote_admite_hasta_40_trabajos() -> None:
    service, batches, documents = batch_service(FakeBatches(count=MAX_WORKS_PER_BATCH - 1))

    service.submit_work(TEACHER, BATCH_ID, "ultimo.pdf", PDF)
    batches.total_works = MAX_WORKS_PER_BATCH
    with pytest.raises(UploadRejectedError, match="máximo de 40"):
        service.submit_work(TEACHER, BATCH_ID, "otro.pdf", PDF)

    assert len(documents.created) == 1


# --- Rutas ----------------------------------------------------------------------------------


def client_as(role: str, service: BatchService | None = None) -> TestClient:
    app = create_app()
    trust_test_tokens(app)
    act_as(app, role)
    actual = service or batch_service()[0]
    app.dependency_overrides[get_batch_service] = lambda: actual
    # La ruta de los lotes arma su servicio de subida; aquí no debe tocar Supabase.
    app.dependency_overrides[get_upload_service] = lambda: None
    return TestClient(app)


def auth() -> dict[str, str]:
    return bearer(make_token())


def upload(client: TestClient, batch_id: UUID = BATCH_ID) -> httpx.Response:
    return client.post(
        f"/lotes/{batch_id}/trabajos",
        files={"archivo": ("Avance 2.pdf", PDF, "application/pdf")},
        headers=auth(),
    )


@pytest.mark.parametrize("role", ["estudiante", "admin"])
def test_solo_el_docente_usa_los_lotes(role: str) -> None:
    service, batches, documents = batch_service()
    client = client_as(role, service)

    body = {"name": "Lote", "period": "2026-2S"}
    assert client.post("/lotes", json=body, headers=auth()).status_code == 403
    assert client.get("/lotes", headers=auth()).status_code == 403
    assert client.get(f"/lotes/{BATCH_ID}", headers=auth()).status_code == 403
    assert upload(client).status_code == 403
    assert batches.created == []
    assert documents.created == []


def test_sin_sesion_no_se_usan_los_lotes() -> None:
    assert client_as("docente").get("/lotes").status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"name": "Lote"},
        {"period": "2026-2S"},
        {"name": "  ", "period": "2026-2S"},
        {"name": "Lote", "period": ""},
        {"name": "x" * 151, "period": "2026-2S"},
        {"name": "Lote", "period": "x" * 21},
    ],
)
def test_el_lote_requiere_nombre_y_periodo(body: dict[str, str]) -> None:
    assert client_as("docente").post("/lotes", json=body, headers=auth()).status_code == 422


def test_ruta_crea_el_lote_y_quita_los_espacios() -> None:
    service, batches, _ = batch_service()
    client = client_as("docente", service)

    response = client.post(
        "/lotes", json={"name": "  Software 7A ", "period": " 2026-2S "}, headers=auth()
    )

    assert response.status_code == 201
    assert batches.created == [(TEACHER, "Software 7A", "2026-2S")]


def test_ruta_del_tablero_y_lote_ajeno() -> None:
    service, _, _ = batch_service(FakeBatches([work(verdicts=("verificada",))]))
    client = client_as("docente", service)

    found = client.get(f"/lotes/{BATCH_ID}", headers=auth())
    missing = client.get(f"/lotes/{uuid4()}", headers=auth())

    assert found.status_code == 200
    assert found.json()["works"][0]["risk"] == "bajo"
    assert missing.status_code == 404


def test_ruta_sube_el_trabajo_y_avisa_lo_que_no_se_acepta() -> None:
    service, batches, _ = batch_service()
    client = client_as("docente", service)

    assert upload(client).status_code == 202
    assert upload(client, uuid4()).status_code == 404
    batches.total_works = MAX_WORKS_PER_BATCH
    rejected = upload(client)
    assert rejected.status_code == 422
    assert "máximo" in rejected.json()["detail"]


# --- Repositorios ---------------------------------------------------------------------------


def test_el_repositorio_crea_el_lote() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/t_lotes_auditoria")
        assert json.loads(request.content) == {
            "docente_id": USER_ID,
            "nombre": "Software 7A",
            "periodo_academico": "2026-2S",
        }
        return httpx.Response(
            201,
            json=[
                {
                    "id": str(BATCH_ID),
                    "docente_id": USER_ID,
                    "nombre": "Software 7A",
                    "periodo_academico": "2026-2S",
                    "creado_en": "2026-11-09T10:00:00+00:00",
                }
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    created = SupabaseBatchRepository(REST_URL, client).create(TEACHER, "Software 7A", "2026-2S")

    assert created.id == BATCH_ID


def test_el_repositorio_lee_el_tablero_con_el_analisis_mas_reciente() -> None:
    row: dict[str, Any] = {
        "id": str(uuid4()),
        "nombre_archivo": "Avance.pdf",
        "autores": ["Ana Vera"],
        "creado_en": "2026-11-09T10:00:00+00:00",
        "t_analisis": [
            {
                "id": str(uuid4()),
                "estado": "completado",
                "progreso": 100,
                "total_referencias": 2,
                "norma_detectada": "APA",
                "indice_veracidad": "75.00",
                "mensaje_error": None,
                "creado_en": "2026-11-09T10:00:00+00:00",
                "t_referencias": [
                    {
                        "t_verificaciones": {"veredicto": "discrepancia"},
                        "t_hallazgos": [
                            {"tipo": "veracidad", "codigo": "ANIO_DISTINTO", "campo": "anio"},
                            {"tipo": "veracidad", "codigo": "OTRA_OBRA", "campo": "doi"},
                            {"tipo": "formato", "codigo": "APA_DOI_FALTANTE", "campo": "doi"},
                        ],
                    },
                    {"t_verificaciones": None, "t_hallazgos": []},
                ],
            }
        ],
    }
    sin_analisis = {**row, "t_analisis": []}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["lote_id"] == f"eq.{BATCH_ID}"
        return httpx.Response(200, json=[row, sin_analisis])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    [stored] = SupabaseBatchRepository(REST_URL, client).works(BATCH_ID)

    assert stored.index == 75.0
    assert stored.authors == ("Ana Vera",)
    assert stored.verdicts == ("discrepancia", None)
    assert stored.different_fields == ("anio",)  # ni el aviso ni el formato son diferencias


def test_el_documento_guarda_su_lote_y_el_individual_no_lo_envia() -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(201, json=[{"id": str(uuid4()), "estado": "en_cola"}])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseDocumentRepository(REST_URL, client)
    document = NewDocument(uuid4(), TEACHER, "T", "t.pdf", "u/d.pdf", "a" * 64, 10)

    repository.create(document, "m")
    repository.create(replace(document, batch_id=BATCH_ID, authors=("Ana Vera",)), "m")

    # Sin lote no se envía ninguna de las dos: el trabajo individual no depende de ellas.
    assert "lote_id" not in bodies[0]
    assert "autores" not in bodies[0]
    assert bodies[2]["lote_id"] == str(BATCH_ID)
    assert bodies[2]["autores"] == ["Ana Vera"]


@pytest.mark.parametrize(
    ("batch_id", "expected"), [(None, "is.null"), (BATCH_ID, f"eq.{BATCH_ID}")]
)
def test_el_duplicado_se_busca_en_el_mismo_lugar(batch_id: UUID | None, expected: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["lote_id"] == expected
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert SupabaseDocumentRepository(REST_URL, client).find_by_hash(TEACHER, "a", batch_id) is None
