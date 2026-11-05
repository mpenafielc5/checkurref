"""Verifica una referencia: la busca en las fuentes y decide su veredicto (T13).

Une la búsqueda (app/sources) con el motor de decisión. Si la búsqueda por
título encuentra la obra con otro año, se vuelve a pedir por DOI: la búsqueda de
Crossref solo trae el año de la publicación en línea, y la referencia puede citar
con razón el del número impreso de la revista (SourceRecord.other_years).
"""

from typing import Protocol

from app.extraction.base import ExtractedFields
from app.sources.lookup import LookupResult, Strategy
from app.verification.decision import (
    THRESHOLDS,
    CheckedField,
    NliScorer,
    Thresholds,
    Verification,
    decide,
)


class Lookup(Protocol):
    async def lookup(self, fields: ExtractedFields) -> LookupResult: ...


class ReferenceVerifier:
    def __init__(self, lookup: Lookup, nli: NliScorer, thresholds: Thresholds = THRESHOLDS) -> None:
        self._lookup = lookup
        self._nli = nli
        self._thresholds = thresholds

    async def verify(self, text: str, fields: ExtractedFields | None) -> Verification:
        """`fields` es None si el extractor no pudo con la referencia: no se puede buscar."""
        fields = fields or ExtractedFields()
        result = await self._lookup.lookup(fields)
        verification = decide(text, fields, result, self._nli, self._thresholds)
        doi = _doi_to_complete(verification)
        if not doi:
            return verification
        complete = await self._lookup.lookup(ExtractedFields(doi=doi))
        if not complete.candidates:
            return verification
        retry = LookupResult(result.strategy, complete.candidates)
        return decide(text, fields, retry, self._nli, self._thresholds)


def _doi_to_complete(verification: Verification) -> str | None:
    """DOI de la obra si salió de la búsqueda por título y el año no coincide."""
    record, year = verification.record, verification.check(CheckedField.YEAR)
    if verification.strategy is not Strategy.BIBLIOGRAPHIC_SEARCH or not record:
        return None
    return record.doi if year and not year.matches else None
