"""Casos de uso: estado de la cuenta y gestión de usuarios (CU-02, HU-11).

Las reglas viven aquí y no solo en la interfaz: quien llame directamente a la API
tampoco puede quitarse su propio rol ni tocar otra cuenta de administrador.
"""

import math
from typing import Any
from uuid import UUID

from app.repositories.profiles import Profile, ProfileRepository
from app.schemas.user import RoleCounts, UserItem, UsersPage

USERS_PAGE_SIZE = 20  # HU-11 CA01
ADMIN_ROLE = "admin"
ROLES = ("estudiante", "docente", ADMIN_ROLE)

SELF_CHANGE = "No puedes cambiar tu propio rol ni desactivar tu propia cuenta."
ADMIN_CHANGE = "Las cuentas de administrador no se modifican desde esta opción."
NOTHING_TO_CHANGE = "Indica el rol o el estado de la cuenta que deseas cambiar."


class AccountDisabledError(Exception):
    """La cuenta está desactivada o no tiene perfil: no puede usar el sistema."""


class UserNotFoundError(Exception):
    """El usuario no existe."""


class UserChangeRejectedError(Exception):
    """El cambio incumple una regla. El mensaje se muestra al usuario."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UserService:
    def __init__(self, profiles: ProfileRepository) -> None:
        self._profiles = profiles

    def active_profile(self, user_id: UUID) -> Profile:
        profile = self._profiles.get(user_id)
        if profile is None or not profile.active:
            raise AccountDisabledError(str(user_id))
        return profile

    def list_users(self, page: int, search: str = "", role: str | None = None) -> UsersPage:
        page = max(page, 1)
        result = self._profiles.list_profiles(
            (page - 1) * USERS_PAGE_SIZE, USERS_PAGE_SIZE, search, role
        )
        return UsersPage(
            items=[_item(profile) for profile in result.items],
            page=page,
            page_size=USERS_PAGE_SIZE,
            total=result.total,
            total_pages=max(1, math.ceil(result.total / USERS_PAGE_SIZE)),
            counts=RoleCounts(
                todos=self._profiles.count(),
                **{name: self._profiles.count(name) for name in ROLES},
            ),
        )

    def update_user(
        self, admin_id: UUID, user_id: UUID, role: str | None, active: bool | None
    ) -> UserItem:
        if role is None and active is None:
            raise UserChangeRejectedError(NOTHING_TO_CHANGE)
        if user_id == admin_id:
            raise UserChangeRejectedError(SELF_CHANGE)
        target = self._profiles.get(user_id)
        if target is None:
            raise UserNotFoundError(str(user_id))
        if target.role == ADMIN_ROLE:
            raise UserChangeRejectedError(ADMIN_CHANGE)

        changes: dict[str, Any] = {}
        if role is not None:
            changes["rol"] = role
        if active is not None:
            changes["activo"] = active
        updated = self._profiles.update(user_id, changes)
        if updated is None:
            raise UserNotFoundError(str(user_id))
        return _item(updated)


def _item(profile: Profile) -> UserItem:
    return UserItem(
        id=profile.id,
        name=profile.name,
        email=profile.email,
        role=profile.role,
        active=profile.active,
        created_at=profile.created_at,
    )
