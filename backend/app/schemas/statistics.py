"""DTO de las estadísticas generales de cada rol (HU-18)."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.report import VerdictCounts
from app.schemas.user import RoleCounts


class StudentStatistics(BaseModel):
    role: Literal["estudiante"] = "estudiante"
    works: int
    references: int
    # None si ningún trabajo tiene referencias con las que calcularlo.
    average_index: float | None
    counts: VerdictCounts
    most_different_field: str | None


class TeacherStatistics(BaseModel):
    role: Literal["docente"] = "docente"
    batches: int
    works: int
    references: int
    counts: VerdictCounts
    high_risk_works: int


class AdminStatistics(BaseModel):
    role: Literal["admin"] = "admin"
    users: RoleCounts
    documents: int
    references: int
    # counts.error_consulta: referencias sin veredicto porque una fuente no respondió.
    counts: VerdictCounts
