"""Consulta de Crossref y OpenAlex con caché, reintentos y límites (T08). Sin red."""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from app.extraction.base import Author, ExtractedFields
from app.repositories.record_cache import SupabaseRecordCache
from app.sources.crossref import CrossrefClient, user_agent
from app.sources.http import ATTEMPTS, QueryFailedError, RateLimiter, SourceHttp
from app.sources.lookup import ReferenceLookup, Strategy
from app.sources.openalex import OpenAlexClient
from app.sources.records import Source, SourceRecord, normalize_doi

DOI = "10.1234/ra.2021.8"
CROSSREF_WORK = {
    "DOI": "10.1234/RA.2021.8",
    "title": ["Redes neuronales en la educación superior"],
    "author": [{"family": "Pérez", "given": "María"}, {"name": "Grupo UNEMI"}],
    "issued": {"date-parts": [[2021, 3]]},
    "published-online": {"date-parts": [[2021, 3]]},
    # Primero en línea y luego en el número de la revista del año siguiente.
    "journal-issue": {"issue": "1", "published-online": {"date-parts": [[2022, 1]]}},
    "container-title": ["Revista Andina"],
    "publisher": "Editorial Andina",
    "volume": "8",
    "issue": "1",
    "page": "10-25",
    "type": "journal-article",
    "score": 42.5,
}
OPENALEX_WORK = {
    "doi": "https://doi.org/10.1234/ra.2021.8",
    "display_name": "Redes neuronales en la educación superior",
    "authorships": [{"author": {"display_name": "María Pérez Vera"}}],
    "publication_year": 2021,
    "primary_location": {
        "source": {"display_name": "Revista Andina", "host_organization_name": "UNEMI"}
    },
    "biblio": {"volume": "8", "issue": "1", "first_page": "10", "last_page": "25"},
    "type": "article",
}

Handler = Callable[[httpx.Request], httpx.Response | Awaitable[httpx.Response]]


def client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# --- DOI ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10.1234/RA.2021.8", DOI),
        ("https://doi.org/10.1234/ra.2021.8.", DOI),
        ("http://dx.doi.org/10.1234/ra.2021.8", DOI),
        ("doi: 10.1234/ra.2021.8", DOI),
        ("doi:https://doi.org/10.1234/ra.2021.8", DOI),  # prefijo repetido
        ("no es un DOI", None),
        (None, None),
    ],
)
def test_normaliza_el_doi_antes_de_buscarlo(value: str | None, expected: str | None) -> None:
    assert normalize_doi(value) == expected


# --- Adaptadores ----------------------------------------------------------------------------


def test_crossref_busca_por_doi_y_traduce_al_formato_comun() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"message": CROSSREF_WORK})

    record = asyncio.run(CrossrefClient(client(handler), mailto="equipo@ejemplo.com").by_doi(DOI))

    assert record == SourceRecord(
        source=Source.CROSSREF,
        doi=DOI,
        title="Redes neuronales en la educación superior",
        authors=(Author("Pérez", "María"), Author("Grupo UNEMI")),
        year=2021,
        other_years=(2022,),
        container="Revista Andina",
        publisher="Editorial Andina",
        volume="8",
        issue="1",
        pages="10-25",
        work_type="journal-article",
        score=42.5,
    )
    assert seen[0].url.path == f"/works/{DOI}"
    assert seen[0].url.params["mailto"] == "equipo@ejemplo.com"  # polite pool


def test_crossref_busca_por_titulo_y_autor() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"message": {"items": [CROSSREF_WORK]}})

    found = asyncio.run(CrossrefClient(client(handler)).search("Redes neuronales", "Pérez"))

    assert [record.doi for record in found] == [DOI]
    params = seen[0].url.params
    assert params["query.bibliographic"] == "Redes neuronales"
    assert params["query.author"] == "Pérez"
    assert params["rows"] == "3"


def test_user_agent_lleva_el_correo_de_contacto() -> None:
    assert (
        user_agent("0.1.0", "equipo@ejemplo.com") == "CheckUrRef/0.1.0 (mailto:equipo@ejemplo.com)"
    )
    assert user_agent("0.1.0", "") == "CheckUrRef/0.1.0"


def test_openalex_traduce_al_mismo_formato_comun() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == "clave"
        return httpx.Response(200, json=OPENALEX_WORK)

    record = asyncio.run(OpenAlexClient(client(handler), api_key="clave").by_doi(DOI))

    assert record is not None
    assert (record.source, record.doi, record.year, record.pages) == (
        Source.OPENALEX,
        DOI,
        2021,
        "10-25",
    )
    assert record.authors == (Author("María Pérez Vera"),)
    assert (record.container, record.publisher) == ("Revista Andina", "UNEMI")


def test_obra_inexistente_no_es_un_error() -> None:
    record = asyncio.run(CrossrefClient(client(lambda _: httpx.Response(404))).by_doi(DOI))

    assert record is None


# --- Reintentos y límites -------------------------------------------------------------------


def test_reintenta_ante_429_respetando_retry_after() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"message": CROSSREF_WORK})

    record = asyncio.run(CrossrefClient(client(handler), backoff_seconds=0).by_doi(DOI))

    assert record is not None
    assert len(calls) == 3


@pytest.mark.parametrize("status", [400, 401, 500])
def test_otro_error_de_la_fuente_no_se_toma_como_obra_inexistente(status: int) -> None:
    with pytest.raises(QueryFailedError):
        asyncio.run(CrossrefClient(client(lambda _: httpx.Response(status))).search("Título"))


@pytest.mark.parametrize("status", [502, 503])
def test_agotados_los_reintentos_es_error_de_consulta(status: int) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(status)

    with pytest.raises(QueryFailedError):
        asyncio.run(CrossrefClient(client(handler), backoff_seconds=0).by_doi(DOI))
    assert len(calls) == ATTEMPTS


def test_no_pasa_de_tres_consultas_simultaneas() -> None:
    in_flight, peak = 0, 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.1)  # sin el semáforo, las 10 se solaparían
        in_flight -= 1
        return httpx.Response(200, json={})

    async def run() -> None:
        http = SourceHttp(client(handler), max_concurrent=3, per_second=1000)
        await asyncio.gather(*(http.get_json("https://fuente/obra") for _ in range(10)))

    asyncio.run(run())

    assert peak == 3


def test_respeta_el_ritmo_por_segundo() -> None:
    async def run() -> float:
        limiter = RateLimiter(per_second=50)
        start = time.perf_counter()
        for _ in range(6):
            await limiter.wait()
        return time.perf_counter() - start

    # En Windows, asyncio.sleep puede despertar hasta ~16 ms antes (resolución del reloj).
    assert asyncio.run(run()) >= 5 / 50 - 0.02


# --- Coordinador ----------------------------------------------------------------------------


def work(source: Source = Source.CROSSREF, doi: str | None = DOI) -> SourceRecord:
    return SourceRecord(source=source, doi=doi, title="Redes neuronales")


class FakeSource:
    def __init__(
        self,
        name: Source,
        by_doi: SourceRecord | None = None,
        found: list[SourceRecord] | None = None,
        fails: bool = False,
    ) -> None:
        self.name = name
        self._by_doi = by_doi
        self._found = found or []
        self._fails = fails
        self.calls: list[str] = []

    async def by_doi(self, doi: str) -> SourceRecord | None:
        self.calls.append(f"doi:{doi}")
        if self._fails:
            raise QueryFailedError("caída")
        return self._by_doi

    async def search(self, title: str, author: str | None = None) -> list[SourceRecord]:
        self.calls.append(f"búsqueda:{title}|{author}")
        if self._fails:
            raise QueryFailedError("caída")
        return self._found


class MemoryCache:
    def __init__(self, records: list[SourceRecord] | None = None) -> None:
        self.records = {record.doi: record for record in records or [] if record.doi}

    def get(self, doi: str) -> SourceRecord | None:
        return self.records.get(doi)

    def put(self, records: list[SourceRecord]) -> None:
        self.records.update({record.doi: record for record in records if record.doi})


REFERENCE = ExtractedFields(
    authors=(Author("Pérez", "M."),), title="Redes neuronales", doi=f"https://doi.org/{DOI}"
)


def lookup(*sources: FakeSource, cache: MemoryCache | None = None) -> ReferenceLookup:
    return ReferenceLookup(list(sources), cache or MemoryCache())


def test_un_doi_en_cache_no_se_vuelve_a_consultar() -> None:
    crossref = FakeSource(Source.CROSSREF)

    result = asyncio.run(lookup(crossref, cache=MemoryCache([work()])).lookup(REFERENCE))

    assert result.strategy is Strategy.DIRECT_DOI
    assert result.candidates == (work(),)
    assert crossref.calls == []


def test_openalex_responde_si_crossref_no_tiene_el_doi() -> None:
    cache = MemoryCache()
    crossref = FakeSource(Source.CROSSREF)
    openalex = FakeSource(Source.OPENALEX, by_doi=work(Source.OPENALEX))

    result = asyncio.run(lookup(crossref, openalex, cache=cache).lookup(REFERENCE))

    assert result.candidates == (work(Source.OPENALEX),)
    assert crossref.calls == [f"doi:{DOI}"]  # el DOI ya va normalizado
    assert DOI in cache.records


def test_si_una_fuente_no_responde_es_error_de_consulta_y_no_no_verificable() -> None:
    crossref = FakeSource(Source.CROSSREF, fails=True)
    openalex = FakeSource(Source.OPENALEX)

    result = asyncio.run(lookup(crossref, openalex).lookup(REFERENCE))

    assert result.candidates == ()
    assert result.query_failed is True


def test_doi_que_nadie_tiene_se_intenta_por_titulo_y_autor() -> None:
    found = work(doi="10.5555/otro")
    crossref = FakeSource(Source.CROSSREF, found=[found])

    result = asyncio.run(lookup(crossref, FakeSource(Source.OPENALEX)).lookup(REFERENCE))

    assert result.strategy is Strategy.BIBLIOGRAPHIC_SEARCH
    assert result.candidates == (found,)
    assert crossref.calls == [f"doi:{DOI}", "búsqueda:Redes neuronales|Pérez"]


def test_sin_doi_ni_titulo_no_se_consulta() -> None:
    crossref = FakeSource(Source.CROSSREF)

    result = asyncio.run(lookup(crossref).lookup(ExtractedFields(year=2021)))

    assert result.strategy is Strategy.NO_QUERY
    assert crossref.calls == []


def test_una_busqueda_repetida_no_vuelve_a_consultar() -> None:
    crossref = FakeSource(Source.CROSSREF, found=[work()])
    without_doi = ExtractedFields(authors=(Author("Pérez", "M."),), title="Redes neuronales")

    async def run() -> None:
        reference_lookup = lookup(crossref)
        await reference_lookup.lookup(without_doi)
        await reference_lookup.lookup(without_doi)

    asyncio.run(run())

    assert crossref.calls == ["búsqueda:Redes neuronales|Pérez"]


# --- Caché en Supabase ----------------------------------------------------------------------

REST_URL = "https://proyecto.supabase.co/rest/v1"


def test_la_cache_guarda_y_rearma_la_obra() -> None:
    table: dict[str, dict[str, Any]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.headers["Prefer"] == "resolution=merge-duplicates"
            for row in json.loads(request.content):
                table[row["doi"]] = row
            return httpx.Response(201)
        doi = request.url.params["doi"].removeprefix("eq.")
        return httpx.Response(200, json=[table[doi]] if doi in table else [])

    cache = SupabaseRecordCache(REST_URL, httpx.Client(transport=httpx.MockTransport(handler)))
    record = asyncio.run(
        CrossrefClient(
            client(lambda _: httpx.Response(200, json={"message": CROSSREF_WORK}))
        ).by_doi(DOI)
    )
    assert record is not None

    cache.put([record])

    assert cache.get(DOI) == record
    assert table[DOI]["anio"] == 2021
    assert table[DOI]["metadatos"]["fuente"] == "crossref"
    assert cache.get("10.9999/no-esta") is None


def test_si_la_cache_falla_el_analisis_sigue() -> None:
    cache = SupabaseRecordCache(
        REST_URL, httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    )

    assert cache.get(DOI) is None
    cache.put([work()])  # no lanza
