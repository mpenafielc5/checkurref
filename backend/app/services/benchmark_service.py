"""Caso de uso: comparar los motores con el estándar de oro (CU-08, HU-12, objetivo 3).

Cada medición usa el mismo texto para ambos motores y se guarda con su fecha y la
versión de cada uno, para comprobar más adelante que un cambio no empeora la
extracción. Sin los dos motores no se mide: el análisis puede recurrir a spaCy si
falta AnyStyle, pero aquí ese reemplazo falsearía la comparación (CA04).
"""

from collections.abc import Callable
from datetime import datetime, timezone
from itertools import groupby
from typing import Protocol

from app.benchmark.evaluation import (
    KEY_FIELDS,
    TIE_MARGIN,
    EngineResult,
    decide_scores,
    evaluate,
)
from app.benchmark.gold_set import FIELDS, GoldReference
from app.extraction.base import Engine, ReferenceExtractor
from app.repositories.benchmark_runs import BenchmarkRunRepository, StoredScore
from app.schemas.lab import (
    BenchmarkOverview,
    BenchmarkRun,
    EngineScores,
    FieldScore,
    GoldSetSummary,
)

# Las mediciones que se muestran; dos motores con nueve campos cada una.
RUNS_SHOWN = 10
ROWS_PER_RUN = 2 * len(FIELDS)
APA = "APA"
IEEE = "IEEE"

ENGINE_NAMES = {Engine.ANYSTYLE: "AnyStyle", Engine.SPACY: "spaCy"}
NOT_INSTALLED = "{name} no está disponible en el servidor. La medición se detuvo y no se guardó."
ENGINE_FAILED = "{name} no pudo procesar ninguna referencia. La medición se detuvo y no se guardó."
EMPTY_GOLD_SET = "El estándar de oro no tiene referencias reales que medir."


class BenchmarkRejectedError(Exception):
    """La medición no se puede hacer. El mensaje se muestra al administrador."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class GoldSetReader(Protocol):
    def load_all(self) -> list[GoldReference]: ...


class BenchmarkService:
    def __init__(
        self,
        gold_set: GoldSetReader,
        runs: BenchmarkRunRepository,
        extractors: list[ReferenceExtractor],
        engine_in_use: Engine,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._gold_set = gold_set
        self._runs = runs
        self._extractors = extractors
        self._engine_in_use = engine_in_use
        self._clock = clock

    def overview(self) -> BenchmarkOverview:
        return self._overview(self._gold_set.load_all())

    def run(self) -> BenchmarkOverview:
        """Mide los dos motores, guarda el resultado y lo devuelve con el historial."""
        for extractor in self._extractors:
            if not extractor.available():
                name = ENGINE_NAMES[extractor.engine]
                raise BenchmarkRejectedError(NOT_INSTALLED.format(name=name))

        references = self._gold_set.load_all()
        if not any(not reference.altered for reference in references):
            raise BenchmarkRejectedError(EMPTY_GOLD_SET)

        executed_at = self._clock()
        scores: list[StoredScore] = []
        for extractor in self._extractors:
            result = evaluate(references, extractor)
            if result.failures == result.references:
                name = ENGINE_NAMES[extractor.engine]
                raise BenchmarkRejectedError(ENGINE_FAILED.format(name=name))
            scores.extend(_scores_of(result, extractor.version(), executed_at))

        self._runs.save(scores)
        return self._overview(references)

    def _overview(self, references: list[GoldReference]) -> BenchmarkOverview:
        rows = self._runs.recent(RUNS_SHOWN * ROWS_PER_RUN)
        return BenchmarkOverview(
            gold_set=_gold_summary(references),
            runs=[_run(list(group)) for _, group in groupby(rows, key=lambda row: row.executed_at)],
            engine_in_use=self._engine_in_use.value,
            key_fields=list(KEY_FIELDS),
            tie_margin=TIE_MARGIN,
        )


def _scores_of(
    result: EngineResult, version: str | None, executed_at: datetime
) -> list[StoredScore]:
    return [
        StoredScore(
            engine=result.engine.value,
            field=name,
            precision=result.by_field[name].precision,
            recall=result.by_field[name].recall,
            f1=result.by_field[name].f1,
            samples=result.references,
            version=version,
            executed_at=executed_at,
        )
        for name in FIELDS
    ]


def _gold_summary(references: list[GoldReference]) -> GoldSetSummary:
    real = [reference for reference in references if not reference.altered]
    return GoldSetSummary(
        total=len(references),
        real=len(real),
        apa=sum(reference.norm == APA for reference in real),
        ieee=sum(reference.norm == IEEE for reference in real),
    )


def _run(rows: list[StoredScore]) -> BenchmarkRun:
    """Rearma una medición. La decisión se recalcula con la misma regla de la tesis."""
    engines = [
        _engine_scores(engine, [row for row in rows if row.engine == engine.value])
        for engine in Engine
        if any(row.engine == engine.value for row in rows)
    ]
    decision = decide_scores({Engine(item.engine): item.key_f1 for item in engines})
    return BenchmarkRun(
        executed_at=rows[0].executed_at,
        engines=engines,
        selected_engine=decision.winner.value,
        tie=decision.tie,
        difference=decision.difference,
    )


def _engine_scores(engine: Engine, rows: list[StoredScore]) -> EngineScores:
    by_field = {row.field: row for row in rows}
    fields = [
        FieldScore(
            field=name,
            precision=by_field[name].precision,
            recall=by_field[name].recall,
            f1=by_field[name].f1,
        )
        for name in FIELDS
        if name in by_field
    ]
    key_scores = [by_field[name].f1 if name in by_field else 0.0 for name in KEY_FIELDS]
    return EngineScores(
        engine=engine.value,
        version=rows[0].version,
        samples=rows[0].samples,
        key_f1=sum(key_scores) / len(KEY_FIELDS),
        fields=fields,
    )
