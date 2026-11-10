"""Rutas de la gestión de usuarios (HU-11). Solo para el administrador."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import UNAVAILABLE, AdminUser, get_user_service
from app.repositories.supabase_http import SupabaseUnavailableError
from app.schemas.user import UserItem, UsersPage, UserUpdate
from app.services.user_service import UserChangeRejectedError, UserNotFoundError, UserService

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

NOT_FOUND = "No se encontró el usuario."


@router.get("", response_model=UsersPage)
def list_users(
    _admin: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
    pagina: Annotated[int, Query(ge=1, description="Página de 20 usuarios.")] = 1,
    buscar: Annotated[str, Query(max_length=100, description="Parte del correo.")] = "",
    rol: Annotated[Literal["estudiante", "docente", "admin"] | None, Query()] = None,
) -> UsersPage:
    try:
        return service.list_users(pagina, buscar, rol)
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


@router.patch(
    "/{user_id}",
    response_model=UserItem,
    responses={
        404: {"description": NOT_FOUND},
        409: {"description": "El cambio incumple una regla de la gestión de usuarios."},
    },
)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    admin: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserItem:
    """Cambia el rol entre estudiante y docente, o activa y desactiva una cuenta."""
    try:
        return service.update_user(admin.id, user_id, body.role, body.active)
    except UserNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    except UserChangeRejectedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.message) from None
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None
