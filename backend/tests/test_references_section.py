"""Extracción del texto del PDF y ubicación de la sección de referencias."""

import pymupdf
import pytest

from app.pipeline.errors import (
    EncryptedPdfError,
    ReferencesNotFoundError,
    ScannedPdfError,
    UnreadablePdfError,
)
from app.pipeline.pdf_text import TextLine, extract_pages
from app.pipeline.references_section import extract_reference_section, find_reference_section
from tests.pdf_factory import PageSpec, make_encrypted_pdf, make_pdf, make_scanned_pdf

REF_1 = "Pérez, M. y López, J. (2021). Redes neuronales en la educación superior."
REF_2 = "Rivas, A. (2020). Aprendizaje automático aplicado. Editorial UNEMI."
REF_3 = "Moreira, L. (2022). Evaluación de fuentes académicas. Revista Andina, 8(1), 10-25."


def line(text: str, page: int = 1) -> TextLine:
    return TextLine(page=page, x0=72.0, text=text)


def texts(result: list[TextLine]) -> list[str]:
    return [item.text for item in result]


@pytest.mark.parametrize(
    "heading",
    [
        "Referencias",
        "REFERENCIAS",
        "7. Referencias",
        "VII. REFERENCIAS BIBLIOGRÁFICAS",
        "Capítulo 6 Referencias",
        "Bibliografía:",
        "Bibliografías",
        "BIBLIOGRAFÍAS",
        "Lista de referencias",
        "References",
    ],
)
def test_reconoce_los_titulos_habituales(heading: str) -> None:
    section = find_reference_section(
        [line("Conclusiones del trabajo."), line(heading), line(REF_1)]
    )

    assert section.heading == heading
    assert texts(section.lines) == [REF_1]


def test_ignora_la_entrada_del_indice_general() -> None:
    document = [
        line("Índice", page=2),
        line("Referencias", page=2),
        line("Introducción al problema.", page=3),
        line("Referencias", page=9),
        line(REF_1, page=9),
    ]

    section = find_reference_section(document)

    assert section.page == 9
    assert texts(section.lines) == [REF_1]


def test_el_capitulo_que_empieza_en_pagina_nueva_cuenta_como_titulo() -> None:
    document = [
        line("Referencias", page=2),  # entrada del índice
        line("Conclusiones del trabajo.", page=8),
        line("Referencias", page=9),  # primera línea de la página 9
        line(REF_1, page=9),
    ]

    assert find_reference_section(document).page == 9


def test_descarta_el_titulo_repetido_en_la_pagina_siguiente() -> None:
    document = [
        line("Referencias", page=9),
        line(REF_1, page=9),
        line("Referencias", page=10),  # encabezado de página de la sección
        line(REF_2, page=10),
    ]

    section = find_reference_section(document)

    assert section.page == 9
    assert texts(section.lines) == [REF_1, REF_2]


def test_la_seccion_termina_en_los_anexos() -> None:
    document = [line("Referencias"), line(REF_1), line("Anexo A"), line("Encuesta aplicada.")]

    assert texts(find_reference_section(document).lines) == [REF_1]


@pytest.mark.parametrize(
    "document",
    [
        pytest.param([line("Introducción."), line("Conclusiones.")], id="sin título"),
        pytest.param([line("Introducción."), line("Referencias")], id="título sin contenido"),
    ],
)
def test_sin_seccion_de_referencias_da_un_error_claro(document: list[TextLine]) -> None:
    with pytest.raises(ReferencesNotFoundError):
        find_reference_section(document)


def test_documento_completo_de_varias_paginas() -> None:
    pdf = make_pdf(
        [
            PageSpec(["Índice general", "Introducción ........ 2", "Referencias ........ 3"]),
            PageSpec(["Introducción", "El problema de las referencias inventadas es real."]),
            PageSpec(
                [
                    "Conclusiones",
                    "Las referencias deben verificarse antes de entregar.",
                    "Referencias",
                    REF_1,
                    "Rivas, A. (2020). Aprendizaje automático en la investi-",
                ]
            ),
            PageSpec(["gación aplicada. Editorial UNEMI.", REF_3, "Anexos", "Encuesta aplicada."]),
        ],
        header="Universidad Estatal de Milagro",
        page_numbers=True,
    )

    section = extract_reference_section(pdf)

    assert section.page == 3
    assert texts(section.lines) == [
        REF_1,
        "Rivas, A. (2020). Aprendizaje automático en la investigación aplicada. Editorial UNEMI.",
        REF_3,
    ]


def test_referencia_partida_entre_dos_paginas_con_encabezado() -> None:
    pdf = make_pdf(
        [
            PageSpec(
                [
                    "Introducción del trabajo con texto suficiente.",
                    "Referencias",
                    "Pérez, M. (2021). Redes neuronales en la investi-",
                ]
            ),
            PageSpec(["gación educativa. Revista Andina, 8(1), 10-25.", REF_2]),
        ],
        header="Universidad Estatal de Milagro",
        page_numbers=True,
    )

    assert texts(extract_reference_section(pdf).lines) == [
        "Pérez, M. (2021). Redes neuronales en la investigación educativa. "
        "Revista Andina, 8(1), 10-25.",
        REF_2,
    ]


def test_une_el_renglon_justificado_que_pymupdf_entrega_partido() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 90), "Texto del trabajo con suficientes caracteres para leerlo.")
    page.insert_text((72, 106), "Referencias")
    page.insert_text((72, 122), "Akerele, J. (2024). Increasing software deployment speed.")
    # Un renglón justificado con espacios anchos, como lo escriben algunos editores.
    page.insert_text((72, 138), "International")
    page.insert_text((240, 138), "Engineering")

    lines = extract_pages(document.tobytes())[0]

    assert lines[-1] == TextLine(page=1, x0=72.0, text="International Engineering")


def test_conserva_la_sangria_de_cada_linea() -> None:
    pdf = make_pdf(
        [
            PageSpec(
                [
                    "Texto del trabajo con suficientes caracteres.",
                    "Referencias",
                    REF_1,
                    (36.0, "Revista Ciencia, 14(2), 45-60."),
                ]
            )
        ]
    )

    section = extract_reference_section(pdf)

    assert [item.x0 for item in section.lines] == [72.0, 108.0]


@pytest.mark.parametrize(
    ("pdf", "error"),
    [
        pytest.param(make_scanned_pdf(), ScannedPdfError, id="escaneado"),
        pytest.param(make_encrypted_pdf(), EncryptedPdfError, id="protegido"),
        pytest.param(b"esto no es un PDF", UnreadablePdfError, id="dañado"),
        pytest.param(b"", UnreadablePdfError, id="vacío"),
    ],
)
def test_pdf_ilegible_da_un_error_claro(pdf: bytes, error: type[Exception]) -> None:
    with pytest.raises(error) as raised:
        extract_pages(pdf)

    assert str(raised.value)  # siempre lleva un mensaje para el usuario
