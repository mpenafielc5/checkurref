"""Adaptador de Crossref, la fuente principal (patrón Adapter).

Con el correo de contacto en el User-Agent y en `mailto`, las consultas van al
polite pool. Sus límites desde diciembre de 2025: 3 consultas simultáneas,
10 por segundo de un solo registro y 3 por segundo de búsquedas.
"""

from typing import Any
from urllib.parse import quote

import httpx

from app.extraction.base import Author
from app.sources.http import SourceHttp
from app.sources.records import Source, SourceRecord, normalize_doi

BASE_URL = "https://api.crossref.org"
MAX_CONCURRENT = 3
# El ritmo de las búsquedas, el más bajo, vale para todas las consultas.
PER_SECOND = 3.0
CANDIDATES = 3
# Campos de las búsquedas, para no traer las listas de referencias de cada obra.
# La búsqueda no admite "journal-issue": la consulta por DOI (sin select) sí lo trae.
SELECT = (
    "DOI,title,author,issued,published-print,published-online,"
    "container-title,publisher,volume,issue,page,type,score"
)
# "issued" es la fecha más temprana (a menudo la publicación en línea del
# artículo); la referencia puede citar con razón el año del número de la
# revista, que llega después y viene en "journal-issue".
DATE_FIELDS = ("issued", "published-print", "published-online")


def user_agent(app_version: str, mailto: str) -> str:
    contact = f" (mailto:{mailto})" if mailto else ""
    return f"CheckUrRef/{app_version}{contact}"


class CrossrefClient:
    name = Source.CROSSREF

    def __init__(
        self, client: httpx.AsyncClient, mailto: str = "", backoff_seconds: float = 1.0
    ) -> None:
        self._http = SourceHttp(client, MAX_CONCURRENT, PER_SECOND, backoff_seconds)
        self._mailto = {"mailto": mailto} if mailto else {}

    async def by_doi(self, doi: str) -> SourceRecord | None:
        body = await self._http.get_json(
            f"{BASE_URL}/works/{quote(doi, safe='/')}", params=self._mailto or None
        )
        return _record(body["message"]) if body else None

    async def search(self, title: str, author: str | None = None) -> list[SourceRecord]:
        params = {"query.bibliographic": title, "rows": str(CANDIDATES), "select": SELECT}
        if author:
            params["query.author"] = author
        body = await self._http.get_json(f"{BASE_URL}/works", params={**params, **self._mailto})
        items = body["message"]["items"] if body else []
        return [_record(item) for item in items]


def _record(item: dict[str, Any]) -> SourceRecord:
    journal_issue = item.get("journal-issue") or {}
    dates = [item.get(key) for key in DATE_FIELDS] + [journal_issue.get(key) for key in DATE_FIELDS]
    years = [year for date in dates if (year := _year(date))]
    return SourceRecord(
        source=Source.CROSSREF,
        doi=normalize_doi(item.get("DOI")),
        title=_first(item.get("title")),
        authors=tuple(
            Author(
                family=str(person.get("family") or person.get("name") or "").strip(),
                given=str(person.get("given") or "").strip(),
            )
            for person in item.get("author") or []
        ),
        year=years[0] if years else None,
        other_years=tuple(sorted(set(years[1:]) - set(years[:1]))),
        container=_first(item.get("container-title")),
        publisher=item.get("publisher") or None,
        volume=item.get("volume") or None,
        issue=item.get("issue") or None,
        pages=item.get("page") or None,
        work_type=item.get("type") or None,
        score=item.get("score"),
        raw=item,
    )


def _year(date: dict[str, Any] | None) -> int | None:
    parts = (date or {}).get("date-parts") or [[None]]
    year = parts[0][0] if parts and parts[0] else None
    return year if isinstance(year, int) else None


def _first(values: list[str] | None) -> str | None:
    return " ".join(values[0].split()) if values else None
