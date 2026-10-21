"""DTO de la sesión del usuario."""

from uuid import UUID

from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str | None
