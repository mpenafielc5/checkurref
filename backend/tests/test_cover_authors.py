"""Autores desde la portada del PDF (T23). Portadas generadas: no se suben PDF de terceros."""

import pytest

from app.pipeline.cover_authors import authors_in, cover_authors
from tests.pdf_factory import (
    PageSpec,
    make_encrypted_pdf,
    make_pdf,
    make_scanned_pdf,
    make_truncated_pdf,
)

COVER = [
    "FACULTAD DE CIENCIAS E INGENIERÍA",
    "CARRERA DE INGENIERÍA DE SOFTWARE",
    "TEMA:",
    "Redes neuronales aplicadas a la educación",
    "AUTORES:",
    "Ana Lucía Vera Torres",
    "Carlos Andrés Mendoza Ríos",
    "ASIGNATURA:",
    "Metodología de la investigación",
    "DOCENTE:",
    "Ing. Pablo Salas",
    "FECHA DE ENTREGA:",
    "20 de septiembre de 2026",
]


def test_portada_con_varios_autores_en_lineas_distintas() -> None:
    assert authors_in(COVER) == ("Ana Lucía Vera Torres", "Carlos Andrés Mendoza Ríos")


def test_portada_sin_llenar_no_da_autores() -> None:
    # Caso real: la plantilla de la portada quedó sin los nombres de los estudiantes.
    lines = [
        "Estudiante(s):",
        "Apellidos y nombres completos",
        "Apellidos y nombres completos",
        "Tutor:",
        "Apellidos y nombres completos",
    ]

    assert authors_in(lines) == ()


@pytest.mark.parametrize(
    "placeholder", ["Nombres y apellidos del estudiante", "Nombre del estudiante", ""]
)
def test_otras_plantillas_sin_llenar_o_en_blanco_no_dan_autores(placeholder: str) -> None:
    assert authors_in(["Estudiante:", placeholder, "Docente:", "Ing. Pablo Salas"]) == ()


@pytest.mark.parametrize("name", ["Ana Vera", "Vera Torres Ana Lucía", "VERA TORRES ANA LUCIA"])
def test_el_nombre_sale_en_el_orden_en_que_se_escribio(name: str) -> None:
    assert authors_in(["Estudiante:", name, "Docente:", "Ing. Pablo Salas"]) == (name,)


@pytest.mark.parametrize(
    "label",
    [
        "Autor",
        "AUTOR:",
        "Autores:",
        "autor(es):",
        "Autor(a):",
        "Estudiante",
        "ESTUDIANTES:",
        "Estudiante(s):",
        "Integrante:",
        "Integrantes",
        "Alumno:",
        "ALUMNOS",
        "Elaborado por:",
        "ELABORADO POR",
        "Realizado por:",
        "Presentado por:",
    ],
)
def test_cada_etiqueta_se_reconoce_en_cualquier_forma(label: str) -> None:
    assert authors_in([label, "Ana Vera", "Tutor:", "Pablo Salas"]) == ("Ana Vera",)


def test_la_etiqueta_con_tilde_no_cambia_el_resultado() -> None:
    assert authors_in(["AUTÓRES:", "Ana Vera"]) == ("Ana Vera",)
    assert authors_in(["Autores:", "Ana Vera", "TÍTULO:", "Una obra"]) == ("Ana Vera",)


def test_el_dato_puede_venir_en_la_misma_linea() -> None:
    assert authors_in(["Autor: José Ñauta", "Tema: Redes"]) == ("José Ñauta",)
    assert authors_in(["Elaborado por José Ñauta", "Curso: 7A"]) == ("José Ñauta",)


def test_quita_los_caracteres_invisibles_de_la_portada() -> None:
    assert authors_in(["AUTORES:​", "​Ana Vera", "ASIGNATURA:​", "Redes"]) == ("Ana Vera",)


@pytest.mark.parametrize(
    "stop",
    [
        "Tema:",
        "Título:",
        "Asignatura",
        "Docente:",
        "Tutor:",
        "Curso:",
        "Paralelo",
        "Fecha de entrega:",
        "Periodo:",
        "Carrera de Ingeniería",
        "Facultad:",
    ],
)
def test_el_dato_termina_en_la_siguiente_etiqueta(stop: str) -> None:
    assert authors_in(["Autores:", "Ana Vera", stop, "Otro Dato"]) == ("Ana Vera",)


def test_un_apellido_igual_a_una_etiqueta_no_corta_la_lista() -> None:
    assert authors_in(["Autores:", "Carrera Vera Juan", "Tema Rivas Ana", "Tutor:"]) == (
        "Carrera Vera Juan",
        "Tema Rivas Ana",
    )


def test_la_lista_termina_en_lo_que_no_es_un_nombre() -> None:
    lines = ["Autores:", "Ana Vera", "21/01/2026", "Luis Rojas"]
    assert authors_in(lines) == ("Ana Vera",)
    assert authors_in(["Autor:", "Ana Vera", "Grupo: 3"]) == ("Ana Vera",)
    long_text = "Este es un párrafo largo que claramente no es el nombre de una persona"
    assert authors_in(["Autores:", "Ana Vera", long_text]) == ("Ana Vera",)


@pytest.mark.parametrize(
    "place", ["Quito - Ecuador", "GUAYAQUIL – ECUADOR", "MILAGRO-ECUADOR", "Universidad Estatal"]
)
def test_el_lugar_al_pie_de_la_portada_no_es_un_autor(place: str) -> None:
    assert authors_in(["Autores:", "Ana Vera", place]) == ("Ana Vera",)


@pytest.mark.parametrize(
    "written",
    ["Ing. Ana Vera", "Sr. Ana Vera", "Lic. Ana Vera", "[Ana Vera]", "[Ana Vera", "Ana Vera."],
)
def test_quita_los_titulos_y_los_signos_alrededor_del_nombre(written: str) -> None:
    assert authors_in(["Autor:", written]) == ("Ana Vera",)


def test_un_apellido_con_guion_es_un_nombre() -> None:
    assert authors_in(["Autor:", "Ana Vera-Rojas"]) == ("Ana Vera-Rojas",)


def test_quita_las_marcas_de_lista_y_no_repite() -> None:
    assert authors_in(["Integrantes:", "1. Ana Vera", "- Luis Rojas", "Ana Vera"]) == (
        "Ana Vera",
        "Luis Rojas",
    )


def test_una_etiqueta_por_persona() -> None:
    assert authors_in(["Estudiante: Ana Vera", "Estudiante: Luis Rojas", "Tutor: Pablo"]) == (
        "Ana Vera",
        "Luis Rojas",
    )


@pytest.mark.parametrize(
    "lines",
    [
        [],
        ["Resumen", "Este trabajo analiza las redes neuronales."],
        ["Docente:", "Pablo Salas"],
        # Una palabra suelta sin dos puntos es otra cosa, no una etiqueta.
        ["Estudiante de la carrera de Software", "Ana Vera"],
        ["Autores que escriben sobre el tema", "Ana Vera"],
        ["Autores:"],
    ],
)
def test_sin_autores_reconocibles_queda_vacio(lines: list[str]) -> None:
    assert authors_in(lines) == ()


def test_une_la_etiqueta_partida_en_dos_lineas() -> None:
    # Caso real: la celda angosta de la plantilla parte "Estudiante(s):" en dos líneas.
    lines = ["Carrera: Software", "Estudiant", "e(s):", "Ana Vera", "Luis Rojas", "Tutor: Pablo"]

    assert authors_in(lines) == ("Ana Vera", "Luis Rojas")


def test_una_palabra_partida_que_no_forma_etiqueta_no_se_une() -> None:
    assert authors_in(["Estudiant", "es de la carrera", "Ana Vera"]) == ()


def test_una_palabra_sola_continua_el_nombre_anterior() -> None:
    # Caso real: el nombre no cupo en la celda y la última palabra pasó a otra línea.
    lines = ["Estudiante(s): Ana Lucía Vera", "Luis Andrés Rojas", "Torres", "Tutor: Pablo"]

    assert authors_in(lines) == ("Ana Lucía Vera", "Luis Andrés Rojas Torres")


def test_si_la_primera_pagina_es_solo_imagen_lee_la_siguiente() -> None:
    pdf = make_pdf(
        [PageSpec(lines=[]), PageSpec(lines=["Estudiante(s):", "Ana Vera", "Tutor:", "Pablo"])]
    )

    assert cover_authors(pdf) == ("Ana Vera",)


def test_no_busca_mas_alla_de_la_segunda_pagina() -> None:
    pdf = make_pdf([PageSpec(lines=[]), PageSpec(lines=[]), PageSpec(lines=["Autor:", "Ana Vera"])])

    assert cover_authors(pdf) == ()


def test_lee_solo_la_primera_pagina_del_pdf() -> None:
    pdf = make_pdf(
        [
            PageSpec(lines=["Autores:", "Ana Vera", "Tutor:", "Pablo Salas"]),
            PageSpec(lines=["Autor:", "Luis Rojas"]),
        ]
    )

    assert cover_authors(pdf) == ("Ana Vera",)


def test_no_usa_los_metadatos_del_pdf() -> None:
    assert cover_authors(make_pdf([PageSpec(lines=["Introducción", "Texto del trabajo."])])) == ()


@pytest.mark.parametrize(
    "content",
    [b"%PDF-roto", make_truncated_pdf(), make_scanned_pdf(), make_encrypted_pdf()],
    ids=["ilegible", "cortado", "escaneado", "con clave"],
)
def test_un_pdf_que_no_se_puede_leer_queda_sin_autores(content: bytes) -> None:
    assert cover_authors(content) == ()
