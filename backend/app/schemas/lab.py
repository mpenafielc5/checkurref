"""DTO del Laboratorio de extracción (HU-13)."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

# Una referencia rara vez pasa de 900 caracteres: el doble ya no es una referencia.
LabReference = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)
]


class LabComparisonRequest(BaseModel):
    reference: LabReference


class EngineFields(BaseModel):
    """Campos con los nombres de la base; los que ve el usuario los pone el frontend."""

    autores: str | None = None
    anio: str | None = None
    titulo: str | None = None
    contenedor: str | None = None
    editorial: str | None = None
    volumen: str | None = None
    numero: str | None = None
    paginas: str | None = None
    doi: str | None = None


class EngineOutput(BaseModel):
    engine: str  # anystyle o spacy
    elapsed_ms: int
    # El motivo si el motor no pudo procesar la referencia.
    error: str | None
    fields: EngineFields | None


class LabComparison(BaseModel):
    engines: list[EngineOutput]
    # Campos en los que los motores no coinciden, para resaltarlos (HU-13 CA02).
    different_fields: list[str]
    compared_fields: int
    matching_fields: int
