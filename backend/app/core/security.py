"""Validación de los tokens de sesión que emite Supabase Auth.

Supabase firma cada token con una clave asimétrica (ES256). La API solo
necesita la clave pública del proyecto, publicada en su JWKS, para comprobar
que el token es auténtico, que no venció y que es de un usuario con sesión.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import jwt

ALGORITHMS = ["ES256"]
AUDIENCE = "authenticated"
REQUIRED_CLAIMS = ["exp", "sub", "aud", "iss"]

KeyResolver = Callable[[str], jwt.PyJWK]
"""Devuelve la clave pública con la que se firmó el token."""


class InvalidSessionError(Exception):
    """El token está mal formado, venció o no lo firmó el proyecto de Supabase."""


class SessionVerificationUnavailableError(Exception):
    """No se pudo obtener la clave pública de Supabase para validar el token."""


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    email: str | None


class TokenVerifier:
    def __init__(self, issuer: str, key_resolver: KeyResolver) -> None:
        self._issuer = issuer
        self._key_resolver = key_resolver

    def verify(self, token: str) -> AuthenticatedUser:
        try:
            key = self._key_resolver(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=AUDIENCE,
                issuer=self._issuer,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWKClientConnectionError as error:
            raise SessionVerificationUnavailableError from error
        except jwt.PyJWTError as error:
            raise InvalidSessionError from error

        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError as error:
            raise InvalidSessionError from error

        email = claims.get("email")
        return AuthenticatedUser(id=user_id, email=email if isinstance(email, str) else None)


def jwks_key_resolver(auth_url: str) -> KeyResolver:
    """Obtiene las claves públicas del proyecto y las guarda en memoria."""
    client = jwt.PyJWKClient(f"{auth_url}/.well-known/jwks.json", cache_keys=True)
    return client.get_signing_key_from_jwt
