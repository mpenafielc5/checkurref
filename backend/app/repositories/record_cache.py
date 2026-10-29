"""Caché compartida de obras por DOI (tabla registros_crossref).

Un DOI se consulta una sola vez para todos los usuarios. También guarda las
obras de OpenAlex que tienen DOI: metadatos.fuente dice de dónde vino cada una,
y la verificación puede enlazar cualquiera de ellas por su DOI.
"""

import logging
from dataclasses import asdict
from typing import Any

import httpx

from app.extraction.base import Author
from app.repositories.supabase_http import SupabaseUnavailableError, ensure_ok
from app.sources.records import Source, SourceRecord

logger = logging.getLogger(__name__)

# Largos de las columnas de registros_crossref.
DOI_LENGTH = 255
CONTAINER_LENGTH = 255
TYPE_LENGTH = 50


class SupabaseRecordCache:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._url = f"{rest_url}/registros_crossref"
        self._client = client

    def get(self, doi: str) -> SourceRecord | None:
        try:
            response = ensure_ok(
                self._client.get(self._url, params={"doi": f"eq.{doi}", "select": "metadatos"})
            )
        except (httpx.HTTPError, SupabaseUnavailableError) as error:
            # Sin caché el análisis sigue: solo consulta la fuente.
            logger.warning("No se pudo leer la caché del DOI %s: %s", doi, error)
            return None
        rows = response.json()
        return _from_row(rows[0]["metadatos"]) if rows else None

    def put(self, records: list[SourceRecord]) -> None:
        rows = [_to_row(record) for record in records if record.doi]
        if not rows:
            return
        try:
            ensure_ok(
                self._client.post(
                    self._url,
                    json=rows,
                    params={"on_conflict": "doi"},
                    headers={"Prefer": "resolution=merge-duplicates"},
                )
            )
        except (httpx.HTTPError, SupabaseUnavailableError) as error:
            # La obra ya se obtuvo; solo no queda en la caché.
            logger.warning("No se pudo guardar en la caché: %s", error)


def _to_row(record: SourceRecord) -> dict[str, Any]:
    fields = asdict(record)
    fields.pop("raw")
    fields["source"] = record.source.value
    return {
        "doi": (record.doi or "")[:DOI_LENGTH],
        "titulo": record.title,
        "autores": [asdict(author) for author in record.authors],
        "anio": record.year,
        "contenedor": record.container[:CONTAINER_LENGTH] if record.container else None,
        "tipo": record.work_type[:TYPE_LENGTH] if record.work_type else None,
        # Los campos ya traducidos, para rearmar el registro, y la respuesta original.
        "metadatos": {"fuente": record.source.value, "campos": fields, "original": record.raw},
    }


def _from_row(metadata: dict[str, Any]) -> SourceRecord:
    fields = dict(metadata["campos"])
    fields["source"] = Source(fields["source"])
    fields["authors"] = tuple(Author(**author) for author in fields["authors"])
    fields["other_years"] = tuple(fields.get("other_years") or ())
    return SourceRecord(**fields, raw=metadata.get("original") or {})
