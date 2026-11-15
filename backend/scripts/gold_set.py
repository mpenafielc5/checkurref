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
python -m scripts.gold_set calibrar final.csv --cache pdf-locales/verificacion-oro.pkl
    Calibra los umbrales del motor de decisión con la partición de calibración (T18),
    con el criterio de calibrate(). Consulta Crossref y OpenAlex
    (usa backend/.env) y guarda sus respuestas en --cache para repetir la medición
    con los mismos datos.
python -m scripts.gold_set revisar final.csv --salida pdf-locales/revision-prueba.csv
    Antes de T17: pone cada real de la partición de prueba junto al registro al que
    lleva su DOI anotado, sin correr el motor de decisión, para revisarlas a mano y
    anotar en notas las que tienen un error real ("Error real: ...").
python -m scripts.gold_set probar final.csv --cache pdf-locales/verificacion-oro.pkl
    Prueba con referencias alteradas (T17): corre la partición de prueba con los
    umbrales calibrados y cuenta las alteradas detectadas por tipo y las reales
    marcadas por error.
"""

import argparse
import asyncio
import csv
import pickle
import shutil
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

import httpx

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
from app.benchmark.verification_eval import (
    CONTROL,
    CONTROL_WITH_ERROR,
    EXPECTED,
    Calibration,
    Case,
    MemoNli,
    Outcome,
    RecordingLookup,
    Score,
    calibrate,
    partition_cases,
    score,
    verify_cases,
)
from app.core.config import Settings, get_settings
from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import ExtractedFields, ReferenceExtractor
from app.extraction.spacy_rules import SpacyExtractor
from app.pipeline.errors import PdfProcessingError
from app.pipeline.references_section import extract_reference_section
from app.pipeline.segmentation import segment_references
from app.repositories.gold_set import SupabaseGoldSetRepository
from app.repositories.supabase_http import shared_client
from app.sources.crossref import CrossrefClient, user_agent
from app.sources.lookup import LookupResult, ReferenceLookup
from app.sources.openalex import OpenAlexClient
from app.sources.records import SourceRecord
from app.verification.decision import THRESHOLDS, Thresholds
from app.verification.factory import SOURCE_TIMEOUT_SECONDS
from app.verification.nli import get_nli_model


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


class _NoRecordCache:
    """Sin la caché de Supabase: la calibración guarda las respuestas en su propio archivo."""

    def get(self, doi: str) -> SourceRecord | None:
        return None

    def put(self, records: list[SourceRecord]) -> None:
        return None


def _partition_cases(path: Path, partition: str, anystyle_command: str) -> list[Case] | None:
    """Casos de la partición con los campos de AnyStyle; None si no se puede medir."""
    references = read_csv(path)
    if problems := validate(references):
        print(f"El estándar de oro tiene {len(problems)} problemas: ejecuten validar.")
        return None
    if not shutil.which(anystyle_command):
        print(f"No se encontró {anystyle_command} (anystyle-cli): la medición usa AnyStyle.")
        return None
    extractor = AnyStyleExtractor(command=anystyle_command)
    return partition_cases(
        references,
        partition,
        lambda texts: [result.fields for result in extractor.extract_all(texts)],
    )


def _read_store(cache: Path) -> dict[str, LookupResult]:
    # Archivo propio, en una carpeta que Git ignora: se lee solo lo que este programa escribió.
    return pickle.loads(cache.read_bytes()) if cache.exists() else {}


def _write_store(cache: Path, store: dict[str, LookupResult], before: int) -> None:
    cache.write_bytes(pickle.dumps(store))
    print(f"\nRespuestas de las fuentes en {cache}: {len(store)} ({len(store) - before} nuevas).")


@asynccontextmanager
async def _sources_lookup(
    settings: Settings, store: dict[str, LookupResult]
) -> AsyncIterator[RecordingLookup]:
    """Búsqueda en Crossref y OpenAlex que guarda sus respuestas en `store`."""
    headers = {"User-Agent": user_agent(settings.app_version, settings.crossref_mailto)}
    async with httpx.AsyncClient(headers=headers, timeout=SOURCE_TIMEOUT_SECONDS) as client:
        sources = [
            CrossrefClient(client, mailto=settings.crossref_mailto),
            OpenAlexClient(client, api_key=settings.openalex_api_key),
        ]
        yield RecordingLookup(ReferenceLookup(sources, _NoRecordCache()), store)


def calibrate_thresholds(path: Path, cache: Path, anystyle_command: str) -> int:
    cases = _partition_cases(path, PARTITIONS[0], anystyle_command)
    if cases is None:
        return 1
    settings = get_settings()
    nli = MemoNli(get_nli_model(Path(settings.nli_model_dir)))
    store = _read_store(cache)
    before = len(store)

    async def run_all() -> tuple[Calibration, list[Outcome]]:
        async with _sources_lookup(settings, store) as lookup:

            async def run(thresholds: Thresholds) -> Score:
                return score(await verify_cases(cases, lookup, nli, thresholds))

            calibration = await calibrate(run, THRESHOLDS)
            return calibration, await verify_cases(cases, lookup, nli, THRESHOLDS)

    calibration, outcomes = asyncio.run(run_all())
    _print_outcomes(outcomes)
    _write_store(cache, store, before)
    _print_calibration(calibration)
    return 0


def run_test_partition(path: Path, cache: Path, anystyle_command: str) -> int:
    cases = _partition_cases(path, PARTITIONS[1], anystyle_command)
    if cases is None:
        return 1
    settings = get_settings()
    nli = MemoNli(get_nli_model(Path(settings.nli_model_dir)))
    store = _read_store(cache)
    before = len(store)

    async def run_all() -> list[Outcome]:
        async with _sources_lookup(settings, store) as lookup:
            return await verify_cases(cases, lookup, nli, THRESHOLDS)

    outcomes = asyncio.run(run_all())
    _print_outcomes(outcomes)
    _write_store(cache, store, before)
    print(f"\nUmbrales fijos (T18): {asdict(THRESHOLDS)}")
    _print_test(score(outcomes))
    return 0


def _print_test(result: Score) -> None:
    print()
    _print_score("Partición de prueba", result)
    print(f"\n{'grupo':<18} {'total':>5} {'alerta':>7} {'esperado':>9}  veredictos")
    for kind, item in result.by_kind.items():
        verdicts = ", ".join(f"{name} {count}" for name, count in sorted(item.verdicts.items()))
        print(f"{kind:<18} {item.total:>5} {item.alerts:>7} {item.exact:>9}  {verdicts}")
    clean = result.by_kind.get(CONTROL)
    wrong = result.by_kind.get(CONTROL_WITH_ERROR)
    if result.altered:
        print(f"\nAlteradas detectadas: {result.alerts} de {result.altered}")
    if clean:
        print(f"Reales sin error marcadas por error: {clean.alerts} de {clean.total}")
    if wrong:
        print(f"Reales con error real detectadas: {wrong.alerts} de {wrong.total}")


def review_test_controls(path: Path, output: Path) -> int:
    references = read_csv(path)
    if problems := validate(references):
        print(f"El estándar de oro tiene {len(problems)} problemas: ejecuten validar.")
        return 1
    controls = [
        reference
        for reference in references
        if reference.partition == PARTITIONS[1] and not reference.altered
    ]
    settings = get_settings()
    store: dict[str, LookupResult] = {}

    async def records() -> list[LookupResult]:
        async with _sources_lookup(settings, store) as lookup:
            # El DOI anotado a mano, no el que saca el extractor: se revisa la tesis.
            return list(
                await asyncio.gather(
                    *(
                        lookup.lookup(ExtractedFields(doi=reference.value("doi")))
                        for reference in controls
                    )
                )
            )

    rows = [
        _review_row(reference, result)
        for reference, result in zip(controls, asyncio.run(records()), strict=True)
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(REVIEW_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} reales de la partición de prueba en {output}.")
    print("Compárenlas con su registro y, si la tesis tiene un error real, escriban en la")
    print('columna notas del estándar de oro: "Error real: <qué está mal>". Luego, probar.')
    return 0


REVIEW_COLUMNS = (
    "id",
    "texto",
    "doi",
    "fuente",
    "registro_titulo",
    "registro_autores",
    "registro_anio",
    "registro_revista",
    "registro_volumen",
    "registro_paginas",
    "error_real",
)


def _review_row(reference: GoldReference, result: LookupResult) -> dict[str, str]:
    row = {"id": reference.id, "texto": reference.text, "doi": reference.value("doi")}
    if not result.candidates:
        missing = "una fuente no respondió" if result.query_failed else "DOI no registrado"
        return {**row, "fuente": missing}
    record = result.candidates[0]
    return {
        **row,
        "fuente": record.source.value,
        "registro_titulo": record.title or "",
        "registro_autores": "; ".join(author.family for author in record.authors),
        "registro_anio": str(record.year or ""),
        "registro_revista": record.container or "",
        "registro_volumen": record.volume or "",
        "registro_paginas": record.pages or "",
    }


def _print_outcomes(outcomes: list[Outcome]) -> None:
    print("Veredicto de cada referencia con los umbrales actuales:")
    for outcome in outcomes:
        verdict = outcome.verdict.value if outcome.verdict else "error_consulta"
        expected = ", ".join(sorted(item.value for item in EXPECTED[outcome.case.kind]))
        mark = "" if outcome.exact else f"  <- esperado: {expected}"
        print(f"  {outcome.case.reference.id:<16} {outcome.case.kind:<10} {verdict}{mark}")


def _print_score(label: str, result: Score) -> None:
    print(
        f"{label}: falsas alarmas {result.false_alarms}, "
        f"alertas {result.alerts} de {result.altered}, "
        f"aciertos exactos {result.exact}, errores de consulta {result.errors}"
    )


def _print_calibration(calibration: Calibration) -> None:
    baseline = calibration.baseline
    print()
    _print_score("Umbrales actuales", baseline)
    for kind, item in baseline.by_kind.items():
        verdicts = ", ".join(f"{name} {count}" for name, count in sorted(item.verdicts.items()))
        print(f"  {kind:<10} {item.total:>2}: alertas {item.alerts}, exactos {item.exact}")
        print(f"             {verdicts}")
    print("\nCada umbral por separado (valor: falsas alarmas/alertas/exactos; * = actual):")
    for name in dict.fromkeys(trial.name for trial in calibration.trials):
        current = getattr(THRESHOLDS, name)
        cells = "  ".join(
            f"{trial.value:.2f}{'*' if trial.value == current else ''}:"
            f"{trial.score.false_alarms}/{trial.score.alerts}/{trial.score.exact}"
            for trial in calibration.trials
            if trial.name == name
        )
        print(f"  {name}\n    {cells}")
    changes = {
        name: (getattr(THRESHOLDS, name), value)
        for name, value in asdict(calibration.chosen).items()
        if value != getattr(THRESHOLDS, name)
    }
    print()
    if not changes:
        print("Decisión: ningún valor supera a los actuales; se conservan.")
        return
    for name, (old, new) in changes.items():
        print(f"Cambio: {name} de {old:.2f} a {new:.2f}")
    _print_score("Con los cambios juntos", calibration.combined)


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
    calibrate_command = commands.add_parser("calibrar")
    calibrate_command.add_argument("csv", type=Path)
    calibrate_command.add_argument(
        "--cache", type=Path, default=Path("pdf-locales/verificacion-oro.pkl")
    )
    calibrate_command.add_argument("--anystyle", default="anystyle", help="comando de anystyle-cli")
    review_command = commands.add_parser("revisar")
    review_command.add_argument("csv", type=Path)
    review_command.add_argument(
        "--salida", type=Path, default=Path("pdf-locales/revision-prueba.csv")
    )
    test_command = commands.add_parser("probar")
    test_command.add_argument("csv", type=Path)
    test_command.add_argument(
        "--cache", type=Path, default=Path("pdf-locales/verificacion-oro.pkl")
    )
    test_command.add_argument("--anystyle", default="anystyle", help="comando de anystyle-cli")

    options = parser.parse_args(arguments)
    if options.command == "evaluar":
        return measure(options.csv, options.motores, options.anystyle)
    if options.command == "calibrar":
        return calibrate_thresholds(options.csv, options.cache, options.anystyle)
    if options.command == "revisar":
        return review_test_controls(options.csv, options.salida)
    if options.command == "probar":
        return run_test_partition(options.csv, options.cache, options.anystyle)
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
