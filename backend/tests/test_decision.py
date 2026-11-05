"""Motor de decisión híbrido y cinco veredictos (T13). Sin fuentes ni modelo real."""

import asyncio
from collections.abc import Sequence
from dataclasses import replace

import pytest

from app.extraction.base import Author, ExtractedFields
from app.sources.lookup import LookupResult, Strategy
from app.sources.records import Source, SourceRecord
from app.verification.decision import (
    CheckedField,
    Verdict,
    decide,
    is_uncovered_work,
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


def test_con_et_al_basta_que_los_autores_citados_firmen_la_obra() -> None:
    fields = replace(FIELDS, authors=(Author("Pérez", "M."),))

    assert verdict_of(RECORD, fields) is Verdict.VERIFIED


def test_reconoce_el_apellido_en_el_nombre_completo_de_openalex() -> None:
    record = replace(
        RECORD,
        source=Source.OPENALEX,
        authors=(Author("María Pérez"), Author("Juan Carlos López-Vera")),
    )

    assert verdict_of(record) is Verdict.VERIFIED


def test_mismo_segundo_apellido_no_es_la_misma_persona() -> None:
    fields = replace(FIELDS, authors=(Author("García Vera", "J."),))
    record = replace(RECORD, authors=(Author("López Vera", "Juan"),))

    verification = decide(TEXT, fields, by_doi(record), FakeNli())

    authors = verification.check(CheckedField.AUTHORS)
    assert authors is not None
    assert authors.matches is False


def test_autor_institucional() -> None:
    fields = replace(FIELDS, authors=(Author("Organización Mundial de la Salud"),))
    record = replace(RECORD, authors=(Author("Organizacion Mundial de la Salud"),))

    assert verdict_of(record, fields) is Verdict.VERIFIED


@pytest.mark.parametrize(
    ("given", "official"),
    [
        ("Rev. Andina", "Revista Andina"),
        ("IEEE Trans. Educ.", "IEEE Transactions on Education"),
        ("Revista Andina", "Revista Andina de Educación"),
    ],
)
def test_revista_abreviada_o_sin_subtitulo_coincide(given: str, official: str) -> None:
    fields = replace(FIELDS, container=given)
    record = replace(RECORD, container=official)

    assert verdict_of(record, fields) is Verdict.VERIFIED


@pytest.mark.parametrize(
    ("given", "official"), [("pp. 10–25", "10-25"), ("10-25", "10"), ("e123", "e123")]
)
def test_paginas_en_otra_forma_coinciden(given: str, official: str) -> None:
    fields = replace(FIELDS, pages=given)
    record = replace(RECORD, pages=official)

    assert verdict_of(record, fields) is Verdict.VERIFIED


def test_volumen_con_prefijo_coincide() -> None:
    assert verdict_of(RECORD, replace(FIELDS, volume="vol. 8")) is Verdict.VERIFIED


# --- Contradicción --------------------------------------------------------------------------


def test_doi_que_lleva_a_otra_obra_es_contradiccion() -> None:
    verification = decide(TEXT, FIELDS, by_doi(OTHER_WORK), FakeNli())

    assert verification.verdict is Verdict.CONTRADICTION
    assert verification.record == OTHER_WORK  # el informe muestra a qué obra lleva
    title = verification.check(CheckedField.TITLE)
    assert title is not None
    assert title.official == OTHER_WORK.title


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


def test_titulo_muy_distinto_no_es_la_obra_aunque_el_nli_lo_acepte() -> None:
    verification = decide(TEXT, WITHOUT_DOI, by_search(OTHER_WORK), FixedNli(ENTAILS))

    assert verification.verdict is Verdict.UNSUPPORTED


# --- Búsqueda por título --------------------------------------------------------------------


def test_elige_el_candidato_que_es_la_obra() -> None:
    verification = decide(TEXT, WITHOUT_DOI, by_search(OTHER_WORK, RECORD), FakeNli())

    assert verification.verdict is Verdict.VERIFIED
    assert verification.record == RECORD


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
        "El título de la obra es «Redes neuronales en la educación superior». "
        "La obra fue escrita por María Pérez y Juan López Vera. "
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


def test_vuelve_a_pedir_por_doi_si_la_busqueda_trae_otro_anio() -> None:
    from_search = replace(RECORD, year=2021, other_years=())  # la búsqueda no trae el impreso
    lookup = FakeLookup({None: by_search(from_search), DOI: by_doi(RECORD)})
    verifier = ReferenceVerifier(lookup, FakeNli())

    verification = asyncio.run(verifier.verify(TEXT, replace(WITHOUT_DOI, year=2022)))

    assert verification.verdict is Verdict.VERIFIED
    assert verification.strategy is Strategy.BIBLIOGRAPHIC_SEARCH
    assert lookup.calls == [None, DOI]


def test_con_el_anio_correcto_no_vuelve_a_consultar() -> None:
    lookup = FakeLookup({None: by_search(RECORD)})

    verification = asyncio.run(ReferenceVerifier(lookup, FakeNli()).verify(TEXT, WITHOUT_DOI))

    assert verification.verdict is Verdict.VERIFIED
    assert lookup.calls == [None]


def test_sin_campos_extraidos_es_no_verificable() -> None:
    lookup = FakeLookup({None: LookupResult(Strategy.NO_QUERY, ())})

    verification = asyncio.run(ReferenceVerifier(lookup, FakeNli()).verify(TEXT, None))

    assert verification.verdict is Verdict.NOT_VERIFIABLE
