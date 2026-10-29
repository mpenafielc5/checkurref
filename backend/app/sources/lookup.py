"""Busca en las fuentes la obra que cita una referencia (T08).

1. Con DOI: búsqueda directa, primero en la caché, luego en Crossref y, si no
   la tiene, en OpenAlex.
2. Sin DOI, o con un DOI que ninguna fuente tiene: búsqueda por título y autor,
   con el mismo orden de fuentes.
3. Sin DOI ni título: no se consulta.

Solo se habla de "no encontrada" cuando todas las fuentes respondieron. Si
alguna no respondió y la obra no apareció, el resultado es un error de consulta:
no se sabe si existe, así que no se marca como No verificable.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.extraction.base import ExtractedFields
from app.sources.http import QueryFailedError
from app.sources.records import Source, SourceRecord, normalize_doi

logger = logging.getLogger(__name__)


class Strategy(str, Enum):
    """Valores del tipo estrategia_busqueda de la base de datos."""

    DIRECT_DOI = "doi_directo"
    BIBLIOGRAPHIC_SEARCH = "busqueda_bibliografica"
    NO_QUERY = "sin_consulta"


@dataclass(frozen=True)
class LookupResult:
    strategy: Strategy
    candidates: tuple[SourceRecord, ...]  # vacío si ninguna fuente tiene la obra
    query_failed: bool = False  # error de consulta: fuera del índice de veracidad


class BibliographicSource(Protocol):
    name: Source

    async def by_doi(self, doi: str) -> SourceRecord | None: ...

    async def search(self, title: str, author: str | None = None) -> list[SourceRecord]: ...


class RecordCache(Protocol):
    """Caché de obras por DOI. Sus fallos no deben detener el análisis."""

    def get(self, doi: str) -> SourceRecord | None: ...

    def put(self, records: list[SourceRecord]) -> None: ...


class ReferenceLookup:
    def __init__(self, sources: list[BibliographicSource], cache: RecordCache) -> None:
        self._sources = sources  # en orden de preferencia: Crossref y luego OpenAlex
        self._cache = cache
        # Las búsquedas sin DOI se recuerdan mientras vive el proceso (un lote repite obras).
        self._searches: dict[tuple[str, str], tuple[SourceRecord, ...]] = {}

    async def lookup(self, fields: ExtractedFields) -> LookupResult:
        doi = normalize_doi(fields.doi)
        if doi:
            result = await self._by_doi(doi)
            if result.candidates or result.query_failed or not fields.title:
                return result
            # Un DOI que nadie tiene puede estar mal escrito: se intenta por título.
        if fields.title:
            author = fields.authors[0].family if fields.authors else None
            return await self._search(fields.title, author)
        return LookupResult(Strategy.NO_QUERY, ())

    async def _by_doi(self, doi: str) -> LookupResult:
        cached = await asyncio.to_thread(self._cache.get, doi)
        if cached:
            return LookupResult(Strategy.DIRECT_DOI, (cached,))
        failed = False
        for source in self._sources:
            try:
                record = await source.by_doi(doi)
            except QueryFailedError as error:
                logger.warning("%s no respondió al buscar el DOI %s: %s", source.name, doi, error)
                failed = True
                continue
            if record:
                await asyncio.to_thread(self._cache.put, [record])
                return LookupResult(Strategy.DIRECT_DOI, (record,))
        return LookupResult(Strategy.DIRECT_DOI, (), query_failed=failed)

    async def _search(self, title: str, author: str | None) -> LookupResult:
        key = (" ".join(title.lower().split()), (author or "").lower())
        if key in self._searches:
            return LookupResult(Strategy.BIBLIOGRAPHIC_SEARCH, self._searches[key])
        failed = False
        for source in self._sources:
            try:
                candidates = tuple(await source.search(title, author))
            except QueryFailedError as error:
                logger.warning("%s no respondió al buscar %r: %s", source.name, title, error)
                failed = True
                continue
            if candidates:
                self._searches[key] = candidates
                # Se guardan para que la verificación pueda enlazar el registro elegido.
                await asyncio.to_thread(
                    self._cache.put, [record for record in candidates if record.doi]
                )
                return LookupResult(Strategy.BIBLIOGRAPHIC_SEARCH, candidates)
        if not failed:
            self._searches[key] = ()
        return LookupResult(Strategy.BIBLIOGRAPHIC_SEARCH, (), query_failed=failed)
