"""Comparación de AnyStyle y spaCy con el estándar de oro (HU-12, objetivo específico 3).

Usa solo las referencias reales. Cada campo de cada referencia se cuenta así:

- verdadero positivo (VP): el motor saca el valor anotado;
- falso positivo (FP): saca un valor distinto, o un valor donde la anotación está vacía;
- falso negativo (FN): la anotación tiene valor y el motor no lo saca bien.

Un valor equivocado es a la vez FP y FN. Los autores se cuentan apellido por
apellido. Dos valores son iguales con la misma comparación que el acuerdo entre
anotadores (sin mayúsculas, guiones ni puntuación del borde); el DOI, además, se
normaliza como antes de buscarlo en Crossref.
"""

from collections import Counter
from dataclasses import dataclass, field

from app.benchmark.gold_set import FIELDS, GoldReference, same_value, surnames, trimmed
from app.extraction.base import Engine, ExtractedFields, ReferenceExtractor
from app.sources.records import normalize_doi

# Campos con los que se busca la referencia en Crossref y OpenAlex: deciden el ganador.
KEY_FIELDS = ("titulo", "autores", "anio", "doi")
# Una diferencia menor queda dentro del margen de error con 100 referencias.
TIE_MARGIN = 0.05
DEFAULT_ENGINE = Engine.ANYSTYLE


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, other: "Counts") -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        total = self.precision + self.recall
        return 2 * self.precision * self.recall / total if total else 0.0


@dataclass
class EngineResult:
    engine: Engine
    references: int
    by_field: dict[str, Counts] = field(default_factory=dict)
    by_norm: dict[str, dict[str, Counts]] = field(default_factory=dict)
    failures: int = 0  # referencias que el motor no pudo procesar
    elapsed_ms: int = 0

    def key_f1(self, norm: str | None = None) -> float:
        """F1 promedio de los campos clave, en total o de una norma."""
        counts = self.by_field if norm is None else self.by_norm.get(norm, {})
        return sum(counts.get(name, Counts()).f1 for name in KEY_FIELDS) / len(KEY_FIELDS)


@dataclass(frozen=True)
class Decision:
    winner: Engine
    tie: bool
    difference: float  # en puntos de F1 (0 a 1)


def as_annotation(fields: ExtractedFields | None) -> dict[str, str]:
    """Los campos de un motor con los nombres y el formato de la anotación."""
    if fields is None:
        return {name: "" for name in FIELDS}
    return {
        "autores": "; ".join(author.family for author in fields.authors),
        "anio": str(fields.year) if fields.year else "",
        "titulo": fields.title or "",
        "contenedor": fields.container or "",
        "editorial": fields.publisher or "",
        "volumen": fields.volume or "",
        "numero": fields.issue or "",
        "paginas": fields.pages or "",
        "doi": fields.doi or "",
    }


def count_field(name: str, expected: str, extracted: str) -> Counts:
    """VP, FP y FN de un campo de una referencia."""
    if name == "autores":
        gold = Counter(trimmed(surname) for surname in surnames(expected))
        found = Counter(trimmed(surname) for surname in surnames(extracted))
        gold.pop("", None)
        found.pop("", None)
        tp = sum((gold & found).values())
        return Counts(tp, sum(found.values()) - tp, sum(gold.values()) - tp)
    if name == "doi":
        expected = normalize_doi(expected) or expected
        extracted = normalize_doi(extracted) or extracted
    has_gold, has_found = bool(trimmed(expected)), bool(trimmed(extracted))
    if has_gold and has_found and same_value(name, expected, extracted):
        return Counts(tp=1)
    return Counts(fp=int(has_found), fn=int(has_gold))


def evaluate(references: list[GoldReference], extractor: ReferenceExtractor) -> EngineResult:
    """Mide un motor con las referencias reales del estándar de oro."""
    real = [reference for reference in references if not reference.altered]
    extractions = extractor.extract_all([reference.text for reference in real])
    result = EngineResult(extractor.engine, len(real))
    for reference, extraction in zip(real, extractions, strict=True):
        result.failures += extraction.fields is None
        result.elapsed_ms += extraction.elapsed_ms
        found = as_annotation(extraction.fields)
        norm_counts = result.by_norm.setdefault(reference.norm, {})
        for name in FIELDS:
            counts = count_field(name, reference.value(name), found[name])
            result.by_field.setdefault(name, Counts()).add(counts)
            norm_counts.setdefault(name, Counts()).add(counts)
    return result


def decide(results: list[EngineResult]) -> Decision:
    """Regla fijada de antemano: mayor F1 promedio en los campos clave.

    Con menos de 5 puntos de diferencia es empate y se mantiene el motor por defecto.
    """
    return decide_scores({result.engine: result.key_f1() for result in results})


def decide_scores(scores: dict[Engine, float]) -> Decision:
    """La misma regla a partir del F1 promedio de cada motor, por ejemplo uno ya guardado."""
    ranked = sorted(scores, key=lambda engine: scores[engine], reverse=True)
    difference = scores[ranked[0]] - scores[ranked[-1]]
    if difference < TIE_MARGIN:
        return Decision(DEFAULT_ENGINE, tie=True, difference=difference)
    return Decision(ranked[0], tie=False, difference=difference)
