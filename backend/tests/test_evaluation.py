"""Comparación de AnyStyle y spaCy con el estándar de oro (HU-12)."""

from pathlib import Path

import pytest

from app.benchmark.evaluation import Counts, EngineResult, count_field, decide, evaluate
from app.benchmark.gold_set import FIELDS, GoldReference, write_csv
from app.extraction.base import Author, Engine, ExtractedFields, ReferenceExtractor
from scripts.gold_set import main

APA_TEXT = "Pérez, M. y López Vera, J. A. (2021). Redes neuronales. Revista Andina, 8(1), 10–25."


def gold(text: str = APA_TEXT, altered: bool = False, **fields: str) -> GoldReference:
    values = {name: "" for name in FIELDS} | fields
    return GoldReference(
        id="R001", text=text, norm="APA", work_type="articulo", fields=values, altered=altered
    )


class FixedExtractor(ReferenceExtractor):
    """Devuelve siempre los mismos campos; falla si el texto dice "falla"."""

    engine = Engine.SPACY

    def __init__(self, fields: ExtractedFields) -> None:
        self._fields = fields

    def extract(self, reference: str) -> ExtractedFields:
        if "falla" in reference:
            raise ValueError("referencia ilegible")
        return self._fields


@pytest.mark.parametrize(
    ("expected", "extracted", "counts"),
    [
        pytest.param("Redes neuronales", "redes neuronales.", Counts(tp=1), id="igual"),
        pytest.param("Redes neuronales", "Revista Andina", Counts(fp=1, fn=1), id="equivocado"),
        pytest.param("", "Revista Andina", Counts(fp=1), id="inventado"),
        pytest.param("Redes neuronales", "", Counts(fn=1), id="faltante"),
        pytest.param("", "", Counts(), id="ambos-vacios"),
    ],
)
def test_cuenta_cada_campo(expected: str, extracted: str, counts: Counts) -> None:
    assert count_field("titulo", expected, extracted) == counts


def test_los_autores_se_cuentan_apellido_por_apellido() -> None:
    assert count_field("autores", "Pérez; López Vera", "Pérez; López") == Counts(1, 1, 1)


def test_el_doi_se_compara_normalizado() -> None:
    assert count_field("doi", "10.1234/ra.8", "https://doi.org/10.1234/RA.8") == Counts(tp=1)


def test_las_paginas_aceptan_el_guion_largo_del_pdf() -> None:
    assert count_field("paginas", "10-25", "10–25") == Counts(tp=1)


def test_mide_solo_las_referencias_reales() -> None:
    references = [
        gold(autores="Pérez; López Vera", anio="2021", titulo="Redes neuronales"),
        gold(text="falla", anio="2020"),
        gold(altered=True, anio="2019"),  # alterada: no cuenta
    ]
    extractor = FixedExtractor(
        ExtractedFields(
            authors=(Author("Pérez"), Author("López Vera")), year=2021, title="Redes neuronales"
        )
    )

    result = evaluate(references, extractor)

    assert (result.references, result.failures) == (2, 1)
    assert result.by_field["anio"] == Counts(tp=1, fn=1)
    assert result.by_field["autores"] == Counts(tp=2)
    assert result.by_norm["APA"]["titulo"] == Counts(tp=1)


def result(engine: Engine, f1: float) -> EngineResult:
    # Con tantos FP como FN, la precisión, la exhaustividad y el F1 valen lo mismo.
    counts = Counts(tp=round(f1 * 100), fp=100 - round(f1 * 100), fn=100 - round(f1 * 100))
    return EngineResult(engine, 100, by_field={name: counts for name in FIELDS})


def test_gana_el_mayor_f1_en_los_campos_clave() -> None:
    decision = decide([result(Engine.ANYSTYLE, 0.70), result(Engine.SPACY, 0.85)])

    assert (decision.winner, decision.tie) == (Engine.SPACY, False)


def test_con_menos_de_cinco_puntos_es_empate_y_se_mantiene_anystyle() -> None:
    decision = decide([result(Engine.ANYSTYLE, 0.80), result(Engine.SPACY, 0.83)])

    assert (decision.winner, decision.tie) == (Engine.ANYSTYLE, True)


def test_sin_anystyle_no_mide_spacy_en_su_lugar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    final = tmp_path / "final.csv"
    write_csv(final, [gold(autores="Pérez; López Vera", anio="2021", titulo="Redes neuronales")])

    code = main(["evaluar", str(final), "--anystyle", "comando-que-no-existe"])

    assert code == 1
    assert "no se mide nada" in capsys.readouterr().out
