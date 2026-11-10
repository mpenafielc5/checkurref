"""Acceso por rol y gestión de usuarios (T16, HU-11). Sin Supabase real."""

import json
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.profiles import SupabaseProfileRepository
from app.repositories.supabase_http import SupabaseUnavailableError
from app.services.user_service import (
    AccountDisabledError,
    UserChangeRejectedError,
    UserNotFoundError,
    UserService,
)
from tests.session_helpers import (
    USER_ID,
    FakeProfiles,
    act_as,
    bearer,
    make_token,
    trust_test_tokens,
)

ADMIN = UUID(USER_ID)
REST_URL = "https://proyecto.supabase.co/rest/v1"
ROW = {
    "id": USER_ID,
    "nombre_completo": "Ana Torres",
    "correo": "atorres@unemi.edu.ec",
    "rol": "docente",
    "activo": True,
    "creado_en": "2026-11-01T10:00:00.5+00:00",
}


def service(role: str = "admin") -> tuple[UserService, FakeProfiles]:
    profiles = FakeProfiles(role)
    return UserService(profiles), profiles


# --- Reglas ---------------------------------------------------------------------------------


def test_una_cuenta_desactivada_o_sin_perfil_no_pasa() -> None:
    users, profiles = service()
    disabled = uuid4()
    profiles.add(disabled, "estudiante", active=False)

    assert users.active_profile(ADMIN).role == "admin"
    with pytest.raises(AccountDisabledError):
        users.active_profile(disabled)
    with pytest.raises(AccountDisabledError):
        users.active_profile(uuid4())


def test_cambia_el_rol_entre_estudiante_y_docente() -> None:
    users, profiles = service()
    target = uuid4()
    profiles.add(target, "estudiante")

    assert users.update_user(ADMIN, target, "docente", None).role == "docente"
    assert users.update_user(ADMIN, target, "estudiante", None).role == "estudiante"


def test_desactivar_y_reactivar_conserva_el_rol() -> None:
    users, profiles = service()
    target = uuid4()
    profiles.add(target, "docente")

    assert users.update_user(ADMIN, target, None, False).active is False
    updated = users.update_user(ADMIN, target, None, True)
    assert (updated.active, updated.role) == (True, "docente")


@pytest.mark.parametrize(("role", "active"), [("estudiante", None), (None, False)])
def test_el_administrador_no_se_cambia_a_si_mismo(role: str | None, active: bool | None) -> None:
    users, profiles = service()

    with pytest.raises(UserChangeRejectedError, match="tu propio rol"):
        users.update_user(ADMIN, ADMIN, role, active)
    assert profiles.items[ADMIN].role == "admin"
    assert profiles.items[ADMIN].active is True


def test_otra_cuenta_de_administrador_no_se_modifica() -> None:
    users, profiles = service()
    other = uuid4()
    profiles.add(other, "admin")

    with pytest.raises(UserChangeRejectedError, match="administrador"):
        users.update_user(ADMIN, other, None, False)
    assert profiles.items[other].active is True


def test_un_cambio_vacio_o_de_un_usuario_inexistente_se_rechaza() -> None:
    users, _ = service()

    with pytest.raises(UserChangeRejectedError):
        users.update_user(ADMIN, uuid4(), None, None)
    with pytest.raises(UserNotFoundError):
        users.update_user(ADMIN, uuid4(), "docente", None)


def test_la_lista_pagina_de_20_en_20_y_cuenta_por_rol() -> None:
    users, profiles = service()
    for _ in range(24):
        profiles.add(uuid4(), "estudiante")
    profiles.add(uuid4(), "docente")

    page = users.list_users(2, role="estudiante")

    assert (len(page.items), page.total, page.total_pages) == (4, 24, 2)
    assert page.counts.model_dump() == {"todos": 26, "estudiante": 24, "docente": 1, "admin": 1}


def test_la_busqueda_es_por_correo_y_no_cambia_los_totales() -> None:
    users, profiles = service()
    target = uuid4()
    wanted = profiles.add(target, "docente")
    profiles.add(uuid4(), "estudiante")

    page = users.list_users(1, search=wanted.email[:12].upper())

    assert [item.id for item in page.items] == [target]
    assert page.counts.todos == 3


# --- Rutas ----------------------------------------------------------------------------------


def app_as(role: str, active: bool = True) -> tuple[TestClient, FakeProfiles]:
    app = create_app()
    trust_test_tokens(app)
    profiles = act_as(app, role, active)
    return TestClient(app), profiles


@pytest.fixture
def anonymous() -> Iterator[TestClient]:
    app = create_app()
    trust_test_tokens(app)
    act_as(app)
    yield TestClient(app)


def auth() -> dict[str, str]:
    return bearer(make_token())


def test_sin_sesion_no_se_entra(anonymous: TestClient) -> None:
    assert anonymous.get("/usuarios").status_code == 401
    assert anonymous.patch(f"/usuarios/{uuid4()}", json={"active": False}).status_code == 401


@pytest.mark.parametrize("role", ["estudiante", "docente"])
def test_solo_el_administrador_usa_estas_rutas(role: str) -> None:
    client, profiles = app_as(role)
    target = uuid4()
    profiles.add(target, "estudiante")

    assert client.get("/usuarios", headers=auth()).status_code == 403
    response = client.patch(f"/usuarios/{target}", json={"role": "docente"}, headers=auth())
    assert response.status_code == 403
    assert profiles.items[target].role == "estudiante"  # la API no aplicó el cambio


def test_una_cuenta_desactivada_no_usa_la_api() -> None:
    client, _ = app_as("admin", active=False)

    response = client.get("/usuarios", headers=auth())

    assert response.status_code == 403
    assert "desactivada" in response.json()["detail"]


def test_ruta_cambia_el_rol_y_lista() -> None:
    client, profiles = app_as("admin")
    target = uuid4()
    profiles.add(target, "estudiante")

    changed = client.patch(f"/usuarios/{target}", json={"role": "docente"}, headers=auth())
    listed = client.get("/usuarios", params={"rol": "docente"}, headers=auth())

    assert changed.status_code == 200
    assert changed.json()["role"] == "docente"
    assert [item["id"] for item in listed.json()["items"]] == [str(target)]


def test_ruta_no_permite_dar_el_rol_de_administrador() -> None:
    client, profiles = app_as("admin")
    target = uuid4()
    profiles.add(target, "estudiante")

    response = client.patch(f"/usuarios/{target}", json={"role": "admin"}, headers=auth())

    assert response.status_code == 422
    assert profiles.items[target].role == "estudiante"


def test_ruta_rechaza_cambiar_la_propia_cuenta_y_avisa_si_no_existe() -> None:
    client, _ = app_as("admin")

    own = client.patch(f"/usuarios/{ADMIN}", json={"active": False}, headers=auth())
    missing = client.patch(f"/usuarios/{uuid4()}", json={"active": False}, headers=auth())

    assert own.status_code == 409
    assert "propio rol" in own.json()["detail"]
    assert missing.status_code == 404


# --- Repositorio ----------------------------------------------------------------------------


def repository(handler: Any) -> SupabaseProfileRepository:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SupabaseProfileRepository(REST_URL, client)


def test_el_repositorio_lee_el_perfil() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["id"] == f"eq.{USER_ID}"
        return httpx.Response(200, json=[ROW])

    profile = repository(handler).get(ADMIN)

    assert profile is not None
    assert (profile.name, profile.role, profile.active) == ("Ana Torres", "docente", True)


def test_el_repositorio_busca_sin_comodines_y_lee_el_total() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["correo"] == "ilike.*torres*"
        assert request.url.params["rol"] == "eq.docente"
        assert request.url.params["order"] == "correo.asc"
        assert request.headers["prefer"] == "count=exact"
        return httpx.Response(200, json=[ROW], headers={"content-range": "0-0/7"})

    page = repository(handler).list_profiles(0, 20, " *tor%res ", "docente")

    assert page.total == 7
    assert page.items[0].email == "atorres@unemi.edu.ec"


def test_el_repositorio_guarda_solo_lo_que_cambia() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.params["id"] == f"eq.{USER_ID}"
        assert json.loads(request.content) == {"activo": False}
        return httpx.Response(200, json=[{**ROW, "activo": False}])

    updated = repository(handler).update(ADMIN, {"activo": False})

    assert updated is not None
    assert updated.active is False


def test_si_supabase_falla_la_ruta_avisa() -> None:
    client, profiles = app_as("admin")

    def broken(*_: Any, **__: Any) -> Any:
        raise SupabaseUnavailableError("caída")

    profiles.list_profiles = broken  # type: ignore[method-assign]

    assert client.get("/usuarios", headers=auth()).status_code == 503
