"""Separación de la lista de referencias en entradas y detección de la norma (T06)."""

import json
from uuid import uuid4

import httpx
import pytest

from app.pipeline.norm_detection import Norm
from app.pipeline.pdf_text import TextLine
from app.pipeline.references_section import ReferenceSection, extract_reference_section
from app.pipeline.segmentation import (
    GLUED,
    NOT_A_REFERENCE,
    TOO_LONG,
    Segmentation,
    SegmentedReference,
    segment_references,
    split_entries,
)
from app.repositories.references import UNCONFIRMED_SPLIT_CODE, SupabaseReferenceRepository
from app.repositories.supabase_http import SupabaseUnavailableError
from tests.pdf_factory import PageSpec, make_pdf

MARGIN = 72.0
HANGING = 108.0  # 36 pt de sangría francesa, como en Word

APA_1 = "Pérez, M. y López, J. (2021). Redes neuronales en la educación superior."
APA_2 = "Rivas, A. (2020). Aprendizaje automático aplicado. Editorial UNEMI."
APA_3 = "Moreira, L. (2022). Evaluación de fuentes académicas. Revista Andina, 8(1), 10-25."
IEEE_1 = '[1] J. Pérez y M. López, "Redes neuronales," Rev. Andina, vol. 8, no. 1, 2021.'
IEEE_2 = '[2] A. Rivas, "Aprendizaje automático aplicado," Editorial UNEMI, 2020.'
IEEE_3 = '[3] L. Moreira, "Evaluación de fuentes," Rev. Andina, vol. 8, pp. 10-25, 2022.'


def line(text: str, x0: float = MARGIN, page: int = 1) -> TextLine:
    return TextLine(page=page, x0=x0, text=text)


def texts(lines: list[TextLine]) -> list[str]:
    return [entry.text for entry in split_entries(lines)]


# --- APA ------------------------------------------------------------------------------------


def test_apa_separa_por_sangria_francesa() -> None:
    lines = [
        line("Pérez, M. y López, J. (2021). Redes neuronales en la educación"),
        line("Superior Tecnológica. Revista Andina, 8(1), 10-25.", HANGING),
        line(APA_2),
        line("Ministerio de Educación. Ley Orgánica de Educación Intercultural."),
        line("Registro Oficial 417.", HANGING),
    ]

    assert texts(lines) == [
        "Pérez, M. y López, J. (2021). Redes neuronales en la educación "
        "Superior Tecnológica. Revista Andina, 8(1), 10-25.",
        APA_2,
        # Sin año entre paréntesis, la sangría basta para reconocerla.
        "Ministerio de Educación. Ley Orgánica de Educación Intercultural. Registro Oficial 417.",
    ]


def test_apa_sin_sangria_separa_por_el_patron_autor_anio() -> None:
    lines = [
        line("Pérez, M. y López, J. (2021). Redes neuronales en la educación"),
        line("Superior Tecnológica. Revista Andina, 8(1), 10-25."),
        line(APA_2),
        line("Organización Mundial de la Salud. (2020, 3 de mayo). Informe sobre"),
        line("Salud Digital. https://www.who.int/"),
        line("Informe-2020"),
    ]

    assert texts(lines) == [
        "Pérez, M. y López, J. (2021). Redes neuronales en la educación "
        "Superior Tecnológica. Revista Andina, 8(1), 10-25.",
        APA_2,
        "Organización Mundial de la Salud. (2020, 3 de mayo). Informe sobre "
        "Salud Digital. https://www.who.int/Informe-2020",
    ]


def test_lista_de_autores_partida_no_empieza_otra_referencia() -> None:
    lines = [
        line("Torres, A., Delgado-"),
        line("Quirós, M. (2021). Un apellido compuesto partido."),
        line("Rivas, A., Moreira, L. y"),
        line("Gómez, P. (2020). Autores en dos líneas."),
    ]

    assert texts(lines) == [
        "Torres, A., Delgado-Quirós, M. (2021). Un apellido compuesto partido.",
        "Rivas, A., Moreira, L. y Gómez, P. (2020). Autores en dos líneas.",
    ]


def test_sangria_de_primera_linea_no_se_confunde_con_la_francesa() -> None:
    lines = [
        line(APA_1, HANGING),
        line("Revista Andina, 8(1), 10-25."),
        line(APA_2, HANGING),
        line("Editorial UNEMI."),
    ]

    assert texts(lines) == [f"{APA_1} Revista Andina, 8(1), 10-25.", f"{APA_2} Editorial UNEMI."]


def test_sangria_de_primera_linea_con_el_anio_en_la_linea_siguiente() -> None:
    # Así llegan muchos trabajos: la primera línea con sangría y el resto en el margen.
    lines = [
        line("Cedeño Mora, R., Vera Ruiz, P., Salazar-Ponce, J.-M., Vargas", HANGING),
        line("Ortiz, O. O., & Mendoza León, A. (2024). Segmentación de referencias."),
        line("Torres-Vélez, C., Zambrano-Gil, A., & Ortega-Haro, J. L.", HANGING),
        line("(2023). Inteligencia artificial en la educación superior."),
        line("https://doi.org/10.1234/abc.2023"),
        line("Rivas, A., Moreira, L., Gómez, P., &", HANGING),
        line("Paredes, D. (2022). Verificación automática de citas."),
    ]

    assert texts(lines) == [
        "Cedeño Mora, R., Vera Ruiz, P., Salazar-Ponce, J.-M., Vargas Ortiz, O. O., "
        "& Mendoza León, A. (2024). Segmentación de referencias.",
        "Torres-Vélez, C., Zambrano-Gil, A., & Ortega-Haro, J. L. (2023). Inteligencia "
        "artificial en la educación superior. https://doi.org/10.1234/abc.2023",
        "Rivas, A., Moreira, L., Gómez, P., & Paredes, D. (2022). "
        "Verificación automática de citas.",
    ]


def test_fuera_de_su_nivel_empieza_si_la_anterior_cerro_con_su_url() -> None:
    lines = [
        line("Rivas, A. (2020). Aprendizaje automático aplicado.", HANGING),
        line("https://editorial.example.org/libro"),
        line("Portal Educativo. (s.f). Guía de citas."),  # sin sangría por descuido
        line(APA_3, HANGING),
        line("https://doi.org/10.1234/ra.2022"),
    ]

    assert texts(lines) == [
        "Rivas, A. (2020). Aprendizaje automático aplicado. https://editorial.example.org/libro",
        "Portal Educativo. (s.f). Guía de citas.",
        f"{APA_3} https://doi.org/10.1234/ra.2022",
    ]


def test_referencia_que_continua_en_la_pagina_siguiente() -> None:
    lines = [
        line(APA_1, page=3),
        line("Revista Andina, 8(1), 10-25.", HANGING, page=3),
        line("Rivas, A. (2020). Aprendizaje automático aplicado.", page=3),
        line("Editorial UNEMI.", HANGING, page=4),
        line(APA_3, page=4),
    ]

    entries = split_entries(lines)

    assert [entry.text for entry in entries] == [
        f"{APA_1} Revista Andina, 8(1), 10-25.",
        APA_2,
        APA_3,
    ]
    assert [entry.page for entry in entries] == [3, 3, 4]


def test_documento_a_dos_columnas() -> None:
    right = 320.0
    lines = [
        line(APA_1),
        line("Revista Andina, 8(1), 10-25.", HANGING),
        line(APA_2, right),
        line("Segunda edición.", right + 36),
    ]

    assert texts(lines) == [f"{APA_1} Revista Andina, 8(1), 10-25.", f"{APA_2} Segunda edición."]


# --- IEEE -----------------------------------------------------------------------------------


def test_ieee_separa_por_la_numeracion() -> None:
    lines = [
        line('[1] J. Pérez y M. López, "Redes neuronales en la educación superior,"'),
        line("Rev. Andina, vol. 8, no. 1, pp. 10-25, 2021.", MARGIN + 20),
        line(IEEE_2),
        line(IEEE_3),
    ]

    assert texts(lines) == [
        '[1] J. Pérez y M. López, "Redes neuronales en la educación superior," '
        "Rev. Andina, vol. 8, no. 1, pp. 10-25, 2021.",
        IEEE_2,
        IEEE_3,
    ]


def test_ieee_con_las_lineas_siguientes_en_el_margen() -> None:
    lines = [
        line(IEEE_1, MARGIN + 18),
        line("Disponible en línea.", MARGIN),
        line(IEEE_2, MARGIN + 18),
    ]

    assert texts(lines) == [f"{IEEE_1} Disponible en línea.", IEEE_2]


def test_ieee_separa_referencias_que_quedaron_en_una_misma_linea() -> None:
    assert texts([line(f"{IEEE_1} {IEEE_2} {IEEE_3}")]) == [IEEE_1, IEEE_2, IEEE_3]


# --- Entradas dudosas -----------------------------------------------------------------------


def test_marca_el_texto_que_precede_a_la_lista_y_sigue_con_las_demas() -> None:
    entries = split_entries([line("A continuación, las obras consultadas."), line(APA_1)])

    assert [(entry.text, entry.issue) for entry in entries] == [
        ("A continuación, las obras consultadas.", NOT_A_REFERENCE),
        (APA_1, None),
    ]


def test_marca_dos_referencias_pegadas_en_una_linea() -> None:
    entries = split_entries([line(f"{APA_1} {APA_2}"), line(APA_3)])

    assert [entry.issue for entry in entries] == [GLUED, None]


def test_marca_una_referencia_pegada_despues_del_doi() -> None:
    entries = split_entries([line(f"{APA_3} https://doi.org/10.1234/ra.2022 {APA_2}")])

    assert [entry.issue for entry in entries] == [GLUED]


def test_marca_una_entrada_demasiado_larga() -> None:
    long_title = "Un título muy extenso " * 50
    entries = split_entries([line(f"Rivas, A. (2020). {long_title}."), line(APA_2)])

    assert [entry.issue for entry in entries] == [TOO_LONG, None]


# --- Norma ----------------------------------------------------------------------------------


def section(lines: list[TextLine]) -> ReferenceSection:
    return ReferenceSection(heading="Referencias", page=1, lines=lines)


def test_lista_apa_guarda_la_norma_de_cada_referencia_y_de_la_lista() -> None:
    result = segment_references(section([line(APA_1), line(APA_2), line(APA_3)]))

    assert result.norm == Norm.APA
    assert [reference.order for reference in result.references] == [1, 2, 3]
    assert {reference.norm for reference in result.references} == {Norm.APA}


def test_lista_que_mezcla_apa_e_ieee_es_mixta() -> None:
    result = segment_references(section([line(APA_1), line(APA_2), line(IEEE_3)]))

    assert result.norm == Norm.MIXED
    assert [reference.norm for reference in result.references] == [Norm.APA, Norm.APA, Norm.IEEE]


def test_una_entrada_dudosa_se_registra(caplog: pytest.LogCaptureFixture) -> None:
    segment_references(section([line("Texto previo a la lista."), line(APA_1)]))

    assert "Referencia 1 (página 1)" in caplog.text


def test_pdf_ieee_completo() -> None:
    pdf = make_pdf(
        [
            PageSpec(
                [
                    "Conclusiones del trabajo con texto suficiente.",
                    "Referencias",
                    '[1] J. Pérez y M. López, "Redes neuronales en la educación superior,"',
                    (18.0, "Rev. Andina, vol. 8, no. 1, pp. 10-25, 2021."),
                    IEEE_2,
                    IEEE_3,
                ]
            )
        ]
    )

    result = segment_references(extract_reference_section(pdf))

    assert result.norm == Norm.IEEE
    assert len(result.references) == 3
    assert result.references[0].text.endswith("pp. 10-25, 2021.")


def test_pdf_apa_con_sangria_francesa() -> None:
    pdf = make_pdf(
        [
            PageSpec(
                [
                    "Conclusiones del trabajo con texto suficiente.",
                    "Referencias",
                    "Pérez, M. y López, J. (2021). Redes neuronales en la educación",
                    (36.0, "Superior. Revista Andina, 8(1), 10-25."),
                    APA_2,
                    APA_3,
                ]
            )
        ]
    )

    result = segment_references(extract_reference_section(pdf))

    assert result.norm == Norm.APA
    assert [reference.text for reference in result.references] == [
        "Pérez, M. y López, J. (2021). Redes neuronales en la educación "
        "Superior. Revista Andina, 8(1), 10-25.",
        APA_2,
        APA_3,
    ]


# --- Repositorio ----------------------------------------------------------------------------

REST_URL = "https://proyecto.supabase.co/rest/v1"


def test_guarda_las_referencias_la_norma_y_las_entradas_dudosas() -> None:
    analysis_id = uuid4()
    seen: list[tuple[str, str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        table = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content) if request.content else None
        seen.append((request.method, table, body))
        if request.method == "POST" and table == "referencias":
            assert isinstance(body, list)
            return httpx.Response(
                201, json=[{"id": f"ref-{row['orden']}", "orden": row["orden"]} for row in body]
            )
        return httpx.Response(204 if request.method != "POST" else 201)

    segmentation = Segmentation(
        references=[
            SegmentedReference(1, 9, "Texto previo.", Norm.UNKNOWN, NOT_A_REFERENCE),
            SegmentedReference(2, 9, APA_1, Norm.APA, None),
        ],
        norm=Norm.APA,
    )
    repository = SupabaseReferenceRepository(
        REST_URL, httpx.Client(transport=httpx.MockTransport(handler))
    )

    repository.save_segmentation(analysis_id, segmentation)

    assert [(method, table) for method, table, _ in seen] == [
        ("DELETE", "referencias"),  # reanalizar reemplaza lo anterior
        ("POST", "referencias"),
        ("POST", "hallazgos"),
        ("PATCH", "analisis"),
    ]
    assert seen[1][2] == [
        {
            "analisis_id": str(analysis_id),
            "orden": 1,
            "texto_crudo": "Texto previo.",
            "pagina": 9,
            "norma": "DESCONOCIDA",
        },
        {
            "analisis_id": str(analysis_id),
            "orden": 2,
            "texto_crudo": APA_1,
            "pagina": 9,
            "norma": "APA",
        },
    ]
    assert seen[2][2] == [
        {
            "referencia_id": "ref-1",
            "tipo": "formato",
            "codigo": UNCONFIRMED_SPLIT_CODE,
            "severidad": "info",
            "valor_dado": "Texto previo.",
            "mensaje": NOT_A_REFERENCE,
        }
    ]
    assert seen[3][2] == {"norma_detectada": "APA", "total_referencias": 2}


def test_supabase_caido_al_guardar_las_referencias() -> None:
    repository = SupabaseReferenceRepository(
        REST_URL, httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    )

    with pytest.raises(SupabaseUnavailableError):
        repository.save_segmentation(uuid4(), Segmentation(references=[], norm=Norm.UNKNOWN))
