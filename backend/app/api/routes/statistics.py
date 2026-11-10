"""Ruta de las estadísticas generales (HU-18). Cada rol recibe solo sus propias cifras."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import UNAVAILABLE, ActiveUser, require_supabase
from app.core.config import Settings, get_settings
from app.repositories.profiles import SupabaseProfileRepository
from app.repositories.statistics import SupabaseStatisticsRepository
from app.repositories.supabase_http import SupabaseUnavailableError, shared_client
from app.schemas.statistics import AdminStatistics, StudentStatistics, TeacherStatistics
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/estadisticas", tags=["estadísticas"])


def get_statistics_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatisticsService:
    require_supabase(settings)
    client = shared_client(settings.supabase_service_role_key)
    return StatisticsService(
        SupabaseStatisticsRepository(settings.supabase_rest_url, client),
        SupabaseProfileRepository(settings.supabase_rest_url, client),
    )


@router.get("", response_model=StudentStatistics | TeacherStatistics | AdminStatistics)
def statistics(
    user: ActiveUser,
    service: Annotated[StatisticsService, Depends(get_statistics_service)],
) -> StudentStatistics | TeacherStatistics | AdminStatistics:
    """Las cifras dependen del rol de la sesión: no hay parámetros para pedir otras."""
    try:
        if user.role == "admin":
            return service.for_admin()
        if user.role == "docente":
            return service.for_teacher(user.id)
        return service.for_student(user.id)
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None
