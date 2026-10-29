"""Cliente HTTP compartido para hablar con Supabase usando la clave de servicio.

La clave de servicio ignora RLS: solo la usa el backend, nunca el frontend.
"""

from functools import lru_cache
from typing import Any

import httpx

TIMEOUT_SECONDS = 20.0


class SupabaseUnavailableError(Exception):
    """Supabase no respondió o rechazó la operación."""


def service_headers(service_key: str) -> dict[str, str]:
    """Encabezados de autenticación con la clave de servicio.

    Las claves nuevas (sb_secret_...) van solo en apikey; las antiguas
    (service_role, un JWT) también en Authorization.
    """
    headers = {"apikey": service_key}
    if service_key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {service_key}"
    return headers


@lru_cache
def shared_client(service_key: str) -> httpx.Client:
    """Un solo cliente por clave: reutiliza las conexiones entre peticiones."""
    return httpx.Client(headers=service_headers(service_key), timeout=TIMEOUT_SECONDS)


def ensure_ok(response: httpx.Response) -> httpx.Response:
    """Convierte cualquier respuesta de error de Supabase en una sola excepción."""
    if response.is_error:
        raise SupabaseUnavailableError(f"Supabase respondió {response.status_code}")
    return response


def send(client: httpx.Client, method: str, url: str, **options: Any) -> list[dict[str, Any]]:
    """Petición a la API de datos; devuelve las filas de la respuesta (o ninguna)."""
    try:
        response = client.request(method, url, **options)
    except httpx.HTTPError as error:
        raise SupabaseUnavailableError(str(error)) from error
    ensure_ok(response)
    return response.json() if response.content else []
