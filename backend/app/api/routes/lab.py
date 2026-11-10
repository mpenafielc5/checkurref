"""Rutas del Laboratorio de extracción (HU-13). Solo para el administrador."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import AdminUser
from app.core.config import Settings, get_settings
from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import ReferenceExtractor
from app.extraction.spacy_rules import SpacyExtractor
from app.schemas.lab import LabComparison, LabComparisonRequest
from app.services.lab_service import LabService

router = APIRouter(prefix="/laboratorio", tags=["laboratorio"])


@lru_cache
def _extractors(anystyle_command: str) -> tuple[ReferenceExtractor, ...]:
    # Los motores se crean una sola vez. Aquí no se usa create_extractor: si AnyStyle
    # falta, el Laboratorio debe decirlo, no mostrar spaCy dos veces.
    return AnyStyleExtractor(command=anystyle_command), SpacyExtractor()


def get_lab_service(settings: Annotated[Settings, Depends(get_settings)]) -> LabService:
    return LabService(list(_extractors(settings.anystyle_command)))


@router.post("/comparar", response_model=LabComparison)
def compare_engines(
    body: LabComparisonRequest,
    _admin: AdminUser,
    service: Annotated[LabService, Depends(get_lab_service)],
) -> LabComparison:
    """Salida de cada motor para una referencia, lado a lado."""
    return service.compare(body.reference)
