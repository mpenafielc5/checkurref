"""Perfiles de los usuarios: rol y estado de la cuenta (PostgREST de Supabase)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import TypeAdapter

from app.repositories.reports import SEARCH_WILDCARDS
from app.repositories.supabase_http import get_counted, send

COLUMNS = "id,nombre_completo,correo,rol,activo,creado_en"
DATETIME = TypeAdapter(datetime)


@dataclass(frozen=True)
class Profile:
    id: UUID
    name: str
    email: str
    role: str  # estudiante, docente o admin
    active: bool
    created_at: datetime


@dataclass(frozen=True)
class ProfilePage:
    items: list[Profile]
    total: int


class ProfileRepository(Protocol):
    def get(self, profile_id: UUID) -> Profile | None: ...

    def list_profiles(
        self, offset: int, limit: int, search: str = "", role: str | None = None
    ) -> ProfilePage:
        """Perfiles por correo; con `search`, los correos que lo contienen."""
        ...

    def count(self, role: str | None = None) -> int:
        """Total de cuentas, o las de un rol."""
        ...

    def update(self, profile_id: UUID, changes: dict[str, Any]) -> Profile | None:
        """Aplica los cambios (columnas de la tabla) y devuelve el perfil; None si no existe."""
        ...


class SupabaseProfileRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/m_perfiles"
        self._client = client

    def get(self, profile_id: UUID) -> Profile | None:
        rows = send(
            self._client,
            "GET",
            self._url,
            params={"select": COLUMNS, "id": f"eq.{profile_id}"},
        )
        return _profile(rows[0]) if rows else None

    def list_profiles(
        self, offset: int, limit: int, search: str = "", role: str | None = None
    ) -> ProfilePage:
        params = {
            "select": COLUMNS,
            "order": "correo.asc",
            "offset": str(offset),
            "limit": str(limit),
        }
        if pattern := SEARCH_WILDCARDS.sub("", search).strip():
            params["correo"] = f"ilike.*{pattern}*"
        if role:
            params["rol"] = f"eq.{role}"
        rows, total = get_counted(self._client, self._url, params)
        return ProfilePage([_profile(row) for row in rows], total)

    def count(self, role: str | None = None) -> int:
        params = {"select": "id", "limit": "1"}
        if role:
            params["rol"] = f"eq.{role}"
        return get_counted(self._client, self._url, params)[1]

    def update(self, profile_id: UUID, changes: dict[str, Any]) -> Profile | None:
        rows = send(
            self._client,
            "PATCH",
            self._url,
            params={"select": COLUMNS, "id": f"eq.{profile_id}"},
            json=changes,
            headers={"Prefer": "return=representation"},
        )
        return _profile(rows[0]) if rows else None


def _profile(row: dict[str, Any]) -> Profile:
    return Profile(
        id=UUID(row["id"]),
        name=row["nombre_completo"],
        email=row["correo"],
        role=row["rol"],
        active=row["activo"],
        created_at=DATETIME.validate_python(row["creado_en"]),
    )
