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
  obra que las fuentes no cubren (leyes, tesis, páginas web).

Un error de consulta no tiene veredicto (None): no se sabe si la obra existe, así
que no cuenta como No verificable ni entra en el índice (RNF10).

Este módulo no consulta nada: recibe el resultado de la búsqueda y el modelo
NLI, y devuelve la decisión. Los umbrales son iniciales; T18 los calibra con la
partición de calibración del estándar de oro.
"""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
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
    """Campo comparado; los cuatro primeros son los valores del tipo campo_nli."""

    TITLE = "titulo"
    AUTHORS = "autores"
    YEAR = "anio"
    CONTAINER = "contenedor"
    DOI = "doi"
    VOLUME = "volumen"
    PAGES = "paginas"


@dataclass(frozen=True)
class Thresholds:
    # Similitud mínima (0-1) para que el título se dé por igual.
    title_match: float = 0.90
    # Por debajo, el título es de otra obra; entre ambos valores decide el NLI.
    title_candidate: float = 0.60
    # Similitud mínima entre dos apellidos para tomarlos como la misma persona.
    surname_match: float = 0.85
    # Parte de los autores citados con la que el registro de un DOI es la obra
    # aunque el título no coincida (citado traducido, por ejemplo).
    doi_author_support: float = 0.50
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
        _assess(fields, record, strategy, nli, thresholds, uncovered)
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

    if not best.same_work:
        verdict = Verdict.CONTRADICTION
    elif any(not check.matches for check in best.checks):
        verdict = Verdict.DISCREPANCY
    else:
        verdict = Verdict.VERIFIED
    return Verification(verdict, strategy, best.record, best.checks, best.nli)


def truthfulness_index(verdicts: Iterable[Verdict | None]) -> float | None:
    """Porcentaje de Verificadas sobre el total, sin contar las No verificables ni los
    errores de consulta (RF12-CA04). None si no queda ninguna referencia que contar."""
    counted = [verdict for verdict in verdicts if verdict not in (None, Verdict.NOT_VERIFIABLE)]
    if not counted:
        return None
    verified = sum(verdict is Verdict.VERIFIED for verdict in counted)
    return round(100 * verified / len(counted), 2)


# --- Identidad de la obra -------------------------------------------------------------------


@dataclass(frozen=True)
class _Assessment:
    """Un candidato evaluado; el mejor es la obra citada con el título más parecido."""

    record: SourceRecord
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
    authors: FieldCheck | None  # None: no hay autores que comparar
    # Autores que coinciden sobre la lista más corta (la citada o la del registro):
    # el registro puede traer solo algunos autores, y eso no la vuelve otra obra.
    author_overlap: float
    year: FieldCheck | None
    nli_confirms_title: bool
    uncovered_work: bool  # tesis, norma legal o página web (is_uncovered_work)


def _assess(
    fields: ExtractedFields,
    record: SourceRecord,
    strategy: Strategy,
    nli: NliScorer,
    thresholds: Thresholds,
    uncovered_work: bool,
) -> _Assessment:
    checks = _compare(fields, record, strategy, thresholds)
    nli_checks = _infer(fields, record, nli)
    by_field = {check.field: check for check in checks}
    title_nli = next((c.scores for c in nli_checks if c.field is CheckedField.TITLE), None)
    evidence = _Evidence(
        title=_title_identity(fields.title, record.title),
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
    )
    return _Assessment(
        record,
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
      tesis, norma o página web sin autores que lo confirmen.
    - Título dudoso: sí, si el año no lo contradice y lo confirman todos los
      autores, o el NLI junto con alguno de ellos (o solo el NLI, sin autores).
    """
    title, authors, year = evidence.title, evidence.authors, evidence.year
    if title is None or title < thresholds.title_candidate:
        return False
    if authors is not None and authors.similarity == 0:
        return False
    if title >= thresholds.title_match:
        return authors is not None or not evidence.uncovered_work
    if year is not None and not year.matches:
        return False
    if authors is None:
        return evidence.nli_confirms_title
    return authors.matches or evidence.nli_confirms_title


def _title_identity(given: str | None, official: str | None) -> float | None:
    """Similitud de los títulos para reconocer la obra.

    Si solo uno de los dos trae subtítulo, también se compara sin él: un título
    incompleto es una discrepancia del campo, pero sigue siendo la misma obra.
    """
    if not given or not official:
        return None
    similarity = _ratio(given, official)
    if ":" in given and ":" not in official:
        similarity = max(similarity, _ratio(given.split(":")[0], official))
    if ":" in official and ":" not in given:
        similarity = max(similarity, _ratio(given, official.split(":")[0]))
    return similarity


# --- Comparación por campo ------------------------------------------------------------------


def _compare(
    fields: ExtractedFields, record: SourceRecord, strategy: Strategy, thresholds: Thresholds
) -> tuple[FieldCheck, ...]:
    checks: list[FieldCheck] = []
    if fields.title and record.title:
        similarity = _ratio(fields.title, record.title)
        checks.append(
            FieldCheck(
                CheckedField.TITLE,
                fields.title,
                record.title,
                similarity,
                similarity >= thresholds.title_match,
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
    if fields.year is not None and record.year is not None:
        matches = fields.year in (record.year, *record.other_years)
        official = fields.year if matches else record.year
        checks.append(_direct(CheckedField.YEAR, str(fields.year), str(official), matches))
    if doi := normalize_doi(fields.doi):
        if strategy is Strategy.BIBLIOGRAPHIC_SEARCH:
            # Se buscó por título porque ninguna fuente registra el DOI citado.
            checks.append(_direct(CheckedField.DOI, doi, record.doi, False))
        elif record.doi:
            checks.append(_direct(CheckedField.DOI, doi, record.doi, doi == record.doi))
    if fields.container and record.container:
        similarity = _container_similarity(fields.container, record.container)
        checks.append(
            FieldCheck(
                CheckedField.CONTAINER,
                fields.container,
                record.container,
                similarity,
                similarity >= thresholds.container_match,
            )
        )
    if fields.volume and record.volume:
        matches = _volume(fields.volume) == _volume(record.volume)
        checks.append(_direct(CheckedField.VOLUME, fields.volume, record.volume, matches))
    if fields.pages and record.pages:
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
    if found == 1 and not _same_person(given[0], official[0], thresholds):
        return 0.0
    return found / min(len(given), len(official))


def _authors_found(
    given: Sequence[Author], official: Sequence[Author], thresholds: Thresholds
) -> int:
    return sum(
        any(_same_person(person, author, thresholds) for author in official) for person in given
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


def _same_person(given: Author, official: Author, thresholds: Thresholds) -> bool:
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
        return False
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
    """ "IEEE Trans. Educ." abrevia "IEEE Transactions on Education"."""
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
    return all(
        long.startswith(word.rstrip(".")) if word.endswith(".") else word == long
        for word, long in zip(short, full, strict=True)
    )


def _volume(value: str) -> str:
    return _without_leading_zeros(re.sub(r"^(vol\.?|volumen)\s*", "", value.strip().lower()))


def _without_leading_zeros(value: str) -> str:
    """ "04" -> "4": las fuentes y las referencias no rellenan los números igual."""
    return (value.lstrip("0") or value) if value.isdigit() else value


def _page_bounds(value: str) -> tuple[str, str | None] | None:
    """Primera y última página ("pp. 10–25" -> ("10", "25")); None si no hay números."""
    numbers = re.findall(r"[a-z]?\d+", value.lower().replace("pp.", "").replace("p.", ""))
    if not numbers:
        return None
    first, last = numbers[0], numbers[1] if len(numbers) > 1 else None
    return _without_leading_zeros(first), _without_leading_zeros(last) if last else None


def _same_pages(given: tuple[str, str | None], official: tuple[str, str | None]) -> bool:
    # Si una de las dos solo trae la primera página, se compara esa.
    return given[0] == official[0] and (None in (given[1], official[1]) or given[1] == official[1])


# --- Coherencia general (NLI) ---------------------------------------------------------------


def _infer(fields: ExtractedFields, record: SourceRecord, nli: NliScorer) -> tuple[NliCheck, ...]:
    """Cada campo de la referencia es una hipótesis frente al registro completo.

    Premisa e hipótesis usan las mismas frases, así que un campo igual al del
    registro queda implicado y uno distinto, contradicho.
    """
    premise = " ".join(
        sentence
        for _, sentence in _sentences(
            record.title,
            [_full_name(author) for author in _named(record.authors)],
            record.year,
            record.container,
        )
    )
    hypotheses = [
        (field, sentence)
        for field, sentence in _sentences(
            fields.title,
            [_full_name(author) for author in _named(fields.authors)],
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


def _full_name(author: Author) -> str:
    return f"{author.given} {author.family}".strip()


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"


# --- Obras que las fuentes no cubren --------------------------------------------------------

UNCOVERED_WORK = re.compile(
    r"\b(tesis|tesina|trabajo de (titulacion|grado|fin de (grado|master))|ley|reglamento|"
    r"decreto|constitucion de la republica|registro oficial|acuerdo ministerial|codigo organico)\b"
)
URL = re.compile(r"https?://|www\.")


def is_uncovered_work(text: str, fields: ExtractedFields) -> bool:
    """Tipo de obra que Crossref y OpenAlex casi nunca registran: tesis, normas
    legales o páginas web (con URL, sin DOI ni datos de revista)."""
    plain = _strip_accents(text).lower()
    if UNCOVERED_WORK.search(plain):
        return True
    is_web_page = URL.search(plain) and "doi.org" not in plain and not fields.doi
    return bool(is_web_page and not (fields.volume or fields.pages))


# --- Texto ----------------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )


def _normalize(text: str) -> str:
    """Minúsculas, sin tildes ni signos: "«Redes», neuronales." -> "redes neuronales"."""
    return " ".join(re.sub(r"[^\w\s]", " ", _strip_accents(text).lower()).split())


def _ratio(a: str, b: str) -> float:
    return fuzz.ratio(_normalize(a), _normalize(b)) / 100


def _named(authors: Sequence[Author]) -> tuple[Author, ...]:
    """Autores con apellido: el extractor a veces deja uno vacío ("Wikipedia. (2025)")."""
    return tuple(author for author in authors if author.family.strip())


def _surnames(authors: Sequence[Author]) -> str:
    return "; ".join(author.family for author in authors)
