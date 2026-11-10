"""Herramienta del estándar de oro (T09). Uso, desde backend/:

python -m scripts.gold_set preparar --apa carpeta-apa --ieee carpeta-ieee --salida base.csv
    Separa las referencias de los PDF publicados de esas carpetas, sortea 50 APA y 50 IEEE (máximo 3
    por documento) más las de reserva y crea la planilla con id, texto, documento
    y norma. Cada carpeta aporta solo las referencias de su norma: una referencia
    APA suelta en un trabajo IEEE no entra. Los campos quedan vacíos: se anotan a
    mano, sin precargarlos con un extractor, para no sesgar la comparación.
python -m scripts.gold_set validar anotado.csv
    Revisa la anotación y cuenta las referencias por norma y tipo de obra.
python -m scripts.gold_set acuerdo anotador_a.csv anotador_b.csv --desde R006 --hasta R025
    Acuerdo entre anotadores en ese rango: coincidencia por campo, kappa y desacuerdos.
python -m scripts.gold_set alterar anotado.csv --salida final.csv
    Agrega las 50 alteradas (semilla fija), las reparte entre calibración y prueba
    y guarda el estándar de oro final.
python -m scripts.gold_set cargar final.csv
    Reemplaza la tabla referencias_oro con el estándar de oro final (usa backend/.env).
python -m scripts.gold_set evaluar final.csv
    Compara AnyStyle y spaCy con las 100 reales (HU-12): precisión, exhaustividad y
    F1 por campo y por norma, y aplica la regla de decisión. Si AnyStyle no está
    instalado, se detiene: nunca mide spaCy en su lugar.
"""

import argparse
import shutil
import sys
from pathlib import Path

from app.benchmark.evaluation import KEY_FIELDS, EngineResult, decide, evaluate
from app.benchmark.gold_set import (
    ALTERATIONS,
    FIELDS,
    NORMS,
    PARTITIONS,
    REAL_PER_NORM,
    GoldReference,
    agreement,
    composition,
    final_set,
    make_alterations,
    read_csv,
    select_sample,
    to_database_row,
    validate,
    write_csv,
)
from app.core.config import get_settings
from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import ReferenceExtractor
from app.extraction.spacy_rules import SpacyExtractor
from app.pipeline.errors import PdfProcessingError
from app.pipeline.references_section import extract_reference_section
from app.pipeline.segmentation import segment_references
from app.repositories.gold_set import SupabaseGoldSetRepository
from app.repositories.supabase_http import shared_client


def prepare(pdfs_by_norm: dict[str, list[Path]], output: Path) -> int:
    candidates: list[GoldReference] = []
    for norm, paths in pdfs_by_norm.items():
        for pdf in _pdf_files(paths):
            try:
                segmentation = segment_references(extract_reference_section(pdf.read_bytes()))
            except PdfProcessingError as error:
                print(f"{pdf.name}: {error}")
                continue
            own = [item for item in segmentation.references if item.norm.value == norm]
            for reference in own:
                candidates.append(
                    GoldReference(
                        id="",
                        text=reference.text,
                        norm=norm,
                        work_type="",
                        notes=reference.issue or "",
                        document=pdf.stem,
                    )
                )
            print(f"{pdf.name}: {len(own)} de {len(segmentation.references)} referencias en {norm}")
    sample = select_sample(candidates)
    write_csv(output, sample)
    print(f"\nPlanilla: {output}, sorteada entre {len(candidates)} referencias.")
    for norm in NORMS:
        count = sum(reference.norm == norm for reference in sample)
        to_annotate = min(count, REAL_PER_NORM)
        print(f"  {norm}: {to_annotate} por anotar y {count - to_annotate} de reserva")
    print("Revisen que cada texto coincida con el PDF y completen tipo_obra y los campos.")
    return 0


def _pdf_files(paths: list[Path]) -> list[Path]:
    # Una carpeta aporta todos sus PDF: PowerShell no expande "*.pdf" como bash.
    return [
        pdf for path in paths for pdf in (sorted(path.glob("*.pdf")) if path.is_dir() else [path])
    ]


def check(path: Path) -> int:
    references = read_csv(path)
    problems = validate(references)
    for problem in problems:
        print(f"- {problem}")
    print(f"\n{len(references)} referencias, {len(problems)} problemas.")
    counts = composition(references)
    print("\nReferencias reales por norma y tipo de obra:")
    for norm in NORMS:
        total = sum(count for (each, _), count in counts.items() if each == norm)
        mark = "" if total >= REAL_PER_NORM else f" (faltan {REAL_PER_NORM - total})"
        print(f"  {norm}: {total} de {REAL_PER_NORM}{mark}")
        for (each, work_type), count in counts.items():
            if each == norm:
                print(f"    {work_type:<15} {count:>3}")
    return 1 if problems else 0


def compare(first: Path, second: Path, start: str, end: str) -> int:
    # Solo el rango del acuerdo: la práctica y las filas sin anotar quedan fuera.
    def in_range(references: list[GoldReference]) -> list[GoldReference]:
        return [reference for reference in references if start <= reference.id <= end]

    result = agreement(in_range(read_csv(first)), in_range(read_csv(second)))
    print(f"Referencias anotadas por ambos ({start} a {end}): {result.common}\n")
    print("Coincidencia por campo:")
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
    write_csv(output, final_set(real, altered))
    print(f"{len(real)} reales + {len(altered)} alteradas en {output}.")
    for kind in ALTERATIONS:
        print(f"  {kind:<10} {sum(reference.alteration == kind for reference in altered):>3}")
    for partition in PARTITIONS:
        print(f"  {partition}: {sum(ref.partition == partition for ref in altered)} alteradas")
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


def measure(path: Path, engines: list[str], anystyle_command: str) -> int:
    references = read_csv(path)
    if problems := validate(references):
        print(f"El estándar de oro tiene {len(problems)} problemas: ejecuten validar.")
        return 1
    extractors: list[ReferenceExtractor] = []
    for engine in engines:
        if engine == "anystyle":
            if not shutil.which(anystyle_command):
                print(f"No se encontró {anystyle_command} (anystyle-cli): no se mide nada.")
                return 1
            extractors.append(AnyStyleExtractor(command=anystyle_command))
        else:
            extractors.append(SpacyExtractor())
    results = [evaluate(references, extractor) for extractor in extractors]
    _print_results(results)
    if len(results) > 1:
        decision = decide(results)
        verdict = "empate: se mantiene" if decision.tie else "gana"
        print(f"\nDecisión: {verdict} {decision.winner.value}", end=" ")
        print(f"(diferencia de {decision.difference * 100:.1f} puntos de F1 en los campos clave).")
    return 0


def _print_results(results: list[EngineResult]) -> None:
    names = " | ".join(f"{result.engine.value:^20}" for result in results)
    print(f"Referencias reales: {results[0].references}\n")
    print(f"{'campo':<12} | {names}")
    print(f"{'':<12} | " + " | ".join(f"{'P':>6}{'R':>7}{'F1':>7}" for _ in results))
    for name in FIELDS:
        cells = " | ".join(
            f"{c.precision:>6.2f}{c.recall:>7.2f}{c.f1:>7.2f}"
            for c in (result.by_field[name] for result in results)
        )
        print(f"{name:<12} | {cells}")
    print(f"\nF1 promedio en {', '.join(KEY_FIELDS)}:")
    for norm in (None, *NORMS):
        label = norm or "total"
        cells = "  ".join(f"{r.engine.value} {r.key_f1(norm):.2f}" for r in results)
        print(f"  {label:<6} {cells}")
    for result in results:
        print(
            f"{result.engine.value}: {result.failures} referencias sin procesar, "
            f"{result.elapsed_ms / max(result.references, 1):.0f} ms por referencia"
        )


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="gold_set", description=(__doc__ or "").split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_command = commands.add_parser("preparar")
    prepare_command.add_argument("--apa", nargs="*", type=Path, default=[])
    prepare_command.add_argument("--ieee", nargs="*", type=Path, default=[])
    prepare_command.add_argument("--salida", type=Path, default=Path("estandar-oro-base.csv"))
    commands.add_parser("validar").add_argument("csv", type=Path)
    compare_command = commands.add_parser("acuerdo")
    compare_command.add_argument("primero", type=Path)
    compare_command.add_argument("segundo", type=Path)
    compare_command.add_argument("--desde", default="R006")
    compare_command.add_argument("--hasta", default="R025")
    alter_command = commands.add_parser("alterar")
    alter_command.add_argument("csv", type=Path)
    alter_command.add_argument("--salida", type=Path, default=Path("estandar-oro-final.csv"))
    commands.add_parser("cargar").add_argument("csv", type=Path)
    measure_command = commands.add_parser("evaluar")
    measure_command.add_argument("csv", type=Path)
    measure_command.add_argument(
        "--motores", nargs="+", choices=["anystyle", "spacy"], default=["anystyle", "spacy"]
    )
    measure_command.add_argument("--anystyle", default="anystyle", help="comando de anystyle-cli")

    options = parser.parse_args(arguments)
    if options.command == "evaluar":
        return measure(options.csv, options.motores, options.anystyle)
    if options.command == "preparar":
        return prepare({"APA": options.apa, "IEEE": options.ieee}, options.salida)
    if options.command == "validar":
        return check(options.csv)
    if options.command == "acuerdo":
        return compare(options.primero, options.segundo, options.desde, options.hasta)
    if options.command == "alterar":
        return alter(options.csv, options.salida)
    return load(options.csv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
