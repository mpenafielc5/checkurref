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

    # Clave secreta de Supabase (sb_secret_... o service_role). Solo existe en el
    # servidor: con ella el backend guarda los PDF y crea los análisis.
    supabase_service_role_key: str = ""

    # Bucket privado de los PDF (migración 2) y modelo con el que se registran
    # los análisis nuevos hasta que el worker use el modelo NLI (T12).
    storage_bucket: str = "documentos"
    analysis_model_version: str = "bert-xnli-es-onnx-int8"

    # Extractor de campos de las referencias (T07): anystyle o spacy. AnyStyle
    # necesita Ruby y anystyle-cli; el comando se puede cambiar si no está en el PATH.
    extraction_engine: Literal["anystyle", "spacy"] = "anystyle"
    anystyle_command: str = "anystyle"

    # Fuentes (T08). Con el correo, Crossref atiende en su polite pool; la clave
    # gratuita de OpenAlex es opcional y multiplica por 10 su presupuesto diario.
    crossref_mailto: str = ""
    openalex_api_key: str = ""

    @property
    def supabase_rest_url(self) -> str:
        """Dirección de la API de datos (PostgREST) del proyecto."""
        return f"{self.supabase_url.rstrip('/')}/rest/v1"

    @property
    def supabase_storage_url(self) -> str:
        """Dirección de Supabase Storage, donde se guardan los PDF."""
        return f"{self.supabase_url.rstrip('/')}/storage/v1"

    @property
    def supabase_auth_url(self) -> str:
        """Dirección de Supabase Auth: emisor de los tokens y origen de sus claves."""
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de la configuración para toda la aplicación."""
    return Settings()
