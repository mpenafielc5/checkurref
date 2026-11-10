"""Rutas del Laboratorio de extracción (HU-12, HU-13). Solo para el administrador."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import UNAVAILABLE, AdminUser, require_supabase
from app.core.config import Settings, get_settings
from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import Engine, ReferenceExtractor
from app.extraction.factory import create_extractor
from app.extraction.spacy_rules import SpacyExtractor
from app.repositories.benchmark_runs import SupabaseBenchmarkRunRepository
from app.repositories.gold_set import SupabaseGoldSetRepository
from app.repositories.supabase_http import SupabaseUnavailableError, shared_client
from app.schemas.lab import BenchmarkOverview, LabComparison, LabComparisonRequest
from app.services.benchmark_service import BenchmarkRejectedError, BenchmarkService
from app.services.lab_service import LabService

router = APIRouter(prefix="/laboratorio", tags=["laboratorio"])


@lru_cache
def _extractors(anystyle_command: str) -> tuple[ReferenceExtractor, ...]:
    # Los motores se crean una sola vez. Aquí no se usa create_extractor: si AnyStyle
    # falta, el Laboratorio debe decirlo, no mostrar spaCy dos veces.
    return AnyStyleExtractor(command=anystyle_command), SpacyExtractor()


def get_lab_service(settings: Annotated[Settings, Depends(get_settings)]) -> LabService:
    return LabService(list(_extractors(settings.anystyle_command)))


@lru_cache
def _engine_in_use(engine: str, anystyle_command: str) -> Engine:
    return create_extractor(Engine(engine), anystyle_command).engine


def get_benchmark_service(settings: Annotated[Settings, Depends(get_settings)]) -> BenchmarkService:
    require_supabase(settings)
    client = shared_client(settings.supabase_service_role_key)
    return BenchmarkService(
        SupabaseGoldSetRepository(settings.supabase_rest_url, client),
        SupabaseBenchmarkRunRepository(settings.supabase_rest_url, client),
        list(_extractors(settings.anystyle_command)),
        _engine_in_use(settings.extraction_engine, settings.anystyle_command),
    )


@router.post("/comparar", response_model=LabComparison)
def compare_engines(
    body: LabComparisonRequest,
    _admin: AdminUser,
    service: Annotated[LabService, Depends(get_lab_service)],
) -> LabComparison:
    """Salida de cada motor para una referencia, lado a lado."""
    return service.compare(body.reference)


@router.get("/benchmark", response_model=BenchmarkOverview)
def benchmark_overview(
    _admin: AdminUser,
    service: Annotated[BenchmarkService, Depends(get_benchmark_service)],
) -> BenchmarkOverview:
    """El estándar de oro, las mediciones guardadas y el motor en uso."""
    try:
        return service.overview()
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


@router.post(
    "/benchmark",
    response_model=BenchmarkOverview,
    responses={409: {"description": "Falta un motor o no hay referencias que medir."}},
)
def run_benchmark(
    _admin: AdminUser,
    service: Annotated[BenchmarkService, Depends(get_benchmark_service)],
) -> BenchmarkOverview:
    """Mide los dos motores con el estándar de oro y guarda el resultado."""
    try:
        return service.run()
    except BenchmarkRejectedError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.message) from None
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None
