"""Extractores de campos AnyStyle y spaCy con interfaz común (T07)."""

import json
import os
import shutil
import subprocess
import sys
from typing import Any

import pytest

from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import (
    EXTRACTION_FAILED,
    Author,
    Engine,
    ExtractedFields,
    ExtractionError,
    ReferenceExtractor,
)
from app.extraction.factory import create_extractor
from app.extraction.spacy_rules import SpacyExtractor

APA_JOURNAL = (
    "Pérez, M. y López Vera, J. A. (2021). Redes neuronales en la educación superior. "
    "Revista Andina, 8(1), 10-25. https://doi.org/10.1234/ra.2021.8"
)
IEEE_JOURNAL = (
    '[3] J. Pérez y M. López, "Redes neuronales en la educación superior," '
    "Rev. Andina, vol. 8, no. 1, pp. 10–25, 2021, doi: 10.1234/ra.2021.8."
)


# --- spaCy ----------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def spacy_extractor() -> SpacyExtractor:
    return SpacyExtractor()


def test_spacy_articulo_apa(spacy_extractor: SpacyExtractor) -> None:
    assert spacy_extractor.extract(APA_JOURNAL) == ExtractedFields(
        authors=(Author("Pérez", "M."), Author("López Vera", "J. A.")),
        year=2021,
        title="Redes neuronales en la educación superior",
        container="Revista Andina",
        volume="8",
        issue="1",
        pages="10-25",
        doi="10.1234/ra.2021.8",
    )


def test_spacy_articulo_ieee(spacy_extractor: SpacyExtractor) -> None:
    assert spacy_extractor.extract(IEEE_JOURNAL) == ExtractedFields(
        authors=(Author("Pérez", "J."), Author("López", "M.")),
        year=2021,
        title="Redes neuronales en la educación superior",
        container="Rev. Andina",
        volume="8",
        issue="1",
        pages="10–25",
        doi="10.1234/ra.2021.8",
    )


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        pytest.param(
            "Rivas, A., & Torres, L. (2020). Aprendizaje automático aplicado. Editorial UNEMI.",
            {
                "authors": (Author("Rivas", "A."), Author("Torres", "L.")),
                "year": 2020,
                "title": "Aprendizaje automático aplicado",
                "publisher": "Editorial UNEMI",
            },
            id="libro APA",
        ),
        pytest.param(
            "García, P. (2019). Lectura crítica. En J. Rivas (Ed.), Escritura académica "
            "(pp. 45-60). Editorial Universitaria.",
            {"title": "Lectura crítica", "container": "Escritura académica", "pages": "45-60"},
            id="capítulo APA",
        ),
        pytest.param(
            "Portal Educativo. (s.f). Guía de citas. Recuperado el 3 de mayo de 2026, de "
            "https://portal.example.org/guia",
            {"authors": (Author("Portal Educativo"),), "year": None, "title": "Guía de citas"},
            id="organización sin fecha",
        ),
        pytest.param(
            "Moreira, L. (2025). ¿Errores o fraude? Una revisión de dos décadas. "
            "Cientometría, 130(7), 3679–3706.",
            {
                "title": "¿Errores o fraude? Una revisión de dos décadas",
                "container": "Cientometría",
                "pages": "3679–3706",
            },
            id="título con subtítulo tras ?",
        ),
        pytest.param(
            '[1] S. Saroja; S. Haseena, "Requisitos funcionales," en Proc. Congreso de '
            "Ingeniería, Lima, Perú, 2023, pp.71-86.",
            {
                "authors": (Author("Saroja", "S."), Author("Haseena", "S.")),
                "container": "Proc. Congreso de Ingeniería",
                "year": 2023,
                "pages": "71-86",
            },
            id="congreso IEEE",
        ),
        pytest.param(
            "[2] M. A. Delgado, Evaluación de fuentes académicas, 2.ª ed. Quito, Ecuador: "
            "Abya-Yala, 2018.",
            {
                "authors": (Author("Delgado", "M. A."),),
                "title": "Evaluación de fuentes académicas",
                "publisher": "Abya-Yala",
                "year": 2018,
            },
            id="libro IEEE",
        ),
    ],
)
def test_spacy_otros_tipos_de_obra(
    spacy_extractor: SpacyExtractor, reference: str, expected: dict[str, Any]
) -> None:
    fields = spacy_extractor.extract(reference)

    assert {key: getattr(fields, key) for key in expected} == expected


# --- Errores por referencia -----------------------------------------------------------------


class FailsOnSecond(ReferenceExtractor):
    engine = Engine.SPACY

    def extract(self, reference: str) -> ExtractedFields:
        if reference == "segunda":
            raise ValueError("texto inesperado")
        return ExtractedFields(title=reference)


def test_un_fallo_marca_solo_esa_referencia(caplog: pytest.LogCaptureFixture) -> None:
    results = FailsOnSecond().extract_all(["primera", "segunda", "tercera"])

    assert [result.fields.title if result.fields else None for result in results] == [
        "primera",
        None,
        "tercera",
    ]
    assert [result.error for result in results] == [None, EXTRACTION_FAILED, None]
    assert "no pudo extraer la referencia 2" in caplog.text


# --- AnyStyle -------------------------------------------------------------------------------

CSL_ITEM = {
    "author": [{"family": "Pérez", "given": "M."}, {"literal": "UNEMI"}],
    "date": ["2021"],
    "title": ["Redes neuronales en la educación superior"],
    "container-title": ["Revista Andina"],
    "volume": ["8"],
    "issue": ["1"],
    "pages": ["10–25"],
    "doi": ["10.1234/ra.2021.8"],
    "type": "article-journal",
}


class FakeAnyStyle:
    """Simula anystyle-cli: devuelve una entrada CSL por cada línea del archivo."""

    def __init__(self, fail_on: str | None = None, returncode: int = 0) -> None:
        self.fail_on = fail_on
        self.returncode = returncode
        self.calls: list[list[str]] = []
        self.inputs: list[list[str]] = []

    def __call__(self, args: list[str], **_options: Any) -> subprocess.CompletedProcess[bytes]:
        self.calls.append(args)
        with open(args[-1], encoding="utf-8") as file:
            lines = file.read().splitlines()
        self.inputs.append(lines)
        if self.fail_on in lines or self.returncode:
            return subprocess.CompletedProcess(args, self.returncode or 1, b"", b"error de Ruby")
        items = [{**CSL_ITEM, "title": [line]} for line in lines]
        return subprocess.CompletedProcess(args, 0, json.dumps(items).encode("utf-8"), b"")


def anystyle(fake: FakeAnyStyle) -> AnyStyleExtractor:
    # Un ejecutable que siempre existe, para no depender de que Ruby esté instalado.
    return AnyStyleExtractor(command=sys.executable, run=fake)


def test_anystyle_traduce_la_salida_csl() -> None:
    fields = anystyle(FakeAnyStyle()).extract("Redes neuronales")

    assert fields == ExtractedFields(
        authors=(Author("Pérez", "M."), Author("UNEMI")),
        year=2021,
        title="Redes neuronales",
        container="Revista Andina",
        volume="8",
        issue="1",
        pages="10–25",
        doi="10.1234/ra.2021.8",
    )


def test_anystyle_procesa_el_documento_en_una_sola_llamada() -> None:
    fake = FakeAnyStyle()

    results = anystyle(fake).extract_all(["Uno", "Dos\ncon salto", "Tres"])

    assert len(fake.calls) == 1
    assert fake.calls[0][1:5] == ["--stdout", "-f", "json", "parse"]
    assert fake.inputs[0] == ["Uno", "Dos con salto", "Tres"]  # una referencia por línea
    assert [result.fields.title if result.fields else None for result in results] == [
        "Uno",
        "Dos con salto",
        "Tres",
    ]


def test_anystyle_si_el_lote_falla_aisla_la_referencia_que_lo_causa() -> None:
    fake = FakeAnyStyle(fail_on="Rota")

    results = anystyle(fake).extract_all(["Uno", "Rota", "Tres"])

    assert [result.error for result in results] == [None, EXTRACTION_FAILED, None]
    assert len(fake.calls) == 4  # el lote y luego una por una


def test_anystyle_no_instalado() -> None:
    extractor = AnyStyleExtractor(command="comando-que-no-existe", run=FakeAnyStyle())

    with pytest.raises(ExtractionError, match="anystyle-cli"):
        extractor.extract("Uno")
    assert [result.error for result in extractor.extract_all(["Uno"])] == [EXTRACTION_FAILED]


def test_anystyle_que_no_responde() -> None:
    def slow(args: list[str], **_options: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(args, 120)

    with pytest.raises(ExtractionError, match="no respondió"):
        AnyStyleExtractor(command=sys.executable, run=slow).extract("Uno")


def test_anystyle_con_respuesta_ilegible() -> None:
    def broken(args: list[str], **_options: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args, 0, b"no es JSON", b"")

    with pytest.raises(ExtractionError, match="ilegible"):
        AnyStyleExtractor(command=sys.executable, run=broken).extract("Uno")


# En el CI (variable CI de GitHub Actions) AnyStyle siempre está instalado: ahí no se omite.
@pytest.mark.skipif(
    shutil.which("anystyle") is None and not os.environ.get("CI"),
    reason="anystyle-cli no está instalado",
)
def test_anystyle_real() -> None:
    fields = AnyStyleExtractor().extract(APA_JOURNAL)

    assert fields.year == 2021
    assert fields.doi is not None and "10.1234/ra.2021.8" in fields.doi


# --- Configuración --------------------------------------------------------------------------


def test_los_extractores_son_intercambiables_por_configuracion() -> None:
    anystyle_extractor = create_extractor(Engine.ANYSTYLE, anystyle_command="anystyle")
    spacy_extractor = create_extractor(Engine.SPACY)

    assert isinstance(anystyle_extractor, AnyStyleExtractor)
    assert isinstance(spacy_extractor, SpacyExtractor)
    assert {anystyle_extractor.engine, spacy_extractor.engine} == {Engine.ANYSTYLE, Engine.SPACY}
