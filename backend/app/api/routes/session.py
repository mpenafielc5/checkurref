"""Ruta protegida de la sesión: confirma quién hace la petición."""

from fastapi import APIRouter

from app.api.dependencies import CurrentUser
from app.schemas.session import CurrentUserResponse

router = APIRouter(tags=["sesión"])


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(user: CurrentUser) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, email=user.email)
