"""Medición de los motores contra el estándar de oro (HU-12). Sin AnyStyle ni Supabase reales."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.lab import get_benchmark_service
from app.benchmark.gold_set import FIELDS, GoldReference, from_database_row, to_database_row
from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import Author, Engine, ExtractedFields, ExtractionError, ReferenceExtractor
from app.main import create_app
from app.repositories.benchmark_runs import StoredScore, SupabaseBenchmarkRunRepository
from app.repositories.gold_set import SupabaseGoldSetRepository
from app.services.benchmark_service import BenchmarkRejectedError, BenchmarkService
from tests.session_helpers import act_as, bearer, make_token, trust_test_tokens

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
REST_URL = "https://proyecto.supabase.co/rest/v1"
ANNOTATED = {
    "autores": "Pérez",
    "anio": "2021",
    "titulo": "Redes neuronales",
    "doi": "10.1234/ab",
}
RIGHT = ExtractedFields(
    authors=(Author("Pérez", "M."),), year=2021, title="Redes neuronales", doi="10.1234/ab"
)
PARTIAL = ExtractedFields(authors=(Author("Pérez", "M."),), year=2021)


def gold(norm: str = "APA", altered: bool = False) -> GoldReference:
    return GoldReference(
        id="R001",
        text="Pérez, M. (2021). Redes neuronales. https://doi.org/10.1234/ab",
        norm=norm,
        work_type="articulo",
        fields=dict(ANNOTATED),
        altered=altered,
        alteration="anio" if altered else "",
    )


class Fixed(ReferenceExtractor):
    def __init__(
        self,
        engine: Engine,
        fields: ExtractedFields | None,
        available: bool = True,
        version: str = "1.0",
    ) -> None:
        self.engine = engine
        self._fields = fields
        self._available = available
        self._version = version
        self.texts: list[str] = []

    def extract(self, reference: str) -> ExtractedFields:
        self.texts.append(reference)
        if self._fields is None:
            raise ExtractionError("falló")
        return self._fields

    def available(self) -> bool:
        return self._available

    def version(self) -> str:
        return self._version


class FakeGold:
    def __init__(self, references: list[GoldReference]) -> None:
        self.references = references

    def load_all(self) -> list[GoldReference]:
        return self.references


class FakeRuns:
    def __init__(self) -> None:
        self.saved: list[StoredScore] = []

    def save(self, scores: list[StoredScore]) -> None:
        self.saved = [*scores, *self.saved]

    def recent(self, limit: int) -> list[StoredScore]:
        return self.saved[:limit]


def service(
    anystyle: Fixed | None = None,
    spacy: Fixed | None = None,
    references: list[GoldReference] | None = None,
    clock: Any = lambda: NOW,
) -> tuple[BenchmarkService, FakeRuns]:
    runs = FakeRuns()
    return (
        BenchmarkService(
            FakeGold([gold()] if references is None else references),
            runs,
            [anystyle or Fixed(Engine.ANYSTYLE, RIGHT), spacy or Fixed(Engine.SPACY, PARTIAL)],
            Engine.ANYSTYLE,
            clock,
        ),
        runs,
    )


def test_mide_cada_motor_por_campo_con_el_mismo_texto() -> None:
    anystyle = Fixed(Engine.ANYSTYLE, RIGHT)
    spacy = Fixed(Engine.SPACY, PARTIAL)
    subject, _ = service(anystyle, spacy)

    [run] = subject.run().runs

    assert anystyle.texts == spacy.texts == [gold().text]
    first, second = run.engines
    assert (first.engine, second.engine) == ("anystyle", "spacy")
    assert [item.field for item in first.fields] == list(FIELDS)
    title = next(item for item in second.fields if item.field == "titulo")
    assert (title.precision, title.recall, title.f1) == (0, 0, 0)
    assert next(item for item in first.fields if item.field == "titulo").f1 == 1


def test_la_regla_de_decision_elige_el_mayor_f1_en_los_campos_clave() -> None:
    subject, _ = service()

    [run] = subject.run().runs

    assert run.engines[0].key_f1 == 1
    assert run.engines[1].key_f1 == 0.5
    assert run.selected_engine == "anystyle"
    assert run.tie is False
    assert run.difference == 0.5


def test_con_menos_de_5_puntos_es_empate_y_se_mantiene_anystyle() -> None:
    subject, _ = service(Fixed(Engine.ANYSTYLE, PARTIAL), Fixed(Engine.SPACY, PARTIAL))

    [run] = subject.run().runs

    assert run.tie is True
    assert run.selected_engine == "anystyle"


def test_cada_medicion_se_guarda_con_su_fecha_y_la_version_de_cada_motor() -> None:
    subject, runs = service(
        Fixed(Engine.ANYSTYLE, RIGHT, version="anystyle 1.6.0"),
        Fixed(Engine.SPACY, PARTIAL, version="spacy 3.8.16"),
    )

    subject.run()

    assert len(runs.saved) == 2 * len(FIELDS)
    assert {row.executed_at for row in runs.saved} == {NOW}
    assert {(row.engine, row.version) for row in runs.saved} == {
        ("anystyle", "anystyle 1.6.0"),
        ("spacy", "spacy 3.8.16"),
    }
    assert {row.samples for row in runs.saved} == {1}


def test_sin_anystyle_se_detiene_y_no_se_reemplaza_por_spacy() -> None:
    spacy = Fixed(Engine.SPACY, PARTIAL)
    subject, runs = service(Fixed(Engine.ANYSTYLE, RIGHT, available=False), spacy)

    with pytest.raises(BenchmarkRejectedError, match="AnyStyle no está disponible"):
        subject.run()

    assert runs.saved == []
    assert spacy.texts == []


def test_si_un_motor_no_procesa_ninguna_referencia_no_se_guarda() -> None:
    subject, runs = service(Fixed(Engine.ANYSTYLE, None))

    with pytest.raises(BenchmarkRejectedError, match="AnyStyle no pudo procesar"):
        subject.run()

    assert runs.saved == []


def test_sin_referencias_reales_no_se_mide() -> None:
    subject, runs = service(references=[gold(altered=True)])

    with pytest.raises(BenchmarkRejectedError, match="no tiene referencias reales"):
        subject.run()

    assert runs.saved == []


def test_el_resumen_cuenta_el_estandar_y_no_mezcla_las_alteradas() -> None:
    subject, _ = service(references=[gold("APA"), gold("IEEE"), gold("IEEE", altered=True)])

    overview = subject.overview()

    assert overview.runs == []
    assert overview.gold_set.model_dump() == {"total": 3, "real": 2, "apa": 1, "ieee": 1}
    assert overview.engine_in_use == "anystyle"
    assert overview.key_fields == ["titulo", "autores", "anio", "doi"]
    assert overview.tie_margin == 0.05


def test_las_mediciones_llegan_de_la_mas_reciente_a_la_mas_antigua() -> None:
    moments = iter([NOW, NOW + timedelta(days=1)])
    subject, _ = service(clock=lambda: next(moments))

    subject.run()
    runs = subject.run().runs

    assert [run.executed_at for run in runs] == [NOW + timedelta(days=1), NOW]


# --- Motores ---------------------------------------------------------------------------------


def test_anystyle_sabe_si_esta_instalado_y_lee_su_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(*_args: Any, **_kwargs: Any) -> Any:
        class Done:
            returncode = 0
            stdout = b"anystyle version 1.6.0 (cli 1.5.0, data 1.3.0)\n"

        return Done()

    monkeypatch.setattr("app.extraction.anystyle.shutil.which", lambda name: name)
    extractor = AnyStyleExtractor(run=run)

    assert extractor.available() is True
    assert extractor.version() == "anystyle version 1.6.0 (cli 1.5.0, data 1.3.0)"

    monkeypatch.setattr("app.extraction.anystyle.shutil.which", lambda _name: None)

    assert extractor.available() is False
    assert extractor.version() is None


# --- Repositorios ----------------------------------------------------------------------------


def test_el_estandar_de_oro_se_lee_de_la_base_como_se_guardo() -> None:
    original = gold(altered=True)
    restored = from_database_row(json.loads(json.dumps(to_database_row(original))))

    assert restored.text == original.text
    assert restored.norm == "APA"
    assert restored.altered is True
    assert restored.value("titulo") == "Redes neuronales"
    assert restored.value("volumen") == ""
    assert restored.id == "R001"


def test_el_repositorio_del_estandar_lee_todas_las_filas() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "campos_anotados" in request.url.params["select"]
        return httpx.Response(200, json=[to_database_row(gold())])

    client = httpx.Client(transport=httpx.MockTransport(handler))

    [loaded] = SupabaseGoldSetRepository(REST_URL, client).load_all()

    assert loaded.text == gold().text


def test_el_repositorio_guarda_y_lee_las_filas_de_una_medicion() -> None:
    sent: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            sent.extend(json.loads(request.content))
            return httpx.Response(201)
        assert request.url.params["order"] == "ejecutado_en.desc"
        assert request.url.params["limit"] == "18"
        return httpx.Response(
            200,
            json=[
                {
                    "motor": "spacy",
                    "campo": "titulo",
                    "precision_score": "0.9500",
                    "recall_score": None,
                    "f1_score": "0.5000",
                    "total_muestras": 100,
                    "version_modelo": None,
                    "ejecutado_en": "2026-11-09T12:00:00+00:00",
                }
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    repository = SupabaseBenchmarkRunRepository(REST_URL, client)

    repository.save([StoredScore("spacy", "titulo", 2 / 3, 0.5, 0.57142, 100, "v" * 80, NOW)])
    [row] = repository.recent(18)

    assert sent[0]["precision_score"] == 0.6667
    assert sent[0]["f1_score"] == 0.5714
    assert len(sent[0]["version_modelo"]) == 60
    assert sent[0]["ejecutado_en"] == NOW.isoformat()
    assert (row.precision, row.recall, row.f1) == (0.95, 0, 0.5)
    assert row.executed_at == NOW


# --- Rutas -----------------------------------------------------------------------------------


def client_as(role: str, subject: BenchmarkService | None = None) -> TestClient:
    app = create_app()
    trust_test_tokens(app)
    act_as(app, role)
    app.dependency_overrides[get_benchmark_service] = lambda: subject or service()[0]
    return TestClient(app)


def auth() -> dict[str, str]:
    return bearer(make_token())


@pytest.mark.parametrize("role", ["estudiante", "docente"])
def test_solo_el_administrador_mide(role: str) -> None:
    client = client_as(role)

    assert client.get("/laboratorio/benchmark", headers=auth()).status_code == 403
    assert client.post("/laboratorio/benchmark", headers=auth()).status_code == 403


def test_ruta_mide_y_devuelve_el_resultado() -> None:
    client = client_as("admin")

    empty = client.get("/laboratorio/benchmark", headers=auth())
    response = client.post("/laboratorio/benchmark", headers=auth())

    assert empty.status_code == 200
    assert empty.json()["runs"] == []
    assert response.status_code == 200
    assert response.json()["runs"][0]["selected_engine"] == "anystyle"


def test_ruta_avisa_si_falta_un_motor() -> None:
    subject, _ = service(Fixed(Engine.ANYSTYLE, RIGHT, available=False))

    response = client_as("admin", subject).post("/laboratorio/benchmark", headers=auth())

    assert response.status_code == 409
    assert "AnyStyle no está disponible" in response.json()["detail"]
