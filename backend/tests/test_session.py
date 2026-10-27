"""Validación del token de Supabase en las rutas protegidas (GET /me)."""

import time
from collections.abc import Iterator

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.api.dependencies import get_token_verifier
from app.core.config import Settings, get_settings
from app.core.security import TokenVerifier
from app.main import create_app
from tests.session_helpers import ISSUER, USER_ID, bearer, make_token, trust_test_tokens


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    trust_test_tokens(app)
    yield TestClient(app)


def test_token_valido_devuelve_el_usuario(client: TestClient) -> None:
    response = client.get("/me", headers=bearer(make_token()))

    assert response.status_code == 200
    assert response.json() == {"id": USER_ID, "email": "estudiante@unemi.edu.ec"}


def test_sin_token_responde_401(client: TestClient) -> None:
    response = client.get("/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("no-es-un-token", id="mal formado"),
        pytest.param(make_token(exp=int(time.time()) - 60), id="vencido"),
        pytest.param(make_token(aud="anon"), id="otra audiencia"),
        pytest.param(make_token(iss="https://otro.supabase.co/auth/v1"), id="otro emisor"),
        pytest.param(make_token(key=ec.generate_private_key(ec.SECP256R1())), id="otra clave"),
        pytest.param(
            make_token(key="secreto-compartido-de-32-bytes-o-mas", algorithm="HS256"),
            id="algoritmo cambiado",
        ),
        pytest.param(make_token(sub="no-es-un-uuid"), id="sujeto invalido"),
    ],
)
def test_token_invalido_responde_401(client: TestClient, token: str) -> None:
    response = client.get("/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "La sesión no es válida o ya venció."


def test_sin_acceso_a_la_clave_publica_responde_503() -> None:
    def unreachable(_token: str) -> jwt.PyJWK:
        raise jwt.PyJWKClientConnectionError("sin conexión")

    app = create_app()
    app.dependency_overrides[get_token_verifier] = lambda: TokenVerifier(
        issuer=ISSUER, key_resolver=unreachable
    )

    response = TestClient(app).get("/me", headers=bearer(make_token()))

    assert response.status_code == 503


def test_sin_supabase_url_responde_503() -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, supabase_url="")

    response = TestClient(app).get("/me", headers=bearer(make_token()))

    assert response.status_code == 503
    assert "SUPABASE_URL" in response.json()["detail"]


def test_health_sigue_siendo_publica(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
