"""Extractor AnyStyle: modelo de aprendizaje automático (CRF) entrenado con referencias.

AnyStyle está escrito en Ruby y no se puede importar desde Python: se ejecuta
anystyle-cli como comando externo, con una referencia por línea, y su salida
JSON (formato CSL) se traduce a ExtractedFields. Fuera de este archivo nadie
sabe que se usa Ruby.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.extraction.base import (
    Author,
    Engine,
    ExtractedFields,
    Extraction,
    ExtractionError,
    ReferenceExtractor,
    elapsed_ms,
)

logger = logging.getLogger(__name__)

YEAR = re.compile(r"\b(1[5-9]|20)\d{2}\b")
# Todo el documento en una sola llamada: arrancar Ruby tarda más que analizar.
DEFAULT_TIMEOUT_SECONDS = 120.0

Runner = Callable[..., subprocess.CompletedProcess[bytes]]


class AnyStyleExtractor(ReferenceExtractor):
    engine = Engine.ANYSTYLE

    def __init__(
        self,
        command: str = "anystyle",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        run: Runner = subprocess.run,
    ) -> None:
        self._command = command
        self._timeout_seconds = timeout_seconds
        self._run = run

    def extract(self, reference: str) -> ExtractedFields:
        return self._parse([reference])[0]

    def extract_all(self, references: list[str]) -> list[Extraction]:
        if not references:
            return []
        start = time.perf_counter()
        try:
            parsed = self._parse(references)
        except ExtractionError as error:
            # Se repite una por una para que el fallo afecte solo a la referencia que lo causa.
            logger.warning("AnyStyle falló con el lote (%s); se procesa una por una", error)
            return super().extract_all(references)
        # Tiempo de cada referencia: el de la llamada repartido entre todas.
        each_ms = elapsed_ms(start) // len(references)
        return [Extraction(fields, each_ms) for fields in parsed]

    def _parse(self, references: list[str]) -> list[ExtractedFields]:
        executable = shutil.which(self._command)
        if executable is None:
            raise ExtractionError(f"No se encontró el comando {self._command} (anystyle-cli)")

        lines = "\n".join(" ".join(reference.split()) for reference in references)
        with tempfile.TemporaryDirectory() as folder:
            input_path = Path(folder) / "referencias.txt"
            input_path.write_text(lines + "\n", encoding="utf-8")
            try:
                completed = self._run(
                    [executable, "--stdout", "-f", "json", "parse", str(input_path)],
                    capture_output=True,
                    timeout=self._timeout_seconds,
                    check=False,
                    env={**os.environ, "RUBYOPT": "-EUTF-8:UTF-8"},
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise ExtractionError(f"AnyStyle no respondió: {error}") from error

        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise ExtractionError(f"AnyStyle terminó con código {completed.returncode}: {detail}")
        try:
            items = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ExtractionError("AnyStyle devolvió una respuesta ilegible") from error
        if not isinstance(items, list) or len(items) != len(references):
            raise ExtractionError("AnyStyle no devolvió una entrada por referencia")
        return [_from_csl(item) for item in items]


def _from_csl(item: dict[str, Any]) -> ExtractedFields:
    """Traduce una entrada CSL de AnyStyle. Cada campo llega como lista de textos."""
    date = _first(item, "date")
    year = YEAR.search(date) if date else None
    return ExtractedFields(
        authors=tuple(
            Author(
                family=str(person.get("family") or person.get("literal") or "").strip(),
                given=str(person.get("given") or "").strip(),
            )
            for person in item.get("author") or []
            if isinstance(person, dict)
        ),
        year=int(year.group()) if year else None,
        title=_first(item, "title"),
        container=_first(item, "container-title"),
        publisher=_first(item, "publisher"),
        volume=_first(item, "volume"),
        issue=_first(item, "issue"),
        pages=_first(item, "pages"),
        doi=_first(item, "doi"),
    )


def _first(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None
