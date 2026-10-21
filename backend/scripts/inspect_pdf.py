"""Prueba manual de la extracción con PDF reales que no se suben al repositorio.

Uso (desde backend/):
    ./.venv/Scripts/python -m scripts.inspect_pdf pdf-locales/*.pdf
"""

import sys
import time
from pathlib import Path

from app.pipeline.errors import PdfProcessingError
from app.pipeline.references_section import extract_reference_section

PREVIEW_LINES = 4


def inspect(path: Path) -> bool:
    print(f"\n=== {path.name}")
    start = time.perf_counter()
    try:
        section = extract_reference_section(path.read_bytes())
    except PdfProcessingError as error:
        print(f"Error: {error}")
        return False
    elapsed = (time.perf_counter() - start) * 1000

    print(f"Título: {section.heading!r} (página {section.page}) · {elapsed:.0f} ms")
    print(f"Líneas de la sección: {len(section.lines)}")
    for line in section.lines[:PREVIEW_LINES]:
        print(f"  [p{line.page} x{line.x0:.0f}] {line.text}")
    if len(section.lines) > PREVIEW_LINES:
        print("  …")
        print(f"  [p{section.lines[-1].page}] {section.lines[-1].text}")
    return True


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__)
        return 1
    results = [inspect(Path(path)) for path in paths]
    print(f"\n{sum(results)} de {len(results)} PDF con sección de referencias encontrada.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
