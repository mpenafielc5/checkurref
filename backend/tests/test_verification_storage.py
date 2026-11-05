"""Hallazgos de veracidad y guardado de la verificación (T14). Sin Supabase real."""

import json
from dataclasses import replace
from typing import Any
from uuid import uuid4

import httpx

from app.repositories.verifications import SupabaseVerificationRepository
from app.sources.lookup import Strategy
from app.verification.decision import CheckedField, Verdict, Verification, decide
from app.verification.findings import (
    INTERNAL_ERROR_CODE,
    OTHER_WORK_CODE,
    QUERY_ERROR_CODE,
    Severity,
    findings_for,
)
from tests.test_decision import (
    FIELDS,
    OTHER_WORK,
    RECORD,
    TEXT,
    WITHOUT_DOI,
    FakeNli,
    by_doi,
    by_search,
)

REST_URL = "https://proyecto.supabase.co/rest/v1"
ANALYSIS_ID = uuid4()


def verified() -> Verification:
    return decide(TEXT, FIELDS, by_doi(RECORD), FakeNli())


# --- Hallazgos ------------------------------------------------------------------------------


def test_verificada_no_tiene_hallazgos() -> None:
    assert findings_for(verified()) == []


def test_cada_campo_distinto_es_un_hallazgo_con_ambos_valores() -> None:
    verification = decide(TEXT, replace(FIELDS, year=2019), by_doi(RECORD), FakeNli())

    [finding] = findings_for(verification)

    assert finding.code == "ANIO_DISTINTO"
    assert finding.severity is Severity.WARNING
    assert (finding.field, finding.given, finding.official) == (CheckedField.YEAR, "2019", "2021")
    assert finding.message == "El año de publicación no coincide con el registro de Crossref."


def test_contradiccion_dice_a_que_obra_lleva_el_doi() -> None:
    findings = findings_for(decide(TEXT, FIELDS, by_doi(OTHER_WORK), FakeNli()))

    assert findings[0].code == OTHER_WORK_CODE
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].official == OTHER_WORK.title


def test_doi_que_nadie_registra_tiene_su_propio_hallazgo() -> None:
    fields = replace(FIELDS, doi="10.1000/inventado")

    [finding] = findings_for(decide(TEXT, fields, by_search(RECORD), FakeNli()))

    assert finding.code == "DOI_NO_REGISTRADO"
    assert finding.official == RECORD.doi  # el DOI de la obra encontrada


def test_errores_de_consulta_e_internos_quedan_como_informativos() -> None:
    query_error = decide(TEXT, WITHOUT_DOI, by_search(failed=True), FakeNli())

    assert [f.code for f in findings_for(query_error)] == [QUERY_ERROR_CODE]
    assert [f.code for f in findings_for(None)] == [INTERNAL_ERROR_CODE]
    assert findings_for(None)[0].severity is Severity.INFO


def test_sin_respaldo_no_tiene_hallazgos() -> None:
    assert findings_for(decide(TEXT, WITHOUT_DOI, by_search(), FakeNli())) == []


# --- Repositorio ----------------------------------------------------------------------------


class Recorder:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        table = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, table, body))
        if table == "verificaciones":
            rows = [{"id": f"v-{row['referencia_id']}", **row} for row in body]
            return httpx.Response(201, json=rows)
        return httpx.Response(201)

    def body(self, method: str, table: str) -> Any:
        return next(b for m, t, b in self.requests if (m, t) == (method, table))


def save(verifications: dict[str, Any], index: float | None) -> Recorder:
    recorder = Recorder()
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    SupabaseVerificationRepository(REST_URL, client).save(ANALYSIS_ID, verifications, index)
    return recorder


def test_guarda_verificacion_inferencias_hallazgos_e_indice() -> None:
    discrepancy = decide(TEXT, replace(FIELDS, year=2019), by_doi(RECORD), FakeNli())

    recorder = save({"ref-1": verified(), "ref-2": discrepancy}, 50.0)

    first, second = recorder.body("POST", "verificaciones")
    assert first == {
        "referencia_id": "ref-1",
        "crossref_doi": RECORD.doi,
        "estrategia": "doi_directo",
        "score_crossref": None,
        "sim_titulo": 1.0,
        "sim_autores": 1.0,
        "coincide_anio": True,
        "veredicto": "verificada",
    }
    assert second["veredicto"] == "discrepancia" and second["coincide_anio"] is False

    inferences = recorder.body("POST", "inferencias_nli")
    assert {row["verificacion_id"] for row in inferences} == {"v-ref-1", "v-ref-2"}
    assert {row["campo"] for row in inferences} == {"titulo", "autores", "anio", "contenedor"}

    [finding] = recorder.body("POST", "hallazgos")
    assert finding["referencia_id"] == "ref-2"
    assert finding["tipo"] == "veracidad"
    assert (finding["campo"], finding["valor_dado"], finding["valor_oficial"]) == (
        "anio",
        "2019",
        "2021",
    )

    assert recorder.body("PATCH", "analisis") == {"indice_veracidad": 50.0}


def test_un_error_de_consulta_solo_deja_su_hallazgo() -> None:
    query_error = decide(TEXT, WITHOUT_DOI, by_search(failed=True), FakeNli())

    recorder = save({"ref-1": query_error, "ref-2": None}, None)

    tables = [(method, table) for method, table, _ in recorder.requests]
    assert ("POST", "verificaciones") not in tables
    codes = [row["codigo"] for row in recorder.body("POST", "hallazgos")]
    assert codes == [QUERY_ERROR_CODE, INTERNAL_ERROR_CODE]
    assert recorder.body("PATCH", "analisis") == {"indice_veracidad": None}


def test_sin_respaldo_se_guarda_sin_registro_ni_similitudes() -> None:
    unsupported = decide(TEXT, WITHOUT_DOI, by_search(), FakeNli())
    assert unsupported.verdict is Verdict.UNSUPPORTED

    [row] = save({"ref-1": unsupported}, 0.0).body("POST", "verificaciones")

    assert row["crossref_doi"] is None
    assert row["estrategia"] == Strategy.BIBLIOGRAPHIC_SEARCH.value
    assert row["sim_titulo"] is None and row["veredicto"] == "sin_respaldo"


def test_una_relevancia_que_no_cabe_en_la_columna_no_se_guarda() -> None:
    record = replace(RECORD, score=250_000.5)

    [row] = save({"ref-1": decide(TEXT, FIELDS, by_doi(record), FakeNli())}, 100.0).body(
        "POST", "verificaciones"
    )

    assert row["score_crossref"] is None
