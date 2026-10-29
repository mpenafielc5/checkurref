"""Herramienta del estándar de oro (T09). Uso, desde backend/:

python -m scripts.gold_set preparar pdf-locales/*.pdf --salida base.csv
    Separa las referencias de PDF públicos y crea la planilla con id, texto y
    norma detectada. Los campos quedan vacíos: se anotan a mano, sin
    precargarlos con un extractor, para no sesgar la comparación.
python -m scripts.gold_set validar anotado.csv
    Revisa la anotación y cuenta las referencias por norma y tipo de obra.
python -m scripts.gold_set acuerdo miguel.csv jackson.csv
    Acuerdo entre anotadores: coincidencia por campo, kappa y desacuerdos.
python -m scripts.gold_set alterar anotado.csv --salida final.csv
    Agrega las 50 referencias alteradas (semilla fija) y guarda el estándar de oro final.
python -m scripts.gold_set cargar final.csv
    Reemplaza la tabla referencias_oro con el estándar de oro final (usa backend/.env).
"""

import argparse
import sys
from pathlib import Path

from app.benchmark.gold_set import (
    FIELDS,
    TARGET_PER_STRATUM,
    GoldReference,
    agreement,
    make_alterations,
    read_csv,
    strata,
    to_database_row,
    validate,
    write_csv,
)
from app.core.config import get_settings
from app.pipeline.errors import PdfProcessingError
from app.pipeline.references_section import extract_reference_section
from app.pipeline.segmentation import segment_references
from app.repositories.gold_set import SupabaseGoldSetRepository
from app.repositories.supabase_http import shared_client


def prepare(pdfs: list[Path], output: Path) -> int:
    references: list[GoldReference] = []
    for pdf in pdfs:
        try:
            segmentation = segment_references(extract_reference_section(pdf.read_bytes()))
        except PdfProcessingError as error:
            print(f"{pdf.name}: {error}")
            continue
        for reference in segmentation.references:
            references.append(
                GoldReference(
                    id=f"R{len(references) + 1:03d}",
                    text=reference.text,
                    norm=reference.norm.value if reference.norm.value in ("APA", "IEEE") else "",
                    work_type="",
                    notes=reference.issue or "",
                )
            )
        print(f"{pdf.name}: {len(segmentation.references)} referencias")
    write_csv(output, references)
    print(f"Planilla: {output} ({len(references)} referencias). Revisen que cada texto")
    print("coincida con el PDF y completen tipo_obra y los campos tal como aparecen.")
    return 0


def check(path: Path) -> int:
    references = read_csv(path)
    problems = validate(references)
    for problem in problems:
        print(f"- {problem}")
    print(f"\n{len(references)} referencias, {len(problems)} problemas.")
    print(f"\nReferencias reales por norma y tipo de obra (meta: {TARGET_PER_STRATUM}):")
    for (norm, work_type), count in strata(references).items():
        mark = "" if count >= TARGET_PER_STRATUM else f"  faltan {TARGET_PER_STRATUM - count}"
        print(f"  {norm:<5} {work_type:<15} {count:>3}{mark}")
    return 1 if problems else 0


def compare(first: Path, second: Path) -> int:
    result = agreement(read_csv(first), read_csv(second))
    print(f"Referencias anotadas por ambos: {result.common}\n")
    print("Coincidencia exacta por campo:")
    for name in FIELDS:
        print(f"  {name:<11} {result.by_field[name]:.0%}")
    print("\nKappa de Cohen (1 = acuerdo total; desde 0.8, casi perfecto):")
    for label, value in result.kappa.items():
        print(f"  {label:<11} {value:.2f}")
    if result.differences:
        print(f"\nDesacuerdos para resolver ({len(result.differences)}):")
        for difference in result.differences:
            print(f"  - {difference}")
    return 0


def alter(path: Path, output: Path) -> int:
    real = read_csv(path)
    problems = validate(real)
    if problems:
        print(f"Primero corrijan los {len(problems)} problemas que muestra el comando validar.")
        return 1
    altered = make_alterations(real)
    write_csv(output, real + altered)
    print(f"{len(real)} reales + {len(altered)} alteradas en {output}.")
    return 0


def load(path: Path) -> int:
    references = read_csv(path)
    if problems := validate(references):
        print(f"El estándar de oro tiene {len(problems)} problemas: ejecuten validar.")
        return 1
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        print("Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en backend/.env.")
        return 1
    repository = SupabaseGoldSetRepository(
        settings.supabase_rest_url, shared_client(settings.supabase_service_role_key)
    )
    repository.replace_all([to_database_row(reference) for reference in references])
    print(f"Cargadas {len(references)} referencias en referencias_oro.")
    return 0


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="gold_set", description=(__doc__ or "").split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_command = commands.add_parser("preparar")
    prepare_command.add_argument("pdfs", nargs="+", type=Path)
    prepare_command.add_argument("--salida", type=Path, default=Path("estandar-oro-base.csv"))
    commands.add_parser("validar").add_argument("csv", type=Path)
    compare_command = commands.add_parser("acuerdo")
    compare_command.add_argument("primero", type=Path)
    compare_command.add_argument("segundo", type=Path)
    alter_command = commands.add_parser("alterar")
    alter_command.add_argument("csv", type=Path)
    alter_command.add_argument("--salida", type=Path, default=Path("estandar-oro-final.csv"))
    commands.add_parser("cargar").add_argument("csv", type=Path)

    options = parser.parse_args(arguments)
    if options.command == "preparar":
        return prepare(options.pdfs, options.salida)
    if options.command == "validar":
        return check(options.csv)
    if options.command == "acuerdo":
        return compare(options.primero, options.segundo)
    if options.command == "alterar":
        return alter(options.csv, options.salida)
    return load(options.csv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
