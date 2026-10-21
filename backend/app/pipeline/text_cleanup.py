"""Limpieza del texto antes de separar las referencias.

1. Quita encabezados y pies de página repetidos y los números de página, que en
   un salto de página se cuelan en medio de una referencia.
2. Une las líneas cortadas: palabras partidas con guion, DOI y URL partidos y
   frases que continúan en minúscula en la línea siguiente.

Una referencia nueva empieza con mayúscula (APA) o con [n] (IEEE), así que las
reglas de unión nunca juntan dos referencias distintas.
"""

import re
from collections import Counter
from dataclasses import replace

from app.pipeline.pdf_text import TextLine

# Líneas del borde superior e inferior de cada página que se revisan.
EDGE_LINES = 2
# Un encabezado se considera repetido si aparece en al menos esta fracción de páginas.
REPEATED_SHARE = 0.5
MIN_PAGES_FOR_REPEATED = 2
# Los encabezados y pies de página son cortos; una línea más larga es contenido.
MAX_FURNITURE_WORDS = 12

PAGE_NUMBER = re.compile(r"^(p[aá]g(ina)?\.?\s*)?\d{1,4}(\s*(de|of|/)\s*\d{1,4})?$", re.IGNORECASE)
URL_OR_DOI = re.compile(r"(https?://|www\.|doi\.org/|^doi:|^10\.\d{4,9}/)", re.IGNORECASE)
URL_CONTINUATION_CHARS = set("/._-=?&%#~")


def remove_page_furniture(pages: list[list[TextLine]]) -> list[list[TextLine]]:
    """Quita números de página y encabezados o pies repetidos en muchas páginas."""
    repeated = _repeated_edge_texts(pages)
    cleaned: list[list[TextLine]] = []
    for lines in pages:
        edges = _edge_indexes(len(lines))
        cleaned.append(
            [
                line
                for index, line in enumerate(lines)
                if index not in edges
                or not (PAGE_NUMBER.match(line.text) or _edge_key(line.text) in repeated)
            ]
        )
    return cleaned


def join_broken_lines(lines: list[TextLine]) -> list[TextLine]:
    """Une cada línea con la anterior cuando es la continuación de la misma frase."""
    joined: list[TextLine] = []
    for line in lines:
        if joined:
            merged = _merge(joined[-1].text, line.text)
            if merged is not None:
                joined[-1] = replace(joined[-1], text=merged)
                continue
        joined.append(line)
    return joined


def _merge(previous: str, current: str) -> str | None:
    """Texto unido si `current` continúa a `previous`; None si es una línea nueva."""
    last_token = previous.rsplit(" ", 1)[-1]
    first = current[0]

    if previous.endswith("-"):
        if URL_OR_DOI.search(last_token):
            return previous + current  # guion propio del DOI o la URL: se conserva
        if len(previous) > 1 and previous[-2].isalpha() and first.islower():
            return previous[:-1] + current  # palabra partida: se quita el guion
        if len(previous) > 1 and previous[-2].isdigit() and first.isdigit():
            return previous + current  # rango de páginas partido, por ejemplo 45-60
        return None

    if URL_OR_DOI.search(last_token) and _looks_like_url_continuation(current):
        return previous + current

    if not previous.endswith(".") and first.islower():
        return f"{previous} {current}"
    return None


def _looks_like_url_continuation(text: str) -> bool:
    # Se mira solo el primer carácter: una referencia nueva empieza con mayúscula
    # o con [n], aunque su primer apellido lleve guion (Delgado-Quirós).
    first = text[0]
    return first.islower() or first.isdigit() or first in URL_CONTINUATION_CHARS


def _edge_indexes(count: int) -> set[int]:
    return set(range(min(EDGE_LINES, count))) | set(range(max(count - EDGE_LINES, 0), count))


def _edge_key(text: str) -> str:
    # Los números cambian de una página a otra ("Capítulo 2 · 14"): se ignoran.
    return re.sub(r"\d+", "#", " ".join(text.lower().split()))


def _repeated_edge_texts(pages: list[list[TextLine]]) -> set[str]:
    if len(pages) < MIN_PAGES_FOR_REPEATED:
        return set()
    counts: Counter[str] = Counter()
    for lines in pages:
        counts.update(
            {
                _edge_key(lines[index].text)
                for index in _edge_indexes(len(lines))
                if len(lines[index].text.split()) <= MAX_FURNITURE_WORDS
            }
        )
    threshold = max(MIN_PAGES_FOR_REPEATED, REPEATED_SHARE * len(pages))
    return {key for key, count in counts.items() if count >= threshold}
