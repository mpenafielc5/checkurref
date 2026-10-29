"""Limpieza previa a la separación de referencias."""

import pytest

from app.pipeline.pdf_text import TextLine
from app.pipeline.text_cleanup import join_broken_lines, remove_page_furniture


def lines(*texts: str, page: int = 1) -> list[TextLine]:
    return [TextLine(page=page, x0=72.0, text=text) for text in texts]


def texts(result: list[TextLine]) -> list[str]:
    return [line.text for line in result]


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        pytest.param(
            "Pérez, M. (2021). Redes neuronales en la investi-",
            "gación educativa. Revista Ciencia, 14(2).",
            "Pérez, M. (2021). Redes neuronales en la investigación educativa. "
            "Revista Ciencia, 14(2).",
            id="palabra partida con guion",
        ),
        pytest.param(
            "https://doi.org/10.1016/j.compedu-",
            "2021.104215",
            "https://doi.org/10.1016/j.compedu-2021.104215",
            id="guion propio del DOI",
        ),
        pytest.param(
            "Recuperado de https://repositorio.unemi.edu.ec/",
            "handle/123/tesis.pdf",
            "Recuperado de https://repositorio.unemi.edu.ec/handle/123/tesis.pdf",
            id="URL partida",
        ),
        pytest.param(
            "Revista Ciencia y Tecnología, 14(2), 45-",
            "60.",
            "Revista Ciencia y Tecnología, 14(2), 45-60.",
            id="rango de páginas partido",
        ),
        pytest.param(
            "Redes neuronales en la educación superior",
            "y su impacto en el aprendizaje.",
            "Redes neuronales en la educación superior y su impacto en el aprendizaje.",
            id="frase que sigue en minúscula",
        ),
    ],
)
def test_une_las_lineas_cortadas(previous: str, current: str, expected: str) -> None:
    assert texts(join_broken_lines(lines(previous, current))) == [expected]


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        pytest.param(
            "Pérez, M. (2021). Redes neuronales. Revista, 14(2), 45-60.",
            "López, J. (2020). Aprendizaje automático. Editorial UNEMI.",
            id="nueva referencia APA",
        ),
        pytest.param(
            "[1] A. Pérez, Redes neuronales, Rev. Cienc., vol. 14, 2021.",
            "[2] J. López, Aprendizaje automático, UNEMI, 2020.",
            id="nueva referencia IEEE",
        ),
        pytest.param(
            "Pérez, M. (2021). Redes neuronales en la educación superior.",
            "y otra cosa que empieza en minúscula tras un punto",
            id="la línea anterior termina en punto",
        ),
        pytest.param(
            "Data, 9(5), 71. https://doi.org/10.3390/data9050071",
            "Delgado-Quirós, L., & Ortega, J. L. (2024). Completeness degree of metadata.",
            id="DOI seguido de un apellido con guion",
        ),
    ],
)
def test_no_une_lineas_independientes(previous: str, current: str) -> None:
    assert texts(join_broken_lines(lines(previous, current))) == [previous, current]


def test_la_union_conserva_la_pagina_y_la_sangria_de_la_primera_linea() -> None:
    first = TextLine(page=3, x0=72.0, text="Redes neuronales en la investi-")
    second = TextLine(page=4, x0=108.0, text="gación educativa.")

    assert join_broken_lines([first, second]) == [
        TextLine(page=3, x0=72.0, text="Redes neuronales en la investigación educativa.")
    ]


CONTENT = [
    "El problema de las referencias inventadas.",
    "Metodología del estudio.",
    "Resultados obtenidos con el estándar de oro.",
    "Conclusiones del trabajo.",
]


def test_quita_encabezados_repetidos_y_numeros_de_pagina() -> None:
    pages = [
        [
            TextLine(page=number, x0=72.0, text="Universidad Estatal de Milagro"),
            TextLine(page=number, x0=72.0, text=f"Capítulo {number}"),
            TextLine(page=number, x0=72.0, text=content),
            TextLine(page=number, x0=300.0, text=f"Página {number} de 4"),
        ]
        for number, content in enumerate(CONTENT, start=1)
    ]

    cleaned = remove_page_furniture(pages)

    assert [texts(page) for page in cleaned] == [[content] for content in CONTENT]


def test_una_linea_larga_nunca_se_toma_como_encabezado() -> None:
    long_line = "Texto del cuerpo que se repite casi igual en cada página del documento número {n}."
    pages = [lines(long_line.format(n=number), "Fin.", page=number) for number in range(1, 5)]

    cleaned = remove_page_furniture(pages)

    assert [texts(page)[0] for page in cleaned] == [
        long_line.format(n=number) for number in range(1, 5)
    ]


def test_con_dos_paginas_tambien_quita_el_encabezado_repetido() -> None:
    pages = [
        lines("Universidad Estatal de Milagro", "Texto uno.", "1", page=1),
        lines("Universidad Estatal de Milagro", "Texto dos.", "2", page=2),
    ]

    cleaned = remove_page_furniture(pages)

    assert [texts(page) for page in cleaned] == [["Texto uno."], ["Texto dos."]]


def test_con_una_sola_pagina_solo_quita_el_numero_de_pagina() -> None:
    page = lines("Universidad Estatal de Milagro", "Texto uno.", "1")

    assert texts(remove_page_furniture([page])[0]) == [
        "Universidad Estatal de Milagro",
        "Texto uno.",
    ]


def test_un_numero_en_medio_de_la_pagina_no_se_quita() -> None:
    page = lines("Primera línea.", "Segunda línea.", "45", "Cuarta línea.", "Quinta línea.")

    assert texts(remove_page_furniture([page])[0]) == texts(page)
