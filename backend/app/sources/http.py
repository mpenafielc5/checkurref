"""Consultas HTTP a las fuentes: concurrencia, ritmo y reintentos.

Crossref y OpenAlex limitan cuántas consultas aceptan. Cada cliente limita las
consultas simultáneas (semáforo) y las que empiezan por segundo (RateLimiter),
y ante 429, 502 o 503 reintenta con espera exponencial, respetando la cabecera
Retry-After cuando la fuente la envía.
"""

import asyncio
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

RETRYABLE_STATUS = {429, 502, 503}
# Solo el 404 significa que la fuente no tiene la obra. Cualquier otro error (un
# 400 por una consulta mal armada, por ejemplo) es un fallo de consulta: tratarlo
# como "no encontrada" llevaría a un veredicto sin respaldo que no corresponde.
NOT_FOUND_STATUS = {404}
ATTEMPTS = 4
MAX_WAIT_SECONDS = 60.0


class QueryFailedError(Exception):
    """La fuente no respondió después de los reintentos.

    La referencia queda como error de consulta, no como No verificable: no se
    sabe si la obra existe.
    """


class RetryableResponseError(Exception):
    def __init__(self, status: int, retry_after: float | None) -> None:
        super().__init__(f"la fuente respondió {status}")
        self.retry_after = retry_after


class RateLimiter:
    """Separa el inicio de las consultas para no pasar de `per_second`."""

    def __init__(self, per_second: float) -> None:
        self._interval = 1 / per_second
        self._next_start = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = asyncio.get_running_loop().time()
            if self._next_start > now:
                await asyncio.sleep(self._next_start - now)
                now = self._next_start
            self._next_start = now + self._interval


class SourceHttp:
    """GET con límite de concurrencia, ritmo y reintentos, compartido por los adaptadores."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        max_concurrent: int,
        per_second: float,
        backoff_seconds: float = 1.0,
    ) -> None:
        self._client = client
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._limiter = RateLimiter(per_second)
        self._backoff = wait_exponential(multiplier=backoff_seconds, max=MAX_WAIT_SECONDS)

    async def get_json(self, url: str, params: dict[str, str] | None = None) -> Any | None:
        """Cuerpo JSON de la respuesta; None si la fuente no tiene la obra."""
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(ATTEMPTS),
                wait=self._wait,
                retry=retry_if_exception_type((RetryableResponseError, httpx.TransportError)),
                reraise=True,
            ):
                with attempt:
                    response = await self._send(url, params)
        except (RetryableResponseError, httpx.TransportError) as error:
            raise QueryFailedError(f"{url}: {error}") from error

        if response.status_code in NOT_FOUND_STATUS:
            return None
        if response.is_error:
            raise QueryFailedError(f"{url}: la fuente respondió {response.status_code}")
        return response.json()

    async def _send(self, url: str, params: dict[str, str] | None) -> httpx.Response:
        async with self._semaphore:
            await self._limiter.wait()
            response = await self._client.get(url, params=params)
        if response.status_code in RETRYABLE_STATUS:
            raise RetryableResponseError(response.status_code, _retry_after(response))
        return response

    def _wait(self, state: RetryCallState) -> float:
        error = state.outcome.exception() if state.outcome else None
        if isinstance(error, RetryableResponseError) and error.retry_after is not None:
            return min(error.retry_after, MAX_WAIT_SECONDS)
        return self._backoff(state)


def _retry_after(response: httpx.Response) -> float | None:
    # Solo la forma en segundos: Crossref y OpenAlex no envían una fecha.
    value = response.headers.get("Retry-After", "")
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None
