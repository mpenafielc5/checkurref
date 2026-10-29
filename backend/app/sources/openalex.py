"""Adaptador de OpenAlex, la fuente de respaldo (patrón Adapter).

Cubre muchas revistas en español que no registran DOI en Crossref. Funciona sin
clave; una clave gratuita (OPENALEX_API_KEY) multiplica por 10 el presupuesto
diario de consultas. Sin clave admite 10 consultas por segundo.
"""

from typing import Any

import httpx

from app.extraction.base import Author
from app.sources.http import SourceHttp
from app.sources.records import Source, SourceRecord, normalize_doi

BASE_URL = "https://api.openalex.org"
MAX_CONCURRENT = 5
PER_SECOND = 8.0
CANDIDATES = 3
SELECT = "doi,display_name,authorships,publication_year,primary_location,biblio,type"


class OpenAlexClient:
    name = Source.OPENALEX

    def __init__(
        self, client: httpx.AsyncClient, api_key: str = "", backoff_seconds: float = 1.0
    ) -> None:
        self._http = SourceHttp(client, MAX_CONCURRENT, PER_SECOND, backoff_seconds)
        self._key = {"api_key": api_key} if api_key else {}

    async def by_doi(self, doi: str) -> SourceRecord | None:
        body = await self._http.get_json(
            f"{BASE_URL}/works/https://doi.org/{doi}", params={"select": SELECT, **self._key}
        )
        return _record(body) if body else None

    async def search(self, title: str, author: str | None = None) -> list[SourceRecord]:
        # La búsqueda de OpenAlex no incluye a los autores: se busca solo por título.
        params = {"search": title, "per-page": str(CANDIDATES), "select": SELECT, **self._key}
        body = await self._http.get_json(f"{BASE_URL}/works", params=params)
        return [_record(item) for item in (body or {}).get("results", [])]


def _record(item: dict[str, Any]) -> SourceRecord:
    biblio = item.get("biblio") or {}
    location = (item.get("primary_location") or {}).get("source") or {}
    first_page, last_page = biblio.get("first_page"), biblio.get("last_page")
    pages = f"{first_page}-{last_page}" if first_page and last_page else first_page
    return SourceRecord(
        source=Source.OPENALEX,
        doi=normalize_doi(item.get("doi")),
        title=item.get("display_name") or None,
        # OpenAlex da el nombre completo sin separar ("Francisco José García-Peñalvo"):
        # con dos apellidos no se puede partir con seguridad, así que va entero.
        authors=tuple(
            Author(family=str(authorship["author"].get("display_name") or "").strip())
            for authorship in item.get("authorships") or []
            if authorship.get("author")
        ),
        year=item.get("publication_year"),
        container=location.get("display_name") or None,
        publisher=location.get("host_organization_name") or None,
        volume=biblio.get("volume") or None,
        issue=biblio.get("issue") or None,
        pages=pages or None,
        work_type=item.get("type") or None,
        score=item.get("relevance_score"),
        raw=item,
    )
