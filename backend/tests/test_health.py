from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_responde_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"


def test_la_raiz_responde_como_la_ruta_de_salud() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_en_produccion_no_se_publica_la_documentacion() -> None:
    settings = Settings(_env_file=None, environment="production")
    client = TestClient(create_app(settings))

    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
    assert client.get("/health").status_code == 200


def test_en_desarrollo_la_documentacion_sigue_disponible() -> None:
    client = TestClient(create_app(Settings(_env_file=None, environment="development")))

    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
