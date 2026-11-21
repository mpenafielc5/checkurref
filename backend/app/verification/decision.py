"""Motor de decisión híbrido (T13): compara una referencia con lo que encontró la
búsqueda en Crossref u OpenAlex y le asigna uno de los cinco veredictos.

Cada campo se compara con la técnica adecuada (RF12-CA01):

- año, DOI, volumen y páginas: comparación directa, porque un modelo de lenguaje
  no compara números de forma fiable;
- título, autores y revista: similitud difusa (rapidfuzz), que tolera tildes
  omitidas, errores de digitación y abreviaturas de revistas;
- coherencia general: NLI, con el registro como premisa y cada campo de la
  referencia como hipótesis. Decide los títulos dudosos (parecidos, pero no
  iguales) y queda guardado para explicar el veredicto.

Veredictos (RF12-CA02):

- Verificada: la obra existe y los campos coinciden.
- Con discrepancias: la obra existe y uno o más campos difieren.
- Contradicción: el registro encontrado corresponde a otra obra: el DOI citado
  lleva a una obra con otro título y otros autores. Con el título igual es la
  misma obra aunque los autores difieran (un error del extractor no la vuelve
  otra), y con los autores iguales también (el título pudo citarse traducido).
- Sin respaldo: la búsqueda terminó sin encontrar la obra.
- No verificable: faltan datos para buscarla, o no se encontró y es un tipo de
  obra que las fuentes no cubren (leyes, tesis, normas técnicas, páginas web).

Un error de consulta no tiene veredicto (None): no se sabe si la obra existe, así
que no cuenta como No verificable ni entra en el índice (RNF10).

Este módulo no consulta nada: recibe el resultado de la búsqueda y el modelo
NLI, y devuelve la decisión. Los umbrales son iniciales; T18 los calibra con la
partición de calibración del estándar de oro.
"""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

from rapidfuzz import fuzz

from app.extraction.base import Author, ExtractedFields
from app.sources.lookup import LookupResult, Strategy
from app.sources.records import SourceRecord, normalize_doi
from app.verification.nli import NliScores


class Verdict(str, Enum):
    """Valores del tipo veredicto de la base de datos."""

    VERIFIED = "verificada"
    DISCREPANCY = "discrepancia"
    CONTRADICTION = "contradiccion"
    UNSUPPORTED = "sin_respaldo"
    NOT_VERIFIABLE = "no_verificable"


class CheckedField(str, Enum):
    """Campo de una referencia; los cuatro primeros son los valores del tipo campo_nli.

    El número y la editorial no se verifican: solo los completa la referencia
    corregida (T26).
    """

    TITLE = "titulo"
    AUTHORS = "autores"
    YEAR = "anio"
    CONTAINER = "contenedor"
    DOI = "doi"
    VOLUME = "volumen"
    PAGES = "paginas"
    ISSUE = "numero"
    PUBLISHER = "editorial"


@dataclass(frozen=True)
class Thresholds:
    """Umbrales calibrados con la partición de calibración del estándar de oro (T18):
    solo doi_author_support mejoró al moverlo; los demás conservan su valor inicial."""

    # Similitud mínima (0-1) para que el título se dé por igual.
    title_match: float = 0.90
    # Por debajo, el título es de otra obra; entre ambos valores decide el NLI.
    title_candidate: float = 0.60
    # Similitud mínima entre dos apellidos para tomarlos como la misma persona.
    surname_match: float = 0.85
    # Parte de los autores citados con la que el registro de un DOI es la obra
    # aunque el título no coincida (citado traducido, por ejemplo). Con la mitad
    # bastaba que una referencia inventada conservara uno de dos autores.
    doi_author_support: float = 0.80
    container_match: float = 0.85
    # Probabilidad de implicación con la que el NLI confirma un título dudoso.
    nli_entailment: float = 0.50


THRESHOLDS = Thresholds()


@dataclass(frozen=True)
class FieldCheck:
    """Un campo de la referencia frente al registro (RF12-CA03)."""

    field: CheckedField
    given: str
    official: str | None  # None: el registro no tiene ese dato
    similarity: float  # 0-1; en la comparación directa, 1 o 0
    matches: bool


@dataclass(frozen=True)
class NliCheck:
    field: CheckedField
    premise: str
    hypothesis: str
    scores: NliScores


@dataclass(frozen=True)
class Verification:
    verdict: Verdict | None  # None: error de consulta (RNF10)
    strategy: Strategy
    record: SourceRecord | None = None  # registro con el que se comparó
    checks: tuple[FieldCheck, ...] = ()
    nli: tuple[NliCheck, ...] = ()
    # Campos con los que se comparó: los extraídos, o con el subtítulo devuelto al
    # título (rejoin_subtitle). None si no se comparó con ningún registro.
    cited: ExtractedFields | None = None

    @property
    def query_failed(self) -> bool:
        return self.verdict is None

    @property
    def mismatches(self) -> tuple[FieldCheck, ...]:
        return tuple(check for check in self.checks if not check.matches)

    def check(self, field: CheckedField) -> FieldCheck | None:
        return next((check for check in self.checks if check.field is field), None)


class NliScorer(Protocol):
    def infer_many(self, pairs: Sequence[tuple[str, str]]) -> list[NliScores]: ...


def decide(
    text: str,
    fields: ExtractedFields,
    result: LookupResult,
    nli: NliScorer,
    thresholds: Thresholds = THRESHOLDS,
) -> Verification:
    """Veredicto de una referencia (`text` es su texto tal como aparece en el PDF)."""
    strategy = result.strategy
    if strategy is Strategy.NO_QUERY:
        return Verification(Verdict.NOT_VERIFIABLE, strategy)
    uncovered = is_uncovered_work(text, fields)
    assessments = [
        _assess(text, fields, record, strategy, nli, thresholds, uncovered)
        for record in result.candidates
    ]
    best = max(assessments, key=_Assessment.rank, default=None)

    # Un resultado de la búsqueda que no es la obra equivale a no encontrarla; el
    # registro al que lleva el DOI citado, en cambio, es una obra distinta.
    if best is None or (not best.same_work and strategy is Strategy.BIBLIOGRAPHIC_SEARCH):
        if result.query_failed:
            return Verification(None, strategy)
        verdict = Verdict.NOT_VERIFIABLE if uncovered else Verdict.UNSUPPORTED
        return Verification(verdict, strategy)

    checks = best.checks
    if not best.same_work:
        verdict = Verdict.CONTRADICTION
    else:
        checks = _flag_missing_authors(checks, best.cited, best.record, text)
        verdict = (
            Verdict.DISCREPANCY if any(not check.matches for check in checks) else Verdict.VERIFIED
        )
    return Verification(verdict, strategy, best.record, checks, best.nli, best.cited)


# Marcas de una lista de autores acortada a propósito: "et al.", "y otros", "y cols." o
# los puntos suspensivos de APA con más de 20 autores.
SHORTENED_AUTHORS = re.compile(
    r"\bet\.?\s+al\b|\by\s+otros\b|\by\s+cols?\b|…|\.\.\.", re.IGNORECASE
)


def _flag_missing_authors(
    checks: tuple[FieldCheck, ...], cited: ExtractedFields, record: SourceRecord, text: str
) -> tuple[FieldCheck, ...]:
    """Una lista de autores incompleta es una discrepancia de la misma obra.

    Se mira solo después de reconocer la obra, para no cambiar cómo se reconoce:
    los autores citados firman la obra, pero el registro tiene más y la referencia
    no los acorta con "et al." ni con puntos suspensivos. Si la acorta, la norma
    decide si estaba permitido (IEEE con más de seis autores; en APA 7 es un
    hallazgo de formato).
    """
    given, official = _named(cited.authors), _named(record.authors)
    if len(given) >= len(official) or SHORTENED_AUTHORS.search(text):
        return checks
    return tuple(
        replace(check, matches=False)
        if check.field is CheckedField.AUTHORS and check.matches
        else check
        for check in checks
    )


def truthfulness_index(verdicts: Iterable[Verdict | None]) -> float | None:
    """Porcentaje de Verificadas sobre el total, sin contar las No verificables ni los
    errores de consulta (RF12-CA04). None si no queda ninguna referencia que contar."""
    counted = [verdict for verdict in verdicts if verdict not in (None, Verdict.NOT_VERIFIABLE)]
    if not counted:
        return None
    verified = sum(verdict is Verdict.VERIFIED for verdict in counted)
    return round(100 * verified / len(counted), 2)


# Cortes del nivel del índice de veracidad (RF20-CA02). El riesgo de un trabajo en un
# lote es su inverso: índice bajo, riesgo alto. Están solo aquí; el frontend recibe el
# nivel ya calculado. Base: en la literatura publicada el 32,7 % de las referencias
# tiene algún error (Logan et al., 2024, doi:10.1177/09610006231177715), y en listas
# de ChatGPT sin revisar solo son reales y correctas entre el 26 y el 62 % (Walters y
# Wilder, 2023, doi:10.1038/s41598-023-41032-5). Alto: menos de la mitad de ese 32,7 %
# con problemas; bajo: más del 40 %, al nivel de una lista generada sin revisar.
LOW_INDEX_BELOW = 60.0
HIGH_INDEX_FROM = 85.0


class IndexLevel(str, Enum):
    HIGH = "alto"
    MEDIUM = "medio"
    LOW = "bajo"


def index_level(index: float | None) -> IndexLevel | None:
    """Nivel del índice con el valor que se muestra (un decimal): así un 84,96, que se ve
    como 85, no queda en el nivel medio. None si no hay índice."""
    if index is None:
        return None
    shown = round(index, 1)
    if shown < LOW_INDEX_BELOW:
        return IndexLevel.LOW
    return IndexLevel.HIGH if shown >= HIGH_INDEX_FROM else IndexLevel.MEDIUM


# --- Identidad de la obra -------------------------------------------------------------------


@dataclass(frozen=True)
class _Assessment:
    """Un candidato evaluado; el mejor es la obra citada con el título más parecido."""

    record: SourceRecord
    cited: ExtractedFields
    checks: tuple[FieldCheck, ...]
    nli: tuple[NliCheck, ...]
    same_work: bool
    title_similarity: float
    author_similarity: float

    def rank(self) -> tuple[bool, float, float]:
        return (self.same_work, self.title_similarity, self.author_similarity)


@dataclass(frozen=True)
class _Evidence:
    """Lo que dice cada señal sobre si el registro es la obra citada."""

    title: float | None  # similitud del título (None: no hay dos títulos que comparar)
    # Similitud con los dos títulos completos: menor si solo coinciden sin el subtítulo.
    whole_title: float | None
    authors: FieldCheck | None  # None: no hay autores que comparar
    # Autores que coinciden sobre la lista más corta (la citada o la del registro):
    # el registro puede traer solo algunos autores, y eso no la vuelve otra obra.
    author_overlap: float
    year: FieldCheck | None
    nli_confirms_title: bool
    uncovered_work: bool  # tesis, norma legal o página web (is_uncovered_work)


def _assess(
    text: str,
    fields: ExtractedFields,
    record: SourceRecord,
    strategy: Strategy,
    nli: NliScorer,
    thresholds: Thresholds,
    uncovered_work: bool,
) -> _Assessment:
    fields = article_number_as_pages(
        rejoin_subtitle(split_labeled_article_number(fields), record), record
    )
    checks = _compare(fields, record, strategy, thresholds, text)
    nli_checks = _infer(fields, record, nli)
    by_field = {check.field: check for check in checks}
    title_nli = next((c.scores for c in nli_checks if c.field is CheckedField.TITLE), None)
    evidence = _Evidence(
        title=title_identity(fields.title, record.title),
        whole_title=title_ratio(fields.title, record.title)
        if fields.title and record.title
        else None,
        authors=by_field.get(CheckedField.AUTHORS),
        author_overlap=_author_overlap(fields.authors, record.authors, thresholds),
        year=by_field.get(CheckedField.YEAR),
        nli_confirms_title=title_nli is not None
        and title_nli.entailment >= thresholds.nli_entailment
        and title_nli.entailment > title_nli.contradiction,
        uncovered_work=uncovered_work,
    )
    same_work = (
        _doi_leads_to_the_work(evidence, thresholds)
        if strategy is Strategy.DIRECT_DOI
        else _search_found_the_work(evidence, thresholds)
    ) and not different_edition(text, record)
    return _Assessment(
        record,
        fields,
        checks,
        nli_checks,
        same_work,
        evidence.title if evidence.title is not None else 0.0,
        evidence.authors.similarity if evidence.authors else 0.0,
    )


def _doi_leads_to_the_work(evidence: _Evidence, thresholds: Thresholds) -> bool:
    """El DOI citado ya señala una obra; la pregunta es si es la citada.

    Lo es con el título igual, o con la mitad o más de los autores en común: el
    título pudo citarse traducido (revistas bilingües) o mal copiado. Si no, es
    Contradicción.
    """
    title, authors = evidence.title, evidence.authors
    if title is not None and title >= thresholds.title_match:
        return True
    if authors is not None:
        return evidence.author_overlap >= thresholds.doi_author_support
    # Sin autores que comparar: lo decide el título dudoso con el NLI.
    return title is None or (title >= thresholds.title_candidate and evidence.nli_confirms_title)


def _search_found_the_work(evidence: _Evidence, thresholds: Thresholds) -> bool:
    """La búsqueda por título devuelve obras parecidas; se exige que algo más lo
    confirme, porque un título genérico se repite en obras distintas.

    - Título igual: sí, salvo que ninguno de los autores coincida, o que sea una
      tesis, norma o página web sin autores que lo confirmen. Si el título solo es
      igual sin el subtítulo, el año también debe coincidir: un autor repite títulos
      cortos (el libro "Ingeniería de software", de 2016, y el artículo "Ingeniería de
      software: principios y práctica", de 1994).
    - Título dudoso: sí, si el año no lo contradice y lo confirman todos los
      autores, o el NLI junto con alguno de ellos (o solo el NLI, sin autores,
      salvo en una tesis, norma o página web: "Telegram Bot API", la página de la
      documentación, no es "telegram: R Wrapper Around the Telegram Bot API").
    """
    title, authors, year = evidence.title, evidence.authors, evidence.year
    if title is None or title < thresholds.title_candidate:
        return False
    if authors is not None and authors.similarity == 0:
        return False
    if title >= thresholds.title_match:
        whole = evidence.whole_title
        if whole is not None and whole < thresholds.title_match and year and not year.matches:
            return False
        return authors is not None or not evidence.uncovered_work
    if year is not None and not year.matches:
        return False
    if authors is None:
        return evidence.nli_confirms_title and not evidence.uncovered_work
    return authors.matches or evidence.nli_confirms_title


# Número de artículo con su palabra: "Artículo 66", "Article e289", "Art. no. 061103".
ARTICLE_LABEL = r"(?:art[ií]culo|article|art\.)\s*(?:n[oº°]\.?\s*)?"
LABELED_ARTICLE = re.compile(rf"\b{ARTICLE_LABEL}(\w+)", re.IGNORECASE)
VOLUME_AND_ARTICLE = re.compile(rf"^(\w+),?\s*{ARTICLE_LABEL}(\w+)$", re.IGNORECASE)
# Preprint de arXiv: su número empieza con el año y el mes del envío (2405 = mayo de 2024).
ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(\d{2})(\d{2})\.", re.IGNORECASE)
# Edición posterior a la primera, como la escribe APA: "(4.ª ed.)", "(2nd ed.)", "(3a ed.)".
LATER_EDITION = re.compile(
    r"\(\s*([2-9]|\d{2})\s*(?:\.?\s*[ªºa°]|nd|rd|th|st)?\.?\s*(?:ed\.?|edici[oó]n|edition)\s*\)"
    # O una versión numerada de una guía: "Guía de la ingeniería, versión 4.0".
    r"|\bversi[oó]n\s*(?:[2-9]|\d{2})(?:\.\d+)?\b",
    re.IGNORECASE,
)
BOOK_TYPES = {"book", "monograph", "edited-book", "reference-book"}
# Número de la edición o versión: "(4.ª ed.)", "(2nd ed.)", "version 4.0", "Versión 3".
EDITION_NUMBER = re.compile(
    r"\b(\d{1,2})\s*(?:\.?\s*[ªºa°]|nd|rd|th|st)?\.?\s*(?:ed\.|edici[oó]n\b|edition\b)"
    r"|\bversi[oó]n\s*(\d{1,2})(?:\.\d+)?\b",
    re.IGNORECASE,
)


def labeled_article_number(text: str, pages: str) -> bool:
    """Las páginas citadas son un número de artículo con su palabra en la referencia."""
    value = pages.strip().casefold()
    return any(match.group(1).casefold() == value for match in LABELED_ARTICLE.finditer(text))


def split_labeled_article_number(fields: ExtractedFields) -> ExtractedFields:
    """Separa el número de artículo que el extractor dejó con el volumen:
    "183, Artículo 111110" -> volumen "183" y páginas "111110"."""
    match = VOLUME_AND_ARTICLE.match(fields.volume or "")
    if not match or fields.pages:
        return fields
    return replace(fields, volume=match.group(1), pages=match.group(2))


def arxiv_year(doi: str | None) -> int | None:
    """Año del primer envío de un preprint de arXiv, según su número; None si no lo es.
    Es el año que DataCite registra para ese DOI."""
    match = ARXIV_DOI.match(normalize_doi(doi) or "")
    return 2000 + int(match.group(1)) if match else None


def expected_year(fields: ExtractedFields, record: SourceRecord) -> int | None:
    """El año de la obra citada. Si se citó el preprint de arXiv, el de su envío: OpenAlex
    une el preprint con el artículo publicado y da el año de este último."""
    return arxiv_year(fields.doi) or record.year


def cited_year_accepted(fields: ExtractedFields, record: SourceRecord, text: str) -> bool:
    """El año citado es el de la obra: el del registro, otro de sus años (el del número
    impreso de la revista), el del preprint de arXiv citado o, en un libro, el de una
    edición posterior que la referencia declara y la fuente no registra ("(4.ª ed.)",
    cuando la fuente solo tiene la primera)."""
    if fields.year is None:
        return False
    if fields.year in (record.year, *record.other_years, arxiv_year(fields.doi)):
        return True
    return _later_edition_year(fields, record, text)


def _later_edition_year(fields: ExtractedFields, record: SourceRecord, text: str) -> bool:
    """El año citado es el de una edición posterior que la fuente no registra. Ese año
    no se compara: el registro solo tiene el de otra edición, y mostrarlo como "En el
    registro" sería falso."""
    return bool(
        fields.year is not None
        and fields.year not in (record.year, *record.other_years, arxiv_year(fields.doi))
        and LATER_EDITION.search(text)
        and record.work_type in BOOK_TYPES
        and record.year is not None
        and fields.year > record.year
        and _all_authors_found(fields, record)
    )


def _all_authors_found(fields: ExtractedFields, record: SourceRecord) -> bool:
    """Todos los autores citados firman la obra del registro. Sin autores que
    confirmar, un título parecido de otra edición no basta para aceptar el año."""
    given, official = _named(fields.authors), _named(record.authors)
    return bool(given and official) and all(
        any(same_person(person, author, THRESHOLDS) for author in official) for person in given
    )


def different_edition(text: str, record: SourceRecord) -> bool:
    """La referencia declara una edición o versión y el título del registro declara
    otra: "version 4.0" frente a "Guide ... : Version 3.0". El registro es otra obra."""
    cited, official = _edition_number(text), _edition_number(record.title or "")
    return cited is not None and official is not None and cited != official


def _edition_number(text: str) -> int | None:
    match = EDITION_NUMBER.search(text)
    if not match:
        return None
    return int(next(group for group in match.groups() if group))


def article_number_as_pages(fields: ExtractedFields, record: SourceRecord) -> ExtractedFields:
    """Devuelve a las páginas el número de artículo que el extractor tomó por volumen.

    Algunas revistas numeran cada artículo en lugar de darle páginas, y ese número va
    en el lugar de las páginas (normas-apa.org, citar revista). Si la referencia omite
    el volumen ("Revista de Educación, 100463."), el extractor lee el número
    como volumen. Se corrige solo si el registro trae ese número como página y otro
    volumen: así, lo que falta es el volumen, no un volumen equivocado.
    """
    if not fields.volume or fields.pages or not record.pages:
        return fields
    if record.volume and _volume(fields.volume) == _volume(record.volume):
        return fields
    if _normalize(fields.volume) != _normalize(record.pages):
        return fields
    return replace(fields, volume=None, pages=fields.volume)


def rejoin_subtitle(fields: ExtractedFields, record: SourceRecord) -> ExtractedFields:
    """Devuelve al título el subtítulo que el extractor dejó en el contenedor.

    El extractor a veces corta el título en los dos puntos y deja el subtítulo al
    inicio del contenedor: título "SIGA" y contenedor "Sistema de gestión académica
    en línea. Congreso Internacional de Tecnología". Si
    el título del registro es el citado más un trozo con el que empieza el contenedor,
    ese trozo vuelve al título y el contenedor se queda con el resto.
    """
    title, container = fields.title, fields.container
    if not title or not container or not record.title:
        return fields
    given, official = _normalize(title), _normalize(record.title)
    if not official.startswith(given + " "):
        return fields
    subtitle = official[len(given) :].strip()
    for end in [match.start() for match in re.finditer(r"[.:]\s", container)] + [len(container)]:
        if _normalize(container[:end]) == subtitle:
            rest = container[end:].lstrip(" .:")
            joined = f"{title.rstrip(' :')}: {container[:end].strip()}"
            return replace(fields, title=joined, container=rest or None)
    return fields


def without_title_note(given: str, official: str) -> str:
    """El título citado sin la nota entre paréntesis del final, si el registro no la trae.

    APA pone tras el título el número de informe o la edición: "Marco de
    autorización (Informe n.° 12)", "Redes neuronales (3.ª ed.)". No es parte del
    título, y las fuentes no la registran. El paréntesis puede venir sin cerrar.
    """
    if official.rstrip(" .").endswith(")"):
        return given
    return TITLE_NOTE.sub("", given) or given


def title_ratio(given: str, official: str) -> float:
    """Similitud de los títulos, con la nota del final o sin ella."""
    return max(_ratio(given, official), _ratio(without_title_note(given, official), official))


def record_lacks_subtitle(given: str, official: str) -> bool:
    """El registro trae solo la parte del título antes de los dos puntos.

    Algunas editoriales registran el capítulo sin su subtítulo (la fuente
    tiene "Tutor virtual" para "Tutor virtual: un asistente para la educación en
    línea"). El título citado es el completo; no hay discrepancia. Al revés, una
    referencia que omite el subtítulo del registro sí la tiene.
    """
    if ":" not in given or ":" in official:
        return False
    main = _normalize(given.split(":", 1)[0])
    return bool(main) and main == _normalize(official)


def _title_in_text(official: str, text: str) -> bool:
    """El título del registro está completo en el texto de la referencia: el extractor
    lo cortó ("... en la educación" de "... en la educación superior (arXiv:...)"),
    pero el estudiante lo citó bien."""
    title = _normalize(official)
    return len(title.split()) >= MIN_WORDS_TITLE_IN_TEXT and f" {title} " in (
        f" {_normalize(text)} "
    )


def _is_cited_container(official_title: str, container: str | None, thresholds: Thresholds) -> bool:
    """El título del registro es el libro o la revista que la referencia cita como
    contenedor: el DOI citado es el del libro de un capítulo. Ese título también está
    en el texto, pero no es el título de la obra citada."""
    return bool(container) and _ratio(official_title, container or "") >= (
        thresholds.container_match
    )


# Un título corto ("Introduction") puede aparecer dentro de otro texto por azar.
MIN_WORDS_TITLE_IN_TEXT = 4


def title_identity(given: str | None, official: str | None) -> float | None:
    """Similitud de los títulos para reconocer la obra.

    Si solo uno de los dos trae subtítulo, también se compara sin él: un título
    incompleto es una discrepancia del campo, pero sigue siendo la misma obra.
    """
    if not given or not official:
        return None
    similarity = title_ratio(given, official)
    if ":" in given and ":" not in official:
        similarity = max(similarity, _ratio(given.split(":")[0], official))
    if ":" in official and ":" not in given:
        similarity = max(similarity, _ratio(given, official.split(":")[0]))
    return similarity


# --- Comparación por campo ------------------------------------------------------------------


def _compare(
    fields: ExtractedFields,
    record: SourceRecord,
    strategy: Strategy,
    thresholds: Thresholds,
    text: str,
) -> tuple[FieldCheck, ...]:
    checks: list[FieldCheck] = []
    if fields.title and record.title:
        similarity = title_ratio(fields.title, record.title)
        checks.append(
            FieldCheck(
                CheckedField.TITLE,
                fields.title,
                record.title,
                similarity,
                similarity >= thresholds.title_match
                or record_lacks_subtitle(fields.title, record.title)
                or (
                    _title_in_text(record.title, text)
                    and not _is_cited_container(record.title, fields.container, thresholds)
                ),
            )
        )
    given_authors, official_authors = _named(fields.authors), _named(record.authors)
    if given_authors and official_authors:
        similarity = _author_similarity(given_authors, official_authors, thresholds)
        checks.append(
            FieldCheck(
                CheckedField.AUTHORS,
                _surnames(given_authors),
                _surnames(official_authors),
                similarity,
                similarity == 1.0,
            )
        )
    if (
        fields.year is not None
        and record.year is not None
        and not _later_edition_year(fields, record, text)
    ):
        matches = cited_year_accepted(fields, record, text)
        official = fields.year if matches else expected_year(fields, record)
        checks.append(_direct(CheckedField.YEAR, str(fields.year), str(official), matches))
    if doi := normalize_doi(fields.doi):
        if strategy is Strategy.BIBLIOGRAPHIC_SEARCH:
            # Se buscó por título porque ninguna fuente registra el DOI citado como obra.
            checks.append(_direct(CheckedField.DOI, doi, record.doi, False))
        elif record.doi:
            # El registro llegó por el DOI citado, así que ese DOI está registrado. Si el
            # registro trae otro, la fuente agrupó dos versiones de la obra (OpenAlex une
            # la preimpresión de arXiv con el artículo publicado): el citado es válido.
            checks.append(_direct(CheckedField.DOI, doi, doi, True))
    if fields.container and record.container:
        # Se compara con el título del contenedor que más se parezca: el libro de un
        # capítulo puede venir después de su colección.
        similarity, official = max(
            (_container_similarity(fields.container, title), title)
            for title in (record.container, *record.other_containers)
        )
        checks.append(
            FieldCheck(
                CheckedField.CONTAINER,
                fields.container,
                official,
                similarity,
                similarity >= thresholds.container_match,
            )
        )
    if fields.volume and record.volume:
        matches = _volume(fields.volume) == _volume(record.volume)
        checks.append(_direct(CheckedField.VOLUME, fields.volume, record.volume, matches))
    # Un número de artículo ("Artículo 66") no se compara con las páginas que la fuente
    # le da dentro del artículo ("1-26", ACM): son datos distintos.
    if fields.pages and record.pages and not labeled_article_number(text, fields.pages):
        given, official = _page_bounds(fields.pages), _page_bounds(record.pages)
        if given and official:
            checks.append(
                _direct(
                    CheckedField.PAGES, fields.pages, record.pages, _same_pages(given, official)
                )
            )
    return tuple(checks)


def _direct(field: CheckedField, given: str, official: str | None, matches: bool) -> FieldCheck:
    return FieldCheck(field, given, official, 1.0 if matches else 0.0, matches)


def _author_similarity(
    given: Sequence[Author], official: Sequence[Author], thresholds: Thresholds
) -> float:
    """Parte de los autores citados que firman la obra (solo en ese sentido: con
    "et al." la referencia nombra menos autores que el registro)."""
    return _authors_found(given, official, thresholds) / len(given)


def _author_overlap(
    given: Sequence[Author], official: Sequence[Author], thresholds: Thresholds
) -> float:
    """Parte de los autores en común sobre la lista más corta. Con un solo autor en
    común, solo cuenta si es el primero de ambas: un apellido frecuente coincide por azar."""
    given, official = _named(given), _named(official)
    if not given or not official:
        return 0.0
    found = _authors_found(given, official, thresholds)
    if found == 1 and not same_person(given[0], official[0], thresholds):
        return 0.0
    return found / min(len(given), len(official))


def _authors_found(
    given: Sequence[Author], official: Sequence[Author], thresholds: Thresholds
) -> int:
    return sum(
        any(same_person(person, author, thresholds) for author in official) for person in given
    )


# Partículas de los apellidos, que no distinguen a una persona de otra.
PARTICLES = {
    "de",
    "del",
    "la",
    "las",
    "los",
    "y",
    "e",
    "da",
    "das",
    "do",
    "dos",
    "di",
    "van",
    "von",
}


def same_person(given: Author, official: Author, thresholds: Thresholds) -> bool:
    """El primer apellido citado aparece en el nombre completo del autor del registro.

    Se busca en el nombre completo porque las fuentes separan mal los dos
    apellidos: OpenAlex no los separa ("María Pérez Vera") y Crossref a veces deja
    el primero entre los nombres (given "Ana Beltran", family "Flandoli"). Una
    organización (sin nombres) se compara entera.
    """
    if not given.given:
        return fuzz.token_set_ratio(_normalize(given.family), _normalize(official.family)) >= (
            thresholds.surname_match * 100
        )
    surname = [word for word in _normalize(given.family).split() if word not in PARTICLES]
    full_name = _normalize(f"{official.given} {official.family}")
    words = [word for word in full_name.split() if word not in PARTICLES]
    if not surname:
        # Un apellido hecho solo de partículas ("Da Do") se busca entero.
        cited = _normalize(given.family)
        return bool(cited) and f" {cited} " in f" {full_name} "
    return any(fuzz.ratio(surname[0], word) >= thresholds.surname_match * 100 for word in words)


# Palabras vacías que una abreviatura de revista suele omitir.
CONTAINER_STOPWORDS = {"de", "del", "la", "el", "los", "las", "y", "en", "of", "the", "and", "on"}
CONTAINER_STOPWORDS |= {"for", "in", "&"}


def _container_similarity(given: str, official: str) -> float:
    if _abbreviates(given, official):
        return 1.0
    a, b = _normalize(given), _normalize(official)
    # token_set_ratio acepta que una contenga a la otra ("Revista Andina" en
    # "Revista Andina de Educación"), frecuente al citar revistas.
    return max(fuzz.ratio(a, b), fuzz.token_set_ratio(a, b)) / 100


def _abbreviates(given: str, official: str) -> bool:
    """ "IEEE Trans. Educ." abrevia "IEEE Transactions on Education".

    La última palabra puede llegar sin su punto: el extractor quita la puntuación
    final ("IEEE Trans. Dependable Secur. Comput").
    """
    short = [
        word
        for word in re.findall(r"\w+\.?", _strip_accents(given).lower())
        if word.rstrip(".") not in CONTAINER_STOPWORDS
    ]
    full = [
        word
        for word in re.findall(r"\w+", _strip_accents(official).lower())
        if word not in CONTAINER_STOPWORDS
    ]
    if len(short) != len(full) or not any(w.endswith(".") for w in short):
        return False
    last = len(short) - 1
    return all(
        long.startswith(word.rstrip("."))
        if word.endswith(".") or position == last
        else word == long
        for position, (word, long) in enumerate(zip(short, full, strict=True))
    )


def _volume(value: str) -> str:
    return _without_leading_zeros(re.sub(r"^(vol\.?|volumen)\s*", "", value.strip().lower()))


def _without_leading_zeros(value: str) -> str:
    """ "04" -> "4": las fuentes y las referencias no rellenan los números igual."""
    return (value.lstrip("0") or value) if value.isdigit() else value


def _page_bounds(value: str) -> tuple[str, str | None] | None:
    """Primera y última página ("pp. 10–25" -> ("10", "25")); None si no hay números."""
    # Sin la letra de los números de artículo: "e289" y "289" son la misma página.
    numbers = re.findall(r"\d+", value.lower().replace("pp.", "").replace("p.", ""))
    if not numbers:
        return None
    first, last = numbers[0], numbers[1] if len(numbers) > 1 else None
    return _without_leading_zeros(first), _without_leading_zeros(last) if last else None


def _same_pages(given: tuple[str, str | None], official: tuple[str, str | None]) -> bool:
    # Si una de las dos solo trae la primera página, se compara esa.
    if given[0] != official[0]:
        return False
    if given[1] is None or official[1] is None:
        return True
    return _same_last_page(given[1], official[1]) or _same_last_page(official[1], given[1])


def _same_last_page(full: str, short: str) -> bool:
    """La última página abreviada es la misma: "644-651" y "644-51"."""
    return full == short or (len(short) < len(full) and full.endswith(short))


# --- Coherencia general (NLI) ---------------------------------------------------------------


def _infer(fields: ExtractedFields, record: SourceRecord, nli: NliScorer) -> tuple[NliCheck, ...]:
    """Cada campo de la referencia es una hipótesis frente al registro completo.

    Premisa e hipótesis usan las mismas frases, así que un campo igual al del
    registro queda implicado y uno distinto, contradicho. Las dos se escriben igual
    aunque la fuente y la norma no lo hagan: el título en minúsculas (APA lo pide en
    tipo oración y las fuentes lo guardan en tipo título) y los autores por su
    apellido (la referencia trae iniciales y la fuente, el nombre completo). Con
    "Agile" frente a "agile" o "M. Pérez" frente a "María Pérez", el modelo
    marcaba como contradicción un campo igual.
    """
    premise = " ".join(
        sentence
        for _, sentence in _sentences(
            _lower(record.title),
            [author.family for author in _named(record.authors)],
            record.year,
            record.container,
        )
    )
    hypotheses = [
        (field, sentence)
        for field, sentence in _sentences(
            _lower(fields.title and without_title_note(fields.title, record.title or "")),
            [author.family for author in _named(fields.authors)],
            fields.year,
            fields.container,
        )
        if _has(record, field)
    ]
    if not premise or not hypotheses:
        return ()
    scores = nli.infer_many([(premise, hypothesis) for _, hypothesis in hypotheses])
    return tuple(
        NliCheck(field, premise, hypothesis, score)
        for (field, hypothesis), score in zip(hypotheses, scores, strict=True)
    )


def _sentences(
    title: str | None, authors: list[str], year: int | None, container: str | None
) -> list[tuple[CheckedField, str]]:
    sentences: list[tuple[CheckedField, str]] = []
    if title:
        sentences.append((CheckedField.TITLE, f"El título de la obra es «{title}»."))
    if authors:
        sentences.append((CheckedField.AUTHORS, f"La obra fue escrita por {_join(authors)}."))
    if year is not None:
        sentences.append((CheckedField.YEAR, f"La obra se publicó en {year}."))
    if container:
        sentences.append((CheckedField.CONTAINER, f"La obra apareció en {container}."))
    return sentences


def _has(record: SourceRecord, field: CheckedField) -> bool:
    values = {
        CheckedField.TITLE: record.title,
        CheckedField.AUTHORS: _named(record.authors),
        CheckedField.YEAR: record.year,
        CheckedField.CONTAINER: record.container,
    }
    return bool(values.get(field))


def _lower(title: str | None) -> str | None:
    return title.lower() if title else title


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"


# --- Obras que las fuentes no cubren --------------------------------------------------------

UNCOVERED_WORK = re.compile(
    r"\b(tesis|tesina|trabajo de (titulacion|grado|fin de (grado|master))|ley|reglamento|"
    r"decreto|constitucion de la republica|registro oficial|acuerdo ministerial|codigo organico)\b"
)
# Norma técnica citada con su organismo como autor: "ISO/IEC. (2023). ISO/IEC 25010...".
STANDARD_BODY = re.compile(r"^(?:iso|iec|ieee std|inen|une|astm|ansi|nist sp)\b[\s/.,]")
URL = re.compile(r"https?://|www\.")
# Nota entre paréntesis al final del título, cerrada o no: "(Informe n.° 12)", "(3.ª ed.)".
TITLE_NOTE = re.compile(r"\s*\([^()]*\)?[\s.]*$")


def is_uncovered_work(text: str, fields: ExtractedFields) -> bool:
    """Tipo de obra que Crossref y OpenAlex casi nunca registran: tesis, normas
    legales o páginas web (con URL, sin DOI ni datos de revista)."""
    plain = _strip_accents(text).lower()
    if UNCOVERED_WORK.search(plain) or STANDARD_BODY.match(plain):
        return True
    is_web_page = URL.search(plain) and "doi.org" not in plain and not fields.doi
    return bool(is_web_page and not (fields.volume or fields.pages))


# --- Texto ----------------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def _normalize(text: str) -> str:
    """Minúsculas, sin tildes ni signos y en letras latinas: "«Redes», neuronales." ->
    "redes neuronales"; "Παπάς" -> "papas"."""
    latin = _strip_accents(text).lower().translate(TO_LATIN)
    return " ".join(re.sub(r"[^\w\s]", " ", latin).split())


# Transliteración simple del griego y del cirílico. OpenAlex da a veces el nombre del
# autor en su alfabeto ("Νίκος Παπάς") y el estudiante lo cita en latino
# ("Papas, N."): sin ella, el mismo autor parecía otro. La comparación es difusa,
# así que basta una correspondencia letra por letra.
TO_LATIN = str.maketrans(
    {
        **dict(zip("αβγδεζηικλμνξοπρσςτυφω", "abgdeziiklmnxoprsstyfo", strict=True)),
        "θ": "th",
        "χ": "ch",
        "ψ": "ps",
        **dict(zip("абвгдезийклмнопрстуфыэіґ", "abvgdeziiklmnoprstufyeig", strict=True)),
        "ж": "zh",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ю": "yu",
        "я": "ya",
        "є": "ye",
        "ъ": "",
        "ь": "",
    }
)


def _ratio(a: str, b: str) -> float:
    return fuzz.ratio(_normalize(a), _normalize(b)) / 100


def _named(authors: Sequence[Author]) -> tuple[Author, ...]:
    """Autores con apellido: el extractor a veces deja uno vacío ("Wikipedia. (2025)")."""
    return tuple(author for author in authors if author.family.strip())


def _surnames(authors: Sequence[Author]) -> str:
    return "; ".join(author.family for author in authors)
