"""DTO de la gestión de usuarios (HU-11)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class UserItem(BaseModel):
    id: UUID
    name: str
    email: str
    role: str  # estudiante, docente o admin
    active: bool
    created_at: datetime


class RoleCounts(BaseModel):
    """Cuentas por rol, sin el filtro de búsqueda: son los totales de los filtros."""

    todos: int
    estudiante: int
    docente: int
    admin: int


class UsersPage(BaseModel):
    items: list[UserItem]
    page: int
    page_size: int
    total: int
    total_pages: int
    counts: RoleCounts


class UserUpdate(BaseModel):
    """Solo se cambia entre estudiante y docente: nadie se vuelve administrador por la API."""

    role: Literal["estudiante", "docente"] | None = None
    active: bool | None = None
