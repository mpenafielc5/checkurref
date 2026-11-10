"""Eliminar un trabajo con todos sus resultados (estudiante y docente). Sin Supabase real."""

import json
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.analyses import get_work_service
from app.main import create_app
from app.repositories.documents import OwnedWork, SupabaseDocumentRepository
from app.repositories.pdf_storage import SupabasePdfStorage
from app.repositories.supabase_http import SupabaseUnavailableError
from app.services.work_service import WorkInProgressError, WorkNotFoundError, WorkService
from tests.session_helpers import USER_ID, act_as, bearer, make_token, trust_test_tokens

OWNER = UUID(USER_ID)
ANALYSIS = uuid4()
DOCUMENT = uuid4()
PATH = f"{USER_ID}/{DOCUMENT}.pdf"
REST_URL = "https://proyecto.supabase.co/rest/v1"
STORAGE_URL = "https://proyecto.supabase.co/storage/v1"


class FakeDocuments:
    def __init__(self, statuses: tuple[str, ...] = ("completado",)) -> None:
        self.work: OwnedWork | None = OwnedWork(DOCUMENT, PATH, statuses)
        self.steps: list[str]
        self.deleted: list[UUID] = []

    def find_owned_work(self, owner_id: UUID, analysis_id: UUID) -> OwnedWork | None:
        return self.work if owner_id == OWNER and analysis_id == ANALYSIS else None

    def delete_document(self, document_id: UUID) -> None:
        self.steps.append("documento")
        self.deleted.append(document_id)


class FakeStorage:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.steps: list[str] = []
        self.removed: list[str] = []

    def remove(self, paths: list[str]) -> None:
        if self.fail:
            raise SupabaseUnavailableError("Supabase respondió 500")
        self.steps.append("pdf")
        self.removed.extend(paths)


def service(
    statuses: tuple[str, ...] = ("completado",), fail: bool = False
) -> tuple[WorkService, FakeDocuments, FakeStorage]:
    documents = FakeDocuments(statuses)
    storage = FakeStorage(fail)
    documents.steps = storage.steps  # un solo registro para comprobar el orden
    return WorkService(documents, storage), documents, storage


# --- Servicio -------------------------------------------------------------------------------


@pytest.mark.parametrize("statuses", [("completado",), ("error",), ("completado", "error")])
def test_borra_primero_el_pdf_y_despues_el_documento(statuses: tuple[str, ...]) -> None:
    work_service, documents, storage = service(statuses)

    work_service.delete(OWNER, ANALYSIS)

    assert storage.steps == ["pdf", "documento"]
    assert storage.removed == [PATH]
    assert documents.deleted == [DOCUMENT]


def test_el_trabajo_de_otra_cuenta_no_existe_para_quien_pregunta() -> None:
    work_service, documents, storage = service()

    with pytest.raises(WorkNotFoundError):
        work_service.delete(uuid4(), ANALYSIS)
    assert storage.removed == []
    assert documents.deleted == []


@pytest.mark.parametrize("status", ["en_cola", "extrayendo", "segmentando", "verificando"])
def test_un_analisis_en_curso_no_se_elimina(status: str) -> None:
    work_service, documents, storage = service(("completado", status))

    with pytest.raises(WorkInProgressError):
        work_service.delete(OWNER, ANALYSIS)
    assert storage.removed == []
    assert documents.deleted == []


def test_si_el_pdf_no_se_borra_el_documento_se_conserva() -> None:
    work_service, documents, _ = service(fail=True)

    with pytest.raises(SupabaseUnavailableError):
        work_service.delete(OWNER, ANALYSIS)
    assert documents.deleted == []


# --- Ruta -----------------------------------------------------------------------------------


def client_as(role: str, work_service: WorkService) -> TestClient:
    app = create_app()
    trust_test_tokens(app)
    act_as(app, role)
    app.dependency_overrides[get_work_service] = lambda: work_service
    return TestClient(app)


@pytest.mark.parametrize("role", ["estudiante", "docente"])
def test_ruta_elimina_el_trabajo_propio(role: str) -> None:
    work_service, documents, _ = service()

    response = client_as(role, work_service).delete(
        f"/analisis/{ANALYSIS}", headers=bearer(make_token())
    )

    assert response.status_code == 204
    assert documents.deleted == [DOCUMENT]


def test_ruta_ajeno_en_curso_y_sin_conexion() -> None:
    headers = bearer(make_token())
    missing = client_as("estudiante", service()[0]).delete(f"/analisis/{uuid4()}", headers=headers)
    running = client_as("estudiante", service(("verificando",))[0]).delete(
        f"/analisis/{ANALYSIS}", headers=headers
    )
    offline = client_as("estudiante", service(fail=True)[0]).delete(
        f"/analisis/{ANALYSIS}", headers=headers
    )

    assert missing.status_code == 404
    assert running.status_code == 409
    assert "cuando se complete" in running.json()["detail"]
    assert offline.status_code == 503


def test_sin_sesion_no_se_elimina() -> None:
    work_service, documents, _ = service()

    assert client_as("estudiante", work_service).delete(f"/analisis/{ANALYSIS}").status_code == 401
    assert documents.deleted == []


# --- Repositorios ---------------------------------------------------------------------------


def test_el_repositorio_busca_el_trabajo_solo_entre_los_del_dueno() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        document: dict[str, Any] = {
            "id": str(DOCUMENT),
            "ruta_storage": PATH,
            "t_analisis": [{"estado": "completado"}, {"estado": "error"}],
        }
        return httpx.Response(200, json=[{"t_documentos": document}])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    work = SupabaseDocumentRepository(REST_URL, client).find_owned_work(OWNER, ANALYSIS)

    params = seen[0].url.params
    assert seen[0].url.path.endswith("/t_analisis")
    assert params["id"] == f"eq.{ANALYSIS}"
    assert params["t_documentos.propietario_id"] == f"eq.{OWNER}"
    assert "t_documentos!inner" in params["select"]
    assert work == OwnedWork(DOCUMENT, PATH, ("completado", "error"))


def test_el_repositorio_no_encuentra_el_trabajo_ajeno() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[])))

    assert SupabaseDocumentRepository(REST_URL, client).find_owned_work(OWNER, ANALYSIS) is None


def test_el_repositorio_borra_el_documento() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    SupabaseDocumentRepository(REST_URL, client).delete_document(DOCUMENT)

    assert seen[0].method == "DELETE"
    assert seen[0].url.path.endswith("/t_documentos")
    assert seen[0].url.params["id"] == f"eq.{DOCUMENT}"


def test_el_almacenamiento_borra_el_pdf_por_lista_y_avisa_si_falla() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    ok = SupabasePdfStorage(
        STORAGE_URL, "documentos", httpx.Client(transport=httpx.MockTransport(handler))
    )
    ok.remove([PATH])

    assert seen[0].method == "DELETE"
    assert seen[0].url.path.endswith("/object/documentos")
    assert json.loads(seen[0].content) == {"prefixes": [PATH]}

    failing = SupabasePdfStorage(
        STORAGE_URL,
        "documentos",
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
    )
    with pytest.raises(SupabaseUnavailableError):
        failing.remove([PATH])
