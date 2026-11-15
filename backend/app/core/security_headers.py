"""Cabeceras de seguridad en todas las respuestas de la API."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

# La API solo responde JSON y PDF: nada se incrusta, se adivina ni se ejecuta.
BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}
# En producción no se publica /docs, así que se puede prohibir todo contenido activo
# (en desarrollo, la página de /docs carga sus scripts desde un CDN).
PRODUCTION_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


def add_security_headers(app: FastAPI, production: bool) -> None:
    headers = BASE_HEADERS | (PRODUCTION_HEADERS if production else {})

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in headers.items():
            response.headers.setdefault(name, value)
        return response
