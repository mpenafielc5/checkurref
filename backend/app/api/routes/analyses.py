"""Rutas de los análisis: subida del PDF (HU-04), historial (HU-07), estado para la
pantalla de progreso (HU-05) e informe de verificación (HU-06)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status

from app.api.dependencies import CurrentUser
from app.core.config import Settings, get_settings
from app.repositories.documents import SupabaseDocumentRepository
from app.repositories.pdf_storage import SupabasePdfStorage
from app.repositories.reports import SupabaseReportRepository
from app.repositories.supabase_http import SupabaseUnavailableError, shared_client
from app.schemas.analysis import AnalysisSubmittedResponse
from app.schemas.report import AnalysisItem, HistoryPage, ReportResponse
from app.services.report_service import (
    AnalysisNotFinishedError,
    AnalysisNotFoundError,
    ReportService,
)
from app.services.upload_service import MAX_PDF_BYTES, UploadRejectedError, UploadService

router = APIRouter(tags=["análisis"])


NOT_FOUND = "No se encontró el análisis."
UNAVAILABLE = "No se pudo consultar la base de datos. Intenta de nuevo en unos minutos."
# Por qué todavía no hay informe, según el estado del análisis.
NOT_FINISHED = {
    "error": "El análisis terminó con un error, así que no tiene informe.",
}
IN_PROGRESS = "El análisis aún no termina. El informe estará listo al completarse."


def _require_supabase(settings: Settings) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La API no tiene configurada la conexión con Supabase.",
        )


def get_upload_service(settings: Annotated[Settings, Depends(get_settings)]) -> UploadService:
    _require_supabase(settings)
    client = shared_client(settings.supabase_service_role_key)
    return UploadService(
        documents=SupabaseDocumentRepository(settings.supabase_rest_url, client),
        storage=SupabasePdfStorage(settings.supabase_storage_url, settings.storage_bucket, client),
        model_version=settings.analysis_model_version,
    )


@router.post(
    "/analisis",
    response_model=AnalysisSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={200: {"description": "El PDF ya se había subido: se devuelve su análisis."}},
)
def submit_analysis(
    user: CurrentUser,
    service: Annotated[UploadService, Depends(get_upload_service)],
    response: Response,
    archivo: Annotated[UploadFile, File(description="PDF del trabajo, hasta 10 MB.")],
) -> AnalysisSubmittedResponse:
    # Se lee un byte más del límite para saber si lo supera sin cargar archivos enormes.
    content = archivo.file.read(MAX_PDF_BYTES + 1)
    try:
        result = service.submit(user.id, archivo.filename or "", content)
    except UploadRejectedError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.message) from None
    except SupabaseUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo guardar el archivo. Intenta de nuevo en unos minutos.",
        ) from None

    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    return AnalysisSubmittedResponse(
        analysis_id=result.analysis.analysis_id,
        document_id=result.analysis.document_id,
        status=result.analysis.status,
        duplicate=result.duplicate,
    )


def get_report_service(settings: Annotated[Settings, Depends(get_settings)]) -> ReportService:
    _require_supabase(settings)
    client = shared_client(settings.supabase_service_role_key)
    return ReportService(SupabaseReportRepository(settings.supabase_rest_url, client))


@router.get("/analisis", response_model=HistoryPage)
def list_analyses(
    user: CurrentUser,
    service: Annotated[ReportService, Depends(get_report_service)],
    pagina: Annotated[int, Query(ge=1, description="Página de 20 trabajos.")] = 1,
    buscar: Annotated[str, Query(max_length=100, description="Parte del nombre del archivo.")] = "",
) -> HistoryPage:
    """Historial de los trabajos del usuario, del más reciente al más antiguo (HU-07)."""
    try:
        return service.history(user.id, pagina, buscar)
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


@router.get(
    "/analisis/{analysis_id}",
    response_model=AnalysisItem,
    responses={404: {"description": NOT_FOUND}},
)
def get_analysis(
    analysis_id: UUID,
    user: CurrentUser,
    service: Annotated[ReportService, Depends(get_report_service)],
) -> AnalysisItem:
    """Estado y avance de un análisis, para abrir la pantalla de progreso (HU-05)."""
    try:
        return service.status(user.id, analysis_id)
    except AnalysisNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


@router.get(
    "/analisis/{analysis_id}/informe",
    response_model=ReportResponse,
    responses={
        404: {"description": NOT_FOUND},
        409: {"description": "El análisis sigue en curso o terminó con error."},
    },
)
def get_report(
    analysis_id: UUID,
    user: CurrentUser,
    service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    """Informe de verificación completo (HU-06): el navegador filtra y pagina."""
    try:
        return service.report(user.id, analysis_id)
    except AnalysisNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    except AnalysisNotFinishedError as error:
        detail = NOT_FINISHED.get(error.status, IN_PROGRESS)
        raise HTTPException(status.HTTP_409_CONFLICT, detail=detail) from None
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None
