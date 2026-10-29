"""Campos que extrajo cada motor de cada referencia (tabla extracciones)."""

from dataclasses import asdict
from typing import Any, Protocol

import httpx

from app.extraction.base import Engine, Extraction
from app.repositories.supabase_http import send

# Largos de las columnas de extracciones: un texto más largo se recorta.
LENGTHS = {"contenedor": 255, "editorial": 255, "volumen": 20, "numero": 20, "paginas": 30}
DOI_LENGTH = 255


class ExtractionRepository(Protocol):
    def save(self, engine: Engine, extractions: dict[str, Extraction]) -> None:
        """Guarda la extracción de cada referencia, por el id de la referencia."""
        ...


class SupabaseExtractionRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/extracciones"
        self._client = client

    def save(self, engine: Engine, extractions: dict[str, Extraction]) -> None:
        rows = [
            _row(reference_id, engine, extraction)
            for reference_id, extraction in extractions.items()
        ]
        if rows:
            send(self._client, "POST", self._url, json=rows)


def _row(reference_id: str, engine: Engine, extraction: Extraction) -> dict[str, Any]:
    # Si el motor falló con esta referencia, la fila queda sin campos: así se ve
    # que se intentó y la verificación la tratará como no consultable.
    fields = extraction.fields
    values: dict[str, Any] = {
        "autores": [asdict(author) for author in fields.authors] if fields else None,
        "anio": fields.year if fields else None,
        "titulo": fields.title if fields else None,
        "contenedor": fields.container if fields else None,
        "editorial": fields.publisher if fields else None,
        "volumen": fields.volume if fields else None,
        "numero": fields.issue if fields else None,
        "paginas": fields.pages if fields else None,
        "doi": fields.doi[:DOI_LENGTH] if fields and fields.doi else None,
    }
    for column, length in LENGTHS.items():
        if values[column]:
            values[column] = values[column][:length]
    return {
        "referencia_id": reference_id,
        "motor": engine.value,
        **values,
        "tiempo_ms": extraction.elapsed_ms,
    }
