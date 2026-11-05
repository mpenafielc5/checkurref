"""Exporta el modelo NLI a ONNX int8 (T12). Solo se usa en desarrollo.

La API no necesita PyTorch: ejecuta el archivo ONNX con onnxruntime. Este
script sí lo necesita, por eso usa su propio entorno (requirements-export.txt):

    py -3.10 -m venv .venv-export
    .\\.venv-export\\Scripts\\python -m pip install -r requirements-export.txt
    .\\.venv-export\\Scripts\\python -m scripts.export_nli

Deja en models/nli (o en la carpeta indicada con --salida) model.onnx,
tokenizer.json y config.json, y compara el modelo cuantizado con el original
para saber cuánto cambian las probabilidades.
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

MODEL_ID = "Recognai/bert-base-spanish-wwm-cased-xnli"
MAX_SIZE_MB = 150  # RNF18

# Pares de prueba: (premisa, hipótesis, relación esperada).
SAMPLES = [
    (
        "Redes neuronales en la educación superior. Revista Andina, 2021. Autores: Pérez, López.",
        "El artículo se publicó en 2021.",
        "entailment",
    ),
    (
        "Redes neuronales en la educación superior. Revista Andina, 2021. Autores: Pérez, López.",
        "El artículo trata sobre agricultura de precisión en la Amazonía.",
        "contradiction",
    ),
    (
        "Aprendizaje automático aplicado. Editorial UNEMI, 2020. Autor: Rivas.",
        "El libro tiene más de trescientas páginas.",
        "neutral",
    ),
]


def export(output: Path) -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        print(f"Exportando {MODEL_ID} a ONNX...")
        model = ORTModelForSequenceClassification.from_pretrained(MODEL_ID, export=True)
        model.save_pretrained(tmp)
        print("Cuantizando a int8...")
        quantize_dynamic(
            Path(tmp) / "model.onnx", output / "model.onnx", weight_type=QuantType.QInt8
        )
        shutil.copy(Path(tmp) / "config.json", output / "config.json")
    AutoTokenizer.from_pretrained(MODEL_ID).backend_tokenizer.save(str(output / "tokenizer.json"))

    size_mb = (output / "model.onnx").stat().st_size / 1_000_000
    print(f"model.onnx: {size_mb:.1f} MB (máximo {MAX_SIZE_MB} MB)")
    labels = json.loads((output / "config.json").read_text(encoding="utf-8"))["id2label"]
    print(f"Etiquetas del modelo: {labels}")


def compare(output: Path) -> None:
    """Probabilidades del modelo cuantizado frente al original en PyTorch."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from app.verification.nli import NliModel

    quantized = NliModel.load(output)
    original = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).eval()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    labels = [original.config.id2label[i].lower() for i in range(original.config.num_labels)]

    largest = 0.0
    for premise, hypothesis, expected in SAMPLES:
        with torch.no_grad():
            logits = original(**tokenizer(premise, hypothesis, return_tensors="pt")).logits
        reference = dict(zip(labels, torch.softmax(logits, dim=-1)[0].tolist(), strict=True))
        scores = quantized.infer(premise, hypothesis)
        mine = {
            "entailment": scores.entailment,
            "neutral": scores.neutral,
            "contradiction": scores.contradiction,
        }
        largest = max(largest, *(abs(mine[k] - reference[k]) for k in mine))
        winner = max(mine, key=lambda key: mine[key])
        print(f"\n{hypothesis}\n  esperada: {expected} | int8: {winner}")
        print("  int8:     " + "  ".join(f"{k} {v:.3f}" for k, v in mine.items()))
        print("  original: " + "  ".join(f"{k} {reference[k]:.3f}" for k in mine))
    print(f"\nMayor diferencia entre int8 y original: {largest:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--salida", type=Path, default=Path("models/nli"))
    parser.add_argument(
        "--solo-comparar", action="store_true", help="no exporta; compara el modelo ya generado"
    )
    args = parser.parse_args()
    if not args.solo_comparar:
        export(args.salida)
    compare(args.salida)


if __name__ == "__main__":
    main()
