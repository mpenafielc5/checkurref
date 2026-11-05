"""Modelo de inferencia de lenguaje natural en español (T12, patrón Singleton).

El modelo Recognai/bert-base-spanish-wwm-cased-xnli, exportado a ONNX int8 por
scripts/export_nli.py, decide si una premisa (el registro de Crossref u
OpenAlex) implica, es neutral o contradice una hipótesis (un campo de la
referencia). Pesa unos 110 MB y tarda en cargarse: se carga una sola vez y lo
reutilizan todos los análisis.

La carpeta del modelo contiene model.onnx, tokenizer.json y config.json; el
orden de las etiquetas se lee de config.json, nunca se supone.
"""

import json
import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from tokenizers import Tokenizer

logger = logging.getLogger(__name__)

MODEL_FILE = "model.onnx"
TOKENIZER_FILE = "tokenizer.json"
CONFIG_FILE = "config.json"

# Premisa e hipótesis juntas. Un registro bibliográfico y un campo caben de sobra.
MAX_TOKENS = 256
BATCH_SIZE = 16

ENTAILMENT = "entailment"
NEUTRAL = "neutral"
CONTRADICTION = "contradiction"


class NliModelError(Exception):
    """La carpeta del modelo no existe o está incompleta."""


@dataclass(frozen=True)
class NliScores:
    """Probabilidades de cada relación; suman 1."""

    entailment: float
    neutral: float
    contradiction: float


class OnnxInput(Protocol):
    name: str


class OnnxSession(Protocol):
    """Lo que se usa de onnxruntime.InferenceSession; las pruebas usan un doble."""

    def get_inputs(self) -> Sequence[OnnxInput]: ...

    def run(self, output_names: list[str] | None, input_feed: dict[str, Any]) -> list[Any]: ...


class NliModel:
    def __init__(self, session: OnnxSession, tokenizer: Tokenizer, labels: Sequence[str]) -> None:
        names = [label.lower() for label in labels]
        if sorted(names) != sorted([ENTAILMENT, NEUTRAL, CONTRADICTION]):
            raise NliModelError(f"Etiquetas del modelo desconocidas: {labels}")
        self._session = session
        self._input_names = {item.name for item in session.get_inputs()}
        self._index = {name: position for position, name in enumerate(names)}
        self._tokenizer = tokenizer
        self._tokenizer.enable_truncation(MAX_TOKENS)
        pad_id = tokenizer.token_to_id("[PAD]") or 0
        self._tokenizer.enable_padding(pad_id=pad_id, pad_token="[PAD]")

    @classmethod
    def load(cls, model_dir: Path) -> "NliModel":
        """Abre el modelo exportado. Solo lo llama get_nli_model."""
        import onnxruntime  # se importa aquí: tarda y las pruebas no lo necesitan

        files = [model_dir / name for name in (MODEL_FILE, TOKENIZER_FILE, CONFIG_FILE)]
        missing = [path.name for path in files if not path.is_file()]
        if missing:
            raise NliModelError(
                f"Faltan {', '.join(missing)} en {model_dir}. "
                "Ejecuta python -m scripts.export_nli para generar el modelo."
            )
        config = json.loads((model_dir / CONFIG_FILE).read_text(encoding="utf-8"))
        id2label: dict[str, str] = config["id2label"]
        labels = [id2label[str(index)] for index in range(len(id2label))]
        session = onnxruntime.InferenceSession(
            str(model_dir / MODEL_FILE), providers=["CPUExecutionProvider"]
        )
        tokenizer = Tokenizer.from_file(str(model_dir / TOKENIZER_FILE))
        return cls(session, tokenizer, labels)

    def infer(self, premise: str, hypothesis: str) -> NliScores:
        return self.infer_many([(premise, hypothesis)])[0]

    def infer_many(self, pairs: Sequence[tuple[str, str]]) -> list[NliScores]:
        """Una inferencia por par (premisa, hipótesis), en lotes para ir más rápido."""
        scores: list[NliScores] = []
        for start in range(0, len(pairs), BATCH_SIZE):
            scores.extend(self._infer_batch(pairs[start : start + BATCH_SIZE]))
        return scores

    def _infer_batch(self, pairs: Sequence[tuple[str, str]]) -> list[NliScores]:
        encodings = self._tokenizer.encode_batch(list(pairs))
        feeds = {
            "input_ids": np.array([item.ids for item in encodings], dtype=np.int64),
            "attention_mask": np.array([item.attention_mask for item in encodings], dtype=np.int64),
            "token_type_ids": np.array([item.type_ids for item in encodings], dtype=np.int64),
        }
        logits = np.asarray(
            self._session.run(None, {k: v for k, v in feeds.items() if k in self._input_names})[0],
            dtype=np.float64,
        )
        exp = np.exp(logits - logits.max(axis=1, keepdims=True))
        probabilities = exp / exp.sum(axis=1, keepdims=True)
        return [
            NliScores(
                entailment=float(row[self._index[ENTAILMENT]]),
                neutral=float(row[self._index[NEUTRAL]]),
                contradiction=float(row[self._index[CONTRADICTION]]),
            )
            for row in probabilities
        ]


_lock = threading.Lock()
_instance: NliModel | None = None


def get_nli_model(model_dir: Path) -> NliModel:
    """La única instancia del modelo: la primera llamada lo carga y las demás lo reutilizan."""
    global _instance
    with _lock:
        if _instance is None:
            logger.info("Cargando el modelo NLI desde %s", model_dir)
            _instance = NliModel.load(model_dir)
        return _instance
