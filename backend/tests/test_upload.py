"""Subida del PDF y creación del análisis en cola (HU-04, POST /analisis)."""

import hashlib
import json
from collections.abc import Iterator
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.analyses import get_upload_service
from app.main import create_app
from app.repositories.documents import AnalysisRef, NewDocument, SupabaseDocumentRepository
from app.repositories.pdf_storage import SupabasePdfStorage
from app.repositories.supabase_http import SupabaseUnavailableError, service_headers
from app.services.upload_service import MAX_PDF_BYTES, UploadRejectedError, UploadService
from tests.pdf_factory import PageSpec, make_pdf
from tests.session_helpers import USER_ID, bearer, make_token, trust_test_tokens

OWNER = UUID(USER_ID)
PDF = make_pdf(
    [PageSpec(lines=["Referencias", "Torres, A. (2020). Un título. Revista, 1(1), 1–2."])]
)


class FakeDocuments:
    def __init__(self, existing: AnalysisRef | None = None, fail: bool = False) -> None:
        self.existing = existing
        self.fail = fail
        self.created: list[NewDocument] = []

    def find_by_hash(self, owner_id: UUID, sha256: str) -> AnalysisRef | None:
        return self.existing

    def create(self, document: NewDocument, model_version: str) -> AnalysisRef:
        if self.fail:
            raise SupabaseUnavailableError("caída")
        self.created.append(document)
        return AnalysisRef(analysis_id=uuid4(), document_id=document.id, status="en_cola")


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def upload(self, path: str, content: bytes) -> None:
        self.files[path] = content

    def delete(self, path: str) -> None:
        self.files.pop(path, None)


def make_service(
    documents: FakeDocuments | None = None, storage: FakeStorage | None = None
) -> tuple[UploadService, FakeDocuments, FakeStorage]:
    documents = documents or FakeDocuments()
    storage = storage or FakeStorage()
    return UploadService(documents, storage, model_version="modelo-prueba"), documents, storage


# --- Servicio -------------------------------------------------------------------------------


def test_guarda_el_pdf_y_deja_el_analisis_en_cola() -> None:
    service, documents, storage = make_service()

    result = service.submit(OWNER, "Avance_cap2.pdf", PDF)

    assert result.duplicate is False
    assert result.analysis.status == "en_cola"
    document = documents.created[0]
    assert document.title == "Avance_cap2"
    assert document.sha256 == hashlib.sha256(PDF).hexdigest()
    assert document.storage_path == f"{OWNER}/{document.id}.pdf"
    assert storage.files[document.storage_path] == PDF


def test_un_pdf_identico_no_se_reanaliza() -> None:
    existing = AnalysisRef(analysis_id=uuid4(), document_id=uuid4(), status="completado")
    service, documents, storage = make_service(FakeDocuments(existing=existing))

    result = service.submit(OWNER, "otro_nombre.pdf", PDF)

    assert result.duplicate is True
    assert result.analysis == existing
    assert documents.created == []
    assert storage.files == {}


@pytest.mark.parametrize(
    ("content", "message"),
    [
        pytest.param(b"", "El archivo está vacío.", id="vacío"),
        pytest.param(b"no soy un pdf", "Solo se aceptan archivos PDF.", id="no es pdf"),
        pytest.param(
            b"%PDF-" + b"0" * MAX_PDF_BYTES, "El archivo supera el máximo de 10 MB.", id="grande"
        ),
    ],
)
def test_rechaza_archivos_invalidos(content: bytes, message: str) -> None:
    service, _documents, storage = make_service()

    with pytest.raises(UploadRejectedError) as error:
        service.submit(OWNER, "trabajo.pdf", content)

    assert error.value.message == message
    assert storage.files == {}


def test_si_la_base_falla_borra_el_pdf_ya_guardado() -> None:
    service, _documents, storage = make_service(FakeDocuments(fail=True))

    with pytest.raises(SupabaseUnavailableError):
        service.submit(OWNER, "trabajo.pdf", PDF)

    assert storage.files == {}


# --- Ruta -----------------------------------------------------------------------------------


@pytest.fixture
def services() -> dict[str, UploadService]:
    return {}


@pytest.fixture
def client(services: dict[str, UploadService]) -> Iterator[TestClient]:
    app = create_app()
    trust_test_tokens(app)
    app.dependency_overrides[get_upload_service] = lambda: services["actual"]
    yield TestClient(app)


def upload(client: TestClient, content: bytes = PDF) -> httpx.Response:
    return client.post(
        "/analisis",
        headers=bearer(make_token()),
        files={"archivo": ("Avance_cap2.pdf", content, "application/pdf")},
    )


def test_ruta_responde_202_con_el_analisis_nuevo(
    client: TestClient, services: dict[str, UploadService]
) -> None:
    services["actual"], _documents, _storage = make_service()

    response = upload(client)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "en_cola"
    assert body["duplicate"] is False


def test_ruta_responde_200_con_el_analisis_existente(
    client: TestClient, services: dict[str, UploadService]
) -> None:
    existing = AnalysisRef(analysis_id=uuid4(), document_id=uuid4(), status="completado")
    services["actual"], _documents, _storage = make_service(FakeDocuments(existing=existing))

    response = upload(client)

    assert response.status_code == 200
    assert response.json() == {
        "analysis_id": str(existing.analysis_id),
        "document_id": str(existing.document_id),
        "status": "completado",
        "duplicate": True,
    }


def test_ruta_explica_por_que_rechaza_el_archivo(
    client: TestClient, services: dict[str, UploadService]
) -> None:
    services["actual"], _documents, _storage = make_service()

    response = upload(client, content=b"texto plano")

    assert response.status_code == 422
    assert response.json()["detail"] == "Solo se aceptan archivos PDF."


def test_ruta_exige_el_archivo(client: TestClient, services: dict[str, UploadService]) -> None:
    services["actual"], _documents, _storage = make_service()

    response = client.post("/analisis", headers=bearer(make_token()))

    assert response.status_code == 422


def test_ruta_responde_503_si_supabase_no_responde(
    client: TestClient, services: dict[str, UploadService]
) -> None:
    services["actual"], _documents, _storage = make_service(FakeDocuments(fail=True))

    response = upload(client)

    assert response.status_code == 503
    assert "Intenta de nuevo" in response.json()["detail"]


def test_ruta_exige_sesion(client: TestClient, services: dict[str, UploadService]) -> None:
    services["actual"], _documents, _storage = make_service()

    response = client.post(
        "/analisis",
        files={"archivo": ("a.pdf", PDF, "application/pdf")},
    )

    assert response.status_code == 401


# --- Repositorios (Supabase simulado) -------------------------------------------------------

REST_URL = "https://proyecto.supabase.co/rest/v1"
STORAGE_URL = "https://proyecto.supabase.co/storage/v1"


def test_busca_el_pdf_identico_del_mismo_usuario_fuera_de_lotes() -> None:
    seen: list[httpx.Request] = []
    document_id, analysis_id = uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        row = {"id": str(document_id), "analisis": [{"id": str(analysis_id), "estado": "en_cola"}]}
        return httpx.Response(200, json=[row])

    repository = SupabaseDocumentRepository(
        REST_URL, httpx.Client(transport=httpx.MockTransport(handler))
    )

    found = repository.find_by_hash(OWNER, "abc")

    assert found == AnalysisRef(analysis_id=analysis_id, document_id=document_id, status="en_cola")
    params = seen[0].url.params
    assert params["propietario_id"] == f"eq.{OWNER}"
    assert params["sha256"] == "eq.abc"
    assert params["lote_id"] == "is.null"


def test_crea_el_documento_y_su_analisis_en_cola() -> None:
    bodies: dict[str, dict[str, object]] = {}
    analysis_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        table = request.url.path.rsplit("/", 1)[-1]
        bodies[table] = json.loads(request.content)
        if table == "analisis":
            return httpx.Response(201, json=[{"id": str(analysis_id), "estado": "en_cola"}])
        return httpx.Response(201, json=[bodies[table]])

    repository = SupabaseDocumentRepository(
        REST_URL, httpx.Client(transport=httpx.MockTransport(handler))
    )
    document = NewDocument(
        id=uuid4(),
        owner_id=OWNER,
        title="Avance",
        file_name="Avance.pdf",
        storage_path="ruta.pdf",
        sha256="abc",
        size_bytes=10,
    )

    created = repository.create(document, "modelo-prueba")

    assert created.analysis_id == analysis_id
    assert bodies["documentos"]["propietario_id"] == str(OWNER)
    assert "version" not in bodies["documentos"]
    # Nadie elige la norma: el pipeline la detecta después.
    assert bodies["analisis"] == {
        "documento_id": str(document.id),
        "version_modelo": "modelo-prueba",
    }


def test_si_falla_el_analisis_borra_el_documento() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(f"{request.method} {request.url.path.rsplit('/', 1)[-1]}")
        if request.url.path.endswith("analisis"):
            return httpx.Response(500)
        return httpx.Response(201, json=[{}])

    repository = SupabaseDocumentRepository(
        REST_URL, httpx.Client(transport=httpx.MockTransport(handler))
    )
    document = NewDocument(uuid4(), OWNER, "A", "A.pdf", "a.pdf", "abc", 10)

    with pytest.raises(SupabaseUnavailableError):
        repository.create(document, "modelo-prueba")

    assert methods == ["POST documentos", "POST analisis", "DELETE documentos"]


def test_sube_el_pdf_sin_reemplazar_otro() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"Key": "documentos/a.pdf"})

    storage = SupabasePdfStorage(
        STORAGE_URL, "documentos", httpx.Client(transport=httpx.MockTransport(handler))
    )

    storage.upload("usuario/doc.pdf", PDF)

    request = seen[0]
    assert str(request.url) == f"{STORAGE_URL}/object/documentos/usuario/doc.pdf"
    assert request.headers["Content-Type"] == "application/pdf"
    assert request.headers["x-upsert"] == "false"
    assert request.content == PDF


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        pytest.param("sb_secret_abc", {"apikey": "sb_secret_abc"}, id="clave nueva"),
        pytest.param(
            "eyJhbGciOi.x.y",
            {"apikey": "eyJhbGciOi.x.y", "Authorization": "Bearer eyJhbGciOi.x.y"},
            id="clave antigua",
        ),
    ],
)
def test_encabezados_segun_el_tipo_de_clave(key: str, expected: dict[str, str]) -> None:
    assert service_headers(key) == expected
