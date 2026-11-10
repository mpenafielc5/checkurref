"""Estadísticas generales de cada rol (HU-18). Sin Supabase real."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.statistics import get_statistics_service
from app.main import create_app
from app.repositories.batches import StoredWork
from app.repositories.statistics import SupabaseStatisticsRepository
from app.repositories.supabase_http import SupabaseUnavailableError
from app.services.statistics_service import StatisticsService
from tests.session_helpers import USER_ID, act_as, bearer, make_token, trust_test_tokens

OWNER = UUID(USER_ID)
NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)
REST_URL = "https://proyecto.supabase.co/rest/v1"


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
        authors=(),
        created_at=NOW,
        status=status,
        progress=100,
        total_references=len(verdicts),
        norm="APA",
        index=index,
        error_message=None,
        verdicts=verdicts,
        different_fields=fields,
    )


class FakeStatistics:
    def __init__(self, works: list[StoredWork] | None = None, verdicts: Any = None) -> None:
        self.works = works or []
        self.verdicts = verdicts or {}
        self.asked: list[tuple[UUID, bool]] = []

    def works_of(self, owner_id: UUID, in_batches: bool) -> list[StoredWork]:
        self.asked.append((owner_id, in_batches))
        return self.works

    def count_batches(self, teacher_id: UUID) -> int:
        return 3 if teacher_id == OWNER else 0

    def count_documents(self) -> int:
        return 12

    def count_references(self) -> int:
        return 200

    def count_verdict(self, verdict: str) -> int:
        return self.verdicts.get(verdict, 0)


class FakeProfiles:
    def count(self, role: str | None = None) -> int:
        return {None: 10, "estudiante": 7, "docente": 2, "admin": 1}[role]

    def get(self, profile_id: UUID) -> Any:
        return None

    def list_profiles(self, offset: int, limit: int, search: str = "", role: Any = None) -> Any:
        raise NotImplementedError

    def update(self, profile_id: UUID, changes: dict[str, Any]) -> Any:
        raise NotImplementedError


def service(statistics: FakeStatistics) -> StatisticsService:
    return StatisticsService(statistics, FakeProfiles())


def test_el_estudiante_ve_el_resumen_de_sus_trabajos_terminados() -> None:
    statistics = FakeStatistics(
        [
            work(index=80.0, verdicts=("verificada", "discrepancia"), fields=("anio", "anio")),
            work(index=60.0, verdicts=("verificada", None), fields=("titulo",)),
        ]
    )

    result = service(statistics).for_student(OWNER)

    assert statistics.asked == [(OWNER, False)]
    assert result.works == 2
    assert result.references == 4
    assert result.average_index == 70
    assert result.counts.verificada == 2
    assert result.counts.discrepancia == 1
    assert result.counts.error_consulta == 1
    assert result.most_different_field == "anio"


def test_solo_cuentan_los_analisis_terminados() -> None:
    statistics = FakeStatistics(
        [
            work(index=50.0, verdicts=("verificada",)),
            work("verificando", index=None, verdicts=("contradiccion",), fields=("doi",)),
            work("error", index=None, verdicts=("contradiccion",)),
        ]
    )

    result = service(statistics).for_student(OWNER)

    assert result.works == 1
    assert result.references == 1
    assert result.average_index == 50
    assert result.counts.contradiccion == 0
    assert result.most_different_field is None


def test_sin_trabajos_no_inventa_un_promedio() -> None:
    result = service(FakeStatistics()).for_student(OWNER)

    assert result.works == 0
    assert result.average_index is None
    assert result.most_different_field is None


def test_el_docente_ve_sus_lotes_y_los_trabajos_de_riesgo_alto() -> None:
    statistics = FakeStatistics(
        [
            work(index=50.0, verdicts=("discrepancia",)),  # índice bajo
            work(index=95.0, verdicts=("verificada", "contradiccion")),  # con contradicción
            work(index=95.0, verdicts=("verificada",)),
            work("verificando", index=10.0, verdicts=("contradiccion",)),
        ]
    )

    result = service(statistics).for_teacher(OWNER)

    assert statistics.asked == [(OWNER, True)]
    assert result.batches == 3
    assert result.works == 3
    assert result.references == 4
    assert result.counts.verificada == 2
    assert result.high_risk_works == 2


def test_el_administrador_ve_las_cifras_globales_y_los_errores_de_consulta() -> None:
    statistics = FakeStatistics(verdicts={"verificada": 150, "contradiccion": 10})

    result = service(statistics).for_admin()

    assert statistics.asked == []  # no necesita traer los trabajos
    assert result.users.model_dump() == {"todos": 10, "estudiante": 7, "docente": 2, "admin": 1}
    assert result.documents == 12
    assert result.references == 200
    assert result.counts.verificada == 150
    assert result.counts.error_consulta == 40


class FailingStatistics(FakeStatistics):
    def count_verdict(self, verdict: str) -> int:
        if verdict == "sin_respaldo":
            raise SupabaseUnavailableError("Supabase respondió 500")
        return super().count_verdict(verdict)


def test_los_conteos_se_hacen_a_la_vez_y_un_fallo_no_se_pierde() -> None:
    # Los conteos corren en paralelo; si uno falla, la ruta igual debe responder 503.
    with pytest.raises(SupabaseUnavailableError):
        service(FailingStatistics()).for_admin()


# --- Repositorio -----------------------------------------------------------------------------


def repository(handler: Any) -> SupabaseStatisticsRepository:
    return SupabaseStatisticsRepository(
        REST_URL, httpx.Client(transport=httpx.MockTransport(handler))
    )


@pytest.mark.parametrize(("in_batches", "expected"), [(True, "not.is.null"), (False, "is.null")])
def test_el_repositorio_solo_lee_los_trabajos_del_dueno(in_batches: bool, expected: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["propietario_id"] == f"eq.{OWNER}"
        assert request.url.params["lote_id"] == expected
        return httpx.Response(200, json=[])

    assert repository(handler).works_of(OWNER, in_batches) == []


def test_el_repositorio_cuenta_sin_traer_las_filas() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Prefer"] == "count=exact"
        assert request.url.params["limit"] == "1"
        assert request.url.params["veredicto"] == "eq.verificada"
        assert request.url.params["t_referencias.t_analisis.estado"] == "eq.completado"
        return httpx.Response(200, json=[{"id": "x"}], headers={"Content-Range": "0-0/57"})

    assert repository(handler).count_verdict("verificada") == 57


# --- Ruta ------------------------------------------------------------------------------------


def client_as(role: str, statistics: FakeStatistics | None = None) -> TestClient:
    app = create_app()
    trust_test_tokens(app)
    act_as(app, role)
    subject = service(statistics or FakeStatistics([work(verdicts=("verificada",))]))
    app.dependency_overrides[get_statistics_service] = lambda: subject
    return TestClient(app)


def auth() -> dict[str, str]:
    return bearer(make_token())


@pytest.mark.parametrize(
    ("role", "expected"),
    [("estudiante", "average_index"), ("docente", "high_risk_works"), ("admin", "users")],
)
def test_cada_rol_recibe_sus_propias_cifras(role: str, expected: str) -> None:
    response = client_as(role).get("/estadisticas", headers=auth())

    assert response.status_code == 200
    assert response.json()["role"] == role
    assert expected in response.json()


def test_sin_sesion_no_hay_estadisticas() -> None:
    assert client_as("estudiante").get("/estadisticas").status_code == 401


def test_un_parametro_no_permite_pedir_las_cifras_de_otra_cuenta() -> None:
    statistics = FakeStatistics()

    client_as("estudiante", statistics).get(
        "/estadisticas", params={"usuario": str(uuid4())}, headers=auth()
    )

    assert statistics.asked == [(OWNER, False)]
