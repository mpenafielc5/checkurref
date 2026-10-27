"""Tokens de sesión firmados para las pruebas de las rutas protegidas."""

import time
from typing import Any
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI

from app.api.dependencies import get_token_verifier
from app.core.security import TokenVerifier

ISSUER = "https://proyecto-de-prueba.supabase.co/auth/v1"
USER_ID = str(uuid4())

PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
PUBLIC_JWK = jwt.PyJWK(
    jwt.algorithms.ECAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True),
    algorithm="ES256",
)


def make_token(key: Any = PRIVATE_KEY, algorithm: str = "ES256", **claims: Any) -> str:
    now = int(time.time())
    payload = {
        "sub": USER_ID,
        "email": "estudiante@unemi.edu.ec",
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
        **claims,
    }
    return jwt.encode(payload, key, algorithm=algorithm)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def trust_test_tokens(app: FastAPI) -> None:
    """Hace que la app valide los tokens con la clave de prueba, sin internet."""
    app.dependency_overrides[get_token_verifier] = lambda: TokenVerifier(
        issuer=ISSUER, key_resolver=lambda _token: PUBLIC_JWK
    )
