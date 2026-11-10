"""Comparación de los motores en el Laboratorio (T16, HU-13). Sin AnyStyle ni spaCy reales."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes.lab import get_lab_service
from app.extraction.base import Author, Engine, ExtractedFields, ExtractionError, ReferenceExtractor
from app.main import create_app
from app.services.lab_service import LabService
from tests.session_helpers import act_as, bearer, make_token, trust_test_tokens

REFERENCE = "Pérez, M. y López, J. (2021). Redes neuronales. Revista Andina, 14(2), 45-60."
FULL = ExtractedFields(
    authors=(Author("Pérez", "M."), Author("López", "J.")),
    year=2021,
    title="Redes neuronales",
    container="Revista Andina",
    volume="14",
    pages="45-60",
    doi="10.1234/ab",
)


class Fixed(ReferenceExtractor):
    def __init__(self, engine: Engine, fields: ExtractedFields | None) -> None:
        self.engine = engine
        self._fields = fields

    def extract(self, reference: str) -> ExtractedFields:
        if self._fields is None:
            raise ExtractionError("No se encontró el comando anystyle (anystyle-cli)")
        return self._fields


def lab(first: ExtractedFields | None, second: ExtractedFields | None) -> LabService:
    return LabService([Fixed(Engine.ANYSTYLE, first), Fixed(Engine.SPACY, second)])


def test_muestra_la_salida_de_cada_motor() -> None:
    result = lab(FULL, FULL).compare(REFERENCE)

    anystyle, spacy = result.engines
    assert (anystyle.engine, spacy.engine) == ("anystyle", "spacy")
    assert anystyle.fields is not None
    assert anystyle.fields.autores == "Pérez, M.; López, J."
    assert anystyle.fields.anio == "2021"


def test_si_coinciden_no_hay_campos_que_resaltar() -> None:
    result = lab(FULL, FULL).compare(REFERENCE)

    assert result.different_fields == []
    assert result.matching_fields == result.compared_fields == 7


def test_resalta_los_campos_en_los_que_no_coinciden() -> None:
    partial = ExtractedFields(
        authors=FULL.authors,
        year=2020,  # distinto
        title="Redes neuronales.",  # el punto final no es una diferencia
        pages="45-60",
        doi="https://doi.org/10.1234/AB",  # el mismo DOI en otra forma
    )

    result = lab(FULL, partial).compare(REFERENCE)

    assert result.different_fields == ["anio", "contenedor", "volumen"]
    assert (result.compared_fields, result.matching_fields) == (7, 4)


def test_si_un_motor_falla_se_dice_y_no_se_reemplaza() -> None:
    result = lab(None, FULL).compare(REFERENCE)

    anystyle, spacy = result.engines
    assert anystyle.fields is None
    assert anystyle.error
    assert spacy.fields is not None
    assert result.different_fields == []  # sin dos resultados no hay nada que comparar


def client_as(role: str) -> TestClient:
    app = create_app()
    trust_test_tokens(app)
    act_as(app, role)
    app.dependency_overrides[get_lab_service] = lambda: lab(FULL, FULL)
    return TestClient(app)


@pytest.mark.parametrize("role", ["estudiante", "docente"])
def test_solo_el_administrador_usa_el_laboratorio(role: str) -> None:
    response = client_as(role).post(
        "/laboratorio/comparar",
        json={"reference": REFERENCE},
        headers=bearer(make_token()),
    )

    assert response.status_code == 403


def test_sin_sesion_no_se_usa_el_laboratorio() -> None:
    response = client_as("admin").post("/laboratorio/comparar", json={"reference": REFERENCE})

    assert response.status_code == 401


@pytest.mark.parametrize("text", ["corta", "x" * 2001])
def test_el_texto_debe_tener_el_largo_de_una_referencia(text: str) -> None:
    response = client_as("admin").post(
        "/laboratorio/comparar", json={"reference": text}, headers=bearer(make_token())
    )

    assert response.status_code == 422


def test_ruta_compara() -> None:
    response = client_as("admin").post(
        "/laboratorio/comparar", json={"reference": REFERENCE}, headers=bearer(make_token())
    )

    assert response.status_code == 200
    assert [item["engine"] for item in response.json()["engines"]] == ["anystyle", "spacy"]
