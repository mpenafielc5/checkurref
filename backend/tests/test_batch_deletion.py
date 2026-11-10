"""Eliminar un lote completo con sus trabajos (amplía HU-23). Sin Supabase real."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.analyses import get_work_service
from app.main import create_app
from app.repositories.batches import StoredBatch, SupabaseBatchRepository
from app.repositories.documents import OwnedWork, SupabaseDocumentRepository
from app.repositories.pdf_storage import SupabasePdfStorage
from app.repositories.supabase_http import SupabaseUnavailableError
from app.services.work_service import BatchNotFoundError, WorkInProgressError, WorkService
from tests.session_helpers import USER_ID, act_as, bearer, make_token, trust_test_tokens

TEACHER = UUID(USER_ID)
BATCH_ID = uuid4()
NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)
REST_URL = "https://proyecto.supabase.co/rest/v1"


def owned(status: str = "completado") -> OwnedWork:
    document = uuid4()
    return OwnedWork(document, f"{USER_ID}/{document}.pdf", (status,))


class FakeDocuments:
    def __init__(self, works: list[OwnedWork], steps: list[str]) -> None:
        self.works = works
        self.steps = steps

    def batch_works(self, batch_id: UUID) -> list[OwnedWork]:
        return self.works if batch_id == BATCH_ID else []

    def delete_batch_documents(self, batch_id: UUID) -> None:
        self.steps.append(f"documentos:{batch_id}")


class FakeStorage:
    def __init__(self, steps: list[str], fail: bool = False) -> None:
        self.steps = steps
        self.fail = fail
        self.removed: list[str] = []

    def remove(self, paths: list[str]) -> None:
        if self.fail:
            raise SupabaseUnavailableError("Supabase respondió 500")
        self.steps.append("pdf")
        self.removed.extend(paths)


class FakeBatches:
    def __init__(self, steps: list[str]) -> None:
        self.steps = steps

    def get(self, batch_id: UUID) -> StoredBatch | None:
        if batch_id != BATCH_ID:
            return None
        return StoredBatch(BATCH_ID, TEACHER, "Software 7A", "2026-2S", NOW)

    def delete(self, batch_id: UUID) -> None:
        self.steps.append(f"lote:{batch_id}")


def service(
    works: list[OwnedWork] | None = None, fail: bool = False
) -> tuple[WorkService, list[str], FakeStorage]:
    steps: list[str] = []
    storage = FakeStorage(steps, fail)
    documents = FakeDocuments(works if works is not None else [owned(), owned("error")], steps)
    return WorkService(documents, storage, FakeBatches(steps)), steps, storage


# --- Servicio -------------------------------------------------------------------------------


def test_borra_los_pdf_luego_los_trabajos_y_al_final_el_lote() -> None:
    works = [owned(), owned("error")]
    work_service, steps, storage = service(works)

    work_service.delete_batch(TEACHER, BATCH_ID)

    # Si el lote se borrara antes, la base dejaría sus trabajos como sueltos.
    assert steps == ["pdf", f"documentos:{BATCH_ID}", f"lote:{BATCH_ID}"]
    assert storage.removed == [work.storage_path for work in works]


def test_un_lote_vacio_se_elimina_sin_tocar_el_almacenamiento() -> None:
    work_service, steps, storage = service([])

    work_service.delete_batch(TEACHER, BATCH_ID)

    assert storage.removed == []
    assert steps[-1] == f"lote:{BATCH_ID}"


def test_el_lote_de_otro_docente_no_existe_para_el() -> None:
    work_service, steps, _ = service()

    with pytest.raises(BatchNotFoundError):
        work_service.delete_batch(uuid4(), BATCH_ID)
    with pytest.raises(BatchNotFoundError):
        work_service.delete_batch(TEACHER, uuid4())
    assert steps == []


def test_con_un_trabajo_en_analisis_no_se_elimina_nada() -> None:
    work_service, steps, _ = service([owned(), owned("verificando")])

    with pytest.raises(WorkInProgressError):
        work_service.delete_batch(TEACHER, BATCH_ID)
    assert steps == []


def test_si_los_pdf_no_se_borran_el_lote_se_conserva() -> None:
    work_service, steps, _ = service(fail=True)

    with pytest.raises(SupabaseUnavailableError):
        work_service.delete_batch(TEACHER, BATCH_ID)
    assert steps == []


# --- Ruta -----------------------------------------------------------------------------------


def client_as(role: str, work_service: WorkService) -> TestClient:
    app = create_app()
    trust_test_tokens(app)
    act_as(app, role)
    app.dependency_overrides[get_work_service] = lambda: work_service
    return TestClient(app)


def test_ruta_elimina_el_lote_ajeno_en_curso_y_sin_conexion() -> None:
    headers = bearer(make_token())
    deleted = client_as("docente", service()[0]).delete(f"/lotes/{BATCH_ID}", headers=headers)
    missing = client_as("docente", service()[0]).delete(f"/lotes/{uuid4()}", headers=headers)
    running = client_as("docente", service([owned("en_cola")])[0]).delete(
        f"/lotes/{BATCH_ID}", headers=headers
    )
    offline = client_as("docente", service(fail=True)[0]).delete(
        f"/lotes/{BATCH_ID}", headers=headers
    )

    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert running.status_code == 409
    assert "aún se analizan" in running.json()["detail"]
    assert offline.status_code == 503


@pytest.mark.parametrize("role", ["estudiante", "admin"])
def test_solo_el_docente_elimina_lotes(role: str) -> None:
    work_service, steps, _ = service()

    response = client_as(role, work_service).delete(
        f"/lotes/{BATCH_ID}", headers=bearer(make_token())
    )

    assert response.status_code == 403
    assert steps == []


# --- Repositorios ---------------------------------------------------------------------------


def recorder() -> tuple[httpx.Client, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "GET":
            document = {
                "id": str(uuid4()),
                "ruta_storage": "a/b.pdf",
                "t_analisis": [{"estado": "completado"}],
            }
            return httpx.Response(200, json=[document])
        return httpx.Response(204)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_el_repositorio_lee_y_borra_los_trabajos_del_lote() -> None:
    client, seen = recorder()
    documents = SupabaseDocumentRepository(REST_URL, client)

    works = documents.batch_works(BATCH_ID)
    documents.delete_batch_documents(BATCH_ID)

    assert seen[0].url.params["lote_id"] == f"eq.{BATCH_ID}"
    assert works[0].storage_path == "a/b.pdf"
    assert works[0].statuses == ("completado",)
    assert seen[1].method == "DELETE"
    assert seen[1].url.path.endswith("/t_documentos")
    assert seen[1].url.params["lote_id"] == f"eq.{BATCH_ID}"


def test_el_repositorio_borra_la_fila_del_lote() -> None:
    client, seen = recorder()

    SupabaseBatchRepository(REST_URL, client).delete(BATCH_ID)

    assert seen[0].method == "DELETE"
    assert seen[0].url.path.endswith("/t_lotes_auditoria")
    assert seen[0].url.params["id"] == f"eq.{BATCH_ID}"


def test_el_almacenamiento_no_llama_si_no_hay_pdf() -> None:
    client, seen = recorder()

    SupabasePdfStorage("https://proyecto.supabase.co/storage/v1", "documentos", client).remove([])

    assert seen == []
