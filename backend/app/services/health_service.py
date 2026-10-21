"""Servicio que informa el estado de la API."""

from app.core.config import Settings
from app.schemas.health import HealthResponse


class HealthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def check(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=self._settings.app_version,
            environment=self._settings.environment,
        )
