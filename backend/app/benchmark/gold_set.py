"""Estándar de oro (T09): referencias anotadas a mano para medir el sistema.

- 100 referencias reales (50 APA y 50 IEEE) sorteadas con semilla fija entre las
  de trabajos de titulación publicados, máximo 3 por documento: así nadie elige
  las fáciles y ninguna tesis pesa más que las otras. El tipo de obra se anota
  solo para informar los resultados, sin cuotas.
- 50 alteradas (año, autor, título, DOI o inventada), generadas con la misma
  semilla a partir de las reales que tienen DOI. Cada real alterada y sus copias
  van a la misma partición: calibración (T18) o prueba (T17).

Los campos se anotan tal como aparecen en el texto, aunque estén mal escritos:
se mide la extracción, no la veracidad. Por eso la validación comprueba que cada
campo anotado aparezca en el texto de la referencia.
"""

import csv
import io
import random
import re
import unicodedata
import uuid
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path

FIELDS = (
    "autores",
    "anio",
    "titulo",
    "contenedor",
    "editorial",
    "volumen",
    "numero",
    "paginas",
    "doi",
)
COLUMNS = (
    "id",
    "texto",
    "documento",
    "norma",
    "tipo_obra",
    *FIELDS,
    "anotador",
    "notas",
    "es_alterada",
    "tipo_alteracion",
    "origen",
    "particion",
)
NORMS = ("APA", "IEEE")
# Libro incluye los capítulos: en las tesis reales son menos del 1 % de las referencias.
WORK_TYPES = ("articulo", "libro", "web", "congreso_tesis")
REAL_PER_NORM = 50
MAX_PER_DOCUMENT = 3
# Filas de reemplazo por norma, por si alguna de las sorteadas no es una referencia.
RESERVE_PER_NORM = 15
RESERVE_NOTE = "Reserva: úsenla solo para reemplazar una fila borrada de la misma norma."
# "inventada" junta el título, el autor y el año de otras referencias, como las de una IA.
ALTERATIONS = ("anio", "autor", "titulo", "doi", "inventada")
ALTERED_TOTAL = 50
# Nunca ±1: Crossref suele registrar el año de la versión en línea, uno antes del impreso.
YEAR_OFFSETS = (-5, -4, -3, -2, 2, 3, 4, 5)
PARTITIONS = ("calibracion", "prueba")
CALIBRATION_SHARE = 0.4
# Semilla fija: las mismas referencias producen siempre el mismo sorteo y las mismas alteradas.
SEED = 2026
AUTHOR_SEPARATOR = ";"
# Puntuación que se cuela al copiar un campo desde el texto y no cambia su valor.
EDGE_PUNCTUATION = " .,;:\"'“”«»"
# Espacio de nombres para que cada referencia conserve su UUID al recargar el estándar de oro.
ID_NAMESPACE = uuid.UUID("6b1f3c2e-8a4d-4e0b-9a51-3f5c7d2e9b10")


@dataclass(frozen=True)
class GoldReference:
    id: str
    text: str
    norm: str
    work_type: str
    # Campos anotados tal como aparecen en el texto; "" si la referencia no lo tiene.
    fields: dict[str, str] = field(default_factory=dict)
    annotator: str = ""
    notes: str = ""
    altered: bool = False
    alteration: str = ""
    source_id: str = ""  # referencia real de la que sale una alterada
    document: str = ""  # PDF del que sale, sin nombres de personas
    partition: str = ""  # calibracion o prueba; vacío si no participa en la verificación

    def value(self, name: str) -> str:
        return self.fields.get(name, "")


@dataclass(frozen=True)
class Agreement:
    common: int  # referencias anotadas por los dos
    by_field: dict[str, float]  # porcentaje de coincidencia exacta por campo
    kappa: dict[str, float]  # kappa de Cohen de las etiquetas (norma y tipo de obra)
    differences: list[str]  # cada desacuerdo, para resolverlo conversando


# --- Archivos CSV ---------------------------------------------------------------------------


def read_csv(path: Path) -> list[GoldReference]:
    """Lee el CSV exportado de Google Sheets, LibreOffice o Excel (coma o punto y coma)."""
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("cp1252")  # Excel en Windows guarda en ANSI
    # Excel en español separa con punto y coma; los demás, con coma.
    header = content.split("\n", 1)[0]
    delimiter = ";" if header.count(";") > header.count(",") else ","
    rows = csv.DictReader(io.StringIO(content, newline=""), delimiter=delimiter)
    return [_from_row(row) for row in rows if (row.get("id") or "").strip()]


def write_csv(path: Path, references: list[GoldReference]) -> None:
    # utf-8-sig para que Excel muestre bien las tildes al abrirlo.
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(_to_row(reference) for reference in references)


def _from_row(row: dict[str, str]) -> GoldReference:
    def cell(name: str) -> str:
        return " ".join((row.get(name) or "").split())

    return GoldReference(
        id=cell("id"),
        text=cell("texto"),
        norm=cell("norma").upper(),
        work_type=cell("tipo_obra").lower(),
        fields={name: cell(name) for name in FIELDS},
        annotator=cell("anotador"),
        notes=cell("notas"),
        altered=cell("es_alterada").lower() in ("si", "sí", "true", "1"),
        alteration=cell("tipo_alteracion"),
        source_id=cell("origen"),
        document=cell("documento"),
        partition=cell("particion").lower(),
    )


def _to_row(reference: GoldReference) -> dict[str, str]:
    return {
        "id": reference.id,
        "texto": reference.text,
        "documento": reference.document,
        "norma": reference.norm,
        "tipo_obra": reference.work_type,
        **{name: reference.value(name) for name in FIELDS},
        "anotador": reference.annotator,
        "notas": reference.notes,
        "es_alterada": "si" if reference.altered else "",
        "tipo_alteracion": reference.alteration,
        "origen": reference.source_id,
        "particion": reference.partition,
    }


# --- Sorteo ---------------------------------------------------------------------------------


def select_sample(candidates: list[GoldReference], seed: int = SEED) -> list[GoldReference]:
    """Las 100 referencias por anotar y las de reserva, sorteadas entre todas las candidatas."""
    rng = random.Random(seed)
    shuffled = candidates[:]
    rng.shuffle(shuffled)
    per_norm: Counter[str] = Counter()
    per_document: Counter[str] = Counter()
    chosen: list[GoldReference] = []
    reserves: list[GoldReference] = []
    for reference in shuffled:
        if reference.norm not in NORMS or per_document[reference.document] >= MAX_PER_DOCUMENT:
            continue
        if per_norm[reference.norm] < REAL_PER_NORM:
            chosen.append(reference)
        elif per_norm[reference.norm] < REAL_PER_NORM + RESERVE_PER_NORM:
            reserves.append(replace(reference, notes=RESERVE_NOTE))
        else:
            continue
        per_norm[reference.norm] += 1
        per_document[reference.document] += 1
    return [
        replace(reference, id=f"R{number:03d}")
        for number, reference in enumerate(chosen + reserves, start=1)
    ]


# --- Validación -----------------------------------------------------------------------------


def validate(references: list[GoldReference]) -> list[str]:
    """Problemas de la anotación, uno por línea; lista vacía si está lista."""
    problems: list[str] = []
    for reference_id, count in Counter(reference.id for reference in references).items():
        if count > 1:
            problems.append(f"{reference_id}: id repetido {count} veces")
    for reference in references:
        problems.extend(f"{reference.id}: {problem}" for problem in _problems(reference))
    real = [reference for reference in references if not reference.altered]
    for document, count in Counter(reference.document for reference in real).items():
        if document and count > MAX_PER_DOCUMENT:
            problems.append(f"{document}: {count} referencias, el máximo es {MAX_PER_DOCUMENT}")
    return problems


def _problems(reference: GoldReference) -> list[str]:
    if not reference.text:
        return ["sin texto"]
    problems = []
    if reference.norm not in NORMS:
        problems.append(f"norma {reference.norm!r} no es APA ni IEEE")
    if reference.work_type not in WORK_TYPES:
        problems.append(f"tipo_obra {reference.work_type!r} no es {', '.join(WORK_TYPES)}")
    if reference.partition and reference.partition not in PARTITIONS:
        problems.append(f"particion {reference.partition!r} no es {', '.join(PARTITIONS)}")
    year = reference.value("anio")
    if year and not re.fullmatch(r"\d{4}", year):
        problems.append(f"anio {year!r} debe tener 4 dígitos")
    text = _comparable(reference.text)
    for name in FIELDS:
        if name == "autores":
            missing = [s for s in surnames(reference.value(name)) if _comparable(s) not in text]
            problems.extend(
                f"el apellido {surname!r} no aparece en el texto" for surname in missing
            )
        elif reference.value(name) and _comparable(reference.value(name)) not in text:
            problems.append(f"{name} {reference.value(name)!r} no aparece tal cual en el texto")
    return problems


def composition(references: list[GoldReference]) -> dict[tuple[str, str], int]:
    """Referencias reales por norma y tipo de obra, para informar los resultados."""
    counts = Counter((ref.norm, ref.work_type) for ref in references if not ref.altered)
    return {(norm, work): counts[(norm, work)] for norm in NORMS for work in WORK_TYPES}


def surnames(authors: str) -> list[str]:
    """Apellidos de "Pérez, M.; López Vera, J. A." (o el nombre de una organización)."""
    return [
        author.split(",")[0].strip() for author in authors.split(AUTHOR_SEPARATOR) if author.strip()
    ]


def _comparable(text: str) -> str:
    # Sin distinguir mayúsculas, guiones largos ni espacios: Sheets y el PDF los cambian.
    text = unicodedata.normalize("NFC", text).casefold().replace("–", "-").replace("—", "-")
    return " ".join(text.split())


# --- Acuerdo entre anotadores ---------------------------------------------------------------


def agreement(first: list[GoldReference], second: list[GoldReference]) -> Agreement:
    """Compara las anotaciones de dos personas sobre las referencias que ambas anotaron."""
    by_id = {reference.id: reference for reference in second}
    pairs = [(reference, by_id[reference.id]) for reference in first if reference.id in by_id]
    differences = [
        f"{a.id} · {name}: {a.value(name)!r} / {b.value(name)!r}"
        for a, b in pairs
        for name in FIELDS
        if not same_value(name, a.value(name), b.value(name))
    ]
    by_field = {
        name: _share([same_value(name, a.value(name), b.value(name)) for a, b in pairs])
        for name in FIELDS
    }
    kappa = {
        "norma": cohen_kappa([a.norm for a, _ in pairs], [b.norm for _, b in pairs]),
        "tipo_obra": cohen_kappa([a.work_type for a, _ in pairs], [b.work_type for _, b in pairs]),
    }
    return Agreement(len(pairs), by_field, kappa, differences)


def same_value(name: str, first: str, second: str) -> bool:
    """Dos anotaciones de un campo dicen lo mismo, aunque cambie la puntuación del borde.

    Un punto final o unas comillas que se colaron al copiar ("planning," o "00087.")
    no son un desacuerdo; tampoco los espacios alrededor del punto y coma de autores.
    """
    if name == "autores":
        return [_trimmed(s) for s in surnames(first)] == [_trimmed(s) for s in surnames(second)]
    return _trimmed(first) == _trimmed(second)


def _trimmed(value: str) -> str:
    return _comparable(value).strip(EDGE_PUNCTUATION)


def cohen_kappa(first: list[str], second: list[str]) -> float:
    """Acuerdo entre dos anotadores descontando el que se daría por azar (1 = total)."""
    if not first:
        return 0.0
    total = len(first)
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / total
    counts_a, counts_b = Counter(first), Counter(second)
    expected = sum(counts_a[label] * counts_b[label] for label in counts_a) / total**2
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def _share(matches: list[bool]) -> float:
    return sum(matches) / len(matches) if matches else 0.0


# --- Referencias alteradas ------------------------------------------------------------------


def make_alterations(
    references: list[GoldReference], total: int = ALTERED_TOTAL, seed: int = SEED
) -> list[GoldReference]:
    """Alteradas a partir de las reales con DOI, repartidas por igual entre los tipos.

    Solo las que tienen DOI: están en Crossref u OpenAlex, así que el sistema puede
    compararlas con su registro. Una real se altera más de una vez solo si no
    alcanzan, y nunca dos veces del mismo tipo.
    """
    rng = random.Random(seed)
    real = [reference for reference in references if not reference.altered]
    pool = [reference for reference in real if reference.value("doi")]
    rng.shuffle(pool)
    uses: Counter[str] = Counter()
    done: set[tuple[str, str]] = set()
    altered: list[GoldReference] = []
    for position in range(total * len(ALTERATIONS)):  # varias vueltas por si alguna no se puede
        if len(altered) == total:
            break
        kind = ALTERATIONS[position % len(ALTERATIONS)]
        # Primero las menos usadas; entre ellas, en el orden del sorteo.
        for reference in sorted(pool, key=lambda candidate: uses[candidate.id]):
            if (reference.id, kind) in done:
                continue
            result = _alter(reference, kind, real, rng)
            if result:
                done.add((reference.id, kind))
                uses[reference.id] += 1
                altered.append(result)
                break
    return _with_partitions(altered, rng)


def final_set(real: list[GoldReference], altered: list[GoldReference]) -> list[GoldReference]:
    """Reales y alteradas; cada real alterada queda en la partición de sus copias."""
    partitions = {reference.source_id: reference.partition for reference in altered}
    return [replace(ref, partition=partitions.get(ref.id, "")) for ref in real] + altered


def _with_partitions(altered: list[GoldReference], rng: random.Random) -> list[GoldReference]:
    # Se reparte por referencia real, no por copia: una real y sus alteradas nunca quedan
    # una en calibración y otra en prueba, porque eso inflaría el resultado de la prueba.
    sources = sorted({reference.source_id for reference in altered})
    rng.shuffle(sources)
    calibration = set(sources[: round(len(sources) * CALIBRATION_SHARE)])
    return [
        replace(ref, partition=PARTITIONS[0] if ref.source_id in calibration else PARTITIONS[1])
        for ref in altered
    ]


def _alter(
    reference: GoldReference, kind: str, real: list[GoldReference], rng: random.Random
) -> GoldReference | None:
    steps = ("titulo", "autor", "anio") if kind == "inventada" else (kind,)
    text, fields = reference.text, reference.fields
    for step in steps:
        changed = _change(replace(reference, text=text, fields=fields), step, real, rng)
        if changed is None:
            return None
        text, fields = changed
    return replace(
        reference,
        id=f"{reference.id}-alt-{kind}",
        text=text,
        fields=fields,
        annotator="script",
        notes="",
        altered=True,
        alteration=kind,
        source_id=reference.id,
    )


def _change(
    reference: GoldReference, kind: str, real: list[GoldReference], rng: random.Random
) -> tuple[str, dict[str, str]] | None:
    """Texto y campos con un solo dato cambiado; None si la referencia no lo tiene."""
    field_name, old = {
        "anio": ("anio", reference.value("anio")),
        "autor": ("autores", (surnames(reference.value("autores")) or [""])[0]),
        "titulo": ("titulo", reference.value("titulo")),
        "doi": ("doi", reference.value("doi")),
    }[kind]
    if not old or old not in reference.text:
        return None

    text: str | None
    if kind == "anio":
        new = str(int(old) + rng.choice(YEAR_OFFSETS))
        # En IEEE el año va al final; en APA, después de los autores.
        text = _replace_year(reference.text, old, new, last=reference.norm == "IEEE")
    else:
        if kind == "doi":
            new = _corrupt_doi(old)
        else:
            options = [
                value
                for other in real
                if other.id != reference.id
                and (value := _field_value(other, kind))
                and value not in reference.text
            ]
            if not options:
                return None
            new = rng.choice(sorted(options))
        text = reference.text.replace(old, new, 1)
    if text is None:
        return None
    fields = {**reference.fields, field_name: reference.value(field_name).replace(old, new, 1)}
    return text, fields


def _field_value(reference: GoldReference, kind: str) -> str:
    if kind == "autor":
        return (surnames(reference.value("autores")) or [""])[0]
    return reference.value("titulo")


def _corrupt_doi(doi: str) -> str:
    """Cambia los últimos dígitos o letras del sufijo: un DOI con forma válida que no existe."""
    characters = list(doi)
    changed = 0
    for index in range(len(characters) - 1, doi.index("/"), -1):
        char = characters[index]
        if char.isdigit():
            characters[index] = str((int(char) + 3) % 10)
            changed += 1
        elif char.isalpha():
            characters[index] = "x" if char.lower() != "x" else "y"
            changed += 1
        if changed == 3:
            break
    return "".join(characters)


def _replace_year(text: str, old: str, new: str, last: bool) -> str | None:
    # El año suelto, no el que va dentro de un DOI o una URL (10.5678/rc.2020.14).
    matches = list(re.finditer(rf"(?<![\w./-]){old}(?![\w/-])", text))
    if not matches:
        return None
    match = matches[-1] if last else matches[0]
    return text[: match.start()] + new + text[match.end() :]


# --- Carga en la base de datos --------------------------------------------------------------


def to_database_row(reference: GoldReference) -> dict[str, object]:
    """Fila de referencias_oro. El UUID sale del id, así recargar no duplica filas."""
    return {
        "id": str(uuid.uuid5(ID_NAMESPACE, reference.id)),
        "texto": reference.text,
        "norma": reference.norm,
        "campos_anotados": {
            **{name: reference.value(name) or None for name in FIELDS},
            "id_planilla": reference.id,
            "tipo_obra": reference.work_type,
            "documento": reference.document or None,
            "origen": reference.source_id or None,
            "particion": reference.partition or None,
        },
        "es_alterada": reference.altered,
        "tipo_alteracion": reference.alteration or None,
    }
