"""Verificación con el estándar de oro (T17 y T18). Sin fuentes ni modelo real."""

import asyncio
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from app.benchmark.gold_set import GoldReference, write_csv
from app.benchmark.verification_eval import (
    CONTROL,
    GRID,
    Case,
    KindScore,
    MemoNli,
    Outcome,
    RecordingLookup,
    Score,
    calibrate,
    partition_cases,
    score,
    verify_cases,
)
from app.extraction.base import ExtractedFields
from app.sources.lookup import LookupResult, Strategy
from app.verification.decision import THRESHOLDS, Thresholds, Verdict
from app.verification.nli import NliScores
from scripts.gold_set import _print_test, _review_row, main
from tests.test_decision import DOI, FIELDS, RECORD, TEXT, FakeNli

REAL = GoldReference(id="R001", text=TEXT, norm="APA", work_type="articulo", partition="prueba")
ALTERED = replace(REAL, id="R001-alt-anio", altered=True, alteration="anio", source_id="R001")


def outcome(reference: GoldReference, verdict: Verdict | None) -> Outcome:
    return Outcome(Case(reference, None), verdict)


def scored(false_alarms: int = 0, alerts: int = 0, exact: int = 0) -> Score:
    return Score(
        {
            CONTROL: KindScore(total=5, alerts=false_alarms, exact=exact),
            "anio": KindScore(total=5, alerts=alerts),
        }
    )


class FakeLookup:
    def __init__(self, result: LookupResult) -> None:
        self.result = result
        self.calls = 0

    async def lookup(self, fields: ExtractedFields) -> LookupResult:
        self.calls += 1
        return self.result


# --- Medidas --------------------------------------------------------------------------------


def test_cuenta_falsas_alarmas_alertas_y_aciertos_exactos() -> None:
    result = score(
        [
            outcome(REAL, Verdict.VERIFIED),
            outcome(REAL, Verdict.DISCREPANCY),
            outcome(ALTERED, Verdict.DISCREPANCY),
            outcome(ALTERED, Verdict.CONTRADICTION),
            outcome(ALTERED, Verdict.VERIFIED),
            outcome(ALTERED, None),
        ]
    )

    assert result.false_alarms == 1
    assert result.alerts == 2  # un error de consulta no es una alerta
    assert result.exact == 2  # el control verificado y el año con discrepancias
    assert result.errors == 1
    assert result.by_kind["anio"].verdicts == {
        "discrepancia": 1,
        "contradiccion": 1,
        "verificada": 1,
        "error_consulta": 1,
    }


def test_una_inventada_alerta_con_sin_respaldo_o_contradiccion() -> None:
    invented = replace(ALTERED, alteration="inventada")

    assert outcome(invented, Verdict.UNSUPPORTED).exact
    assert outcome(invented, Verdict.CONTRADICTION).exact
    assert not outcome(invented, Verdict.DISCREPANCY).exact


def test_toma_solo_la_particion_pedida_con_los_campos_del_extractor() -> None:
    other = replace(REAL, id="R002", partition="calibracion")

    cases = partition_cases([REAL, ALTERED, other], "prueba", lambda texts: [FIELDS] * len(texts))

    assert [case.reference.id for case in cases] == ["R001", "R001-alt-anio"]
    assert [case.kind for case in cases] == [CONTROL, "anio"]
    assert cases[0].fields == FIELDS


def test_verifica_cada_caso_con_los_umbrales_dados() -> None:
    lookup = FakeLookup(LookupResult(Strategy.DIRECT_DOI, (RECORD,)))
    cases = [Case(REAL, FIELDS), Case(ALTERED, replace(FIELDS, year=2017))]

    outcomes = asyncio.run(verify_cases(cases, lookup, FakeNli(), THRESHOLDS))

    assert [item.verdict for item in outcomes] == [Verdict.VERIFIED, Verdict.DISCREPANCY]


# --- Criterio de calibración ----------------------------------------------------------------


def run_with(scores: dict[tuple[str, float], Score], default: Score):  # type: ignore[no-untyped-def]
    """Medición falsa: la puntuación depende del único umbral que difiere del actual."""

    async def run(thresholds: Thresholds) -> Score:
        for (name, value), result in scores.items():
            if getattr(thresholds, name) == value and getattr(THRESHOLDS, name) != value:
                others = replace(thresholds, **{name: getattr(THRESHOLDS, name)})
                if others == THRESHOLDS:
                    return result
        changed = {
            name for name, _ in scores if getattr(thresholds, name) != getattr(THRESHOLDS, name)
        }
        if len(changed) > 1:
            return combined_score
        return default

    combined_score = scored(false_alarms=0, alerts=9, exact=9)
    return run


def test_sin_mejora_se_conservan_los_umbrales_actuales() -> None:
    calibration = asyncio.run(calibrate(run_with({}, scored(alerts=3)), THRESHOLDS))

    assert calibration.chosen == THRESHOLDS
    assert calibration.combined.key() == calibration.baseline.key()
    assert len(calibration.trials) == 6 * len(GRID)


def test_menos_falsas_alarmas_gana_aunque_alerte_menos() -> None:
    better = {("title_match", 0.8): scored(false_alarms=0, alerts=2)}

    calibration = asyncio.run(
        calibrate(run_with(better, scored(false_alarms=1, alerts=5)), THRESHOLDS)
    )

    assert calibration.chosen == replace(THRESHOLDS, title_match=0.8)


def test_ante_un_empate_queda_el_valor_actual() -> None:
    same = {("nli_entailment", 0.7): scored(alerts=3)}

    calibration = asyncio.run(calibrate(run_with(same, scored(alerts=3)), THRESHOLDS))

    assert calibration.chosen == THRESHOLDS


def test_si_juntos_empeoran_queda_el_mejor_cambio_solo() -> None:
    improvements = {
        ("title_match", 0.8): scored(alerts=12),
        ("nli_entailment", 0.7): scored(alerts=11),
    }

    calibration = asyncio.run(calibrate(run_with(improvements, scored(alerts=3)), THRESHOLDS))

    # Juntos dan 9 alertas, menos que las 12 del mejor cambio por sí solo.
    assert calibration.chosen == replace(THRESHOLDS, title_match=0.8)
    assert calibration.combined.alerts == 12


# --- Respuestas guardadas -------------------------------------------------------------------


def test_repite_la_busqueda_guardada_sin_consultar_otra_vez() -> None:
    inner = FakeLookup(LookupResult(Strategy.DIRECT_DOI, (RECORD,)))
    store: dict[str, LookupResult] = {}
    lookup = RecordingLookup(inner, store)

    first = asyncio.run(lookup.lookup(FIELDS))
    second = asyncio.run(
        RecordingLookup(FakeLookup(LookupResult(Strategy.NO_QUERY, ())), store).lookup(FIELDS)
    )

    assert inner.calls == 1
    assert first == second


def test_una_busqueda_con_una_fuente_caida_no_se_guarda() -> None:
    inner = FakeLookup(LookupResult(Strategy.DIRECT_DOI, (), query_failed=True))
    store: dict[str, LookupResult] = {}

    asyncio.run(RecordingLookup(inner, store).lookup(FIELDS))

    assert store == {}


class CountingNli:
    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []

    def infer_many(self, pairs: Sequence[tuple[str, str]]) -> list[NliScores]:
        self.pairs.extend(pairs)
        return [NliScores(0.9, 0.05, 0.05) for _ in pairs]


def test_el_nli_calcula_cada_par_una_sola_vez() -> None:
    inner = CountingNli()
    nli = MemoNli(inner)

    nli.infer_many([("a", "b"), ("a", "b"), ("c", "d")])
    scores = nli.infer_many([("a", "b")])

    assert inner.pairs == [("a", "b"), ("c", "d")]
    assert scores == [NliScores(0.9, 0.05, 0.05)]


def test_una_real_con_error_comprobado_no_es_falsa_alarma() -> None:
    wrong = replace(REAL, id="R002", notes="Error real: el DOI citado no existe.")

    result = score([outcome(wrong, Verdict.UNSUPPORTED), outcome(REAL, Verdict.VERIFIED)])

    assert result.false_alarms == 0
    assert result.alerts == 0  # tampoco cuenta como alteradas detectadas
    assert result.exact == 2
    assert result.by_kind["control_con_error"].alerts == 1


def test_entre_valores_igual_de_buenos_gana_el_mas_cercano_al_actual() -> None:
    async def run(thresholds: Thresholds) -> Score:
        improves = thresholds.title_match in (0.45, 0.5, 0.55)
        return scored(false_alarms=0 if improves else 1)

    calibration = asyncio.run(calibrate(run, THRESHOLDS))

    assert calibration.chosen == replace(THRESHOLDS, title_match=0.55)


# --- Comandos del script --------------------------------------------------------------------


def test_probar_y_calibrar_sin_anystyle_no_miden(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    final = tmp_path / "final.csv"
    write_csv(final, [])

    for command in ("probar", "calibrar"):
        assert main([command, str(final), "--anystyle", "comando-que-no-existe"]) == 1
    assert "la medición usa AnyStyle" in capsys.readouterr().out


def test_la_revision_pone_la_real_junto_a_su_registro() -> None:
    row = _review_row(
        replace(REAL, fields={"doi": DOI}), LookupResult(Strategy.DIRECT_DOI, (RECORD,))
    )

    assert row["doi"] == DOI
    assert row["registro_titulo"] == RECORD.title
    assert row["registro_autores"] == "Pérez; López Vera"
    assert row["registro_anio"] == "2021"


def test_la_revision_avisa_un_doi_que_ninguna_fuente_registra() -> None:
    row = _review_row(REAL, LookupResult(Strategy.DIRECT_DOI, ()))

    assert row["fuente"] == "DOI no registrado"
    assert "registro_titulo" not in row


def test_el_informe_de_la_prueba_separa_alteradas_y_reales(
    capsys: pytest.CaptureFixture[str],
) -> None:
    wrong = replace(REAL, notes="Error real: título traducido.")
    _print_test(
        score(
            [
                outcome(REAL, Verdict.VERIFIED),
                outcome(wrong, Verdict.DISCREPANCY),
                outcome(ALTERED, Verdict.DISCREPANCY),
                outcome(ALTERED, Verdict.VERIFIED),
            ]
        )
    )

    out = capsys.readouterr().out
    assert "Alteradas detectadas: 1 de 2" in out
    assert "Reales sin error marcadas por error: 0 de 1" in out
    assert "Reales con error real detectadas: 1 de 1" in out


def test_no_repite_un_doi_guardado_cuyo_registro_no_es_una_obra() -> None:
    # Guardado antes de que el número de una revista dejara de tomarse como la obra.
    issue = replace(RECORD, title=None, authors=())
    store = {repr(FIELDS): LookupResult(Strategy.DIRECT_DOI, (issue,))}
    current = LookupResult(Strategy.BIBLIOGRAPHIC_SEARCH, (RECORD,))

    result = asyncio.run(RecordingLookup(FakeLookup(current), store).lookup(FIELDS))

    assert result == current
    assert store[repr(FIELDS)] == current
