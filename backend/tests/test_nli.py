"""Modelo NLI en ONNX int8 (T12). Sin el modelo real, salvo la última prueba."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing

from app.verification import nli
from app.verification.nli import NliModel, NliModelError, NliScores, get_nli_model

# Orden real del modelo de Recognai: contradicción, neutral, implicación.
LABELS = ["contradiction", "neutral", "entailment"]
REAL_MODEL = Path(__file__).resolve().parents[1] / "models" / "nli"


@dataclass(frozen=True)
class FakeInput:
    name: str


class FakeSession:
    """Devuelve siempre los mismos logits y guarda lo que recibió."""

    def __init__(
        self,
        logits: Sequence[float],
        inputs: Sequence[str] = ("input_ids", "attention_mask", "token_type_ids"),
    ) -> None:
        self.logits = list(logits)
        self.inputs = [FakeInput(name) for name in inputs]
        self.calls: list[dict[str, Any]] = []

    def get_inputs(self) -> Sequence[FakeInput]:
        return self.inputs

    def run(self, output_names: list[str] | None, input_feed: dict[str, Any]) -> list[Any]:
        self.calls.append(input_feed)
        rows = len(input_feed["input_ids"])
        return [np.array([self.logits] * rows, dtype=np.float32)]


def tiny_tokenizer() -> Tokenizer:
    words = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "el", "año", "es", "2021"]
    tokenizer = Tokenizer(WordLevel({w: i for i, w in enumerate(words)}, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]",
        pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", 2), ("[SEP]", 3)],
    )
    return tokenizer


def make_model(session: FakeSession, labels: Sequence[str] = LABELS) -> NliModel:
    return NliModel(session, tiny_tokenizer(), labels)


def test_las_probabilidades_siguen_el_orden_de_etiquetas_del_modelo() -> None:
    model = make_model(FakeSession([4.0, 0.0, 0.0]))

    scores = model.infer("el año es 2021", "el año es 2021")

    assert scores.contradiction > 0.9
    assert scores.entailment == pytest.approx(scores.neutral)
    assert scores.entailment + scores.neutral + scores.contradiction == pytest.approx(1.0)


def test_pasa_premisa_e_hipotesis_como_par() -> None:
    session = FakeSession([0.0, 0.0, 1.0])

    make_model(session).infer("el año", "es 2021")

    feed = session.calls[0]
    assert feed["input_ids"].tolist() == [[2, 4, 5, 3, 6, 7, 3]]
    assert feed["token_type_ids"].tolist() == [[0, 0, 0, 0, 1, 1, 1]]


def test_rellena_los_pares_cortos_del_mismo_lote() -> None:
    session = FakeSession([0.0, 0.0, 1.0])

    make_model(session).infer_many([("el año es 2021", "el año"), ("el", "año")])

    assert session.calls[0]["attention_mask"].tolist() == [
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 0, 0, 0, 0],
    ]


def test_solo_envia_las_entradas_que_declara_el_modelo() -> None:
    session = FakeSession([0.0, 0.0, 1.0], inputs=("input_ids", "attention_mask"))

    make_model(session).infer("el año", "es 2021")

    assert set(session.calls[0]) == {"input_ids", "attention_mask"}


def test_procesa_por_lotes() -> None:
    session = FakeSession([0.0, 0.0, 1.0])

    scores = make_model(session).infer_many([("el año", "es 2021")] * (nli.BATCH_SIZE + 4))

    assert len(scores) == nli.BATCH_SIZE + 4
    assert [len(call["input_ids"]) for call in session.calls] == [nli.BATCH_SIZE, 4]


def test_sin_pares_no_consulta_el_modelo() -> None:
    session = FakeSession([0.0, 0.0, 1.0])

    assert make_model(session).infer_many([]) == []
    assert session.calls == []


def test_rechaza_etiquetas_desconocidas() -> None:
    with pytest.raises(NliModelError):
        make_model(FakeSession([0.0, 1.0]), labels=["positivo", "negativo"])


def test_carpeta_incompleta_explica_como_generar_el_modelo(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"id2label": {}}), encoding="utf-8")

    with pytest.raises(NliModelError, match=r"model\.onnx, tokenizer\.json.*export_nli"):
        NliModel.load(tmp_path)


def test_el_modelo_se_carga_una_sola_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    loads: list[Path] = []

    def fake_load(model_dir: Path) -> NliModel:
        loads.append(model_dir)
        return make_model(FakeSession([0.0, 0.0, 1.0]))

    monkeypatch.setattr(nli, "_instance", None)
    monkeypatch.setattr(NliModel, "load", staticmethod(fake_load))

    first = get_nli_model(Path("models/nli"))
    second = get_nli_model(Path("models/nli"))

    assert first is second
    assert loads == [Path("models/nli")]


@pytest.mark.skipif(
    not (REAL_MODEL / "model.onnx").is_file(),
    reason="modelo no generado (python -m scripts.export_nli)",
)
def test_modelo_real_distingue_las_tres_relaciones() -> None:
    model = NliModel.load(REAL_MODEL)
    premise = "Redes neuronales en la educación superior. Revista Andina, 2021."

    entails, contradicts = model.infer_many(
        [
            (premise, "El artículo se publicó en 2021."),
            (premise, "El artículo trata sobre agricultura de precisión en la Amazonía."),
        ]
    )

    assert isinstance(entails, NliScores)
    assert entails.entailment > 0.8
    assert contradicts.contradiction > 0.8
