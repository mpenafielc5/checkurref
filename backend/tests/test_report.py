"""Historial, estado de un análisis e informe de verificación (HU-05, HU-06, HU-07)."""

import json
from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.analyses import get_report_service
from app.extraction.base import Author, ExtractedFields
from app.main import create_app
from app.reports.highlight import highlight
from app.repositories.reports import (
    AnalysisPage,
    AnalysisRecord,
    StoredFinding,
    StoredInference,
    StoredReference,
    StoredVerification,
    SupabaseReportRepository,
)
from app.repositories.supabase_http import SupabaseUnavailableError
from app.services.report_service import (
    AnalysisNotFinishedError,
    AnalysisNotFoundError,
    ReportService,
)
from tests.session_helpers import USER_ID, act_as, bearer, make_token, trust_test_tokens

OWNER = UUID(USER_ID)
ANALYSIS_ID = uuid4()
REST_URL = "https://proyecto.supabase.co/rest/v1"

APA = (
    "Pérez, M. y López Vera, J. (2019). Redes neuronales en la educación superior. "
    "Revista Andina, 8(1), 10-25."
)
FIELDS = ExtractedFields(
    authors=(Author("Pérez", "M."), Author("López Vera", "J.")),
    year=2019,
    title="Redes neuronales en la educación superior",
    container="Revista Andina",
    volume="8",
    pages="10-25",
)


def analysis(status: str = "completado", owner: UUID = OWNER) -> AnalysisRecord:
    return AnalysisRecord(
        analysis_id=ANALYSIS_ID,
        document_id=uuid4(),
        owner_id=owner,
        file_name="Avance_cap2.pdf",
        status=status,
        progress=100 if status == "completado" else 62,
        created_at=datetime(2026, 11, 2, 20, 15, tzinfo=timezone.utc),
        finished_at=None,
        duration_ms=4100,
        norm="APA",
        engine="anystyle",
        total_references=3,
        index=50.0,
        error_message=None,
    )


DISCREPANCY = StoredReference(
    order=1,
    page=12,
    norm="APA",
    text=APA,
    fields=FIELDS,
    verification=StoredVerification(
        verdict="discrepancia",
        strategy="doi_directo",
        doi="10.1234/ra.2021.8",
        title_similarity=1.0,
        author_similarity=1.0,
        year_matches=False,
        corrected=[
            {
                "texto": "Pérez, M. y López Vera, J.",
                "campo": "autores",
                "cursiva": False,
                "cambiado": False,
            },
            {"texto": " (", "campo": None, "cursiva": False, "cambiado": False},
            {"texto": "2021", "campo": "anio", "cursiva": False, "cambiado": True},
            {
                "texto": "). Redes neuronales en la educación superior.",
                "campo": None,
                "cursiva": False,
                "cambiado": False,
            },
        ],
        inferences=(StoredInference("anio", 0.01, 0.02, 0.97),),
    ),
    findings=(
        StoredFinding(
            "veracidad", "ANIO_DISTINTO", "advertencia", "El año…", "anio", "2019", "2021"
        ),
        StoredFinding(
            "formato",
            "APA_DOI_FALTA",
            "advertencia",
            "Falta el DOI.",
            "doi",
            None,
            "https://doi.org/10.1234/ra.2021.8",
        ),
    ),
)
VERIFIED = StoredReference(
    order=2,
    page=12,
    norm="APA",
    text="Rivas, A. (2020). Aprendizaje automático aplicado. Editorial UNEMI.",
    fields=ExtractedFields(
        authors=(Author("Rivas", "A."),), year=2020, title="Aprendizaje automático aplicado"
    ),
    verification=StoredVerification(
        "verificada", "busqueda_bibliografica", None, 0.97, 1.0, True, None
    ),
)
QUERY_ERROR = StoredReference(
    order=3,
    page=13,
    norm="APA",
    text="Mora, A. (2023). Gestión del riesgo. Revista X.",
    fields=ExtractedFields(title="Gestión del riesgo"),
    verification=None,
    findings=(StoredFinding("veracidad", "ERROR_CONSULTA", "info", "No se pudo consultar…"),),
)


class FakeReports:
    def __init__(
        self,
        record: AnalysisRecord | None = None,
        references: list[StoredReference] | None = None,
        page: AnalysisPage | None = None,
        down: bool = False,
    ) -> None:
        self.record = record
        self._references = references or []
        self.page = page or AnalysisPage([], 0)
        self.down = down
        self.listed: list[tuple[UUID, int, int, str]] = []

    def get_analysis(self, analysis_id: UUID) -> AnalysisRecord | None:
        if self.down:
            raise SupabaseUnavailableError("caída")
        return self.record

    def references(self, analysis_id: UUID, engine: str) -> list[StoredReference]:
        return self._references

    def list_analyses(
        self, owner_id: UUID, offset: int, limit: int, search: str = ""
    ) -> AnalysisPage:
        self.listed.append((owner_id, offset, limit, search))
        return self.page


def report_of(*references: StoredReference) -> Any:
    return ReportService(FakeReports(analysis(), list(references))).report(OWNER, ANALYSIS_ID)


# --- Resaltado del texto original -----------------------------------------------------------


def colored(text: str, fields: ExtractedFields | None) -> list[tuple[str, str | None]]:
    return [(s.text, s.field.value if s.field else None) for s in highlight(text, fields)]


def test_resalta_los_campos_de_una_referencia_apa() -> None:
    assert colored(APA, FIELDS) == [
        ("Pérez, M. y López Vera, J.", "autores"),
        (" (", None),
        ("2019", "anio"),
        ("). ", None),
        ("Redes neuronales en la educación superior", "titulo"),
        (". ", None),
        ("Revista Andina", "contenedor"),
        (", 8(1), 10-25.", None),
    ]


def test_resalta_los_campos_de_una_referencia_ieee_sin_el_numero() -> None:
    text = '[3] J. Pérez y M. López, "Redes neuronales," Rev. Andina, vol. 8, pp. 1–5, 2021.'
    fields = ExtractedFields(
        authors=(Author("Pérez", "J."),),
        year=2021,
        title="Redes neuronales",
        container="Rev. Andina",
    )

    assert colored(text, fields)[:4] == [
        ("[3] ", None),
        ("J. Pérez y M. López", "autores"),
        (', "', None),
        ("Redes neuronales", "titulo"),
    ]
    assert ("2021", "anio") in colored(text, fields)


def test_el_texto_nunca_cambia_aunque_un_campo_no_aparezca() -> None:
    fields = ExtractedFields(title="Otro título que no está", year=2019)

    segments = highlight(APA, fields)

    assert "".join(s.text for s in segments) == APA
    assert [s.field.value for s in segments if s.field] == ["anio"]


def test_sin_campos_extraidos_el_texto_va_sin_color() -> None:
    assert colored(APA, None) == [(APA, None)]


def test_las_posiciones_no_se_corren_con_letras_que_cambian_de_largo() -> None:
    # "ß" pasa a "ss" al ignorar mayúsculas: las posiciones deben ser las del texto real.
    text = "Groß, A. (2020). Straße und Stadt. Revista, 1, 2."
    fields = ExtractedFields(authors=(Author("Groß", "A."),), year=2020, title="Straße und Stadt")

    assert ("Straße und Stadt", "titulo") in colored(text, fields)


# --- Informe --------------------------------------------------------------------------------


def test_informe_cuenta_veredictos_y_errores_de_consulta() -> None:
    report = report_of(DISCREPANCY, VERIFIED, QUERY_ERROR)

    assert report.total_references == 3
    assert report.counts.discrepancia == 1
    assert report.counts.verificada == 1
    assert report.counts.error_consulta == 1
    assert report.index == 50.0


def test_informe_compara_cada_campo_con_su_valor_oficial() -> None:
    [reference] = report_of(DISCREPANCY).references

    by_field = {c.field: c for c in reference.comparisons}
    assert [c.field for c in reference.comparisons] == ["titulo", "autores", "anio"]
    assert (by_field["anio"].given, by_field["anio"].official, by_field["anio"].matches) == (
        "2019",
        "2021",
        False,
    )
    assert by_field["titulo"].matches is True
    assert by_field["titulo"].similarity == 1.0  # nivel de confianza (HU-06 CA02)


def test_informe_separa_hallazgos_de_veracidad_y_de_formato() -> None:
    [reference] = report_of(DISCREPANCY).references

    assert [f.code for f in reference.veracity_findings] == ["ANIO_DISTINTO"]
    assert [f.code for f in reference.format_findings] == ["APA_DOI_FALTA"]


def test_informe_trae_la_referencia_corregida_con_sus_cambios() -> None:
    [reference] = report_of(DISCREPANCY).references

    assert reference.corrected is not None
    assert reference.corrected.text == (
        "Pérez, M. y López Vera, J. (2021). Redes neuronales en la educación superior."
    )
    assert reference.corrected.changed_fields == ["anio"]


def test_informe_trae_el_nli_por_campo() -> None:
    [reference] = report_of(DISCREPANCY).references

    assert [(n.field, n.contradiction) for n in reference.nli] == [("anio", 0.97)]


def test_referencia_con_error_de_consulta_no_tiene_veredicto_ni_comparaciones() -> None:
    [reference] = report_of(QUERY_ERROR).references

    assert reference.verdict is None
    assert reference.comparisons == []
    assert reference.veracity_findings[0].code == "ERROR_CONSULTA"


def test_campos_con_mas_diferencias() -> None:
    other = replace(DISCREPANCY, order=4)

    report = report_of(DISCREPANCY, other, VERIFIED)

    assert [(f.field, f.references) for f in report.most_different_fields] == [("anio", 2)]


def test_el_informe_de_otro_usuario_no_existe() -> None:
    service = ReportService(FakeReports(analysis(owner=uuid4())))

    with pytest.raises(AnalysisNotFoundError):
        service.report(OWNER, ANALYSIS_ID)


def test_un_analisis_en_curso_no_tiene_informe() -> None:
    service = ReportService(FakeReports(analysis(status="verificando")))

    with pytest.raises(AnalysisNotFinishedError):
        service.report(OWNER, ANALYSIS_ID)


# --- Historial ------------------------------------------------------------------------------


def test_historial_pagina_de_20_en_20() -> None:
    reports = FakeReports(page=AnalysisPage([analysis()], total=41))

    page = ReportService(reports).history(OWNER, 3)

    assert reports.listed == [(OWNER, 40, 20, "")]
    assert (page.page, page.page_size, page.total, page.total_pages) == (3, 20, 41, 3)
    assert page.items[0].file_name == "Avance_cap2.pdf"


def test_historial_vacio_tiene_una_pagina() -> None:
    page = ReportService(FakeReports()).history(OWNER, 1)

    assert (page.total, page.total_pages, page.items) == (0, 1, [])


# --- Repositorio ----------------------------------------------------------------------------


ANALYSIS_ROW = {
    "id": str(ANALYSIS_ID),
    "documento_id": str(uuid4()),
    "estado": "completado",
    "progreso": 100,
    # Postgres puede enviar entre 1 y 6 decimales en los segundos.
    "creado_en": "2026-11-02T20:15:31.12345+00:00",
    "finalizado_en": "2026-11-02T20:15:35.5+00:00",
    "duracion_ms": 4100,
    "norma_detectada": "APA",
    "extractor_principal": "anystyle",
    "total_referencias": 1,
    "indice_veracidad": 100,
    "mensaje_error": None,
    "t_documentos": {"propietario_id": USER_ID, "nombre_archivo": "Avance_cap2.pdf"},
}
REFERENCE_ROW = {
    "orden": 1,
    "pagina": 12,
    "norma": "APA",
    "texto_crudo": APA,
    "t_extracciones": [
        {
            "motor": "anystyle",
            "autores": [{"family": "Pérez", "given": "M."}],
            "anio": 2019,
            "titulo": "Redes neuronales en la educación superior",
            "contenedor": "Revista Andina",
            "editorial": None,
            "volumen": "8",
            "numero": "1",
            "paginas": "10-25",
            "doi": None,
        }
    ],
    "t_verificaciones": {
        "veredicto": "verificada",
        "estrategia": "doi_directo",
        "crossref_doi": "10.1234/ra.2021.8",
        "sim_titulo": 1.0,
        "sim_autores": 1.0,
        "coincide_anio": True,
        "referencia_corregida": None,
        "t_inferencias_nli": [
            {"campo": "titulo", "p_implicacion": 0.95, "p_neutral": 0.03, "p_contradiccion": 0.02}
        ],
    },
    "t_hallazgos": [],
}


def repository(handler: Any) -> SupabaseReportRepository:
    return SupabaseReportRepository(REST_URL, httpx.Client(transport=httpx.MockTransport(handler)))


def test_lee_el_analisis_con_su_propietario_y_archivo() -> None:
    record = repository(lambda _: httpx.Response(200, json=[ANALYSIS_ROW])).get_analysis(
        ANALYSIS_ID
    )

    assert record is not None
    assert record.owner_id == OWNER
    assert record.file_name == "Avance_cap2.pdf"
    assert record.created_at.microsecond == 123450
    assert record.index == 100.0


def test_lee_las_referencias_con_la_extraccion_del_motor_principal() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[REFERENCE_ROW])

    [reference] = repository(handler).references(ANALYSIS_ID, "anystyle")

    assert seen[0].url.params["t_extracciones.motor"] == "eq.anystyle"
    assert seen[0].url.params["order"] == "orden.asc"
    assert reference.fields is not None and reference.fields.year == 2019
    assert reference.verification is not None
    assert reference.verification.inferences[0].entailment == 0.95


def test_verificacion_como_lista_o_ausente() -> None:
    as_list = {**REFERENCE_ROW, "t_verificaciones": [REFERENCE_ROW["t_verificaciones"]]}
    absent = {**REFERENCE_ROW, "t_verificaciones": None, "t_extracciones": []}

    first, second = repository(lambda _: httpx.Response(200, json=[as_list, absent])).references(
        ANALYSIS_ID, "anystyle"
    )

    assert first.verification is not None and first.verification.verdict == "verificada"
    assert second.verification is None and second.fields is None


def test_historial_pide_el_total_y_solo_trabajos_propios_fuera_de_lotes() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[ANALYSIS_ROW], headers={"Content-Range": "0-0/41"})

    page = repository(handler).list_analyses(OWNER, 40, 20)

    params = seen[0].url.params
    assert seen[0].headers["Prefer"] == "count=exact"
    assert params["t_documentos.propietario_id"] == f"eq.{OWNER}"
    assert params["t_documentos.lote_id"] == "is.null"
    assert (params["offset"], params["limit"], params["order"]) == ("40", "20", "creado_en.desc")
    assert page.total == 41


# --- Rutas ----------------------------------------------------------------------------------


@pytest.fixture
def services() -> dict[str, ReportService]:
    return {}


@pytest.fixture
def client(services: dict[str, ReportService]) -> Iterator[TestClient]:
    app = create_app()
    trust_test_tokens(app)
    act_as(app)
    app.dependency_overrides[get_report_service] = lambda: services["actual"]
    yield TestClient(app)


def get(client: TestClient, path: str) -> httpx.Response:
    return client.get(path, headers=bearer(make_token()))


def test_ruta_del_informe(client: TestClient, services: dict[str, ReportService]) -> None:
    services["actual"] = ReportService(FakeReports(analysis(), [DISCREPANCY]))

    response = get(client, f"/analisis/{ANALYSIS_ID}/informe")

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["discrepancia"] == 1
    assert body["references"][0]["corrected"]["changed_fields"] == ["anio"]


@pytest.mark.parametrize(
    ("record", "status"),
    [(None, 404), (analysis(owner=uuid4()), 404), (analysis(status="verificando"), 409)],
)
def test_ruta_del_informe_sin_informe(
    client: TestClient,
    services: dict[str, ReportService],
    record: AnalysisRecord | None,
    status: int,
) -> None:
    services["actual"] = ReportService(FakeReports(record))

    assert get(client, f"/analisis/{ANALYSIS_ID}/informe").status_code == status


def test_ruta_del_informe_de_un_analisis_con_error_explica_el_motivo(
    client: TestClient, services: dict[str, ReportService]
) -> None:
    services["actual"] = ReportService(FakeReports(analysis(status="error")))

    response = get(client, f"/analisis/{ANALYSIS_ID}/informe")

    assert response.status_code == 409
    assert "error" in response.json()["detail"]


def test_ruta_del_estado_para_la_pantalla_de_progreso(
    client: TestClient, services: dict[str, ReportService]
) -> None:
    services["actual"] = ReportService(FakeReports(analysis(status="verificando")))

    response = get(client, f"/analisis/{ANALYSIS_ID}")

    assert response.status_code == 200
    assert (response.json()["status"], response.json()["progress"]) == ("verificando", 62)


def test_ruta_del_historial(client: TestClient, services: dict[str, ReportService]) -> None:
    services["actual"] = ReportService(FakeReports(page=AnalysisPage([analysis()], total=1)))

    response = get(client, "/analisis?pagina=1")

    assert response.status_code == 200
    assert response.json()["items"][0]["analysis_id"] == str(ANALYSIS_ID)


def test_ruta_del_historial_rechaza_una_pagina_invalida(
    client: TestClient, services: dict[str, ReportService]
) -> None:
    services["actual"] = ReportService(FakeReports())

    assert get(client, "/analisis?pagina=0").status_code == 422


def test_las_rutas_exigen_sesion(client: TestClient, services: dict[str, ReportService]) -> None:
    services["actual"] = ReportService(FakeReports(analysis()))

    assert client.get(f"/analisis/{ANALYSIS_ID}/informe").status_code == 401
    assert client.get("/analisis").status_code == 401


def test_sin_conexion_con_supabase_responde_503(
    client: TestClient, services: dict[str, ReportService]
) -> None:
    services["actual"] = ReportService(FakeReports(down=True))

    assert get(client, f"/analisis/{ANALYSIS_ID}").status_code == 503


def test_el_json_del_informe_usa_los_nombres_de_la_api() -> None:
    body = json.loads(report_of(DISCREPANCY).model_dump_json())

    assert set(body["references"][0]) >= {"segments", "comparisons", "nli", "corrected"}


def test_historial_busca_por_nombre_sin_comodines() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[], headers={"Content-Range": "*/0"})

    repository(handler).list_analyses(OWNER, 0, 20, " Avance_cap*2% ")

    assert seen[0].url.params["t_documentos.nombre_archivo"] == "ilike.*Avance_cap2*"


def test_ruta_del_historial_pasa_la_busqueda(
    client: TestClient, services: dict[str, ReportService]
) -> None:
    reports = FakeReports()
    services["actual"] = ReportService(reports)

    get(client, "/analisis?pagina=2&buscar=avance")

    assert reports.listed == [(OWNER, 20, 20, "avance")]
