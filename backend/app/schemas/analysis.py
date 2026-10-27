"""DTO de la subida de un trabajo y su análisis."""

from uuid import UUID

from pydantic import BaseModel


class AnalysisSubmittedResponse(BaseModel):
    analysis_id: UUID
    document_id: UUID
    # Estado del análisis en la base: en_cola, extrayendo, ..., completado o error.
    status: str
    # True si el PDF ya se había subido: se devuelve el análisis existente.
    duplicate: bool
