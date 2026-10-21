"""Configuración de la aplicación, leída desde variables de entorno o del archivo .env."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CheckUrRef API"
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "test"] = "development"

    # Orígenes del frontend autorizados a llamar a la API (CORS).
    cors_origins: list[str] = ["http://localhost:3000"]

    # URL del proyecto de Supabase (pública). Los tokens de sesión se validan con
    # la clave pública del proyecto, así que no hace falta ningún secreto.
    supabase_url: str = ""

    @property
    def supabase_auth_url(self) -> str:
        """Dirección de Supabase Auth: emisor de los tokens y origen de sus claves."""
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de la configuración para toda la aplicación."""
    return Settings()
