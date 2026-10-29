"""Estándar de oro (T09): referencias anotadas a mano para medir los extractores.

Diseño estratificado: 100 referencias reales (2 normas x 5 tipos de obra x 10)
y 50 alteradas a propósito (año, autor, título y DOI), generadas con semilla
fija a partir de las reales para que sean controladas y reproducibles.

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
    "norma",
    "tipo_obra",
    *FIELDS,
    "anotador",
    "notas",
    "es_alterada",
    "tipo_alteracion",
    "origen",
)
NORMS = ("APA", "IEEE")
WORK_TYPES = ("articulo", "libro", "capitulo", "web", "congreso_tesis")
ALTERATIONS = ("anio", "autor", "titulo", "doi")
TARGET_PER_STRATUM = 10
ALTERED_TOTAL = 50
# Semilla fija: las mismas referencias reales producen siempre las mismas alteradas.
SEED = 2026
AUTHOR_SEPARATOR = ";"
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
    )


def _to_row(reference: GoldReference) -> dict[str, str]:
    return {
        "id": reference.id,
        "texto": reference.text,
        "norma": reference.norm,
        "tipo_obra": reference.work_type,
        **{name: reference.value(name) for name in FIELDS},
        "anotador": reference.annotator,
        "notas": reference.notes,
        "es_alterada": "si" if reference.altered else "",
        "tipo_alteracion": reference.alteration,
        "origen": reference.source_id,
    }


# --- Validación -----------------------------------------------------------------------------


def validate(references: list[GoldReference]) -> list[str]:
    """Problemas de la anotación, uno por línea; lista vacía si está lista."""
    problems: list[str] = []
    for reference_id, count in Counter(reference.id for reference in references).items():
        if count > 1:
            problems.append(f"{reference_id}: id repetido {count} veces")
    for reference in references:
        problems.extend(f"{reference.id}: {problem}" for problem in _problems(reference))
    return problems


def _problems(reference: GoldReference) -> list[str]:
    if not reference.text:
        return ["sin texto"]
    problems = []
    if reference.norm not in NORMS:
        problems.append(f"norma {reference.norm!r} no es APA ni IEEE")
    if reference.work_type not in WORK_TYPES:
        problems.append(f"tipo_obra {reference.work_type!r} no es {', '.join(WORK_TYPES)}")
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


def strata(references: list[GoldReference]) -> dict[tuple[str, str], int]:
    """Referencias reales por norma y tipo de obra; la meta es TARGET_PER_STRATUM en cada una."""
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
        if _comparable(a.value(name)) != _comparable(b.value(name))
    ]
    by_field = {
        name: _share([_comparable(a.value(name)) == _comparable(b.value(name)) for a, b in pairs])
        for name in FIELDS
    }
    kappa = {
        "norma": cohen_kappa([a.norm for a, _ in pairs], [b.norm for _, b in pairs]),
        "tipo_obra": cohen_kappa([a.work_type for a, _ in pairs], [b.work_type for _, b in pairs]),
    }
    return Agreement(len(pairs), by_field, kappa, differences)


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
    """Alteradas a partir de las reales, repartidas por igual entre los cuatro tipos.

    Cada una cambia un solo dato en el texto y en sus campos anotados, como lo
    haría una referencia inventada o mal copiada.
    """
    rng = random.Random(seed)
    real = [reference for reference in references if not reference.altered]
    pool = real[:]
    rng.shuffle(pool)
    used: set[str] = set()
    altered: list[GoldReference] = []
    for position in range(total * 4):  # varias vueltas por si alguna no se puede alterar
        if len(altered) == total:
            break
        kind = ALTERATIONS[position % len(ALTERATIONS)]
        for reference in pool:
            if reference.id in used:
                continue
            result = _alter(reference, kind, real, rng)
            if result:
                used.add(reference.id)
                altered.append(result)
                break
    return altered


def _alter(
    reference: GoldReference, kind: str, real: list[GoldReference], rng: random.Random
) -> GoldReference | None:
    field_name, old = {
        "anio": ("anio", reference.value("anio")),
        "autor": ("autores", (surnames(reference.value("autores")) or [""])[0]),
        "titulo": ("titulo", reference.value("titulo")),
        "doi": ("doi", reference.value("doi")),
    }[kind]
    if not old or old not in reference.text:
        return None

    if kind == "anio":
        new = str(int(old) + rng.choice((-3, -2, -1, 1, 2, 3)))
    elif kind == "doi":
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

    # En IEEE el año va al final; en APA, después de los autores.
    text = _replace_once(reference.text, old, new, last=kind == "anio" and reference.norm == "IEEE")
    fields = {**reference.fields, field_name: reference.value(field_name).replace(old, new, 1)}
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


def _replace_once(text: str, old: str, new: str, last: bool) -> str:
    index = text.rfind(old) if last else text.find(old)
    return text[:index] + new + text[index + len(old) :]


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
            "origen": reference.source_id or None,
        },
        "es_alterada": reference.altered,
        "tipo_alteracion": reference.alteration or None,
    }
