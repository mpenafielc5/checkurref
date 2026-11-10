"""Caso de uso: comparar los motores de extracción sobre una referencia (CU-08, HU-13).

Cada motor procesa el mismo texto. Si uno no puede (por ejemplo, AnyStyle no está
instalado), su resultado trae el motivo y no se reemplaza por el otro: el
Laboratorio existe justamente para ver qué hace cada uno.
"""

from app.benchmark.gold_set import same_value
from app.extraction.base import ExtractedFields, Extraction, ReferenceExtractor
from app.schemas.lab import EngineFields, EngineOutput, LabComparison
from app.sources.records import normalize_doi

AUTHOR_SEPARATOR = "; "


class LabService:
    def __init__(self, extractors: list[ReferenceExtractor]) -> None:
        self._extractors = extractors

    def compare(self, reference: str) -> LabComparison:
        outputs = [_output(extractor, reference) for extractor in self._extractors]
        different = _different_fields(outputs)
        compared = _compared_fields(outputs)
        return LabComparison(
            engines=outputs,
            different_fields=different,
            compared_fields=len(compared),
            matching_fields=len(compared) - len(different),
        )


def _output(extractor: ReferenceExtractor, reference: str) -> EngineOutput:
    [result] = extractor.extract_all([reference])
    return _to_output(extractor, result)


def _to_output(extractor: ReferenceExtractor, result: Extraction) -> EngineOutput:
    return EngineOutput(
        engine=extractor.engine.value,
        elapsed_ms=result.elapsed_ms,
        error=result.error,
        fields=_fields(result.fields) if result.fields else None,
    )


def _fields(fields: ExtractedFields) -> EngineFields:
    authors = AUTHOR_SEPARATOR.join(
        f"{author.family}, {author.given}" if author.given else author.family
        for author in fields.authors
    )
    return EngineFields(
        autores=authors or None,
        anio=str(fields.year) if fields.year else None,
        titulo=fields.title,
        contenedor=fields.container,
        editorial=fields.publisher,
        volumen=fields.volume,
        numero=fields.issue,
        paginas=fields.pages,
        doi=fields.doi,
    )


def _compared_fields(outputs: list[EngineOutput]) -> list[str]:
    """Campos que al menos un motor sacó, en el orden de la tabla."""
    processed = [output.fields for output in outputs if output.fields]
    return [
        name
        for name in EngineFields.model_fields
        if any(getattr(fields, name) for fields in processed)
    ]


def _different_fields(outputs: list[EngineOutput]) -> list[str]:
    processed = [output.fields for output in outputs if output.fields]
    if len(processed) < len(outputs) or len(processed) < 2:
        return []  # sin dos resultados no hay nada que comparar
    first, second = processed
    return [
        name
        for name in _compared_fields(outputs)
        if not _same(name, getattr(first, name), getattr(second, name))
    ]


def _same(name: str, first: str | None, second: str | None) -> bool:
    if not first or not second:
        return not first and not second
    if name == "doi":
        return normalize_doi(first) == normalize_doi(second)
    return same_value(name, first, second)
