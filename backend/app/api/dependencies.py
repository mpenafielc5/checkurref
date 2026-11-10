"""Dependencias compartidas por las rutas: la sesión, la cuenta activa y el rol."""

from collections.abc import Callable
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
from app.repositories.profiles import Profile, SupabaseProfileRepository
from app.repositories.supabase_http import SupabaseUnavailableError, shared_client
from app.services.user_service import AccountDisabledError, UserService

UNAVAILABLE = "No se pudo consultar la base de datos. Intenta de nuevo en unos minutos."
ACCOUNT_DISABLED = "Tu cuenta está desactivada. Comunícate con el administrador."
WRONG_ROLE = "Tu rol no tiene acceso a esta función."

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


def require_supabase(settings: Settings) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La API no tiene configurada la conexión con Supabase.",
        )


def get_user_service(settings: Annotated[Settings, Depends(get_settings)]) -> UserService:
    require_supabase(settings)
    client = shared_client(settings.supabase_service_role_key)
    return UserService(SupabaseProfileRepository(settings.supabase_rest_url, client))


def get_active_profile(
    user: CurrentUser,
    users: Annotated[UserService, Depends(get_user_service)],
) -> Profile:
    """Perfil de quien llama. Un token sigue vigente hasta una hora después de desactivar
    la cuenta: por eso el estado se consulta en cada petición y no se lee del token."""
    try:
        return users.active_profile(user.id)
    except AccountDisabledError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ACCOUNT_DISABLED) from None
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


ActiveUser = Annotated[Profile, Depends(get_active_profile)]


def _require_role(role: str) -> Callable[[Profile], Profile]:
    def check(profile: ActiveUser) -> Profile:
        if profile.role != role:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=WRONG_ROLE)
        return profile

    return check


TeacherUser = Annotated[Profile, Depends(_require_role("docente"))]
AdminUser = Annotated[Profile, Depends(_require_role("admin"))]
