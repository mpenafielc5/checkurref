"""Arma el verificador de un análisis: fuentes, caché y modelo NLI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from app.core.config import Settings
from app.sources.crossref import CrossrefClient, user_agent
from app.sources.lookup import RecordCache, ReferenceLookup
from app.sources.openalex import OpenAlexClient
from app.verification.decision import NliScorer
from app.verification.verifier import ReferenceVerifier

SOURCE_TIMEOUT_SECONDS = 20.0


@asynccontextmanager
async def open_verifier(
    settings: Settings, cache: RecordCache, nli: NliScorer
) -> AsyncIterator[ReferenceVerifier]:
    """Verificador con su propia conexión a Crossref y OpenAlex.

    Vive lo que dura un análisis: los límites de concurrencia de las fuentes
    (asyncio) quedan atados al bucle de eventos que los crea.
    """
    headers = {"User-Agent": user_agent(settings.app_version, settings.crossref_mailto)}
    async with httpx.AsyncClient(headers=headers, timeout=SOURCE_TIMEOUT_SECONDS) as client:
        sources = [
            CrossrefClient(client, mailto=settings.crossref_mailto),
            OpenAlexClient(client, api_key=settings.openalex_api_key),
        ]
        yield ReferenceVerifier(ReferenceLookup(sources, cache), nli)
