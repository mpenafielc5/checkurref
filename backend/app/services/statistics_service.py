"""Caso de uso: estadísticas generales de cada rol (HU-18).

Solo cuentan los análisis terminados: uno en curso aún no tiene veredictos y uno
con error no tiene resultado (CA04). Cada método recibe el id de quien consulta y
no acepta otro: nadie puede pedir las cifras de otra cuenta.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from app.repositories.batches import StoredWork
from app.repositories.profiles import ProfileRepository
from app.repositories.statistics import StatisticsRepository
from app.schemas.report import VerdictCounts
from app.schemas.statistics import AdminStatistics, StudentStatistics, TeacherStatistics
from app.schemas.user import RoleCounts
from app.services.batch_service import (
    COMPLETED,
    CONTRADICTION,
    HIGH,
    count_verdict,
    most_different_fields,
    risk_of,
    verdict_counts,
)

VERDICTS = ("verificada", "discrepancia", CONTRADICTION, "sin_respaldo", "no_verificable")
ROLES = ("estudiante", "docente", "admin")


class StatisticsService:
    def __init__(self, statistics: StatisticsRepository, profiles: ProfileRepository) -> None:
        self._statistics = statistics
        self._profiles = profiles

    def for_student(self, student_id: UUID) -> StudentStatistics:
        works = _finished(self._statistics.works_of(student_id, in_batches=False))
        indexes = [work.index for work in works if work.index is not None]
        different = most_different_fields(works)
        return StudentStatistics(
            works=len(works),
            references=_references(works),
            average_index=sum(indexes) / len(indexes) if indexes else None,
            counts=verdict_counts(works),
            most_different_field=different[0].field if different else None,
        )

    def for_teacher(self, teacher_id: UUID) -> TeacherStatistics:
        works = _finished(self._statistics.works_of(teacher_id, in_batches=True))
        return TeacherStatistics(
            batches=self._statistics.count_batches(teacher_id),
            works=len(works),
            references=_references(works),
            counts=verdict_counts(works),
            high_risk_works=sum(_is_high_risk(work) for work in works),
        )

    def for_admin(self) -> AdminStatistics:
        totals = _count_together(
            {
                **{verdict: _verdict_counter(self._statistics, verdict) for verdict in VERDICTS},
                "referencias": self._statistics.count_references,
                "documentos": self._statistics.count_documents,
                "todos": self._profiles.count,
                **{role: _role_counter(self._profiles, role) for role in ROLES},
            }
        )
        by_verdict = {verdict: totals[verdict] for verdict in VERDICTS}
        references = totals["referencias"]
        return AdminStatistics(
            users=RoleCounts(todos=totals["todos"], **{role: totals[role] for role in ROLES}),
            documents=totals["documentos"],
            references=references,
            # Las referencias sin veredicto son las que una fuente no pudo responder.
            counts=VerdictCounts(
                **by_verdict, error_consulta=max(references - sum(by_verdict.values()), 0)
            ),
        )


def _count_together(counters: dict[str, Callable[[], int]]) -> dict[str, int]:
    """Hace los conteos a la vez: cada uno es una consulta a la base que no depende de
    las demás, así que el tiempo total es el de la más lenta y no la suma de todas.
    Si alguno falla, su error se propaga como si se hubiera hecho solo."""
    with ThreadPoolExecutor(max_workers=len(counters)) as pool:
        futures = {name: pool.submit(counter) for name, counter in counters.items()}
        return {name: future.result() for name, future in futures.items()}


def _verdict_counter(statistics: StatisticsRepository, verdict: str) -> Callable[[], int]:
    return lambda: statistics.count_verdict(verdict)


def _role_counter(profiles: ProfileRepository, role: str) -> Callable[[], int]:
    return lambda: profiles.count(role)


def _finished(works: list[StoredWork]) -> list[StoredWork]:
    return [work for work in works if work.status == COMPLETED]


def _references(works: list[StoredWork]) -> int:
    return sum(len(work.verdicts) for work in works)


def _is_high_risk(work: StoredWork) -> bool:
    return risk_of(work.index, count_verdict(work, CONTRADICTION)) == HIGH
