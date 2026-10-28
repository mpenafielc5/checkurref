"""Prueba manual de la extracción con PDF reales que no se suben al repositorio.

Uso (desde backend/):
    ./.venv/Scripts/python -m scripts.inspect_pdf pdf-locales/*.pdf
"""

import sys
import time
from pathlib import Path

from app.pipeline.errors import PdfProcessingError
from app.pipeline.references_section import extract_reference_section
from app.pipeline.segmentation import segment_references


def inspect(path: Path) -> bool:
    print(f"\n=== {path.name}")
    start = time.perf_counter()
    try:
        section = extract_reference_section(path.read_bytes())
        segmentation = segment_references(section)
    except PdfProcessingError as error:
        print(f"Error: {error}")
        return False
    elapsed = (time.perf_counter() - start) * 1000

    references = segmentation.references
    print(f"Título: {section.heading!r} (página {section.page}) · {elapsed:.0f} ms")
    print(f"Líneas de la sección: {len(section.lines)}")
    print(f"Referencias: {len(references)} · norma de la lista: {segmentation.norm.value}")
    for reference in references:
        mark = f"  << {reference.issue}" if reference.issue else ""
        print(f"  {reference.order:>3}. [{reference.norm.value}] {reference.text}{mark}")
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
