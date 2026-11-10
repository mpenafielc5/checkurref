"""Revisión de formato de cada referencia según APA 7 o IEEE (T25, HU-21).

Todas las reglas están en un solo catálogo, al final del módulo: agregar una es
escribir su comprobación y sumar una línea. Solo se revisa lo que se puede ver en
el texto plano del PDF, que pierde las cursivas. Ante la duda, una regla no se
dispara: un falso aviso le haría cambiar al estudiante algo que estaba bien.

El formato nunca cambia el veredicto, el índice de veracidad ni el riesgo en el
lote. Cada referencia se revisa contra su propia norma; si no se reconoció, contra
la de la lista. Si tampoco la lista tiene una, no se revisa y el informe lo explica.

Fuentes: normas-apa.org (DOI y URL, autores, fecha, orden de la lista) y la guía de
referencias de IEEE de 2025. Criterio de la herramienta: las tildes y la ñ no
cuentan para el orden alfabético, porque esas fuentes no lo definen.
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from app.extraction.base import ExtractedFields
from app.pipeline.norm_detection import Norm
from app.pipeline.patterns import IEEE_NUMBER, INITIALS, LOWER, SURNAME_FIRST, UNDATED, UPPER
from app.pipeline.segmentation import Segmentation, SegmentedReference
from app.verification.corrected import trusted_record
from app.verification.decision import CheckedField, Verification
from app.verification.findings import Finding, Severity

MIXED_NORM_CODE = "NORMA_MIXTA"
ALPHABETICAL_CODE = "APA_ORDEN_ALFABETICO"
NUMBERING_CODE = "IEEE_NUMERACION"

# Autores que se muestran en un hallazgo: el estudiante corrige el resto igual.
MAX_SHOWN = 3
# Largo del inicio de una referencia sin número que se muestra en IEEE_NUMERACION.
SHOWN_START = 40

ANY_DOI = re.compile(r"10\.\d{4,9}/\S+")
# Un DOI que no es enlace: con "doi:" o suelto. Uno dentro de una URL (la de doi.org o
# la de una editorial) viene después de una barra y no cuenta.
UNLINKED_DOI = re.compile(
    r"(?P<prefix>\bdoi:?\s*|(?<![\w/.-]))(?P<doi>10\.\d{4,9}/\S+)", re.IGNORECASE
)
APA_DOI_LINK = "https://doi.org/"
TRAILING_PUNCTUATION = ".,;)"
URL = re.compile(r"(?:https?://|www\.|doi:\s*)\S+|\b10\.\d{4,9}/\S+", re.IGNORECASE)

PLAIN_YEAR = re.compile(r"(?<![\w/.:-])((?:19|20)\d{2})(?![\w/-])")
# El año de IEEE fuera de lugar: entre paréntesis o entre comas, antes del título.
# Un año suelto no basta: puede ser parte de un nombre, como ISO 50001:2011.
IEEE_EARLY_YEAR = re.compile(r"\(((?:19|20)\d{2})[^)]{0,30}\)|,\s((?:19|20)\d{2})[,.]")
# Un año dentro de un paréntesis, con o sin fecha exacta: (2020), (07 de julio de 1985).
PAREN_YEAR = re.compile(r"\([^()]{0,40}\b(?:19|20)\d{2}[a-z]?\b[^()]{0,40}\)")
PAREN_NO_YEAR = re.compile(rf"\(\s*(?:{UNDATED}|s/f|en prensa|in press)\s*\)", re.IGNORECASE)
# Con el punto que lo cierra en APA, "(Eds.)."; si queda, la última inicial parece sin punto.
EDITORS = re.compile(r"\(\s*(?:Eds?|Coords?|Comps?)\.?\s*\)\.?", re.IGNORECASE)

STARTS_WITH_AUTHOR = re.compile(rf"^{SURNAME_FIRST}")

ET_AL = re.compile(r"\bet\.?\s+al\b\.?|\by\s+otros\b|\by\s+cols?\b\.?", re.IGNORECASE)
RETRIEVED = re.compile(
    r"\b(?:Recuperado\s+de|Retrieved\s+from)\s*:?\s*(?P<url>(?:https?://|www\.)\S+)?",
    re.IGNORECASE,
)

ORGANIZATION = re.compile(
    r"\b(?:Ministerio|Universidad|Organizaci[oó]n|Instituto|Asociaci[oó]n|Banco|Gobierno"
    r"|Naciones|Secretar[ií]a|Presidencia|Asamblea|Consejo|Comisi[oó]n|Fundaci[oó]n|Sociedad"
    r"|Centro|Departamento|Agencia|Diario|Redacci[oó]n|Editorial|University|Institute"
    r"|Association|Organization|Society|Committee|Ministry|Department|Agency|Corporation)\b"
)
# Lo que nunca va en una lista de autores: lo que hay antes de la fecha es otra cosa.
NOT_AUTHORS = re.compile(rf"\d|https?:|www\.|[{LOWER}]{{3}}\.\s")
AUTHOR_SEPARATOR = re.compile(r"\s*(?:,\s*(?:(?:y|e|and)\s+)?|;|&|\s(?:y|e|and)\s)\s*")
INITIALS_ONLY = re.compile(rf"(?:[{UPPER}][a-zª]?\.\s?-?)+")
INITIALS_NO_PERIOD = re.compile(rf"[{UPPER}](?:\s[{UPPER}])*")
INITIALS_THEN_SURNAME = re.compile(rf"(?P<initials>{INITIALS})\s?(?P<surname>[{UPPER}][\w'’ -]+)")
FULL_GIVEN_NAME = re.compile(rf"[{UPPER}][{LOWER}]{{2,}}(?:\s(?:[{UPPER}][{LOWER}]+|[{UPPER}]\.))*")
SURNAME_LIKE = re.compile(rf"[{UPPER}][\w'’-]+(?:\s[\w'’-]{{2,}}){{0,3}}")

LEADING_NUMBER = re.compile(rf"^\s*{IEEE_NUMBER}\s*")
# Número de la lista; la lectura de algunos PDF pierde el corchete de apertura: "45] ...".
WRITTEN_NUMBER = re.compile(r"^\s*\[?(\d{1,3})\]")
OPENING_QUOTE = re.compile(r"[“\"«„‘]")
ANY_QUOTE = re.compile(r"[“”\"«»„‘]|``|''")
# "En" o "In" antes del libro o las actas que contienen la obra.
INSIDE_ANOTHER_WORK = re.compile(r"(?:^|[.,]\s)(?:En|In)\s")
BOOK_TYPES = frozenset({"book", "monograph", "edited-book", "reference-book"})

# Abreviaturas de IEEE: cada forma incorrecta con la que le corresponde.
IEEE_VOLUME = re.compile(r"\b(?:[Vv]olumen|[Vv]olume|Vol\.?|vol)\s*(\d+)")
IEEE_ISSUE = re.compile(
    r"\b(?:[Nn][úu]mero|[Nn]umber|[Nn][úu]m\.?|[Nn]ro\.?|No\.?|no|[Nn][º°]\.?|[Ii]ssue)\s*(\d+)"
)
IEEE_PAGES = re.compile(
    r"\b(?:[Pp][áa]ginas?|[Pp][áa]gs?\.?|pp(?!\.)|Pp\.?)\s*(\d+(?:\s?[-–]\s?\d+)?)"
)
IEEE_PAGE_RANGE_AS_ONE = re.compile(r"\bp\.\s?(\d+\s?[-–]\s?\d+)")
PAGE_RANGE = re.compile(r"[-–]")

# Un nombre que empieza con una partícula o un artículo no se compara: en español va
# por lo que sigue ("de la Torre", en la T), pero en otros idiomas va en la partícula.
UNCLEAR_FOR_ORDER = frozenset(
    {
        "de",
        "del",
        "la",
        "las",
        "los",
        "el",
        "the",
        "van",
        "von",
        "der",
        "den",
        "di",
        "da",
        "du",
        "dos",
        "le",
        "al",
    }
)
ORDER_HEAD_END = re.compile(r",|\(|\.\s|\.$")


@dataclass(frozen=True)
class _Entry:
    text: str
    fields: ExtractedFields | None
    # Datos del registro, solo si es seguro que el registro es la obra citada.
    record_doi: str | None = None
    record_type: str | None = None


# Lo que se muestra de un hallazgo: cómo aparece en el trabajo y cómo debería ir.
_Hit = tuple[str, str]
_Check = Callable[[_Entry], _Hit | None]


# --- Datos compartidos por las reglas -------------------------------------------------------


def _has_doi(entry: _Entry) -> bool:
    return bool(ANY_DOI.search(entry.text)) or bool(entry.fields and entry.fields.doi)


def _trimmed(value: str) -> str:
    return value.rstrip(TRAILING_PUNCTUATION)


def _without_urls(text: str) -> str:
    """Quita URL y DOI, conservando las posiciones: sus números no son años."""
    return URL.sub(lambda match: " " * len(match.group()), text)


def _apa_authors(text: str) -> str | None:
    """Autores de una referencia APA: lo que va antes de la fecha entre paréntesis."""
    match = PAREN_YEAR.search(text) or PAREN_NO_YEAR.search(text)
    if match is None:
        return None
    authors = text[: match.start()].strip()
    return None if NOT_AUTHORS.search(authors) else authors


def _body(text: str) -> str:
    return LEADING_NUMBER.sub("", text, count=1)


def _ieee_authors(text: str) -> str | None:
    """Autores de una referencia IEEE: lo que va antes del título entre comillas."""
    body = _body(text)
    match = OPENING_QUOTE.search(body)
    return body[: match.start()].strip() if match else None


def _initials_of(given: str) -> str:
    return " ".join(f"{word[0]}." for word in given.split())


def _shown(wrong: list[_Hit]) -> _Hit | None:
    if not wrong:
        return None
    shown = wrong[:MAX_SHOWN]
    return "; ".join(given for given, _ in shown), "; ".join(right for _, right in shown)


# --- Reglas de APA 7 ------------------------------------------------------------------------


def _apa_missing_doi(entry: _Entry) -> _Hit | None:
    if entry.record_doi is None or _has_doi(entry):
        return None
    return "Sin DOI", f"{APA_DOI_LINK}{entry.record_doi}"


def _apa_doi_form(entry: _Entry) -> _Hit | None:
    match = UNLINKED_DOI.search(entry.text)
    if match is None:
        return None
    doi = _trimmed(match.group("doi"))
    return f"{match.group('prefix')}{doi}", f"{APA_DOI_LINK}{doi}"


def _apa_year_in_parens(entry: _Entry) -> _Hit | None:
    if PAREN_YEAR.search(entry.text) or PAREN_NO_YEAR.search(entry.text):
        return None
    # Sin autor reconocible puede ser texto que no es una referencia (un anexo, un
    # certificado) y que quedó al final de la lista.
    if not STARTS_WITH_AUTHOR.match(entry.text):
        return None
    match = PLAIN_YEAR.search(_without_urls(entry.text))
    return (match.group(1), f"({match.group(1)})") if match else None


def _apa_author_form(entry: _Entry) -> _Hit | None:
    authors = _apa_authors(entry.text)
    if authors is None or ORGANIZATION.search(authors):
        return None
    tokens = _split(EDITORS.sub("", authors))
    tokens = [token.strip(" .") if _is_bare(token) else token.strip() for token in tokens]
    families = {author.family for author in entry.fields.authors} if entry.fields else set()
    wrong: list[_Hit] = []
    position = 0
    # La inicial antes del apellido solo se cree desde el primer autor: más adelante,
    # suele ser el resto de un nombre que la lectura del PDF partió.
    initials_first = True
    while position < len(tokens):
        token = tokens[position]
        following = tokens[position + 1] if position + 1 < len(tokens) else ""
        surname = bool(SURNAME_LIKE.fullmatch(token))
        if initials_first and (match := INITIALS_THEN_SURNAME.fullmatch(token)):
            wrong.append((token, f"{match['surname']}, {match['initials'].strip()}"))
            position += 1
            continue
        initials_first = False
        if surname and INITIALS_ONLY.fullmatch(following):
            position += 2
        elif surname and (
            INITIALS_NO_PERIOD.fullmatch(following)
            or _is_full_given_name(following, token, tokens[position + 2 :], families)
        ):
            wrong.append((f"{token}, {following}", f"{token}, {_initials_of(following)}"))
            position += 2
        else:
            position += 1
    return _shown(wrong)


def _is_full_given_name(candidate: str, surname: str, rest: list[str], families: set[str]) -> bool:
    """El nombre completo después de un apellido. Con el extractor se confirma que es un
    autor y no el inicio de un título; si le siguen iniciales ("Quispe, Mendoza,
    L. O."), es otro apellido."""
    return (
        bool(FULL_GIVEN_NAME.fullmatch(candidate))
        and (not families or surname in families)
        and not (rest and INITIALS_ONLY.fullmatch(rest[0]))
    )


def _split(authors: str) -> list[str]:
    return [token for token in AUTHOR_SEPARATOR.split(authors) if token.strip()]


def _is_bare(token: str) -> bool:
    """Un apellido o nombre con el punto final de la lista; una inicial lo conserva."""
    return not INITIALS_ONLY.fullmatch(token.strip())


def _apa_et_al(entry: _Entry) -> _Hit | None:
    authors = _apa_authors(entry.text)
    # En una obra editada se acepta nombrar al editor principal seguido de et al.
    if authors is None or EDITORS.search(authors):
        return None
    match = ET_AL.search(authors)
    if match is None:
        return None
    return (
        match.group().strip(),
        "Hasta 20 autores se escriben todos; con 21 o más, los primeros 19, "
        "puntos suspensivos y el último",
    )


def _apa_retrieved_from(entry: _Entry) -> _Hit | None:
    match = RETRIEVED.search(entry.text)
    if match is None:
        return None
    url = match.group("url")
    return match.group().strip(), _trimmed(url) if url else "Solo la URL"


# --- Reglas de IEEE -------------------------------------------------------------------------


def _ieee_missing_doi(entry: _Entry) -> _Hit | None:
    if entry.record_doi is None or _has_doi(entry):
        return None
    return "Sin DOI", f"doi: {entry.record_doi}"


def _ieee_author_form(entry: _Entry) -> _Hit | None:
    wrong: list[_Hit] = []
    authors = _ieee_authors(entry.text)
    if authors is not None and ORGANIZATION.search(authors):
        return None
    if authors is None:
        match = re.match(SURNAME_FIRST, _body(entry.text))
        tokens = _split(match.group()) if match else []
    else:
        tokens = _split(authors)
    position = 0
    while position < len(tokens) - 1:
        surname, given = tokens[position].strip(), tokens[position + 1].strip()
        if SURNAME_LIKE.fullmatch(surname) and INITIALS_ONLY.fullmatch(given):
            wrong.append((f"{surname}, {given}", f"{given} {surname}"))
            position += 2
        else:
            position += 1
    # Un solo "nombre apellido" puede ser una organización (Amazon Web Services): el
    # nombre completo solo se cree si hay varios autores.
    people = entry.fields.authors if entry.fields and len(entry.fields.authors) > 1 else ()
    for author in people:
        written = f"{author.given} {author.family}".strip()
        if (
            author.family
            and FULL_GIVEN_NAME.fullmatch(author.given)
            and written in entry.text
            and not ORGANIZATION.search(written)
        ):
            wrong.append((written, f"{_initials_of(author.given)} {author.family}"))
    return _shown(wrong)


def _ieee_title_quotes(entry: _Entry) -> _Hit | None:
    # Un libro va sin comillas: solo se exigen si hay señales de una obra dentro de otra.
    fields = entry.fields
    if fields is None or not fields.title or not fields.container:
        return None
    if ANY_QUOTE.search(entry.text) or entry.record_type in BOOK_TYPES:
        return None
    if not (
        fields.volume
        or fields.pages
        or fields.doi
        or INSIDE_ANOTHER_WORK.search(entry.text)
        or entry.record_type
    ):
        return None
    title = fields.title.strip().rstrip(".,")
    return title, f"“{title},”"


def _ieee_abbreviations(entry: _Entry) -> _Hit | None:
    wrong: list[_Hit] = []
    text = _without_urls(entry.text)
    if match := IEEE_VOLUME.search(text):
        wrong.append((match.group().strip(), f"vol. {match.group(1)}"))
    if match := IEEE_ISSUE.search(text):
        wrong.append((match.group().strip(), f"no. {match.group(1)}"))
    if match := IEEE_PAGES.search(text) or IEEE_PAGE_RANGE_AS_ONE.search(text):
        pages = match.group(1)
        wrong.append(
            (match.group().strip(), f"{'pp.' if PAGE_RANGE.search(pages) else 'p.'} {pages}")
        )
    return _shown(wrong)


def _ieee_year_position(entry: _Entry) -> _Hit | None:
    text = _without_urls(entry.text)
    title_start = _title_start(entry)
    if title_start is None:
        return None
    match = IEEE_EARLY_YEAR.search(text, 0, title_start)
    if match is None:
        return None
    year = match.group(1) or match.group(2)
    return match.group().strip(" ,."), f"Al final de la referencia: ..., {year}."


def _title_start(entry: _Entry) -> int | None:
    title = (entry.fields.title or "").strip().rstrip(".,") if entry.fields else ""
    start = entry.text.lower().find(title.lower()) if title else -1
    if start >= 0:
        return start
    quote = OPENING_QUOTE.search(entry.text)
    return quote.start() if quote else None


# --- Catálogo -------------------------------------------------------------------------------


@dataclass(frozen=True)
class FormatRule:
    code: str
    message: str
    field: CheckedField | None = None
    severity: Severity = Severity.WARNING
    # None en las reglas de la lista completa, que miran todas las referencias.
    check: _Check | None = None


APA_RULES = (
    FormatRule(
        "APA_DOI_FALTANTE",
        "La obra tiene un DOI registrado y la referencia no lo incluye.",
        CheckedField.DOI,
        check=_apa_missing_doi,
    ),
    FormatRule(
        "APA_DOI_FORMATO",
        "En APA 7, el DOI se escribe como enlace que empieza con https://doi.org/.",
        CheckedField.DOI,
        check=_apa_doi_form,
    ),
    FormatRule(
        "APA_ANIO_PARENTESIS",
        "En APA 7, el año va entre paréntesis después de los autores.",
        CheckedField.YEAR,
        check=_apa_year_in_parens,
    ),
    FormatRule(
        "APA_AUTOR_FORMATO",
        "En APA 7, cada autor se escribe con el apellido seguido de las iniciales.",
        CheckedField.AUTHORS,
        check=_apa_author_form,
    ),
    FormatRule(
        "APA_ET_AL_EN_LISTA",
        "En la lista de referencias de APA 7 no se usa et al.: se escriben los autores.",
        CheckedField.AUTHORS,
        check=_apa_et_al,
    ),
    FormatRule(
        "APA_RECUPERADO_DE",
        "En APA 7 no se escribe «Recuperado de» antes de la URL, salvo con fecha de "
        "recuperación en una página que cambia con el tiempo.",
        check=_apa_retrieved_from,
    ),
)
IEEE_RULES = (
    FormatRule(
        "IEEE_AUTOR_FORMATO",
        "En IEEE, cada autor se escribe con las iniciales antes del apellido.",
        CheckedField.AUTHORS,
        check=_ieee_author_form,
    ),
    FormatRule(
        "IEEE_TITULO_COMILLAS",
        "En IEEE, el título de un artículo, capítulo o ponencia va entre comillas.",
        CheckedField.TITLE,
        check=_ieee_title_quotes,
    ),
    FormatRule(
        "IEEE_ABREVIATURAS",
        "En IEEE, el volumen, el número y las páginas se abrevian vol., no. y pp.",
        check=_ieee_abbreviations,
    ),
    FormatRule(
        "IEEE_ANIO_POSICION",
        "En IEEE, el año va hacia el final de la referencia, no antes del título.",
        CheckedField.YEAR,
        check=_ieee_year_position,
    ),
    FormatRule(
        "IEEE_DOI_FALTANTE",
        "La obra tiene un DOI registrado y la referencia no lo incluye.",
        CheckedField.DOI,
        check=_ieee_missing_doi,
    ),
)
LIST_RULES = (
    FormatRule(
        ALPHABETICAL_CODE,
        "En APA 7, la lista se ordena alfabéticamente por el apellido del primer autor.",
    ),
    FormatRule(NUMBERING_CODE, "En IEEE, las referencias se numeran [1], [2], [3]… en orden."),
    FormatRule(MIXED_NORM_CODE, "La lista combina referencias en APA y en IEEE."),
)
RULES_BY_NORM = {Norm.APA: APA_RULES, Norm.IEEE: IEEE_RULES}
CATALOG = {rule.code: rule for rule in (*APA_RULES, *IEEE_RULES, *LIST_RULES)}


# --- Revisión -------------------------------------------------------------------------------


def review_norm(reference_norm: Norm, document_norm: Norm) -> Norm | None:
    """Norma contra la que se revisa una referencia; None si no se puede revisar."""
    for norm in (reference_norm, document_norm):
        if norm in RULES_BY_NORM:
            return norm
    return None


def review_reference(
    reference: SegmentedReference,
    document_norm: Norm,
    fields: ExtractedFields | None,
    verification: Verification | None,
) -> list[Finding]:
    """Hallazgos de formato de una referencia. Una entrada cuya separación no se pudo
    confirmar no se revisa: puede ser solo un pedazo de una referencia."""
    norm = review_norm(reference.norm, document_norm)
    if norm is None or reference.issue:
        return []
    record = trusted_record(fields, verification) if fields and verification else None
    entry = _Entry(
        reference.text,
        fields,
        record.doi if record else None,
        record.work_type if record else None,
    )
    found: list[Finding] = []
    for rule in RULES_BY_NORM[norm]:
        if rule.check and (hit := rule.check(entry)):
            found.append(_finding(rule, *hit))
    return found


def review_list(segmentation: Segmentation) -> dict[int, list[Finding]]:
    """Hallazgos de las reglas de la lista completa, por el orden de la referencia.

    Cada regla deja un solo hallazgo, en el primer caso, y dice cuántos encontró:
    una lista desordenada no debe llenar el informe con el mismo aviso.
    """
    references = [item for item in segmentation.references if not item.issue]
    found: dict[int, list[Finding]] = {}
    if segmentation.norm is Norm.MIXED:
        _add(found, _mixed_norm(references))
    elif segmentation.norm is Norm.APA:
        _add(found, _alphabetical_order(references))
    elif segmentation.norm is Norm.IEEE:
        _add(found, _numbering(references))
    return found


def _add(found: dict[int, list[Finding]], result: tuple[int, Finding] | None) -> None:
    if result:
        order, finding = result
        found.setdefault(order, []).append(finding)


def _finding(rule: FormatRule, given: str, official: str, extra: str = "") -> Finding:
    message = f"{rule.message} {extra}".strip()
    return Finding(rule.code, rule.severity, message, rule.field, given, official)


def _cases(count: int) -> str:
    return f"Se encontraron {count} casos en la lista." if count > 1 else ""


def _mixed_norm(references: list[SegmentedReference]) -> tuple[int, Finding] | None:
    counts = Counter(item.norm for item in references if item.norm in RULES_BY_NORM)
    apa, ieee = counts[Norm.APA], counts[Norm.IEEE]
    if not apa or not ieee:
        return None
    # El aviso va en la primera referencia de la norma con menos referencias y habla de
    # ella: qué norma sigue y cuál siguen las demás.
    minority, majority = (Norm.APA, Norm.IEEE) if apa < ieee else (Norm.IEEE, Norm.APA)
    first = next(item for item in references if item.norm is minority)
    if apa == ieee:
        official = "Una sola norma en toda la lista"
        extra = f"La lista tiene {apa} en APA y {ieee} en IEEE."
    else:
        official = f"{majority.value}, como las otras {counts[majority]} referencias de la lista"
        extra = (
            f"Es la única referencia en {minority.value} de la lista."
            if counts[minority] == 1
            else f"Es la primera de las {counts[minority]} referencias en {minority.value}."
        )
    finding = _finding(CATALOG[MIXED_NORM_CODE], minority.value, official, extra)
    return first.order, finding


def _order_key(text: str) -> tuple[str, str] | None:
    """Apellido o nombre con el que se ordena y su clave de comparación letra por letra;
    None si no se puede saber dónde va (un número o una partícula de otro idioma)."""
    # Sin autores y fecha reconocibles puede ser un pedazo de otra referencia o un anexo.
    authors = _apa_authors(text)
    if not authors:
        return None
    head = ORDER_HEAD_END.split(authors, maxsplit=1)[0].strip()
    words = head.split()
    if not words or words[0].lower() in UNCLEAR_FOR_ORDER or not words[0][0].isalpha():
        return None
    # Una sola letra es una inicial: la referencia no empieza por el apellido.
    if len(words[0].rstrip(".")) < 2:
        return None
    decomposed = unicodedata.normalize("NFKD", head).casefold()
    key = "".join(char for char in decomposed if char.isalpha())
    return (head, key) if key else None


def _alphabetical_order(references: list[SegmentedReference]) -> tuple[int, Finding] | None:
    first_case: tuple[int, str, str] | None = None
    cases = 0
    previous: tuple[str, str] | None = None
    for reference in references:
        current = _order_key(reference.text)
        if current is None:
            continue
        if previous and current[1] < previous[1]:
            cases += 1
            first_case = first_case or (reference.order, current[0], previous[0])
        previous = current
    if first_case is None:
        return None
    order, name, before = first_case
    finding = _finding(
        CATALOG[ALPHABETICAL_CODE],
        f"{name} aparece después de {before}",
        f"{name} antes de {before}",
        _cases(cases),
    )
    return order, finding


def _numbering(references: list[SegmentedReference]) -> tuple[int, Finding] | None:
    first_case: tuple[int, str, str] | None = None
    cases = 0
    previous = 0
    # Lo que queda sin número al final no es de la lista: suele ser un anexo o un capítulo.
    last = max(
        (i for i, item in enumerate(references) if WRITTEN_NUMBER.match(item.text)), default=-1
    )
    for reference in references[: last + 1]:
        match = WRITTEN_NUMBER.match(reference.text)
        expected = previous + 1
        number = int(match.group(1)) if match else None
        if number != expected:
            cases += 1
            given = f"[{number}]" if match else f"{reference.text[:SHOWN_START].strip()}…"
            first_case = first_case or (reference.order, given, f"[{expected}]")
        # Después de un salto se sigue desde el número escrito: un salto es un solo caso.
        previous = number if number is not None else expected
    if first_case is None:
        return None
    order, given, right = first_case
    return order, _finding(CATALOG[NUMBERING_CODE], given, right, _cases(cases))
