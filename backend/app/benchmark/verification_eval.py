"""Verificación con el estándar de oro: calibración de umbrales (T18) y prueba (T17).

Cada referencia de una partición pasa por lo mismo que un trabajo subido: el
extractor saca sus campos, se busca en Crossref y OpenAlex y el motor de decisión
da el veredicto. Las reales de control deben salir Verificada; las alteradas,
con el veredicto esperado de su tipo (EXPECTED). Una real con
un error comprobado a mano en la propia tesis (nota "Error real: ...") no es una
falsa alarma si el sistema alerta: se informa aparte.

Las respuestas de las fuentes y del NLI se guardan la primera vez (RecordingLookup,
MemoNli): así cada combinación de umbrales se compara con los mismos datos y la
calibración no repite cientos de consultas.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field, fields, replace
from typing import Protocol

from app.benchmark.gold_set import GoldReference
from app.extraction.base import ExtractedFields
from app.sources.lookup import LookupResult, Strategy, is_work
from app.verification.decision import NliScorer, Thresholds, Verdict
from app.verification.nli import NliScores
from app.verification.verifier import ReferenceVerifier

CONTROL = "control"
CONTROL_WITH_ERROR = "control_con_error"
CONTROLS = (CONTROL, CONTROL_WITH_ERROR)
REAL_ERROR_NOTE = "error real"
# Veredictos esperados de cada tipo de alteración, fijados antes de medir.
EXPECTED: dict[str, frozenset[Verdict]] = {
    CONTROL: frozenset({Verdict.VERIFIED}),
    CONTROL_WITH_ERROR: frozenset(set(Verdict) - {Verdict.VERIFIED}),
    "anio": frozenset({Verdict.DISCREPANCY}),
    "autor": frozenset({Verdict.DISCREPANCY}),
    "titulo": frozenset({Verdict.CONTRADICTION}),
    "doi": frozenset({Verdict.DISCREPANCY}),
    "inventada": frozenset({Verdict.UNSUPPORTED, Verdict.CONTRADICTION}),
}
# Valores que se prueban para cada umbral: de 0,30 a 0,95 en pasos de 0,05.
GRID = tuple(round(0.30 + 0.05 * step, 2) for step in range(14))


class Lookup(Protocol):
    async def lookup(self, fields: ExtractedFields) -> LookupResult: ...


@dataclass(frozen=True)
class Case:
    """Una referencia del estándar de oro con los campos que sacó el extractor."""

    reference: GoldReference
    fields: ExtractedFields | None

    @property
    def kind(self) -> str:
        if self.reference.altered:
            return self.reference.alteration
        if self.reference.notes.lower().startswith(REAL_ERROR_NOTE):
            return CONTROL_WITH_ERROR
        return CONTROL


@dataclass(frozen=True)
class Outcome:
    case: Case
    verdict: Verdict | None  # None: una fuente no respondió

    @property
    def alerts(self) -> bool:
        return self.verdict is not None and self.verdict is not Verdict.VERIFIED

    @property
    def exact(self) -> bool:
        return self.verdict in EXPECTED[self.case.kind]


@dataclass
class KindScore:
    total: int = 0
    alerts: int = 0
    exact: int = 0
    errors: int = 0
    verdicts: dict[str, int] = field(default_factory=dict)


@dataclass
class Score:
    by_kind: dict[str, KindScore]

    @property
    def false_alarms(self) -> int:
        return self.by_kind.get(CONTROL, KindScore()).alerts

    @property
    def alerts(self) -> int:
        return sum(score.alerts for kind, score in self.by_kind.items() if kind not in CONTROLS)

    @property
    def altered(self) -> int:
        return sum(score.total for kind, score in self.by_kind.items() if kind not in CONTROLS)

    @property
    def exact(self) -> int:
        return sum(score.exact for score in self.by_kind.values())

    @property
    def errors(self) -> int:
        return sum(score.errors for score in self.by_kind.values())

    def key(self) -> tuple[int, int, int]:
        """Orden del criterio: menos falsas alarmas, más alertas, más aciertos exactos."""
        return (-self.false_alarms, self.alerts, self.exact)


@dataclass(frozen=True)
class Trial:
    name: str
    value: float
    score: Score


@dataclass
class Calibration:
    baseline: Score
    trials: list[Trial]
    chosen: Thresholds
    combined: Score  # los valores elegidos, medidos juntos


def partition_cases(
    references: Sequence[GoldReference],
    partition: str,
    extract: Callable[[list[str]], list[ExtractedFields | None]],
) -> list[Case]:
    """Controles y alteradas de una partición, con los campos que sacó el extractor."""
    selected = [reference for reference in references if reference.partition == partition]
    extracted = extract([reference.text for reference in selected])
    return [Case(reference, item) for reference, item in zip(selected, extracted, strict=True)]


async def verify_cases(
    cases: Sequence[Case], lookup: Lookup, nli: NliScorer, thresholds: Thresholds
) -> list[Outcome]:
    verifier = ReferenceVerifier(lookup, nli, thresholds)
    verifications = await asyncio.gather(
        *(verifier.verify(case.reference.text, case.fields) for case in cases)
    )
    return [
        Outcome(case, verification.verdict)
        for case, verification in zip(cases, verifications, strict=True)
    ]


def score(outcomes: Sequence[Outcome]) -> Score:
    by_kind: dict[str, KindScore] = {}
    for outcome in outcomes:
        item = by_kind.setdefault(outcome.case.kind, KindScore())
        item.total += 1
        item.alerts += outcome.alerts
        item.exact += outcome.exact
        item.errors += outcome.verdict is None
        label = outcome.verdict.value if outcome.verdict else "error_consulta"
        item.verdicts[label] = item.verdicts.get(label, 0) + 1
    return Score(by_kind)


async def calibrate(
    run: Callable[[Thresholds], Awaitable[Score]], current: Thresholds
) -> Calibration:
    """Busca cada umbral por separado: menos falsas alarmas, luego más alertas y
    luego más veredictos exactos.

    Un valor reemplaza al actual solo si lo supera: ante un empate se conserva el
    actual, y entre varios valores igual de buenos se toma el más cercano al actual.
    Al final se miden juntos los elegidos; si empeoran, queda solo el cambio que más
    mejora por sí solo.
    """
    baseline = await run(current)
    trials: list[Trial] = []
    best_single: Trial | None = None
    chosen = current
    for name in (item.name for item in fields(Thresholds)):
        own = getattr(current, name)
        tried = [Trial(name, value, await run(replace(current, **{name: value}))) for value in GRID]
        trials.extend(tried)
        top = max(trial.score.key() for trial in tried)
        best = Trial(name, own, baseline)
        if top > baseline.key():
            best = min(
                (trial for trial in tried if trial.score.key() == top),
                key=lambda trial: abs(trial.value - own),
            )
        if best.value != own:
            chosen = replace(chosen, **{name: best.value})
            if best_single is None or best.score.key() > best_single.score.key():
                best_single = best
    combined = await run(chosen) if chosen != current else baseline
    if best_single and combined.key() < best_single.score.key():
        chosen = replace(current, **{best_single.name: best_single.value})
        combined = best_single.score
    return Calibration(baseline, trials, chosen, combined)


class RecordingLookup:
    """Guarda cada búsqueda la primera vez y luego la repite sin consultar las fuentes.

    Una búsqueda en la que alguna fuente no respondió no se guarda: se intenta de nuevo.
    Tampoco se repite una guardada que la consulta actual ya no daría: un DOI cuyo
    registro no es una obra (el número de una revista) ahora se busca por título.
    """

    def __init__(self, inner: Lookup, store: dict[str, LookupResult]) -> None:
        self._inner = inner
        self.store = store

    async def lookup(self, fields: ExtractedFields) -> LookupResult:
        key = repr(fields)
        stored = self.store.get(key)
        if stored is not None and _still_valid(stored):
            return stored
        result = await self._inner.lookup(fields)
        if not result.query_failed:
            self.store[key] = result
        return result


def _still_valid(result: LookupResult) -> bool:
    if result.strategy is not Strategy.DIRECT_DOI:
        return True
    return all(is_work(record) for record in result.candidates)


class MemoNli:
    """El modelo NLI da siempre lo mismo para el mismo par: se calcula una vez."""

    def __init__(self, inner: NliScorer) -> None:
        self._inner = inner
        self._memo: dict[tuple[str, str], NliScores] = {}

    def infer_many(self, pairs: Sequence[tuple[str, str]]) -> list[NliScores]:
        missing = [pair for pair in dict.fromkeys(pairs) if pair not in self._memo]
        if missing:
            self._memo.update(zip(missing, self._inner.infer_many(missing), strict=True))
        return [self._memo[pair] for pair in pairs]
