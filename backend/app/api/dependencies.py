"""Dependencias compartidas por las rutas: la sesión del usuario."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.security import (
    AuthenticatedUser,
    InvalidSessionError,
    SessionVerificationUnavailableError,
    TokenVerifier,
    jwks_key_resolver,
)

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="access_token de la sesión de Supabase.",
)


@lru_cache
def _build_verifier(auth_url: str) -> TokenVerifier:
    # Un solo validador por proyecto: así la clave pública se descarga una vez.
    return TokenVerifier(issuer=auth_url, key_resolver=jwks_key_resolver(auth_url))


def get_token_verifier(settings: Annotated[Settings, Depends(get_settings)]) -> TokenVerifier:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La API no tiene configurada SUPABASE_URL.",
        )
    return _build_verifier(settings.supabase_auth_url)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> AuthenticatedUser:
    """Usuario de la sesión. Toda ruta protegida declara esta dependencia."""
    if credentials is None:
        raise _unauthorized("Falta el token de sesión.")
    try:
        return verifier.verify(credentials.credentials)
    except InvalidSessionError:
        raise _unauthorized("La sesión no es válida o ya venció.") from None
    except SessionVerificationUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo verificar la sesión. Intenta de nuevo.",
        ) from None


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
