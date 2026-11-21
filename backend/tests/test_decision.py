"""Motor de decisión híbrido y cinco veredictos (T13). Sin fuentes ni modelo real."""

import asyncio
from collections.abc import Sequence
from dataclasses import replace

import pytest

from app.extraction.base import Author, ExtractedFields
from app.sources.lookup import LookupResult, Strategy
from app.sources.records import Source, SourceRecord
from app.verification.decision import (
    THRESHOLDS,
    CheckedField,
    IndexLevel,
    Verdict,
    decide,
    index_level,
    is_uncovered_work,
    same_person,
    truthfulness_index,
)
from app.verification.nli import NliModel, NliScores
from app.verification.verifier import ReferenceVerifier
from tests.test_nli import REAL_MODEL

DOI = "10.1234/ra.2021.8"
TEXT = (
    "Pérez, M. y López Vera, J. (2021). Redes neuronales en la educación superior. "
    "Revista Andina, 8(1), 10-25. https://doi.org/10.1234/ra.2021.8"
)
FIELDS = ExtractedFields(
    authors=(Author("Pérez", "M."), Author("López Vera", "J.")),
    year=2021,
    title="Redes neuronales en la educación superior",
    container="Revista Andina",
    volume="8",
    issue="1",
    pages="10-25",
    doi=DOI,
)
RECORD = SourceRecord(
    source=Source.CROSSREF,
    doi=DOI,
    title="Redes neuronales en la educación superior",
    authors=(Author("Pérez", "María"), Author("López Vera", "Juan")),
    year=2021,
    other_years=(2022,),
    container="Revista Andina",
    volume="8",
    issue="1",
    pages="10-25",
)
OTHER_WORK = SourceRecord(
    source=Source.CROSSREF,
    doi=DOI,
    title="Producción de cacao en la provincia de Los Ríos",
    authors=(Author("Mora", "Ana"),),
    year=2019,
)
WITHOUT_DOI = replace(FIELDS, doi=None)

ENTAILS = NliScores(entailment=0.95, neutral=0.04, contradiction=0.01)
CONTRADICTS = NliScores(entailment=0.01, neutral=0.04, contradiction=0.95)


class FakeNli:
    """Implicación si la hipótesis aparece tal cual en la premisa; si no, contradicción."""

    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []

    def infer_many(self, pairs: Sequence[tuple[str, str]]) -> list[NliScores]:
        self.pairs.extend(pairs)
        return [ENTAILS if hypothesis in premise else CONTRADICTS for premise, hypothesis in pairs]


class FixedNli:
    def __init__(self, scores: NliScores) -> None:
        self.scores = scores

    def infer_many(self, pairs: Sequence[tuple[str, str]]) -> list[NliScores]:
        return [self.scores] * len(pairs)


def by_doi(*records: SourceRecord) -> LookupResult:
    return LookupResult(Strategy.DIRECT_DOI, records)


def by_search(*records: SourceRecord, failed: bool = False) -> LookupResult:
    return LookupResult(Strategy.BIBLIOGRAPHIC_SEARCH, records, query_failed=failed)


def verdict_of(
    record: SourceRecord,
    fields: ExtractedFields = FIELDS,
    result: LookupResult | None = None,
) -> Verdict | None:
    return decide(TEXT, fields, result or by_doi(record), FakeNli()).verdict


# --- Verificada y Con discrepancias ---------------------------------------------------------


def test_verificada_si_la_obra_existe_y_los_campos_coinciden() -> None:
    verification = decide(TEXT, FIELDS, by_doi(RECORD), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    assert verification.record == RECORD
    assert verification.mismatches == ()
    assert {check.field for check in verification.checks} == {
        CheckedField.TITLE,
        CheckedField.AUTHORS,
        CheckedField.YEAR,
        CheckedField.DOI,
        CheckedField.CONTAINER,
        CheckedField.VOLUME,
        CheckedField.PAGES,
    }


def test_tolera_tildes_mayusculas_y_signos_en_el_titulo() -> None:
    fields = replace(FIELDS, title="«Redes neuronales en la Educacion Superior».")

    assert verdict_of(RECORD, fields) is Verdict.VERIFIED


def test_tolera_un_error_de_digitacion_en_el_titulo() -> None:
    fields = replace(FIELDS, title="Redes nueronales en la educación superior")

    assert verdict_of(RECORD, fields) is Verdict.VERIFIED


def test_acepta_el_anio_del_numero_impreso() -> None:
    assert verdict_of(RECORD, replace(FIELDS, year=2022)) is Verdict.VERIFIED


def test_anio_distinto_es_discrepancia_con_el_valor_oficial() -> None:
    verification = decide(TEXT, replace(FIELDS, year=2019), by_doi(RECORD), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY
    year = verification.check(CheckedField.YEAR)
    assert year is not None
    assert (year.given, year.official, year.matches) == ("2019", "2021", False)


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"volume": "9"}, CheckedField.VOLUME),
        ({"pages": "30-45"}, CheckedField.PAGES),
        ({"container": "Revista de Agronomía"}, CheckedField.CONTAINER),
        ({"authors": (Author("Pérez", "M."), Author("Castro", "L."))}, CheckedField.AUTHORS),
    ],
)
def test_un_campo_distinto_es_discrepancia(change: dict[str, object], field: CheckedField) -> None:
    verification = decide(TEXT, replace(FIELDS, **change), by_doi(RECORD), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY
    assert [check.field for check in verification.mismatches] == [field]


def test_titulo_sin_subtitulo_es_la_misma_obra_con_discrepancia() -> None:
    record = replace(RECORD, title=f"{RECORD.title}: un estudio en Ecuador")

    verification = decide(TEXT, WITHOUT_DOI, by_search(record), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY
    assert [check.field for check in verification.mismatches] == [CheckedField.TITLE]


def test_registro_sin_el_subtitulo_citado_coincide() -> None:
    # Algunas editoriales registran el capítulo sin su subtítulo: la cita completa no
    # es una discrepancia.
    fields = replace(WITHOUT_DOI, title=f"{RECORD.title}: un estudio en Ecuador")

    verification = decide(TEXT, fields, by_search(RECORD), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    title = verification.check(CheckedField.TITLE)
    assert title is not None and title.matches


def test_numero_de_informe_tras_el_titulo_no_es_discrepancia() -> None:
    # Caso real (datos cambiados): APA pone el número tras el título y la fuente no lo registra;
    # el extractor además dejó el paréntesis sin cerrar.
    fields = replace(FIELDS, title=f"{RECORD.title} (Informe n.° 12")

    verification = decide(TEXT, fields, by_doi(RECORD), FakeNli())

    assert verification.verdict is Verdict.VERIFIED


def test_otra_obra_del_autor_con_el_mismo_titulo_principal_y_otro_anio_no_es_la_citada() -> None:
    # Caso real (datos cambiados): un libro de 2016 y un artículo de 1994 del mismo
    # autor, con el mismo título principal.
    fields = replace(WITHOUT_DOI, title="Redes neuronales", year=2016)
    record = replace(RECORD, title="Redes neuronales: principios y práctica", year=1994)

    verification = decide(TEXT, fields, by_search(record), FakeNli())

    assert verification.verdict is Verdict.UNSUPPORTED


def test_titulo_sin_subtitulo_con_el_mismo_anio_sigue_siendo_la_obra() -> None:
    fields = replace(WITHOUT_DOI, title="Redes neuronales")
    record = replace(RECORD, title="Redes neuronales: principios y práctica")

    verification = decide(TEXT, fields, by_search(record), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY


def test_pagina_web_sin_autores_con_titulo_dudoso_no_se_confirma_solo_con_el_nli() -> None:
    # Caso real: la página "Telegram Bot API" y el paquete de R "telegram: R Wrapper
    # Around the Telegram Bot API"; el NLI implica el título, pero es otra obra.
    text = "Telegram. (s. f.). Telegram Bot API. https://core.telegram.org/bots/api"
    fields = ExtractedFields(title="Telegram Bot API")
    record = SourceRecord(
        source=Source.CROSSREF,
        doi="10.32614/cran.package.telegram",
        title="telegram: R Wrapper Around the Telegram Bot API",
    )

    verification = decide(text, fields, by_search(record), FixedNli(ENTAILS))

    assert verification.verdict is Verdict.NOT_VERIFIABLE


def test_titulo_igual_con_otros_autores_es_discrepancia_y_no_contradiccion() -> None:
    # Puede ser un error del extractor en los autores: la obra es la misma.
    fields = replace(FIELDS, authors=(Author("Castro", "L."),))

    assert verdict_of(RECORD, fields) is Verdict.DISCREPANCY


def test_doi_citado_que_nadie_registra_es_discrepancia_si_la_obra_aparece() -> None:
    fields = replace(FIELDS, doi="10.1000/inventado")

    verification = decide(TEXT, fields, by_search(RECORD), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY
    doi = verification.check(CheckedField.DOI)
    assert doi is not None
    assert (doi.given, doi.official, doi.matches) == ("10.1000/inventado", DOI, False)


def test_sin_doi_en_la_referencia_el_doi_no_se_compara() -> None:
    verification = decide(TEXT, WITHOUT_DOI, by_search(RECORD), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    assert verification.check(CheckedField.DOI) is None


def test_un_dato_que_el_registro_no_tiene_no_cuenta_como_diferencia() -> None:
    record = replace(RECORD, volume=None, pages=None, container=None)

    assert verdict_of(record) is Verdict.VERIFIED


# --- Autores, revista y páginas -------------------------------------------------------------


ONE_AUTHOR = replace(FIELDS, authors=(Author("Pérez", "M."),))


@pytest.mark.parametrize(
    "text",
    [
        TEXT.replace("Pérez, M. y López Vera, J.", "Pérez, M. et al."),
        TEXT.replace("Pérez, M. y López Vera, J.", "Pérez, M., y otros"),
        TEXT.replace("Pérez, M. y López Vera, J.", "Pérez, M., ... López Vera, J."),
    ],
)
def test_con_et_al_basta_que_los_autores_citados_firmen_la_obra(text: str) -> None:
    verification = decide(text, ONE_AUTHOR, by_doi(RECORD), FakeNli())

    assert verification.verdict is Verdict.VERIFIED


def test_una_lista_de_autores_incompleta_es_una_discrepancia() -> None:
    # Caso real: se cita solo al último de cinco autores, sin "et al.".
    text = TEXT.replace("Pérez, M. y López Vera, J.", "López Vera, J.")
    fields = replace(FIELDS, authors=(Author("López Vera", "J."),))

    verification = decide(text, fields, by_doi(RECORD), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY
    assert [check.field for check in verification.mismatches] == [CheckedField.AUTHORS]


def test_reconoce_el_apellido_en_el_nombre_completo_de_openalex() -> None:
    record = replace(
        RECORD,
        source=Source.OPENALEX,
        authors=(Author("María Pérez"), Author("Juan Carlos López-Vera")),
    )

    assert verdict_of(record) is Verdict.VERIFIED


def test_reconoce_el_primer_apellido_que_crossref_dejo_entre_los_nombres() -> None:
    # Caso real: Crossref registra given "Ana Beltran", family "Flandoli".
    fields = replace(FIELDS, authors=(Author("Beltran Flandoli", "A."),))
    record = replace(RECORD, authors=(Author("Flandoli", "Ana Beltran"),))

    assert verdict_of(record, fields) is Verdict.VERIFIED


def test_mismo_segundo_apellido_no_es_la_misma_persona() -> None:
    fields = replace(FIELDS, authors=(Author("García Vera", "J."),))
    record = replace(RECORD, authors=(Author("López Vera", "Juan"),))

    verification = decide(TEXT, fields, by_doi(record), FakeNli())

    authors = verification.check(CheckedField.AUTHORS)
    assert authors is not None
    assert authors.matches is False


@pytest.mark.parametrize(
    ("cited", "official"),
    [("Papas", "Νίκος Παπάς"), ("Petrova", "Анна Петрова")],
)
def test_autor_en_alfabeto_griego_o_cirilico_es_el_mismo_que_en_latino(
    cited: str, official: str
) -> None:
    # Caso real: OpenAlex da el nombre en griego y la referencia lo cita en latino.
    assert same_person(Author(cited, "N."), Author(official), THRESHOLDS)
    assert not same_person(Author("Vera", "N."), Author(official), THRESHOLDS)


def test_apellido_hecho_solo_de_particulas_se_compara_entero() -> None:
    # Caso real: un apellido como "Da Do", en el que las dos palabras son partículas.
    assert same_person(Author("Da Do", "A. L."), Author("Da Do", "Ana Lucía"), THRESHOLDS)
    assert not same_person(Author("Da Do", "A. L."), Author("Del Río", "Ana"), THRESHOLDS)


# --- Casos reales de los trabajos de un curso (20 de noviembre de 2026) ----------------------


def test_numero_de_articulo_con_su_palabra_no_se_compara_con_las_paginas() -> None:
    # ACM registra las páginas dentro del artículo (1-26); APA cita "Artículo 66".
    text = TEXT.replace("8(1), 10-25.", "8(1), Artículo 66.")
    fields = replace(FIELDS, pages="66")

    assert decide(text, fields, by_doi(replace(RECORD, pages="1-26")), FakeNli()).verdict is (
        Verdict.VERIFIED
    )
    # Sin la palabra, sí son páginas distintas.
    assert verdict_of(replace(RECORD, pages="1-26"), fields) is Verdict.DISCREPANCY


def test_numero_de_articulo_que_el_extractor_dejo_con_el_volumen() -> None:
    text = TEXT.replace("8(1), 10-25.", "8, Artículo 111110.")
    fields = replace(FIELDS, volume="8, Artículo 111110", issue=None, pages=None)
    record = replace(RECORD, issue=None, pages="111110")

    assert decide(text, fields, by_doi(record), FakeNli()).verdict is Verdict.VERIFIED


def test_preprint_de_arxiv_unido_al_articulo_publicado_acepta_el_anio_del_envio() -> None:
    doi = "10.48550/arXiv.2405.20362"
    fields = replace(FIELDS, year=2024, doi=doi, container=None, volume=None, issue=None)
    fields = replace(fields, pages=None)
    record = replace(RECORD, doi="10.1111/jels.12413", year=2025, other_years=())
    text = TEXT.replace("2021", "2024")

    assert decide(text, fields, by_doi(record), FakeNli()).verdict is Verdict.VERIFIED
    # Otro año que no es el del envío ni el del registro sigue siendo una discrepancia.
    wrong = decide(text, replace(fields, year=2022), by_doi(record), FakeNli())
    year = wrong.check(CheckedField.YEAR)
    assert year is not None
    assert (year.given, year.official, year.matches) == ("2022", "2024", False)


def test_edicion_posterior_de_un_libro_que_la_fuente_no_registra() -> None:
    text = "Rivas, L. y Mora, R. (2021). Arquitectura de software (4.ª ed.). Editorial Andina."
    fields = ExtractedFields(
        authors=(Author("Rivas", "L."), Author("Mora", "R.")),
        year=2021,
        title="Arquitectura de software",
        publisher="Editorial Andina",
    )
    book = SourceRecord(
        source=Source.OPENALEX,
        doi=None,
        title="Arquitectura de software",
        authors=(Author("Luis Rivas"), Author("Rosa Mora")),
        year=1997,
        work_type="book",
    )

    assert decide(text, fields, by_search(book), FakeNli()).verdict is Verdict.VERIFIED
    # Sin la edición en la referencia, el año distinto es una discrepancia.
    plain = text.replace(" (4.ª ed.)", "")
    assert decide(plain, fields, by_search(book), FakeNli()).verdict is Verdict.DISCREPANCY


def test_version_posterior_de_una_guia_que_la_fuente_no_registra() -> None:
    text = "Rivas, L. (2024). Guía de la ingeniería de software, versión 4.0. IEEE."
    fields = ExtractedFields(
        authors=(Author("Rivas", "L."),), year=2024, title="Guía de la ingeniería de software"
    )
    guide = SourceRecord(
        source=Source.OPENALEX,
        doi=None,
        title="Guía de la ingeniería de software",
        authors=(Author("Luis Rivas"),),
        year=2001,
        work_type="book",
    )

    assert decide(text, fields, by_search(guide), FakeNli()).verdict is Verdict.VERIFIED
    # Sin autores que confirmar, el título de otra edición no basta: el año se compara.
    no_authors = replace(fields, authors=())
    verification = decide(text, no_authors, by_search(guide), FakeNli())
    assert verification.verdict is Verdict.DISCREPANCY
    year = verification.check(CheckedField.YEAR)
    assert year is not None
    assert (year.given, year.official) == ("2024", "2001")


def test_otra_version_en_el_registro_no_es_la_obra_citada() -> None:
    # Caso real: la referencia cita la versión 4.0 de una guía y la fuente solo
    # registra la 3.0, con su número en el título: no se comparan como la misma obra.
    text = "Rivas, L. (Ed.). (2024). Guía de la ingeniería de software, versión 4.0. IEEE."
    fields = ExtractedFields(year=2024, title="Guía de la ingeniería de software")
    other = SourceRecord(
        source=Source.OPENALEX,
        doi=None,
        title="Guía de la ingeniería de software: versión 3.0",
        authors=(Author("Pablo Salas"),),
        year=2014,
        work_type="book",
    )

    assert decide(text, fields, by_search(other), FakeNli()).verdict is Verdict.UNSUPPORTED


def test_el_anio_de_una_edicion_posterior_no_se_muestra_como_del_registro() -> None:
    text = "Rivas, L. y Mora, R. (2021). Arquitectura de software (4.ª ed.). Editorial Andina."
    fields = ExtractedFields(
        authors=(Author("Rivas", "L."), Author("Mora", "R.")),
        year=2021,
        title="Arquitectura de software",
    )
    book = SourceRecord(
        source=Source.OPENALEX,
        doi=None,
        title="Arquitectura de software",
        authors=(Author("Luis Rivas"), Author("Rosa Mora")),
        year=1997,
        work_type="book",
    )

    verification = decide(text, fields, by_search(book), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    assert verification.check(CheckedField.YEAR) is None


def test_el_libro_del_capitulo_en_el_texto_no_cuenta_como_su_titulo() -> None:
    # Caso real: el capítulo se citó con el DOI del libro; el título del libro está en
    # la referencia, pero como contenedor, no como título de la obra citada.
    text = (
        "Vera, A. (2025). Un capítulo sobre redes. En L. Mora (Ed.), Redes neuronales en "
        "la educación superior (pp. 73-89). Editorial UNEMI. https://doi.org/10.1234/ra.2021.8"
    )
    fields = replace(
        FIELDS,
        authors=(Author("Vera", "A."),),
        title="Un capítulo sobre redes",
        container="Redes neuronales en la educación superior",
    )
    record = replace(RECORD, container=None, work_type="edited-book")

    title = decide(text, fields, by_doi(record), FakeNli()).check(CheckedField.TITLE)
    assert title is not None
    assert title.matches is False


def test_titulo_cortado_por_el_extractor_pero_completo_en_el_texto() -> None:
    record = replace(RECORD, title="Redes neuronales en la educación superior tecnológica")
    text = TEXT.replace("superior.", "superior tecnológica.")

    assert decide(text, FIELDS, by_doi(record), FakeNli()).verdict is Verdict.VERIFIED
    assert verdict_of(record) is Verdict.DISCREPANCY


def test_norma_tecnica_que_no_esta_en_las_fuentes_no_es_verificable() -> None:
    text = "ISO/IEC. (2023). ISO/IEC 25010:2023. Systems and software engineering. ISO."
    fields = ExtractedFields(title="ISO/IEC 25010:2023. Systems and software engineering")

    assert decide(text, fields, by_search(), FakeNli()).verdict is Verdict.NOT_VERIFIABLE
    assert not is_uncovered_work("Isola, M. (2020). Redes. Revista Andina, 8, 1-2.", fields)


def test_autor_institucional() -> None:
    fields = replace(FIELDS, authors=(Author("Organización Mundial de la Salud"),))
    record = replace(RECORD, authors=(Author("Organizacion Mundial de la Salud"),))

    assert verdict_of(record, fields) is Verdict.VERIFIED


@pytest.mark.parametrize(
    ("given", "official"),
    [
        ("Rev. Andina", "Revista Andina"),
        ("IEEE Trans. Educ.", "IEEE Transactions on Education"),
        # El extractor quita el punto de la última abreviatura.
        (
            "IEEE Trans. Dependable Secur. Comput",
            "IEEE Transactions on Dependable and Secure Computing",
        ),
        ("Revista Andina", "Revista Andina de Educación"),
    ],
)
def test_revista_abreviada_o_sin_subtitulo_coincide(given: str, official: str) -> None:
    fields = replace(FIELDS, container=given)
    record = replace(RECORD, container=official)

    assert verdict_of(record, fields) is Verdict.VERIFIED


def test_el_libro_de_un_capitulo_coincide_aunque_crossref_ponga_antes_la_coleccion() -> None:
    # Caso real (datos cambiados): ["Notas de Computación", "Teoría y Práctica de
    # Bibliotecas Digitales"]; la referencia cita el libro.
    fields = replace(FIELDS, container="Teoría y práctica de bibliotecas digitales")
    record = replace(
        RECORD,
        container="Notas de Computación",
        other_containers=("Teoría y Práctica de Bibliotecas Digitales",),
    )

    verification = decide(TEXT, fields, by_doi(record), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    container = next(c for c in verification.checks if c.field is CheckedField.CONTAINER)
    assert container.official == "Teoría y Práctica de Bibliotecas Digitales"


@pytest.mark.parametrize(
    ("given", "official"),
    [("pp. 10–25", "10-25"), ("10-25", "10"), ("e123", "e123"), ("644-651", "644-51")],
)
def test_paginas_en_otra_forma_coinciden(given: str, official: str) -> None:
    fields = replace(FIELDS, pages=given)
    record = replace(RECORD, pages=official)

    assert verdict_of(record, fields) is Verdict.VERIFIED


def test_volumen_con_prefijo_coincide() -> None:
    assert verdict_of(RECORD, replace(FIELDS, volume="vol. 8")) is Verdict.VERIFIED


def test_ceros_a_la_izquierda_no_son_una_diferencia() -> None:
    record = replace(RECORD, volume="08", pages="010-025")

    assert verdict_of(record) is Verdict.VERIFIED


def test_devuelve_al_titulo_el_subtitulo_que_quedo_en_el_contenedor() -> None:
    # El extractor cortó el título en los dos puntos y dejó el subtítulo en la revista.
    record = replace(RECORD, title="Redes neuronales: en la educación superior")
    fields = replace(
        FIELDS, title="Redes neuronales", container="En la educación superior. Revista Andina"
    )

    verification = decide(TEXT, fields, by_doi(record), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    assert verification.cited is not None
    assert verification.cited.title == "Redes neuronales: En la educación superior"
    assert verification.cited.container == "Revista Andina"


def test_un_titulo_corto_que_no_es_el_inicio_del_registro_no_se_toca() -> None:
    fields = replace(FIELDS, title="Redes", container="Neuronales. Revista Andina")

    verification = decide(TEXT, fields, by_doi(RECORD), FakeNli())

    assert verification.cited is not None
    assert verification.cited.title == "Redes"


def test_el_doi_citado_vale_aunque_la_fuente_traiga_el_de_otra_version() -> None:
    # OpenAlex une la preimpresión de arXiv con el artículo publicado: el DOI citado
    # lleva al registro, aunque el registro traiga el del artículo.
    record = replace(RECORD, doi="10.1145/publicado.2021")

    verification = decide(TEXT, FIELDS, by_doi(record), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    doi = verification.check(CheckedField.DOI)
    assert doi is not None and doi.matches and doi.official == DOI


def test_numero_de_articulo_con_letra_es_la_misma_pagina() -> None:
    verification = decide(
        TEXT, replace(FIELDS, pages="289"), by_doi(replace(RECORD, pages="e289")), FakeNli()
    )

    assert verification.verdict is Verdict.VERIFIED


# --- Contradicción --------------------------------------------------------------------------


def test_doi_que_lleva_a_otra_obra_es_contradiccion() -> None:
    verification = decide(TEXT, FIELDS, by_doi(OTHER_WORK), FakeNli())

    assert verification.verdict is Verdict.CONTRADICTION
    assert verification.record == OTHER_WORK  # el informe muestra a qué obra lleva
    title = verification.check(CheckedField.TITLE)
    assert title is not None
    assert title.official == OTHER_WORK.title


def test_doi_con_titulo_citado_traducido_es_la_misma_obra() -> None:
    # Revista bilingüe: el registro está en inglés y la referencia cita el título en español.
    record = replace(RECORD, title="Neural networks in higher education")

    verification = decide(TEXT, FIELDS, by_doi(record), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY
    assert [check.field for check in verification.mismatches] == [CheckedField.TITLE]


def test_doi_cuyo_registro_trae_solo_algunos_autores_sigue_siendo_la_obra() -> None:
    # Metadatos incompletos: el registro solo lista al primer autor y el título está traducido.
    record = replace(
        RECORD, title="Neural networks in higher education", authors=(Author("Pérez"),)
    )
    fields = replace(FIELDS, authors=FIELDS.authors + (Author("Ruiz", "P."), Author("Vela", "A.")))

    verification = decide(TEXT, fields, by_doi(record), FakeNli())

    assert verification.verdict is Verdict.DISCREPANCY
    authors = verification.check(CheckedField.AUTHORS)
    assert authors is not None and authors.similarity == 0.25  # el campo sí difiere


def test_doi_con_otro_titulo_y_un_apellido_en_comun_por_azar_es_contradiccion() -> None:
    # "Pérez" coincide, pero no es el primer autor de ambas listas: puede ser azar.
    record = replace(OTHER_WORK, authors=(Author("Mora", "Luis"), Author("Pérez", "Ana")))

    assert verdict_of(record) is Verdict.CONTRADICTION


def test_doi_con_otro_titulo_y_solo_la_mitad_de_los_autores_es_contradiccion() -> None:
    # Así queda una referencia inventada que conserva el DOI y uno de dos autores:
    # con el umbral calibrado (T18), la mitad de los autores no basta.
    record = replace(OTHER_WORK, authors=(Author("Pérez", "Ana"), Author("Mora", "Luis")))

    assert verdict_of(record) is Verdict.CONTRADICTION


def test_doi_con_otro_titulo_y_todos_los_autores_es_la_misma_obra() -> None:
    # El título pudo citarse traducido: el DOI y los autores dicen que es la obra.
    record = replace(OTHER_WORK, authors=RECORD.authors)

    assert verdict_of(record) is Verdict.DISCREPANCY


def test_referencia_sin_titulo_se_confirma_por_los_autores() -> None:
    only_doi = ExtractedFields(authors=FIELDS.authors, year=2021, doi=DOI)

    assert verdict_of(RECORD, only_doi) is Verdict.VERIFIED
    assert verdict_of(OTHER_WORK, only_doi) is Verdict.CONTRADICTION


# --- Título dudoso: decide el NLI -----------------------------------------------------------


DOUBTFUL = replace(RECORD, title="Redes neuronales profundas para la educación universitaria")


def test_titulo_dudoso_confirmado_por_el_nli() -> None:
    fields = replace(WITHOUT_DOI, authors=(Author("Ruiz", "P."),) + FIELDS.authors)

    verification = decide(TEXT, fields, by_search(DOUBTFUL), FixedNli(ENTAILS))

    assert verification.verdict is Verdict.DISCREPANCY  # misma obra, título distinto


def test_titulo_dudoso_que_el_nli_rechaza_no_es_la_obra() -> None:
    fields = replace(WITHOUT_DOI, authors=(Author("Ruiz", "P."),) + FIELDS.authors)

    verification = decide(TEXT, fields, by_search(DOUBTFUL), FixedNli(CONTRADICTS))

    assert verification.verdict is Verdict.UNSUPPORTED
    assert verification.record is None


def test_titulo_dudoso_confirmado_por_todos_los_autores() -> None:
    verification = decide(TEXT, WITHOUT_DOI, by_search(DOUBTFUL), FixedNli(CONTRADICTS))

    assert verification.verdict is Verdict.DISCREPANCY


def test_titulo_dudoso_con_otro_anio_no_es_la_obra() -> None:
    # El NLI acepta títulos de tema parecido; el año distinto delata otra obra.
    fields = replace(WITHOUT_DOI, authors=(Author("Ruiz", "P."),) + FIELDS.authors, year=2014)

    verification = decide(TEXT, fields, by_search(DOUBTFUL), FixedNli(ENTAILS))

    assert verification.verdict is Verdict.UNSUPPORTED


def test_titulo_dudoso_sin_autores_que_comparar_lo_decide_el_nli() -> None:
    fields = replace(WITHOUT_DOI, authors=())

    accepted = decide(TEXT, fields, by_search(DOUBTFUL), FixedNli(ENTAILS))
    rejected = decide(TEXT, fields, by_search(DOUBTFUL), FixedNli(CONTRADICTS))

    assert accepted.verdict is Verdict.DISCREPANCY
    assert rejected.verdict is Verdict.UNSUPPORTED


def test_titulo_muy_distinto_no_es_la_obra_aunque_el_nli_lo_acepte() -> None:
    verification = decide(TEXT, WITHOUT_DOI, by_search(OTHER_WORK), FixedNli(ENTAILS))

    assert verification.verdict is Verdict.UNSUPPORTED


# --- Búsqueda por título --------------------------------------------------------------------


def test_elige_el_candidato_que_es_la_obra() -> None:
    verification = decide(TEXT, WITHOUT_DOI, by_search(OTHER_WORK, RECORD), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    assert verification.record == RECORD


def test_en_la_busqueda_un_titulo_igual_sin_ningun_autor_en_comun_no_es_la_obra() -> None:
    # Títulos genéricos: la búsqueda trae otra obra con el mismo título.
    fields = replace(WITHOUT_DOI, authors=(Author("Castro", "L."),))

    assert verdict_of(RECORD, fields, by_search(RECORD)) is Verdict.UNSUPPORTED


def test_pagina_web_hallada_solo_por_un_titulo_igual_es_no_verificable() -> None:
    text = "Wikipedia. (2025). Trastorno del espectro autista. https://es.wikipedia.org/wiki/TEA"
    fields = ExtractedFields(
        authors=(Author(""),), year=2025, title="Trastorno del espectro autista"
    )
    record = replace(
        RECORD, title="Trastorno del espectro autista", authors=(Author("Conde", "A."),)
    )

    verification = decide(text, fields, by_search(record), FakeNli())

    assert verification.verdict is Verdict.NOT_VERIFIABLE


def test_autor_sin_apellido_no_se_compara() -> None:
    fields = replace(FIELDS, authors=(Author(""),) + FIELDS.authors)

    assert verdict_of(RECORD, fields) is Verdict.VERIFIED


def test_candidatos_que_no_son_la_obra_es_sin_respaldo() -> None:
    assert verdict_of(OTHER_WORK, WITHOUT_DOI, by_search(OTHER_WORK)) is Verdict.UNSUPPORTED


def test_sin_candidatos_es_sin_respaldo() -> None:
    assert verdict_of(RECORD, WITHOUT_DOI, by_search()) is Verdict.UNSUPPORTED


# --- No verificable y errores de consulta ---------------------------------------------------


def test_sin_datos_para_buscar_es_no_verificable() -> None:
    result = LookupResult(Strategy.NO_QUERY, ())

    assert decide("Texto ilegible", ExtractedFields(), result, FakeNli()).verdict is (
        Verdict.NOT_VERIFIABLE
    )


@pytest.mark.parametrize(
    "text",
    [
        "Mora, A. (2023). Gestión del riesgo en pymes [Tesis de maestría, Universidad Estatal "
        "de Milagro]. Repositorio UNEMI.",
        "Asamblea Nacional. (2018). Ley Orgánica de Educación Superior. Registro Oficial 297.",
        "INEC. (2024). Encuesta nacional de empleo. https://www.ecuadorencifras.gob.ec/empleo",
    ],
)
def test_obra_no_encontrada_de_un_tipo_no_cubierto_es_no_verificable(text: str) -> None:
    fields = ExtractedFields(title="Gestión del riesgo", year=2023)

    assert decide(text, fields, by_search(), FakeNli()).verdict is Verdict.NOT_VERIFIABLE


def test_articulo_web_con_datos_de_revista_no_se_toma_como_pagina_web() -> None:
    text = "Mora, A. (2023). Gestión del riesgo. Revista X, 4, 1-9. https://revistax.org/a/1"

    assert not is_uncovered_work(text, ExtractedFields(volume="4", pages="1-9"))


def test_error_de_consulta_no_tiene_veredicto() -> None:
    verification = decide(TEXT, WITHOUT_DOI, by_search(failed=True), FakeNli())

    assert verification.verdict is None
    assert verification.query_failed is True


def test_candidatos_que_no_son_la_obra_tras_un_fallo_son_error_de_consulta() -> None:
    result = by_search(OTHER_WORK, failed=True)

    assert decide(TEXT, WITHOUT_DOI, result, FakeNli()).verdict is None


def test_un_fallo_no_impide_verificar_si_la_obra_aparecio() -> None:
    assert verdict_of(RECORD, WITHOUT_DOI, by_search(RECORD, failed=True)) is Verdict.VERIFIED


# --- NLI ------------------------------------------------------------------------------------


def test_cada_campo_es_una_hipotesis_frente_al_registro() -> None:
    verification = decide(TEXT, replace(FIELDS, year=2019), by_doi(RECORD), FakeNli())

    by_field = {check.field: check for check in verification.nli}
    assert set(by_field) == {
        CheckedField.TITLE,
        CheckedField.AUTHORS,
        CheckedField.YEAR,
        CheckedField.CONTAINER,
    }
    assert by_field[CheckedField.TITLE].premise == (
        "El título de la obra es «redes neuronales en la educación superior». "
        "La obra fue escrita por Pérez y López Vera. "
        "La obra se publicó en 2021. La obra apareció en Revista Andina."
    )
    assert by_field[CheckedField.YEAR].hypothesis == "La obra se publicó en 2019."
    assert by_field[CheckedField.YEAR].scores == CONTRADICTS
    assert by_field[CheckedField.TITLE].scores == ENTAILS


def test_no_pregunta_al_nli_por_datos_que_el_registro_no_tiene() -> None:
    verification = decide(TEXT, FIELDS, by_doi(replace(RECORD, container=None)), FakeNli())

    assert CheckedField.CONTAINER not in {check.field for check in verification.nli}


@pytest.mark.skipif(
    not (REAL_MODEL / "model.onnx").is_file(),
    reason="modelo no generado (python -m scripts.export_nli)",
)
def test_con_el_modelo_real() -> None:
    model = NliModel.load(REAL_MODEL)

    matching = decide(TEXT, FIELDS, by_doi(RECORD), model)
    other = decide(TEXT, FIELDS, by_doi(OTHER_WORK), model)

    assert matching.verdict is Verdict.VERIFIED
    assert all(check.scores.entailment > 0.8 for check in matching.nli)
    assert other.verdict is Verdict.CONTRADICTION
    assert all(check.scores.contradiction > 0.8 for check in other.nli)


# --- Índice de veracidad --------------------------------------------------------------------


def test_indice_sin_contar_no_verificables_ni_errores_de_consulta() -> None:
    verdicts = [
        Verdict.VERIFIED,
        Verdict.VERIFIED,
        Verdict.VERIFIED,
        Verdict.DISCREPANCY,
        Verdict.NOT_VERIFIABLE,
        None,
    ]

    assert truthfulness_index(verdicts) == 75.0


def test_indice_redondeado_a_dos_decimales() -> None:
    assert truthfulness_index([Verdict.VERIFIED, Verdict.UNSUPPORTED, Verdict.CONTRADICTION]) == (
        33.33
    )


def test_sin_referencias_que_contar_no_hay_indice() -> None:
    assert truthfulness_index([Verdict.NOT_VERIFIABLE, None]) is None


# --- Verificador ----------------------------------------------------------------------------


class FakeLookup:
    def __init__(self, results: dict[str | None, LookupResult]) -> None:
        self.results = results  # por DOI pedido; None = búsqueda por título
        self.calls: list[str | None] = []

    async def lookup(self, fields: ExtractedFields) -> LookupResult:
        key = fields.doi if fields.doi in self.results else None
        self.calls.append(key)
        return self.results[key]

    async def lookup_everywhere(self, fields: ExtractedFields) -> LookupResult:
        self.calls.append("todas")
        return self.results.get("todas", self.results[None])


def test_vuelve_a_pedir_por_doi_si_la_busqueda_trae_otro_anio() -> None:
    from_search = replace(RECORD, year=2021, other_years=())  # la búsqueda no trae el impreso
    lookup = FakeLookup({None: by_search(from_search), DOI: by_doi(RECORD)})
    verifier = ReferenceVerifier(lookup, FakeNli())

    verification = asyncio.run(verifier.verify(TEXT, replace(WITHOUT_DOI, year=2022)))

    assert verification.verdict is Verdict.VERIFIED
    assert verification.strategy is Strategy.BIBLIOGRAPHIC_SEARCH
    assert lookup.calls == [None, DOI]


def test_si_solo_hay_un_titulo_parecido_busca_en_todas_las_fuentes() -> None:
    # Caso real (datos cambiados): Crossref trae otra obra de los mismos autores, con un
    # título parecido; OpenAlex tiene la citada, con su título y otro año.
    other_work = replace(RECORD, doi="10.5555/otra", title="Redes neuronales para la educación")
    cited = replace(RECORD, doi="10.5555/citada", year=2022, other_years=())
    lookup = FakeLookup(
        {
            None: by_search(other_work),
            "todas": by_search(other_work, cited),
            "10.5555/citada": by_doi(cited),  # con otro año, se vuelve a pedir por DOI
        }
    )
    verifier = ReferenceVerifier(lookup, FixedNli(ENTAILS))

    verification = asyncio.run(verifier.verify(TEXT, WITHOUT_DOI))

    assert verification.record is not None and verification.record.doi == "10.5555/citada"
    assert [check.field for check in verification.mismatches] == [CheckedField.YEAR]
    assert lookup.calls[:2] == [None, "todas"]


def test_con_el_anio_correcto_no_vuelve_a_consultar() -> None:
    lookup = FakeLookup({None: by_search(RECORD)})

    verification = asyncio.run(ReferenceVerifier(lookup, FakeNli()).verify(TEXT, WITHOUT_DOI))

    assert verification.verdict is Verdict.VERIFIED
    assert lookup.calls == [None]


def test_sin_campos_extraidos_es_no_verificable() -> None:
    lookup = FakeLookup({None: LookupResult(Strategy.NO_QUERY, ())})

    verification = asyncio.run(ReferenceVerifier(lookup, FakeNli()).verify(TEXT, None))

    assert verification.verdict is Verdict.NOT_VERIFIABLE


@pytest.mark.parametrize(
    ("index", "level"),
    [
        (None, None),
        (0.0, IndexLevel.LOW),
        (59.9, IndexLevel.LOW),
        (60.0, IndexLevel.MEDIUM),
        (84.9, IndexLevel.MEDIUM),
        (84.96, IndexLevel.HIGH),  # se muestra como 85,0
        (85.0, IndexLevel.HIGH),
        (100.0, IndexLevel.HIGH),
    ],
)
def test_nivel_del_indice_con_los_cortes_de_rf20(
    index: float | None, level: IndexLevel | None
) -> None:
    assert index_level(index) is level
