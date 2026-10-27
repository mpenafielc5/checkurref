"""Ruta de subida: recibe el PDF y deja su análisis en cola (HU-04)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.api.dependencies import CurrentUser
from app.core.config import Settings, get_settings
from app.repositories.documents import SupabaseDocumentRepository
from app.repositories.pdf_storage import SupabasePdfStorage
from app.repositories.supabase_http import SupabaseUnavailableError, shared_client
from app.schemas.analysis import AnalysisSubmittedResponse
from app.services.upload_service import MAX_PDF_BYTES, UploadRejectedError, UploadService

router = APIRouter(tags=["análisis"])


def get_upload_service(settings: Annotated[Settings, Depends(get_settings)]) -> UploadService:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La API no tiene configurada la conexión con Supabase.",
        )
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
