"""Detección de la norma de cada referencia y de la lista completa (T06)."""

import pytest

from app.pipeline.norm_detection import Norm, detect_document_norm, detect_reference_norm

APA = [
    "Pérez, M. y López, J. (2021). Redes neuronales en la educación superior. "
    "Revista Andina, 8(1), 10-25. https://doi.org/10.1234/ra.2021.8",
    "Rivas, A. (2020). Aprendizaje automático aplicado. Editorial UNEMI.",
    "Delgado Quirós, M. A., & Torres, L. (s.f.). Evaluación de fuentes académicas.",
    "Organización Mundial de la Salud. (2020, 3 de mayo). Informe sobre salud digital.",
    "Portal Educativo. (s.f). Guía de citas. https://portal.example.org/guia",
    "García, P. (2019). Lectura crítica. En J. Rivas (Ed.), Escritura académica "
    "(pp. 45-60). Editorial Universitaria.",
]
IEEE = [
    '[1] J. Pérez y M. López, "Redes neuronales en la educación superior," '
    "Rev. Andina, vol. 8, no. 1, pp. 10-25, 2021.",
    '[12] A. Rivas, "Aprendizaje automático aplicado," en Proc. Congreso de '
    "Ingeniería, Lima, Perú, 2020, pp. 1-6, doi: 10.1109/CI.2020.1.",
    "M. A. Delgado, Evaluación de fuentes académicas, 2.ª ed. Quito, Ecuador: Abya-Yala, 2018.",
]
UNKNOWN = [
    "Ministerio de Educación. Ley Orgánica de Educación Intercultural.",
    "Texto que no es una referencia.",
]


@pytest.mark.parametrize("text", APA)
def test_reconoce_referencias_apa(text: str) -> None:
    assert detect_reference_norm(text) == Norm.APA


@pytest.mark.parametrize("text", IEEE)
def test_reconoce_referencias_ieee(text: str) -> None:
    assert detect_reference_norm(text) == Norm.IEEE


@pytest.mark.parametrize("text", UNKNOWN)
def test_sin_rasgos_suficientes_la_norma_es_desconocida(text: str) -> None:
    assert detect_reference_norm(text) == Norm.UNKNOWN


@pytest.mark.parametrize(
    ("norms", "expected"),
    [
        pytest.param([Norm.APA] * 5, Norm.APA, id="toda APA"),
        pytest.param([Norm.IEEE] * 3 + [Norm.UNKNOWN], Norm.IEEE, id="IEEE con una desconocida"),
        pytest.param([Norm.APA] * 3 + [Norm.IEEE] * 2, Norm.MIXED, id="mezcla"),
        pytest.param([Norm.APA, Norm.APA, Norm.IEEE], Norm.MIXED, id="mezcla en lista corta"),
        pytest.param([Norm.APA] * 19 + [Norm.IEEE], Norm.APA, id="una confusa en lista larga"),
        pytest.param([Norm.UNKNOWN] * 2, Norm.UNKNOWN, id="ninguna reconocida"),
        pytest.param([], Norm.UNKNOWN, id="vacía"),
    ],
)
def test_norma_de_la_lista(norms: list[Norm], expected: Norm) -> None:
    assert detect_document_norm(norms) == expected
