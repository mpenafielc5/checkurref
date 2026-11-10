"""Rutas de los lotes de auditoría (HU-08, HU-09). Solo para el docente."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status

from app.api.dependencies import UNAVAILABLE, TeacherUser, require_supabase
from app.api.routes.analyses import get_upload_service
from app.core.config import Settings, get_settings
from app.repositories.batches import SupabaseBatchRepository
from app.repositories.supabase_http import SupabaseUnavailableError, shared_client
from app.schemas.analysis import AnalysisSubmittedResponse
from app.schemas.batch import BatchCreate, BatchDetail, BatchesPage, BatchSummary
from app.services.batch_service import BatchNotFoundError, BatchService
from app.services.upload_service import MAX_PDF_BYTES, UploadRejectedError, UploadService

router = APIRouter(prefix="/lotes", tags=["lotes"])

NOT_FOUND = "No se encontró el lote."


def get_batch_service(
    settings: Annotated[Settings, Depends(get_settings)],
    uploads: Annotated[UploadService, Depends(get_upload_service)],
) -> BatchService:
    require_supabase(settings)
    client = shared_client(settings.supabase_service_role_key)
    return BatchService(SupabaseBatchRepository(settings.supabase_rest_url, client), uploads)


@router.post("", response_model=BatchSummary, status_code=status.HTTP_201_CREATED)
def create_batch(
    body: BatchCreate,
    teacher: TeacherUser,
    service: Annotated[BatchService, Depends(get_batch_service)],
) -> BatchSummary:
    try:
        return service.create(teacher.id, body.name, body.period)
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


@router.get("", response_model=BatchesPage)
def list_batches(
    teacher: TeacherUser,
    service: Annotated[BatchService, Depends(get_batch_service)],
    pagina: Annotated[int, Query(ge=1, description="Página de 20 lotes.")] = 1,
) -> BatchesPage:
    try:
        return service.list_batches(teacher.id, pagina)
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


@router.get("/{batch_id}", response_model=BatchDetail, responses={404: {"description": NOT_FOUND}})
def get_batch(
    batch_id: UUID,
    teacher: TeacherUser,
    service: Annotated[BatchService, Depends(get_batch_service)],
) -> BatchDetail:
    """Estado del lote y su tablero: indicadores y trabajos con su riesgo."""
    try:
        return service.detail(teacher.id, batch_id)
    except BatchNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
    except SupabaseUnavailableError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=UNAVAILABLE) from None


@router.post(
    "/{batch_id}/trabajos",
    response_model=AnalysisSubmittedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        200: {"description": "El PDF ya estaba en el lote: se devuelve su análisis."},
        404: {"description": NOT_FOUND},
    },
)
def submit_batch_work(
    batch_id: UUID,
    teacher: TeacherUser,
    service: Annotated[BatchService, Depends(get_batch_service)],
    response: Response,
    archivo: Annotated[UploadFile, File(description="PDF del trabajo, hasta 10 MB.")],
) -> AnalysisSubmittedResponse:
    """Sube un PDF al lote; el navegador envía los archivos uno por uno."""
    content = archivo.file.read(MAX_PDF_BYTES + 1)
    try:
        result = service.submit_work(teacher.id, batch_id, archivo.filename or "", content)
    except BatchNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from None
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
