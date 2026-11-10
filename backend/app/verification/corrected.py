"""Referencia corregida en APA 7 o IEEE con los datos del registro (T26, HU-19).

Corrige solo lo que está mal: un campo que coincide con el registro queda como
lo escribió el estudiante; uno que difiere o que falta se toma del registro y se
marca como cambiado, para que el informe lo resalte (RF16-CA04). Las mayúsculas
del título no se cambian: corregirlas a ciegas rompería los nombres propios, y
eso le corresponde a la revisión de formato (T25).

El texto se devuelve en segmentos: cada uno dice a qué campo pertenece, si va en
cursiva y si cambió.

Fuentes de los formatos: normas-apa.org (artículo, libro, capítulo, autores) y
la guía de referencias de IEEE de 2025 (artículo, libro, capítulo, actas, "et
al." con más de seis autores, "doi: ..."). Criterio de la herramienta: las actas
en APA siguen el formato del capítulo, y los libros en IEEE van sin ciudad
porque las fuentes no la traen.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz

from app.extraction.base import Author, ExtractedFields
from app.pipeline.norm_detection import Norm
from app.pipeline.patterns import IEEE_NUMBER
from app.sources.lookup import Strategy
from app.sources.records import Source, SourceRecord, normalize_doi
from app.verification.decision import (
    THRESHOLDS,
    CheckedField,
    FieldCheck,
    Verdict,
    Verification,
    same_person,
    title_identity,
)

# Con más autores, APA lista los primeros 19, "..." y el último; IEEE, el primero y "et al.".
APA_MAX_AUTHORS = 20
IEEE_MAX_AUTHORS = 6

LEADING_NUMBER = re.compile(rf"^\s*{IEEE_NUMBER}")
PAGE_PREFIX = re.compile(r"^\s*pp?\.\s*", re.IGNORECASE)


@dataclass(frozen=True)
class Segment:
    text: str
    field: CheckedField | None = None
    italic: bool = False
    changed: bool = False


@dataclass(frozen=True)
class CorrectedReference:
    segments: tuple[Segment, ...]

    @property
    def text(self) -> str:
        """Texto plano para copiar al portapapeles."""
        return "".join(segment.text for segment in self.segments)

    @property
    def changed_fields(self) -> tuple[CheckedField, ...]:
        fields = (segment.field for segment in self.segments if segment.changed and segment.field)
        return tuple(dict.fromkeys(fields))


def corrected_reference(
    text: str, norm: Norm, fields: ExtractedFields, verification: Verification
) -> CorrectedReference | None:
    """Referencia corregida; None si la norma de la referencia (no la del documento) no
    es APA ni IEEE, o si no es seguro que el registro sea la obra citada.

    Es seguro cuando el DOI citado lleva a la obra o el título es el mismo. Con un
    título solo parecido, la búsqueda pudo hallar otra obra de los mismos autores:
    copiar sus datos cambiaría la obra citada en vez de corregirla.
    """
    record = trusted_record(fields, verification)
    if record is None:
        return None
    if norm is Norm.APA:
        return CorrectedReference(tuple(_apa(_merge(fields, record, verification, text), text)))
    if norm is Norm.IEEE:
        return CorrectedReference(tuple(_ieee(_merge(fields, record, verification, text), text)))
    return None


def trusted_record(fields: ExtractedFields, verification: Verification) -> SourceRecord | None:
    """El registro, si es seguro que es la obra citada; si no, None."""
    record = verification.record
    if record is None or verification.verdict not in (Verdict.VERIFIED, Verdict.DISCREPANCY):
        return None
    if verification.strategy is not Strategy.DIRECT_DOI:
        title = title_identity(fields.title, record.title)
        if title is None or title < THRESHOLDS.title_match:
            return None
    return record


# --- Valor de cada campo --------------------------------------------------------------------


class _Kind(Enum):
    ARTICLE = "articulo"
    BOOK = "libro"
    CHAPTER = "capitulo"
    PROCEEDINGS = "actas"
    OTHER = "otro"


# Tipos de obra de Crossref y de OpenAlex.
KINDS = {
    "journal-article": _Kind.ARTICLE,
    "article": _Kind.ARTICLE,
    "book": _Kind.BOOK,
    "monograph": _Kind.BOOK,
    "edited-book": _Kind.BOOK,
    "reference-book": _Kind.BOOK,
    "book-chapter": _Kind.CHAPTER,
    "book-section": _Kind.CHAPTER,
    "book-part": _Kind.CHAPTER,
    "reference-entry": _Kind.CHAPTER,
    "proceedings-article": _Kind.PROCEEDINGS,
}


@dataclass(frozen=True)
class _Value:
    text: str
    changed: bool


@dataclass(frozen=True)
class _Person:
    author: Author
    cited: bool  # la referencia ya lo nombraba


@dataclass(frozen=True)
class _Values:
    """El valor que lleva la referencia corregida en cada campo."""

    kind: _Kind
    people: tuple[_Person, ...]
    removed_authors: bool  # la referencia nombra autores que el registro no tiene
    fields: dict[CheckedField, _Value]

    def get(self, field: CheckedField) -> _Value | None:
        return self.fields.get(field)


def _merge(
    cited: ExtractedFields, record: SourceRecord, verification: Verification, text: str
) -> _Values:
    checks = {check.field: check for check in verification.checks}
    year = cited.year if cited.year in (record.year, *record.other_years) else record.year
    values = {
        CheckedField.TITLE: _title(cited.title, record.title),
        CheckedField.YEAR: _Value(str(year), year != cited.year) if year else None,
        CheckedField.CONTAINER: _pick(
            checks, CheckedField.CONTAINER, cited.container, record.container
        ),
        CheckedField.VOLUME: _pick(checks, CheckedField.VOLUME, cited.volume, record.volume),
        CheckedField.ISSUE: _pick(checks, CheckedField.ISSUE, cited.issue, record.issue),
        CheckedField.PAGES: _pick(checks, CheckedField.PAGES, cited.pages, record.pages),
        CheckedField.PUBLISHER: _pick(
            checks, CheckedField.PUBLISHER, cited.publisher, record.publisher
        ),
        CheckedField.DOI: _doi(checks.get(CheckedField.DOI), cited.doi, record.doi),
    }
    present = {field: value for field, value in values.items() if value is not None}
    people, removed = _people(cited.authors, record)
    return _Values(_kind(record, present, text), people, removed, present)


# "En _Libro_" (APA) o ', in _Libro_' / ', en _Libro_' (IEEE) en el texto citado.
IN_A_BOOK = re.compile(r"(?:\.\s+En\s|[,”\"]\s*(?:in|en)\s)")


def _kind(record: SourceRecord, present: dict[CheckedField, _Value], text: str) -> _Kind:
    """Tipo de obra según la fuente. Si la fuente no lo dice (Crossref registra
    muchos capítulos como "other"), se deduce de los datos y de cómo la citó el
    estudiante (criterio de la herramienta)."""
    kind = KINDS.get(record.work_type or "", _Kind.OTHER)
    if kind is not _Kind.OTHER:
        return kind
    if CheckedField.VOLUME in present and CheckedField.CONTAINER in present:
        return _Kind.ARTICLE
    if CheckedField.CONTAINER in present and IN_A_BOOK.search(text):
        return _Kind.CHAPTER
    return _Kind.OTHER


def _pick(
    checks: dict[CheckedField, FieldCheck],
    field: CheckedField,
    given: str | None,
    official: str | None,
) -> _Value | None:
    """El dato citado si coincide con el registro (o el registro no lo tiene); si no, el oficial."""
    check = checks.get(field)
    if given and (not official or (check.matches if check else _same_text(given, official))):
        return _Value(given, False)
    return _Value(official, True) if official else None


def _title(given: str | None, official: str | None) -> _Value | None:
    """El título citado si solo difiere del registro en mayúsculas o en signos al final."""
    if given and (not official or _same_text(given, official)):
        return _Value(given, False)
    return _Value(official, True) if official else None


def _doi(check: FieldCheck | None, given: str | None, official: str | None) -> _Value | None:
    """El DOI del registro. Uno citado que ninguna fuente tiene no se conserva."""
    cited = normalize_doi(given)
    if official:
        return _Value(official, cited != official)
    if cited and (check is None or check.matches):
        return _Value(cited, False)
    return None


def _same_text(a: str, b: str) -> bool:
    def plain(value: str) -> str:
        return " ".join(value.casefold().strip(" .,;:").split()).lstrip("0")

    return plain(a) == plain(b)


def _people(cited: Sequence[Author], record: SourceRecord) -> tuple[tuple[_Person, ...], bool]:
    """Los autores del registro, en su orden. Los que la referencia ya nombraba van
    como los escribió el estudiante: las fuentes separan mal los dos apellidos.

    Cada autor citado se usa una sola vez y con el autor del registro que más se le
    parece: "Huertas-Tato" y "Huertas-García" comparten el primer apellido.
    """
    official = [author for author in record.authors if _is_person_or_group(author, record)]
    named = [author for author in cited if author.family.strip()]
    if not official:
        return tuple(_Person(author, True) for author in named), False
    available = list(named)
    people = []
    for author in official:
        match = _closest(author, available)
        if match:
            available.remove(match)
        if match and _same_first_initial(match, author):
            people.append(_Person(match, True))
        elif match:  # el apellido citado es correcto; la inicial, no
            people.append(_Person(Author(match.family, author.given), False))
        elif record.source is Source.OPENALEX:
            people.append(_Person(_split_full_name(author), False))
        else:
            people.append(_Person(author, False))
    return tuple(people), bool(available)  # citados que el registro no tiene


def _closest(author: Author, cited: Sequence[Author]) -> Author | None:
    candidates = [c for c in cited if same_person(c, author, THRESHOLDS)]
    full_name = f"{author.given} {author.family}".casefold()
    return max(
        candidates,
        key=lambda c: (
            _same_first_initial(c, author),
            fuzz.partial_ratio(c.family.casefold(), full_name),
        ),
        default=None,
    )


def _is_person_or_group(author: Author, record: SourceRecord) -> bool:
    """Descarta lo que Crossref a veces registra como autor y no lo es: una afiliación
    ("MS in Management, Lamar University, Texas, USA") sin nombres, junto a autores
    que sí los tienen (criterio de la herramienta)."""
    if not author.family.strip():
        return False
    if author.given or record.source is not Source.CROSSREF:
        return True
    others_have_names = any(other.given for other in record.authors)
    return not (others_have_names and ("," in author.family or len(author.family.split()) > 6))


def _same_first_initial(cited: Author, official: Author) -> bool:
    """Sin nombres en alguno de los dos (organización u OpenAlex), no hay inicial que comparar."""
    if not cited.given or not official.given:
        return True
    return _initials(cited.given)[:1] == _initials(official.given)[:1]


def _split_full_name(author: Author) -> Author:
    """OpenAlex da el nombre completo sin separar. Criterio de la herramienta: con
    cuatro palabras o más, las dos últimas son los apellidos; si no, la última."""
    words = author.family.split()
    if len(words) < 2:
        return author
    surnames = 2 if len(words) >= 4 else 1
    return Author(" ".join(words[-surnames:]), " ".join(words[:-surnames]))


def _initials(given: str) -> str:
    """ "María José" -> "M. J."; "Jean-Marc" -> "J.-M." (normas-apa.org); las
    partículas en minúscula ("de los") se omiten."""
    parts = []
    for word in re.split(r"\s+|(?<=\.)(?=\w)", given.strip()):
        if word and not word[0].islower():
            parts.append("-".join(f"{piece[0]}." for piece in word.split("-") if piece))
    return " ".join(parts)


# --- APA 7 ----------------------------------------------------------------------------------


def _apa(values: _Values, text: str) -> list[Segment]:
    out: list[Segment] = []
    title = values.get(CheckedField.TITLE)
    title_italic = values.kind in (_Kind.BOOK, _Kind.OTHER)
    year = values.get(CheckedField.YEAR)
    date = _seg(year, CheckedField.YEAR) if year else Segment("s.f.")

    if values.people:
        out += [_apa_authors(values, _apa_connector(text)), Segment(" ("), date, Segment("). ")]
        if title:
            out += [_seg(title, CheckedField.TITLE, title_italic), Segment(_end(title.text))]
    elif title:  # sin autor, el título pasa al lugar del autor (normas-apa.org)
        out += [_seg(title, CheckedField.TITLE, title_italic), Segment(" ("), date]
        out.append(Segment("). "))

    container = values.get(CheckedField.CONTAINER)
    pages = values.get(CheckedField.PAGES)
    publisher = values.get(CheckedField.PUBLISHER)
    if values.kind is _Kind.ARTICLE:
        out += _apa_journal(values)
    elif values.kind in (_Kind.CHAPTER, _Kind.PROCEEDINGS) and container:
        out += [Segment("En "), _seg(container, CheckedField.CONTAINER, italic=True)]
        if pages:
            out += [Segment(" (pp. "), _pages(pages), Segment(")")]
        out.append(Segment(". "))
        if publisher:
            out += [_seg(publisher, CheckedField.PUBLISHER), Segment(". ")]
    elif publisher:
        out += [_seg(publisher, CheckedField.PUBLISHER), Segment(". ")]
    elif container:
        out += [_seg(container, CheckedField.CONTAINER), Segment(". ")]

    doi = values.get(CheckedField.DOI)
    if doi:
        out.append(Segment(f"https://doi.org/{doi.text}", CheckedField.DOI, changed=doi.changed))
    return _without_trailing_space(out)


def _apa_journal(values: _Values) -> list[Segment]:
    """ "_Revista, volumen_(número), páginas. " (normas-apa.org, artículo de revista)."""
    container, volume = values.get(CheckedField.CONTAINER), values.get(CheckedField.VOLUME)
    issue, pages = values.get(CheckedField.ISSUE), values.get(CheckedField.PAGES)
    out: list[Segment] = []
    if container:
        out.append(_seg(container, CheckedField.CONTAINER, italic=True))
    if volume:
        out += [Segment(", ", italic=True), _seg(volume, CheckedField.VOLUME, italic=True)]
    if issue:
        out += [Segment("("), _seg(issue, CheckedField.ISSUE), Segment(")")]
    if pages:
        out += [Segment(", "), _pages(pages)]
    return out + [Segment(". ")] if out else []


def _apa_connector(text: str) -> str:
    """normas-apa.org usa " y"; ", &" o " &" también se aceptan: se respeta lo que usó
    el estudiante, con su coma."""
    authors = text.split("(", 1)[0]
    if ", &" in authors:
        return ", &"
    return " &" if "&" in authors else " y"


def _apa_authors(values: _Values, connector: str) -> Segment:
    names = [_apa_name(person.author) for person in values.people]
    if len(names) > APA_MAX_AUTHORS:
        text = ", ".join(names[: APA_MAX_AUTHORS - 1]) + ", ... " + names[-1]
    elif len(names) == 1:
        text = names[0]
    else:
        text = f"{', '.join(names[:-1])}{connector} {names[-1]}"
    changed = values.removed_authors or not all(person.cited for person in values.people)
    return Segment(text, CheckedField.AUTHORS, changed=changed)


def _apa_name(author: Author) -> str:
    initials = _initials(author.given)
    return f"{author.family}, {initials}" if initials else author.family


def _end(title: str) -> str:
    """Punto tras el título, salvo que ya termine en signo de pregunta o exclamación."""
    return " " if title.rstrip().endswith(("?", "!")) else ". "


# --- IEEE -----------------------------------------------------------------------------------


def _ieee(values: _Values, text: str) -> list[Segment]:
    """Conserva el número [n] original y los conectores del estudiante ("y"/"en" o "and"/"in")."""
    number = LEADING_NUMBER.match(text)
    spanish = " y " in re.split(r"[\"“«]", text, maxsplit=1)[0]
    out: list[Segment] = [Segment(f"[{number.group(1)}] ")] if number else []
    if values.people:
        out += [_ieee_authors(values, "y" if spanish else "and"), Segment(", ")]

    title, container = values.get(CheckedField.TITLE), values.get(CheckedField.CONTAINER)
    if values.kind is _Kind.BOOK and title:
        out += [_seg(title, CheckedField.TITLE, italic=True), Segment(". ")]
    elif title:
        out += [Segment("“"), _seg(title, CheckedField.TITLE), Segment(",” ")]
        if container:
            if values.kind in (_Kind.CHAPTER, _Kind.PROCEEDINGS):
                out.append(Segment("en " if spanish else "in "))
            out += [_seg(container, CheckedField.CONTAINER, italic=True), Segment(", ")]

    article = values.kind is _Kind.ARTICLE
    volume, issue = values.get(CheckedField.VOLUME), values.get(CheckedField.ISSUE)
    publisher, pages = values.get(CheckedField.PUBLISHER), values.get(CheckedField.PAGES)
    year, doi = values.get(CheckedField.YEAR), values.get(CheckedField.DOI)
    details: list[list[Segment]] = []
    if article and volume:
        details.append([Segment("vol. "), _seg(volume, CheckedField.VOLUME)])
    if article and issue:
        details.append([Segment("no. "), _seg(issue, CheckedField.ISSUE)])
    if values.kind in (_Kind.BOOK, _Kind.CHAPTER) and publisher:
        details.append([_seg(publisher, CheckedField.PUBLISHER)])
    # En el artículo las páginas van antes del año; en libros, capítulos y actas, después.
    if article and pages:
        details.append([Segment("pp. "), _pages(pages)])
    if year:
        details.append([_seg(year, CheckedField.YEAR)])
    if not article and pages:
        details.append([Segment("pp. "), _pages(pages)])
    if doi:
        details.append([Segment("doi: "), _seg(doi, CheckedField.DOI)])

    for position, detail in enumerate(details):
        out += ([Segment(", ")] if position else []) + detail
    # Todas las referencias terminan en punto, también las que llevan DOI (guía IEEE).
    return _without_trailing_space(out, separators=" ,") + [Segment(".")]


def _ieee_authors(values: _Values, connector: str) -> Segment:
    names = [_ieee_name(person.author) for person in values.people]
    if len(names) > IEEE_MAX_AUTHORS:
        # Con "et al." basta que el primero sea el que cita la referencia.
        return Segment(
            f"{names[0]} et al.", CheckedField.AUTHORS, changed=not values.people[0].cited
        )
    if len(names) == 1:
        text = names[0]
    elif len(names) == 2:
        text = f"{names[0]} {connector} {names[1]}"
    else:
        text = f"{', '.join(names[:-1])}, {connector} {names[-1]}"
    changed = values.removed_authors or not all(person.cited for person in values.people)
    return Segment(text, CheckedField.AUTHORS, changed=changed)


def _ieee_name(author: Author) -> str:
    initials = _initials(author.given)
    return f"{initials} {author.family}" if initials else author.family


# --- Segmentos ------------------------------------------------------------------------------


def _seg(value: _Value, field: CheckedField, italic: bool = False) -> Segment:
    """Sin la puntuación con la que el campo venía pegado al siguiente ("71-86,")."""
    text = value.text.strip().rstrip(" ,;")
    if field is CheckedField.TITLE:
        text = text.rstrip(".")
    return Segment(text, field, italic, value.changed)


def _pages(value: _Value) -> Segment:
    """Páginas sin "pp." ni "p.": el formato ya lo pone donde corresponde."""
    pages = PAGE_PREFIX.sub("", value.text).strip().rstrip(" ,;.")
    return Segment(pages, CheckedField.PAGES, changed=value.changed)


def _without_trailing_space(segments: list[Segment], separators: str = " ") -> list[Segment]:
    """Quita el separador sobrante del final ("Editorial. " -> "Editorial.")."""
    if segments and segments[-1].field is None:
        last = segments[-1]
        trimmed = last.text.rstrip(separators)
        segments = segments[:-1] + ([Segment(trimmed, italic=last.italic)] if trimmed else [])
    return segments
