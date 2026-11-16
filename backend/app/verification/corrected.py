"""Referencia corregida en APA 7 o IEEE con los datos del registro (T26, HU-19).

Corrige solo lo que está mal: un campo que coincide con el registro queda como
lo escribió el estudiante; uno que difiere o que falta se toma del registro y se
marca como cambiado, para que el informe lo resalte (RF16-CA04). Las mayúsculas
del título no se cambian: corregirlas a ciegas rompería los nombres propios, y
eso le corresponde a la revisión de formato (T25).

El texto se devuelve en segmentos: cada uno dice a qué campo pertenece, si va en
cursiva y si cambió.

Fuentes de los formatos:
- normas-apa.org: artículo, revista sin volumen, número de artículo, libro, libro
  con editor, capítulo con sus editores, informe, edición, autores.
- "Manual de estilo APA (7.ª ed.): ejemplos", Revista SOBRE (2020), hecho con los
  ejemplos de apastyle.apa.org: libro con editor, edición, capítulo, "y" sin coma.
- apastyle.apa.org, Manual de APA 7: actas (sección 10.5: en una revista, formato
  de artículo; como libro, de capítulo) y preprints (sección 10.8: "_Título_.
  arXiv. DOI").
- IEEE Reference Guide (2025): artículo, libro, capítulo, actas, preprint de arXiv
  ("“Title,” year, arXiv number"), "et al." con más de seis autores, "doi: ...".
- Guía IEEE de la Biblioteca de la Universidade da Coruña (2026): en un trabajo en
  español, los conectores van en español ("y", "en").
Criterio de la herramienta: las actas en APA van como capítulo salvo que el
estudiante las cite como revista (Crossref no distingue los dos casos); en IEEE,
un preprint que no es de arXiv queda sin referencia corregida (la guía no da su
formato), y los libros van sin ciudad porque las fuentes no la traen.
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
    record_lacks_subtitle,
    same_person,
    title_identity,
    without_title_note,
)

# Con más autores, APA lista los primeros 19, "..." y el último; IEEE, el primero y "et al.".
APA_MAX_AUTHORS = 20
IEEE_MAX_AUTHORS = 6

LEADING_NUMBER = re.compile(rf"^\s*{IEEE_NUMBER}")
PAGE_PREFIX = re.compile(r"^\s*pp?\.\s*", re.IGNORECASE)
# Espacios alrededor del guion del rango: "120– 143" (un salto de línea del PDF).
PAGE_DASH = re.compile(r"\s*([-‐‑–—])\s*")
# Datos que, junto con las páginas o el volumen, identifican la publicación.
PUBLICATION_FIELDS = (CheckedField.AUTHORS, CheckedField.YEAR, CheckedField.CONTAINER)
# Número de artículo en lugar de páginas: con letra ("e289") o un solo número largo. La
# guía IEEE lo advierte así: "there is only one long number" (Periodical With Article ID).
ARTICLE_NUMBER = re.compile(r"^(?:[a-z]\d+|\d{5,})$", re.IGNORECASE)
PAGE_RANGE_DASH = re.compile(r"\d\s*[-‐‑–—]\s*\w")
# Número de arXiv: nuevo (2101.00001) o antiguo (cond-mat/0101001), con versión.
ARXIV_NUMBER = re.compile(r"arxiv[.:]\s*((?:[a-z.\-]+/)?\d{4}\.?\d{3,5}(?:v\d+)?)", re.IGNORECASE)
# Obra citada por sus editores: "Salas, D. (Ed.). (2012)".
EDITED_WORK = re.compile(
    r"\((?P<role>(?:eds?|coords?|comps?|dirs?)\.?)\)\.?\s*\((?:\d{4}|s\.\s?f\.)",
    re.IGNORECASE,
)
# Nota entre paréntesis al final del título: "(Informe n.° 12)", "(3.ª ed.)".
APA_TITLE_NOTE = re.compile(r"\s\([^()]+\)$")
# Los editores del libro en un capítulo APA: "En C. Ruiz y B. Torres (Eds.),".
# "En" con mayúscula y tras un punto: el "en" de un título ("educación en línea") no
# empieza los editores.
APA_EDITORS = re.compile(
    r"\.\s+En\s+(?P<names>(?:(?!\.\s+En\s)[^()])+?)\s*"
    r"\((?P<role>(?i:eds?|coords?|comps?|dirs?)\.?)\)\s*,"
)


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
        values = _merge(fields, record, verification, text)
        # La guía IEEE solo da el formato del preprint de arXiv: sin su número, mejor
        # ninguna referencia corregida que una armada como artículo de revista.
        if values.kind is _Kind.PREPRINT and _arxiv_number(values, text) is None:
            return None
        return CorrectedReference(tuple(_ieee(values, text)))
    return None


# Idioma de una traducción que Crossref registra aparte: "Título [Russian]".
TRANSLATION_TAG = re.compile(
    r"\[(arabic|bengali|chinese|english|french|german|hindi|indonesian|italian|japanese|"
    r"korean|persian|portuguese|russian|spanish|swahili|thai|turkish|ukrainian|urdu|"
    r"vietnamese)\]\s*$",
    re.IGNORECASE,
)


def trusted_record(fields: ExtractedFields, verification: Verification) -> SourceRecord | None:
    """El registro, si es seguro que es la obra citada; si no, None."""
    record = verification.record
    if record is None or verification.verdict not in (Verdict.VERIFIED, Verdict.DISCREPANCY):
        return None
    if verification.strategy is not Strategy.DIRECT_DOI:
        title = title_identity(fields.title, record.title)
        if title is None:
            return None
        if title < THRESHOLDS.title_match and not _same_publication(verification):
            return None
        if is_translation(fields.title, record.title):
            return None
    return record


def _same_publication(verification: Verification) -> bool:
    """Mismos autores, año y revista o libro, y mismas páginas o volumen: es la obra
    citada aunque su título se haya copiado distinto (criterio de la herramienta).
    Con un título solo parecido, la búsqueda pudo hallar otra obra de los mismos
    autores, pero no en la misma publicación y las mismas páginas."""
    checks = {check.field: check for check in verification.checks}
    required = [checks.get(field) for field in PUBLICATION_FIELDS]
    locators = [
        checks[field] for field in (CheckedField.PAGES, CheckedField.VOLUME) if field in checks
    ]
    return (
        all(check is not None and check.matches for check in required)
        and bool(locators)
        and all(check.matches for check in locators)
    )


def is_translation(cited_title: str | None, record_title: str | None) -> bool:
    """El registro es una traducción de la obra citada, con su propio DOI.

    Los organismos internacionales (UNESCO, por ejemplo) registran cada idioma de un
    informe con otro DOI y el idioma al final del título. La búsqueda puede hallar
    una traducción: la obra existe, pero sus datos no son los de la versión citada.
    """
    tag = TRANSLATION_TAG.search(record_title or "")
    return tag is not None and tag.group(1).lower() not in (cited_title or "").lower()


# --- Valor de cada campo --------------------------------------------------------------------


class _Kind(Enum):
    ARTICLE = "articulo"
    BOOK = "libro"
    CHAPTER = "capitulo"
    PROCEEDINGS = "actas"
    PREPRINT = "preprint"
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
    "preprint": _Kind.PREPRINT,  # OpenAlex (arXiv, medRxiv, ...)
    "posted-content": _Kind.PREPRINT,  # Crossref
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
            checks, CheckedField.CONTAINER, cited.container, record.container, text
        ),
        CheckedField.VOLUME: _pick(checks, CheckedField.VOLUME, cited.volume, record.volume, text),
        CheckedField.ISSUE: _pick(checks, CheckedField.ISSUE, cited.issue, record.issue, text),
        CheckedField.PAGES: _pick(checks, CheckedField.PAGES, cited.pages, record.pages, text),
        CheckedField.PUBLISHER: _pick(
            checks, CheckedField.PUBLISHER, cited.publisher, record.publisher, text
        ),
        CheckedField.DOI: _doi(checks.get(CheckedField.DOI), cited.doi, record.doi),
    }
    present = {field: value for field, value in values.items() if value is not None}
    people, removed = _people(cited.authors, record)
    kind = _kind(record, present, text)
    if kind is _Kind.PREPRINT and (repository := _repository(record)):
        present[CheckedField.CONTAINER] = _Value(
            repository, repository.casefold() not in text.casefold()
        )
    return _Values(kind, people, removed, present)


def _repository(record: SourceRecord) -> str | None:
    """El repositorio del preprint sin la institución que OpenAlex le agrega:
    "arXiv (Cornell University)" -> "arXiv"."""
    name = record.container or record.publisher
    return re.sub(r"\s*\([^()]*\)$", "", name).strip() or None if name else None


# "En _Libro_" (APA) o ', in _Libro_' / ', en _Libro_' (IEEE) en el texto citado.
IN_A_BOOK = re.compile(r"(?:\.\s+En\s|[,”\"]\s*(?:in|en)\s)")


def _kind(record: SourceRecord, present: dict[CheckedField, _Value], text: str) -> _Kind:
    """Tipo de obra según la fuente. Si la fuente no lo dice (Crossref registra
    muchos capítulos como "other"), se deduce de los datos y de cómo la citó el
    estudiante (criterio de la herramienta)."""
    kind = KINDS.get(record.work_type or "", _Kind.OTHER)
    if kind is _Kind.PROCEEDINGS and _cited_like_a_journal(present, text):
        # APA 7 (Manual, sección 10.5; apastyle.apa.org, "Conference proceeding
        # references"): las actas publicadas en una revista o con periodicidad siguen
        # el formato de artículo; las publicadas como libro, el de capítulo. Crossref
        # no distingue los dos casos ("proceedings-article"), así que si el estudiante
        # las citó como revista, con volumen (NeurIPS: "Advances in Neural Information
        # Processing Systems, 36, 68539-68551"), se respeta ese formato.
        return _Kind.ARTICLE
    if kind is not _Kind.OTHER:
        return kind
    if CheckedField.VOLUME in present and CheckedField.CONTAINER in present:
        return _Kind.ARTICLE
    if CheckedField.CONTAINER in present and IN_A_BOOK.search(text):
        return _Kind.CHAPTER
    return _Kind.OTHER


def _cited_like_a_journal(present: dict[CheckedField, _Value], text: str) -> bool:
    """Con volumen y contenedor, y sin el "En" o "in" de un libro."""
    has_volume = CheckedField.VOLUME in present and CheckedField.CONTAINER in present
    return has_volume and not IN_A_BOOK.search(text)


def _pick(
    checks: dict[CheckedField, FieldCheck],
    field: CheckedField,
    given: str | None,
    official: str | None,
    text: str,
) -> _Value | None:
    """El dato citado si coincide con el registro (o el registro no lo tiene); si no, el oficial.

    Si coincide y el texto de la referencia trae el dato oficial tal cual, se usa ese:
    el extractor a veces pierde un trozo ("(CIT" por "(CIT)", "289" por "e289").
    """
    check = checks.get(field)
    if given and (not official or (check.matches if check else _same_text(given, official))):
        if official and official != given and given in official and official in text:
            return _Value(official, False)
        return _Value(given, False)
    return _Value(official, True) if official else None


def _title(given: str | None, official: str | None) -> _Value | None:
    """El título citado si solo difiere del registro en mayúsculas o en signos al final,
    si el registro lo trae sin su subtítulo, o si solo le suma la nota del final
    ("(Informe n.° 12)", "(3.ª ed.)"), que las fuentes no registran."""
    if given and (
        not official
        or _same_text(given, official)
        or record_lacks_subtitle(given, official)
        or _same_text(without_title_note(given, official), official)
    ):
        return _Value(given, False)
    return _Value(official, True) if official else None


def _doi(check: FieldCheck | None, given: str | None, official: str | None) -> _Value | None:
    """El DOI del registro. Uno citado que ninguna fuente tiene no se conserva; uno citado
    que la fuente reconoce sí, aunque el registro traiga el de otra versión de la obra."""
    cited = normalize_doi(given)
    if cited and check is not None and check.matches:
        return _Value(cited, False)
    if official:
        return _Value(official, cited != official)
    if cited and check is None:
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
    """ "María José" -> "M. J." (normas-apa.org, SOBRE: "Apellidos, N."). Con guion,
    "Jean-Marc" -> "J.-M.", y sin las partículas en minúscula ("de los"): criterio de la
    herramienta, ninguna de las fuentes revisadas trata esos casos."""
    parts = []
    for word in re.split(r"\s+|(?<=\.)(?=\w)", given.strip()):
        if word and not word[0].islower():
            parts.append("-".join(f"{piece[0]}." for piece in word.split("-") if piece))
    return " ".join(parts)


# --- APA 7 ----------------------------------------------------------------------------------


def _apa(values: _Values, text: str) -> list[Segment]:
    out: list[Segment] = []
    title = values.get(CheckedField.TITLE)
    # Libro, preprint u otra obra completa: título en cursiva. Preprint (APA 7, sección
    # 10.8; apastyle.apa.org, "Preprint article references"): "_Título_. arXiv. DOI".
    title_italic = values.kind in (_Kind.BOOK, _Kind.PREPRINT, _Kind.OTHER)
    year = values.get(CheckedField.YEAR)
    # Sin fecha, "s.f." como en la guía de normas-apa.org ("(s.f.)"); la de la Revista
    # SOBRE escribe "s. f.": las fuentes no coinciden.
    date = _seg(year, CheckedField.YEAR) if year else Segment("s.f.")

    if values.people:
        role = _apa_role(text)
        out += [_apa_authors(values, _apa_connector(text)), Segment(f"{role} ("), date]
        out.append(Segment("). "))
        if title:
            out += [*_apa_title(title, title_italic), Segment(_end(title.text))]
    elif title:  # sin autor, el título pasa al lugar del autor (normas-apa.org)
        out += [*_apa_title(title, title_italic), Segment(" ("), date]
        out.append(Segment("). "))

    container = values.get(CheckedField.CONTAINER)
    pages = values.get(CheckedField.PAGES)
    publisher = values.get(CheckedField.PUBLISHER)
    if values.kind is _Kind.PREPRINT:
        if container:
            out += [_seg(container, CheckedField.CONTAINER), Segment(". ")]
    elif values.kind is _Kind.ARTICLE:
        out += _apa_journal(values)
    elif values.kind in (_Kind.CHAPTER, _Kind.PROCEEDINGS) and container:
        out += [
            Segment(f"En {_apa_editors(text)}"),
            _seg(container, CheckedField.CONTAINER, italic=True),
        ]
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
    """ "_Revista, volumen_(número), páginas. " (normas-apa.org, citar revista). Sin
    volumen, el número va tras una coma: "_Revista Internacional Magisterio_, (54),
    10-17." (normas-apa.org, citar revista; Revista SOBRE, artículo de revista). El
    número de artículo va en lugar de las páginas (normas-apa.org, citar revista)."""
    container, volume = values.get(CheckedField.CONTAINER), values.get(CheckedField.VOLUME)
    issue, pages = values.get(CheckedField.ISSUE), values.get(CheckedField.PAGES)
    out: list[Segment] = []
    if container:
        out.append(_seg(container, CheckedField.CONTAINER, italic=True))
    if volume:
        out += [Segment(", ", italic=True), _seg(volume, CheckedField.VOLUME, italic=True)]
    if issue:
        opening = "(" if volume or not container else ", ("
        out += [Segment(opening), _seg(issue, CheckedField.ISSUE), Segment(")")]
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


def _apa_role(text: str) -> str:
    """ " (Ed.)." si la obra se cita por sus editores: "Apellido, N. (Ed.). (año)."
    (normas-apa.org, libro con editor); si no, nada."""
    match = EDITED_WORK.search(text)
    return f" ({match.group('role')})." if match else ""


def _apa_title(value: _Value, italic: bool) -> list[Segment]:
    """El título; en cursiva, la nota del final queda fuera: "_Título_ (Informe n.° 3)"
    o "_Título_ (3.ª ed.)" (normas-apa.org, informes y libros)."""
    title = _seg(value, CheckedField.TITLE, italic)
    note = APA_TITLE_NOTE.search(title.text) if italic else None
    if note is None or note.start() == 0:
        return [title]
    main = Segment(title.text[: note.start()], title.field, True, title.changed)
    return [main, Segment(title.text[note.start() :], title.field, False, title.changed)]


def _apa_editors(text: str) -> str:
    """Los editores del libro como los citó el estudiante, con su rol y la coma
    ("C. Ruiz y B. Torres (Eds.), "), como piden normas-apa.org y la guía de la Revista
    SOBRE para el capítulo: "En N. Apellidos (Ed.), _Título del libro_ (pp. x-x)". Antes
    del último va " y" sin coma, como entre los autores (Revista SOBRE, ejemplo de capítulo
    con tres editores). Las fuentes casi nunca
    registran a los editores, así que no se comprueban: solo se evita perderlos."""
    match = APA_EDITORS.search(text)
    if match is None:
        return ""
    names = re.sub(r",\s+y\s+", " y ", " ".join(match.group("names").split()))
    return f"{names} ({match.group('role')}), "


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
    """Conserva el número [n] original y los conectores del estudiante ("y"/"en" o "and"/"in").

    Las dos formas tienen fuente: la IEEE Reference Guide usa "and" e "in"; la guía IEEE
    de la Biblioteca de la Universidade da Coruña (2026) traduce esos elementos al idioma
    del trabajo ("y", "En línea"). Como las dos son válidas, no se cambia la elegida.
    """
    number = LEADING_NUMBER.match(text)
    spanish = " y " in re.split(r"[\"“«]", text, maxsplit=1)[0]
    out: list[Segment] = [Segment(f"[{number.group(1)}] ")] if number else []
    if values.people:
        out += [_ieee_authors(values, "y" if spanish else "and"), Segment(", ")]

    title, container = values.get(CheckedField.TITLE), values.get(CheckedField.CONTAINER)
    if values.kind is _Kind.PREPRINT:
        return out + _ieee_preprint(values, text)
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
    # En el artículo las páginas van antes del año; en libros, capítulos y actas, y el
    # número de artículo ("Art. no. 061103"), después (IEEE Reference Guide, Periodicals).
    article_number = pages is not None and ARTICLE_NUMBER.match(_pages(pages).text)
    if article and pages and not article_number:
        details.append(_ieee_pages(pages))
    if year:
        details.append([_seg(year, CheckedField.YEAR)])
    if pages and article_number:
        details.append([Segment("Art. no. "), _pages(pages)])
    elif not article and pages:
        details.append(_ieee_pages(pages))
    if doi:
        details.append([Segment("doi: "), _seg(doi, CheckedField.DOI)])

    for position, detail in enumerate(details):
        out += ([Segment(", ")] if position else []) + detail
    # Todas las referencias terminan en punto, también las que llevan DOI (guía IEEE).
    return _without_trailing_space(out, separators=" ,") + [Segment(".")]


def _ieee_pages(pages: _Value) -> list[Segment]:
    """ "pp. 2787–2793" o, con una sola página, "p. 475" (IEEE Reference Guide)."""
    segment = _pages(pages)
    return [Segment("pp. " if PAGE_RANGE_DASH.search(segment.text) else "p. "), segment]


def _ieee_preprint(values: _Values, text: str) -> list[Segment]:
    """ "“Título,” año, arXiv:número." (IEEE Reference Guide, Unpublished, Preprint
    arXiv: J. K. Author, “Title of paper,” year, arXiv number)."""
    out: list[Segment] = []
    title, year = values.get(CheckedField.TITLE), values.get(CheckedField.YEAR)
    if title:
        out += [Segment("“"), _seg(title, CheckedField.TITLE), Segment(",” ")]
    if year:
        out += [_seg(year, CheckedField.YEAR), Segment(", ")]
    number = _arxiv_number(values, text)
    if number:
        changed = number.casefold() not in text.replace(" ", "").casefold()
        out.append(Segment(number, CheckedField.DOI, changed=changed))
    return _without_trailing_space(out, separators=" ,") + [Segment(".")]


def _arxiv_number(values: _Values, text: str) -> str | None:
    """ "arXiv:2101.00001", del DOI de arXiv (10.48550/arXiv.2101.00001) o del texto."""
    doi = values.get(CheckedField.DOI)
    for source in (doi.text if doi else "", text):
        if match := ARXIV_NUMBER.search(source):
            return f"arXiv:{match.group(1)}"
    return None


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
    return Segment(PAGE_DASH.sub(r"\1", pages), CheckedField.PAGES, changed=value.changed)


def _without_trailing_space(segments: list[Segment], separators: str = " ") -> list[Segment]:
    """Quita el separador sobrante del final ("Editorial. " -> "Editorial.")."""
    if segments and segments[-1].field is None:
        last = segments[-1]
        trimmed = last.text.rstrip(separators)
        segments = segments[:-1] + ([Segment(trimmed, italic=last.italic)] if trimmed else [])
    return segments
