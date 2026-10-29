"""Extractor spaCy: reglas lingüísticas sobre el tokenizador de spaCy en español.

spaCy no trae un modelo para referencias bibliográficas, y entrenar uno exigiría
cientos de referencias anotadas. Este extractor usa el tokenizador de spaCy y su
Matcher para ubicar las marcas de cada campo (año entre paréntesis, vol., no.,
pp., URL) y reglas de puntuación según la norma detectada (T06) para separar
autores, título y fuente. Es la alternativa basada en reglas que el Laboratorio
compara con AnyStyle, que sí es un modelo entrenado.
"""

import re
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import takewhile

import spacy
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc, Span

from app.extraction.base import Author, Engine, ExtractedFields, ReferenceExtractor
from app.pipeline.norm_detection import Norm, detect_reference_norm
from app.pipeline.patterns import IEEE_NUMBER, INITIALS, UNDATED, UPPER

YEAR_TEXT = r"^(19|20)\d{2}[a-z]?$"
NUMBER_TEXT = r"^[A-Za-z]?\d+$"
PAGES_TEXT = r"^[A-Za-z]?\d+([-–][A-Za-z]?\d+)?$"

IEEE_PREFIX = re.compile(rf"^{IEEE_NUMBER}\s*")
DOI = re.compile(r"10\.\d{4,9}/[^\s\"<>]+")
URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
NO_DATE = re.compile(rf"\((?:{UNDATED})\)\.?", re.IGNORECASE)
# Fin de un bloque de la referencia: punto (o ? !) seguido de mayúscula, ¿, ¡ o una URL.
# El punto de una inicial ("En J. Rivas") no cierra el bloque.
BLOCK_END = re.compile(rf"(?<=[.?!])(?<!\b[{UPPER}]\.)\s+(?=[{UPPER}¿¡]|https?://|www\.)")
# "Revista Andina, 8(1), 10-25" o "Revista Andina, 8, 10-25"
JOURNAL = re.compile(
    r"^(?P<container>.+?),\s*(?P<volume>\d+)\s*(?:\((?P<issue>[^)]+)\))?"
    r"(?:,\s*(?P<pages>[A-Za-z]?\d+(?:\s*[-–]\s*[A-Za-z]?\d+)?))?"
)
# "En J. Rivas (Ed.), Escritura académica (pp. 45-60)"
CHAPTER = re.compile(
    r"^(?:En|In)\s.+?\((?:Eds?|Coords?|Comps?)\.\),\s*(?P<container>.+?)"
    r"(?:\s*\((?:[^)]*?)pp?\.\s*(?P<pages>[^)]+)\))?\.?$"
)
RETRIEVED = re.compile(r"^(?:Recuperado|Retrieved|Disponible|Available)\b", re.IGNORECASE)
APA_PERSON = re.compile(rf"\s*([^,]+?),\s*({INITIALS})\s*(?=,|$)")
IEEE_PERSON = re.compile(rf"^({INITIALS})\s*(.+)$")
AUTHOR_SEPARATOR = re.compile(r",?\s(?:&|y|e|and)\s")
IEEE_AUTHOR_SPLIT = re.compile(r",\s(?:and\s|y\s)?|\s(?:and|y)\s|;\s")
IEEE_PUBLISHER = re.compile(r":\s*(?P<publisher>[^,:]+),\s*(?:19|20)\d{2}")
QUOTED_TITLE = re.compile(r"[“\"](?P<title>[^”\"]+?)[,.]?[”\"]")
ET_AL = re.compile(r"\bet\s+al\.?|…|\.\.\.", re.IGNORECASE)


@dataclass(frozen=True)
class Markers:
    year: Span | None  # año entre paréntesis (APA) o el último año suelto (IEEE)
    volume: str | None
    issue: str | None
    pages: str | None


class SpacyExtractor(ReferenceExtractor):
    engine = Engine.SPACY

    def __init__(self) -> None:
        self._nlp, self._matcher = _pipeline()

    def extract(self, reference: str) -> ExtractedFields:
        text = IEEE_PREFIX.sub("", " ".join(reference.split()))
        doc = self._nlp(text)
        markers = self._markers(doc)
        doi = _doi(text)
        if detect_reference_norm(reference) is Norm.IEEE:
            return _ieee(text, markers, doi)
        # APA y las no identificadas: autor-año es el formato más común en los trabajos.
        return _apa(text, markers, doi)

    def _markers(self, doc: Doc) -> Markers:
        found: dict[str, list[Span]] = {}
        for match_id, start, end in self._matcher(doc):
            found.setdefault(self._nlp.vocab.strings[match_id], []).append(doc[start:end])
        years = found.get("YEAR_IN_PARENS") or found.get("YEAR") or []
        # En APA el año va después de los autores; en IEEE, al final.
        year = (years[0] if "YEAR_IN_PARENS" in found else years[-1]) if years else None
        return Markers(
            year=year,
            volume=_last_token(found.get("VOLUME")),
            issue=_last_token(found.get("ISSUE")),
            pages=_last_token(found.get("PAGES")),
        )


@lru_cache
def _pipeline() -> tuple[Language, Matcher]:
    """Tokenizador en español (sin modelo que descargar) y patrones de las marcas."""
    nlp = spacy.blank("es")
    matcher = Matcher(nlp.vocab)
    dot = {"ORTH": ".", "OP": "?"}
    matcher.add(
        "YEAR_IN_PARENS",
        [[{"ORTH": "("}, {"TEXT": {"REGEX": YEAR_TEXT}}, {"ORTH": {"NOT_IN": [")"]}, "OP": "*"}]],
        greedy="LONGEST",
    )
    matcher.add("YEAR", [[{"TEXT": {"REGEX": YEAR_TEXT}}]])
    matcher.add(
        "VOLUME", [[{"LOWER": {"IN": ["vol", "vol."]}}, dot, {"TEXT": {"REGEX": NUMBER_TEXT}}]]
    )
    matcher.add(
        "ISSUE",
        [
            [
                {"LOWER": {"IN": ["no", "no.", "núm", "núm.", "nro", "nro."]}},
                dot,
                {"TEXT": {"REGEX": NUMBER_TEXT}},
            ]
        ],
    )
    matcher.add(
        "PAGES",
        [
            [{"LOWER": {"IN": ["pp", "pp.", "p", "p."]}}, dot, {"TEXT": {"REGEX": PAGES_TEXT}}],
            # Sin espacio, "pp.71-86" llega como un solo token.
            [{"LOWER": {"REGEX": r"^pp?\.\d+([-–]\d+)?$"}}],
        ],
    )
    return nlp, matcher


def _apa(text: str, markers: Markers, doi: str | None) -> ExtractedFields:
    year: int | None = None
    if markers.year is not None and markers.year[0].text == "(":
        authors_text, rest = text[: markers.year.start_char], text[markers.year.end_char :]
        year = _year_of(markers.year)
        rest = rest.removeprefix(")")
    elif no_date := NO_DATE.search(text):
        authors_text, rest = text[: no_date.start()], text[no_date.end() :]
    else:
        authors_text, rest = "", text

    blocks = [
        block
        for block in BLOCK_END.split(rest.strip(" ."))
        if block and not (URL.match(block) or DOI.match(block) or RETRIEVED.match(block))
    ]
    fields = ExtractedFields(authors=_apa_authors(authors_text), year=year, doi=doi)
    if not blocks:
        return fields

    # La fuente es el primer bloque con forma de revista o de capítulo; lo anterior
    # es el título, aunque tenga un subtítulo después de "?" o "!".
    for index, block in enumerate(blocks[1:], start=1):
        title = _title(blocks[:index])
        if journal := JOURNAL.match(block):
            return replace(
                fields,
                title=title,
                container=journal["container"],
                volume=journal["volume"],
                issue=journal["issue"],
                pages=_clean_pages(journal["pages"]),
            )
        if chapter := CHAPTER.match(block.rstrip(".")):
            return replace(
                fields,
                title=title,
                container=chapter["container"],
                pages=_clean_pages(chapter["pages"]),
            )
    # Libro o página web: título y, después, la editorial o el sitio.
    publisher = blocks[1].rstrip(".") if len(blocks) > 1 else None
    return replace(fields, title=_title(blocks[:1]), publisher=publisher)


def _ieee(text: str, markers: Markers, doi: str | None) -> ExtractedFields:
    quoted = QUOTED_TITLE.search(text)
    if quoted:
        authors_text = text[: quoted.start()]
        title: str | None = quoted["title"].strip()
        rest = text[quoted.end() :]
    else:
        # Libro: "I. Apellido, Título, ed. Ciudad: Editorial, año."
        parts = text.split(", ")
        persons = list(takewhile(IEEE_PERSON.match, parts))
        authors_text = ", ".join(persons)
        remaining = parts[len(persons) :]
        title = remaining[0].strip(" .") if remaining else None
        rest = ", ".join(remaining[1:])

    container_text = re.sub(r"^[\s,]*(?:en|in)\s", "", rest).strip(" ,.")
    container = container_text.split(", ")[0].strip(" .") if quoted and container_text else None
    publisher = IEEE_PUBLISHER.search(text)
    return ExtractedFields(
        authors=_ieee_authors(authors_text.strip(" ,")),
        year=_year_of(markers.year) if markers.year is not None else None,
        title=title,
        container=container or None,
        publisher=publisher["publisher"].strip() if publisher else None,
        volume=markers.volume,
        issue=markers.issue,
        pages=_clean_pages(markers.pages),
        doi=doi,
    )


def _apa_authors(text: str) -> tuple[Author, ...]:
    text = ET_AL.sub("", text).strip(" ,")
    if not text:
        return ()
    persons = APA_PERSON.findall(AUTHOR_SEPARATOR.sub(", ", text))
    if not persons:
        return (Author(family=text.rstrip(".")),)  # organización como autora
    return tuple(Author(family=family.strip(), given=given.strip()) for family, given in persons)


def _ieee_authors(text: str) -> tuple[Author, ...]:
    authors: list[Author] = []
    for part in IEEE_AUTHOR_SPLIT.split(ET_AL.sub("", text)):
        part = part.strip(" ,.")
        if not part:
            continue
        person = IEEE_PERSON.match(part)
        if person:
            authors.append(Author(family=person[2].strip(), given=person[1].strip()))
        else:
            authors.append(Author(family=part))
    return tuple(authors)


def _title(blocks: list[str]) -> str:
    return " ".join(blocks).rstrip(".")


def _year_of(span: Span) -> int | None:
    for token in span:
        if re.match(YEAR_TEXT, token.text):
            return int(token.text[:4])
    return None


def _doi(text: str) -> str | None:
    match = DOI.search(text)
    return match.group().rstrip(".,;)") if match else None


def _clean_pages(pages: str | None) -> str | None:
    if not pages:
        return None
    return re.sub(r"\s*([-–])\s*", r"\1", re.sub(r"^pp?\.\s*", "", pages)).strip()


def _last_token(spans: list[Span] | None) -> str | None:
    """Número de la primera marca encontrada: el último token de "vol. 8"."""
    return spans[0][-1].text if spans else None
