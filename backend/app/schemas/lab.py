"""DTO del Laboratorio de extracción (HU-12, HU-13)."""

from datetime import datetime
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


class FieldScore(BaseModel):
    field: str
    precision: float
    recall: float
    f1: float


class EngineScores(BaseModel):
    engine: str  # anystyle o spacy
    version: str | None
    samples: int  # referencias reales medidas
    key_f1: float  # F1 promedio en los campos clave: decide el motor
    fields: list[FieldScore]


class BenchmarkRun(BaseModel):
    """Una medición guardada."""

    executed_at: datetime
    engines: list[EngineScores]
    selected_engine: str
    tie: bool  # diferencia dentro del margen de error: se mantiene el motor por defecto
    difference: float  # en puntos de F1, de 0 a 1


class GoldSetSummary(BaseModel):
    total: int
    real: int  # las únicas que miden a los motores; las alteradas prueban la verificación
    apa: int
    ieee: int


class BenchmarkOverview(BaseModel):
    gold_set: GoldSetSummary
    runs: list[BenchmarkRun]  # de la más reciente a la más antigua
    # El motor que usa el análisis ahora: si falta AnyStyle, puede no ser el seleccionado.
    engine_in_use: str
    key_fields: list[str]
    tie_margin: float
