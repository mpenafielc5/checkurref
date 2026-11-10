"""Tokens de sesión firmados para las pruebas de las rutas protegidas."""

import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI

from app.api.dependencies import get_token_verifier, get_user_service
from app.core.security import TokenVerifier
from app.repositories.profiles import Profile, ProfilePage
from app.services.user_service import UserService

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


class FakeProfiles:
    """Perfiles en memoria; el del usuario de las pruebas se crea con el rol indicado."""

    def __init__(self, role: str = "estudiante", active: bool = True) -> None:
        self.items: dict[UUID, Profile] = {}
        self.add(UUID(USER_ID), role, active)

    def add(self, profile_id: UUID, role: str, active: bool = True) -> Profile:
        profile = Profile(
            profile_id,
            f"Usuario {role}",
            f"{role}.{str(profile_id)[:8]}@unemi.edu.ec",
            role,
            active,
            datetime(2026, 11, 1, tzinfo=timezone.utc),
        )
        self.items[profile_id] = profile
        return profile

    def get(self, profile_id: UUID) -> Profile | None:
        return self.items.get(profile_id)

    def list_profiles(
        self, offset: int, limit: int, search: str = "", role: str | None = None
    ) -> ProfilePage:
        found = sorted(
            (
                item
                for item in self.items.values()
                if search.lower() in item.email and (role is None or item.role == role)
            ),
            key=lambda item: item.email,
        )
        return ProfilePage(found[offset : offset + limit], len(found))

    def count(self, role: str | None = None) -> int:
        return sum(role is None or item.role == role for item in self.items.values())

    def update(self, profile_id: UUID, changes: dict[str, Any]) -> Profile | None:
        current = self.items.get(profile_id)
        if current is None:
            return None
        updated = replace(
            current,
            role=changes.get("rol", current.role),
            active=changes.get("activo", current.active),
        )
        self.items[profile_id] = updated
        return updated


def act_as(app: FastAPI, role: str = "estudiante", active: bool = True) -> FakeProfiles:
    """La API lee el rol y el estado de la cuenta de estos perfiles, no de Supabase."""
    profiles = FakeProfiles(role, active)
    app.dependency_overrides[get_user_service] = lambda: UserService(profiles)
    return profiles


def trust_test_tokens(app: FastAPI) -> None:
    """Hace que la app valide los tokens con la clave de prueba, sin internet."""
    app.dependency_overrides[get_token_verifier] = lambda: TokenVerifier(
        issuer=ISSUER, key_resolver=lambda _token: PUBLIC_JWK
    )
