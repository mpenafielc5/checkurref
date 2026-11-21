"""Referencia corregida en APA 7 e IEEE (T26, HU-19). Sin fuentes ni modelo real."""

from dataclasses import replace

import pytest

from app.extraction.base import Author, ExtractedFields
from app.pipeline.norm_detection import Norm
from app.sources.records import Source, SourceRecord
from app.verification.corrected import CorrectedReference, _initials, corrected_reference
from app.verification.decision import CheckedField, decide
from tests.test_decision import DOI, RECORD, FakeNli, by_doi, by_search

ARTICLE = replace(RECORD, work_type="journal-article")
SURNAMES = [
    "Acosta",
    "Aguirre",
    "Benítez",
    "Cabrera",
    "Castillo",
    "Delgado",
    "Espinoza",
    "Fajardo",
    "Gallardo",
    "Herrera",
    "Iturralde",
    "Jaramillo",
    "Kuffó",
    "Lozano",
    "Mendoza",
    "Naranjo",
    "Ortega",
    "Paredes",
    "Quiroz",
    "Rosales",
    "Salazar",
    "Torres",
]

APA_WRONG = (
    "Pérez, M. y López Vera, J. (2019). Redes neuronales en la educación superior. "
    "Revista Andina, 9(1), 10-25."
)
APA_WRONG_FIELDS = ExtractedFields(
    authors=(Author("Pérez", "M."), Author("López Vera", "J.")),
    year=2019,
    title="Redes neuronales en la educación superior",
    container="Revista Andina",
    volume="9",
    issue="1",
    pages="10-25",
)
IEEE_WRONG = (
    "[3] M. Pérez y J. López Vera, “Redes neuronales en la educación superior,” "
    "Rev. Andina, vol. 8, no. 1, pp. 30–45, 2019."
)
IEEE_WRONG_FIELDS = ExtractedFields(
    authors=(Author("Pérez", "M."), Author("López Vera", "J.")),
    year=2019,
    title="Redes neuronales en la educación superior",
    container="Rev. Andina",
    volume="8",
    issue="1",
    pages="30–45",
)


def correct(
    text: str,
    fields: ExtractedFields,
    record: SourceRecord = ARTICLE,
    norm: Norm = Norm.APA,
    by: str = "search",
) -> CorrectedReference:
    result = by_doi(record) if by == "doi" else by_search(record)
    corrected = corrected_reference(text, norm, fields, decide(text, fields, result, FakeNli()))
    assert corrected is not None
    return corrected


# --- Una prueba por norma con datos erróneos (criterio de T26) ------------------------------


def test_apa_con_datos_erroneos() -> None:
    corrected = correct(APA_WRONG, APA_WRONG_FIELDS)

    assert corrected.text == (
        "Pérez, M. y López Vera, J. (2021). Redes neuronales en la educación superior. "
        "Revista Andina, 8(1), 10-25. https://doi.org/10.1234/ra.2021.8"
    )
    assert corrected.changed_fields == (CheckedField.YEAR, CheckedField.VOLUME, CheckedField.DOI)


def test_revista_sin_volumen_pone_coma_antes_del_numero() -> None:
    # normas-apa.org: "Revista Internacional Magisterio, (54), 10-17."
    text = APA_WRONG.replace("9(1)", "(1)")
    fields = replace(APA_WRONG_FIELDS, volume=None, year=2021)

    corrected = correct(text, fields, record=replace(ARTICLE, volume=None))

    assert "Revista Andina, (1), 10-25." in corrected.text


def test_ieee_con_datos_erroneos_conserva_el_numero() -> None:
    corrected = correct(IEEE_WRONG, IEEE_WRONG_FIELDS, norm=Norm.IEEE)

    assert corrected.text == (
        "[3] M. Pérez y J. López Vera, “Redes neuronales en la educación superior,” "
        "Rev. Andina, vol. 8, no. 1, pp. 10-25, 2021, doi: 10.1234/ra.2021.8."
    )
    assert corrected.changed_fields == (CheckedField.PAGES, CheckedField.YEAR, CheckedField.DOI)


# --- Qué cambia y qué se conserva -----------------------------------------------------------


def test_lo_que_coincide_queda_como_lo_escribio_el_estudiante() -> None:
    # La abreviatura "Rev. Andina" es válida en IEEE: no se cambia por el nombre completo.
    corrected = correct(IEEE_WRONG, IEEE_WRONG_FIELDS, norm=Norm.IEEE)

    container = next(s for s in corrected.segments if s.field is CheckedField.CONTAINER)
    assert container.text == "Rev. Andina"
    assert container.changed is False


def test_un_titulo_que_solo_difiere_en_mayusculas_no_se_cambia() -> None:
    record = replace(ARTICLE, title="Redes Neuronales en la Educación Superior")

    corrected = correct(APA_WRONG, APA_WRONG_FIELDS, record=record)

    assert "Redes neuronales en la educación superior." in corrected.text
    assert CheckedField.TITLE not in corrected.changed_fields


def test_un_titulo_distinto_se_toma_del_registro() -> None:
    title = "Redes nueronales en la educacion superior"
    fields = replace(APA_WRONG_FIELDS, title=title)
    text = APA_WRONG.replace("Redes neuronales en la educación superior", title)

    corrected = correct(text, fields)

    assert "Redes neuronales en la educación superior." in corrected.text
    assert CheckedField.TITLE in corrected.changed_fields


def test_un_doi_que_ninguna_fuente_registra_no_se_conserva() -> None:
    fields = replace(APA_WRONG_FIELDS, doi="10.1000/inventado")
    record = replace(ARTICLE, doi=None)

    corrected = correct(APA_WRONG, fields, record=record)

    assert "10.1000" not in corrected.text


def test_una_referencia_verificada_sale_igual_sin_cambios() -> None:
    fields = replace(APA_WRONG_FIELDS, year=2021, volume="8", doi=DOI)
    text = APA_WRONG.replace("2019", "2021").replace("9(1)", "8(1)")

    corrected = correct(text, fields, by="doi")

    assert corrected.changed_fields == ()


def test_revista_y_volumen_van_en_cursiva_en_apa() -> None:
    corrected = correct(APA_WRONG, APA_WRONG_FIELDS)

    italic = "".join(segment.text for segment in corrected.segments if segment.italic)
    assert italic == "Revista Andina, 8"  # el número entre paréntesis no (normas-apa.org)


def test_respeta_el_ampersand_si_el_estudiante_lo_uso() -> None:
    text = APA_WRONG.replace(" y ", " & ")

    assert correct(text, APA_WRONG_FIELDS).text.startswith("Pérez, M. & López Vera, J. (2021)")


# --- Autores --------------------------------------------------------------------------------


def test_agrega_el_autor_que_falta_y_quita_el_que_sobra() -> None:
    fields = replace(APA_WRONG_FIELDS, authors=(Author("Pérez", "M."), Author("Castro", "L.")))
    record = replace(
        ARTICLE, authors=(Author("Pérez", "María"), Author("López Vera", "Juan Carlos"))
    )

    corrected = correct(APA_WRONG, fields, record=record)

    assert corrected.text.startswith("Pérez, M. y López Vera, J. C. (2021)")
    assert CheckedField.AUTHORS in corrected.changed_fields


def test_corrige_la_inicial_y_conserva_el_apellido_citado() -> None:
    fields = replace(APA_WRONG_FIELDS, authors=(Author("Pérez", "J."), Author("López Vera", "J.")))

    corrected = correct(APA_WRONG, fields)

    assert corrected.text.startswith("Pérez, M. y López Vera, J. (2021)")
    assert CheckedField.AUTHORS in corrected.changed_fields


def test_conserva_los_dos_apellidos_que_crossref_separo_mal() -> None:
    # Caso real: Crossref registra given "Ana Beltran", family "Flandoli".
    fields = replace(APA_WRONG_FIELDS, authors=(Author("Beltran Flandoli", "A."),))
    record = replace(ARTICLE, authors=(Author("Flandoli", "Ana Beltran"),))

    corrected = correct("Beltran Flandoli, A. (2019). Redes.", fields, record=record)

    assert corrected.text.startswith("Beltran Flandoli, A. (2021)")


def test_separa_el_nombre_completo_de_openalex() -> None:
    fields = replace(APA_WRONG_FIELDS, authors=(Author("Pérez", "M."),))
    record = replace(
        ARTICLE,
        source=Source.OPENALEX,
        authors=(Author("María Pérez"), Author("Francisco José García Peñalvo")),
    )

    corrected = correct(APA_WRONG, fields, record=record)

    assert corrected.text.startswith("Pérez, M. y García Peñalvo, F. J. (2021)")


def test_apa_con_mas_de_veinte_autores() -> None:
    authors = tuple(Author(surname, "A.") for surname in SURNAMES)  # 22 autores
    fields = replace(APA_WRONG_FIELDS, authors=authors)
    record = replace(ARTICLE, authors=authors)

    names = correct(APA_WRONG, fields, record=record).segments[0].text

    assert names.startswith("Acosta, A., Aguirre, A.")
    assert names.endswith("Quiroz, A., ... Torres, A.")  # los primeros 19 y el último
    assert "Rosales" not in names and "Salazar" not in names


def test_ieee_con_mas_de_seis_autores_usa_et_al() -> None:
    authors = tuple(Author(surname, "A.") for surname in SURNAMES[:7])
    fields = replace(IEEE_WRONG_FIELDS, authors=authors[:1])
    record = replace(ARTICLE, authors=authors)

    corrected = correct(IEEE_WRONG, fields, record=record, norm=Norm.IEEE)

    assert corrected.text.startswith("[3] A. Acosta et al., “Redes")
    assert CheckedField.AUTHORS not in corrected.changed_fields


@pytest.mark.parametrize(
    ("given", "initials"),
    [
        ("María José", "M. J."),
        ("M.J.", "M. J."),
        ("Jean-Marc", "J.-M."),
        ("María de los Ángeles", "M. Á."),
        ("", ""),
    ],
)
def test_iniciales(given: str, initials: str) -> None:
    assert _initials(given) == initials


# --- Tipos de obra --------------------------------------------------------------------------


BOOK = SourceRecord(
    source=Source.CROSSREF,
    doi="10.5555/libro",
    title="Aprendizaje automático aplicado",
    authors=(Author("Rivas", "Ana"),),
    year=2020,
    publisher="Editorial UNEMI",
    work_type="book",
)
BOOK_FIELDS = ExtractedFields(
    authors=(Author("Rivas", "A."),), year=2018, title="Aprendizaje automático aplicado"
)


def test_libro_en_apa_con_titulo_en_cursiva_y_editorial() -> None:
    corrected = correct("Rivas, A. (2018). Aprendizaje automático aplicado.", BOOK_FIELDS, BOOK)

    assert corrected.text == (
        "Rivas, A. (2020). Aprendizaje automático aplicado. Editorial UNEMI. "
        "https://doi.org/10.5555/libro"
    )
    title = next(s for s in corrected.segments if s.field is CheckedField.TITLE)
    assert title.italic is True


def test_libro_en_ieee() -> None:
    corrected = correct("[1] A. Rivas, Aprendizaje.", BOOK_FIELDS, BOOK, norm=Norm.IEEE)

    assert corrected.text == (
        "[1] A. Rivas, Aprendizaje automático aplicado. Editorial UNEMI, 2020, doi: 10.5555/libro."
    )


def test_capitulo_en_apa() -> None:
    chapter = replace(BOOK, title="Redes", container="Manual de IA", pages="10-20")
    chapter = replace(chapter, work_type="book-chapter")
    fields = replace(BOOK_FIELDS, title="Redes", year=2020)

    corrected = correct("Rivas, A. (2020). Redes.", fields, chapter)

    assert corrected.text == (
        "Rivas, A. (2020). Redes. En Manual de IA (pp. 10-20). Editorial UNEMI. "
        "https://doi.org/10.5555/libro"
    )


def test_capitulo_conserva_editores_subtitulo_que_la_fuente_omite_y_paginas_limpias() -> None:
    # Caso real (datos cambiados): la fuente registra el capítulo sin su subtítulo.
    text = (
        "Mora, L. A., y Vera, P. (2018). Tutor virtual: Un asistente para la educación "
        "en línea. En C. Ruiz, J. Salas, y B. Torres (Eds.), Ingeniería del aprendizaje "
        "en línea (pp. 120– 143). Editorial Andina."
    )
    fields = ExtractedFields(
        authors=(Author("Mora", "L. A."), Author("Vera", "P.")),
        year=2018,
        title="Tutor virtual: Un asistente para la educación en línea",
        container="Ingeniería del aprendizaje en línea",
        pages="120– 143",
        publisher="Editorial Andina",
    )
    record = SourceRecord(
        source=Source.CROSSREF,
        doi="10.5555/capitulo-7",
        title="Tutor virtual",
        authors=(Author("Mora", "Luis A."), Author("Vera", "Pablo")),
        year=2018,
        container="Ingeniería del Aprendizaje en Línea",
        pages="120-143",
        work_type="book-chapter",
    )

    corrected = correct(text, fields, record)

    assert corrected.text == (
        "Mora, L. A. y Vera, P. (2018). Tutor virtual: Un asistente para la educación en "
        "línea. En C. Ruiz, J. Salas y B. Torres (Eds.), Ingeniería del aprendizaje en "
        "línea (pp. 120–143). Editorial Andina. "
        "https://doi.org/10.5555/capitulo-7"
    )
    assert CheckedField.TITLE not in corrected.changed_fields


def test_informe_citado_por_su_editor_conserva_el_numero_sin_cursiva() -> None:
    text = (
        "Salas, D. (Ed.). (2021). Marco de autorización para servicios web (RFC 9999). "
        "Editorial Técnica. https://doi.org/10.5555/RFC9999"
    )
    fields = ExtractedFields(
        authors=(Author("Salas", "D."),),
        year=2021,  # el registro dice 2012: así hay referencia corregida
        title="Marco de autorización para servicios web (RFC 9999)",
        publisher="Editorial Técnica",
        doi="10.5555/RFC9999",
    )
    record = SourceRecord(
        source=Source.CROSSREF,
        doi="10.5555/rfc9999",
        title="Marco de Autorización para Servicios Web",
        authors=(Author("Salas", "D."),),
        year=2012,
        publisher="Editorial Técnica",
        work_type="report",
    )

    corrected = correct(text, fields, record, by="doi")

    assert corrected.text == (
        "Salas, D. (Ed.). (2012). Marco de autorización para servicios web (RFC 9999). "
        "Editorial Técnica. https://doi.org/10.5555/rfc9999"
    )
    titles = [s for s in corrected.segments if s.field is CheckedField.TITLE]
    assert [(s.text, s.italic) for s in titles] == [
        ("Marco de autorización para servicios web", True),
        (" (RFC 9999)", False),
    ]


def test_actas_citadas_como_revista_conservan_el_formato_y_el_volumen() -> None:
    # Caso real (datos cambiados): Crossref pone el volumen en el nombre de las actas.
    text = (
        "Rivas, T. (2023). Herramientas que los modelos de lenguaje aprenden solos. "
        "Avances en Sistemas de Computación Neuronal, 36, 68539–68551. "
        "https://actas.ejemplo.org/articulo.pdf"
    )
    fields = ExtractedFields(
        authors=(Author("Rivas", "T."),),
        year=2023,
        title="Herramientas que los modelos de lenguaje aprenden solos",
        container="Avances en Sistemas de Computación Neuronal",
        volume="36",
        pages="68539–68551",
    )
    record = SourceRecord(
        source=Source.CROSSREF,
        doi="10.5555/actas-2997",
        title="Herramientas que los Modelos de Lenguaje Aprenden Solos",
        authors=(Author("Rivas", "Tomás"),),
        year=2023,
        container="Avances en Sistemas de Computación Neuronal 36",
        pages="68539-68551",
        publisher="Fundación de Computación Neuronal",
        work_type="proceedings-article",
    )

    corrected = correct(text, fields, record)

    assert corrected.text == (
        "Rivas, T. (2023). Herramientas que los modelos de lenguaje aprenden solos. "
        "Avances en Sistemas de Computación Neuronal, 36, 68539–68551. "
        "https://doi.org/10.5555/actas-2997"
    )


def test_titulo_copiado_distinto_en_la_misma_publicacion_y_numero_de_articulo() -> None:
    # Caso real: el título está reescrito, falta el volumen y el extractor tomó el
    # número de artículo por volumen. Autores, año, revista y número coinciden.
    text = (
        "Paz, S. (2022). Cincuenta años de investigación sobre la familia y el logro "
        "académico: Un metaanálisis de segundo orden. Revista de Educación, 100463."
    )
    fields = ExtractedFields(
        authors=(Author("Paz", "S."),),
        year=2022,
        title=(
            "Cincuenta años de investigación sobre la familia y el logro académico: "
            "Un metaanálisis de segundo orden"
        ),
        container="Revista de Educación",
        volume="100463",
    )
    record = SourceRecord(
        source=Source.CROSSREF,
        doi="10.5555/re.2022.100463",
        title=(
            "Cincuenta años de familia y logro académico en la investigación: "
            "Un metaanálisis de segundo orden"
        ),
        authors=(Author("Paz", "Sonia"),),
        year=2022,
        container="Revista de Educación",
        volume="37",
        pages="100463",
        work_type="journal-article",
    )
    verification = decide(text, fields, by_search(record), FakeNli())
    assert verification.cited is not None

    corrected = corrected_reference(text, Norm.APA, verification.cited, verification)

    assert [check.field for check in verification.mismatches] == [CheckedField.TITLE]
    assert corrected is not None
    assert corrected.text == (
        "Paz, S. (2022). Cincuenta años de familia y logro académico en la investigación: "
        "Un metaanálisis de segundo orden. Revista de Educación, 37, 100463. "
        "https://doi.org/10.5555/re.2022.100463"
    )


def test_preprint_de_arxiv_en_apa_y_en_ieee() -> None:
    # Caso real: OpenAlex registra el preprint en "arXiv (Cornell University)" y le
    # agrega el volumen y las páginas de la versión publicada en el congreso.
    text = (
        "Vera, A. (2017). Atención para traducir textos. arXiv. "
        "https://doi.org/10.48550/arXiv.2101.00001"
    )
    fields = ExtractedFields(
        authors=(Author("Vera", "A."),),
        year=2017,
        title="Atención para traducir textos",
        doi="10.48550/arXiv.2101.00001",
    )
    record = SourceRecord(
        source=Source.OPENALEX,
        doi="10.48550/arxiv.2101.00001",
        title="Atención para traducir textos",
        authors=(Author("Andrea Vera"),),
        year=2017,
        container="arXiv (Cornell University)",
        publisher="Cornell University",
        volume="30",
        pages="5998-6008",
        work_type="preprint",
    )

    apa = correct(text, fields, record, by="doi")

    assert apa.text == (
        "Vera, A. (2017). Atención para traducir textos. arXiv. "
        "https://doi.org/10.48550/arxiv.2101.00001"
    )
    title = next(s for s in apa.segments if s.field is CheckedField.TITLE)
    assert title.italic is True
    ieee = correct("[4] A. Vera, " + text, fields, record, norm=Norm.IEEE, by="doi")
    assert ieee.text == "[4] A. Vera, “Atención para traducir textos,” 2017, arXiv:2101.00001."
    # Otro repositorio sin número de arXiv: la guía IEEE no da su formato.
    other = replace(record, doi="10.1101/2020.01.01.123456", container="medRxiv")
    fields = replace(fields, doi=other.doi)
    verification = decide("[4] x", fields, by_doi(other), FakeNli())
    assert corrected_reference("[4] x", Norm.IEEE, fields, verification) is None


def test_doi_de_arxiv_unido_al_articulo_publicado_sigue_siendo_el_preprint() -> None:
    # Caso real: OpenAlex une el preprint con su versión en un congreso y da el tipo y
    # el contenedor del congreso; la referencia citó el preprint por su DOI de arXiv.
    text = (
        "Vera, A. (2021). Atención para traducir textos (arXiv:2101.00001). arXiv. "
        "https://doi.org/10.48550/arXiv.2101.00001"
    )
    fields = ExtractedFields(
        authors=(Author("Vera", "A."),),
        year=2021,
        title="Atención para traducir textos",
        doi="10.48550/arXiv.2101.00001",
    )
    record = SourceRecord(
        source=Source.OPENALEX,
        doi="10.18653/v1/2022.acl-long.1",
        title="Atención para traducir textos",
        authors=(Author("Andrea Vera"),),
        year=2021,
        container="Proceedings of the conference - Association for Computational Linguistics",
        pages="1-10",
        work_type="conference-paper",
    )

    apa = correct(text, fields, record, by="doi")

    assert apa.text == (
        "Vera, A. (2021). Atención para traducir textos. arXiv. "
        "https://doi.org/10.48550/arxiv.2101.00001"
    )
    ieee = correct("[4] A. Vera, " + text, fields, record, norm=Norm.IEEE, by="doi")
    assert ieee.text == "[4] A. Vera, “Atención para traducir textos,” 2021, arXiv:2101.00001."


@pytest.mark.parametrize(
    "extracted",
    ["Redes neuronales en la educación", None],
    ids=["cortado por el extractor", "sin título extraído"],
)
def test_titulo_bien_escrito_en_la_referencia_no_se_marca_como_corregido(
    extracted: str | None,
) -> None:
    # Caso real: el extractor cortó el título o no lo encontró, pero la referencia lo
    # trae completo; se conserva como lo escribió el estudiante.
    text = APA_WRONG.replace(
        "Pérez, M. y López Vera, J. (2019)", "Pérez, M. y López Vera, J. (2021)"
    )
    text = text.replace("9(1), 10-25.", "8(1), 10-25.")
    fields = replace(APA_WRONG_FIELDS, year=2021, volume="8", title=extracted)
    record = replace(ARTICLE, title="Redes Neuronales en la Educación Superior")

    corrected = correct(text, fields, record, by="doi")

    assert "(2021). Redes neuronales en la educación superior. Revista Andina" in corrected.text
    assert CheckedField.TITLE not in corrected.changed_fields


def test_guion_perdido_al_unir_las_lineas_del_pdf_se_devuelve_sin_marcar() -> None:
    # Caso real: "objeto-" al final de una línea y "relacionado" en la siguiente; al
    # unir las líneas se quitó el guion, como si fuera una palabra partida en sílabas.
    title = "Redes neuronales en la educación superior objetorelacionada"
    text = APA_WRONG.replace("Redes neuronales en la educación superior", title)
    fields = replace(APA_WRONG_FIELDS, title=title)
    record = replace(ARTICLE, title="Redes Neuronales en la Educación Superior Objeto-Relacionada")

    corrected = correct(text, fields, record)

    assert "Redes neuronales en la educación superior objeto-relacionada." in corrected.text
    assert CheckedField.TITLE not in corrected.changed_fields


# --- Casos reales de los trabajos de un curso: lo que el estudiante escribió bien ----------

GOOD_APA = (
    "Pérez, M. y da Silva Vera, J. (2021). Redes neuronales en la educación superior. "
    "Revista Andina, 8(1), 10-25. https://doi.org/10.1234/ra.2021.8"
)
GOOD_FIELDS = ExtractedFields(
    authors=(Author("Pérez", "M."), Author("da Silva Vera", "J.")),
    year=2021,
    title="Redes neuronales en la educación superior",
    container="Revista Andina",
    volume="8",
    issue="1",
    pages="10-25",
    doi="10.1234/ra.2021.8",
)
GOOD_RECORD = replace(ARTICLE, authors=(Author("Pérez", "María"), Author("da Silva Vera", "Juan")))


def test_autores_bien_escritos_se_copian_aunque_el_extractor_pierda_una_particula() -> None:
    # Caso real: AnyStyle dejó "Silva Vera, J." y la referencia corregida perdía el "da".
    fields = replace(GOOD_FIELDS, authors=(Author("Pérez", "M."), Author("Silva Vera", "J.")))

    corrected = correct(GOOD_APA, fields, GOOD_RECORD, by="doi")

    assert corrected.text.startswith("Pérez, M. y da Silva Vera, J. (2021). ")
    assert CheckedField.AUTHORS not in corrected.changed_fields


def test_nombre_invertido_por_la_fuente_no_cambia_la_inicial() -> None:
    # Caso real: Crossref registra "M, Pérez" para "Pérez, M.".
    record = replace(GOOD_RECORD, authors=(Author("M", "Pérez"), Author("da Silva Vera", "Juan")))

    corrected = correct(GOOD_APA, GOOD_FIELDS, record, by="doi")

    assert corrected.text.startswith("Pérez, M. y da Silva Vera, J. (2021). ")


def test_autores_que_no_estan_en_formato_apa_si_se_corrigen() -> None:
    text = GOOD_APA.replace("Pérez, M. y da Silva Vera, J.", "María Pérez & Juan da Silva Vera.")
    fields = replace(
        GOOD_FIELDS, authors=(Author("Pérez", "María"), Author("da Silva Vera", "Juan"))
    )

    corrected = correct(text, fields, GOOD_RECORD, by="doi")

    assert corrected.text.startswith("Pérez, M. & da Silva Vera, J. (2021). ")


def test_revista_sin_volumen_conserva_solo_el_numero() -> None:
    # Caso real: "Revista, (94)." y el extractor tomó el 94 como volumen.
    text = GOOD_APA.replace("8(1), 10-25.", "(94).")
    fields = replace(GOOD_FIELDS, volume="94", issue=None, pages=None)
    record = replace(GOOD_RECORD, volume=None, issue="94", pages=None)

    corrected = correct(text, fields, record, by="doi")

    assert "Revista Andina, (94). https://doi.org/" in corrected.text


def test_actas_sin_en_repetido_ni_parentesis_abierto() -> None:
    # Caso real: el extractor dejó "En Congreso ... (CIE" como nombre de las actas.
    text = (
        "Vera, A. (2023). Redes en el aula. En Congreso de Educación Superior (CIE) "
        "(pp. 1–6). IEEE. https://doi.org/10.5555/cie.2023.1"
    )
    fields = ExtractedFields(
        authors=(Author("Vera", "A."),),
        year=2023,
        title="Redes en el aula",
        container="En Congreso de Educación Superior (CIE",
        pages="1–6",
        doi="10.5555/cie.2023.1",
    )
    record = SourceRecord(
        source=Source.CROSSREF,
        doi="10.5555/cie.2023.1",
        title="Redes en el aula",
        authors=(Author("Vera", "Ana"),),
        year=2023,
        container="Congreso de Educación Superior (CIE)",
        publisher="IEEE",
        pages="1-6",
        work_type="proceedings-article",
    )

    corrected = correct(text, fields, record, by="doi")

    assert "En Congreso de Educación Superior (CIE) (pp. 1–6). IEEE." in corrected.text
    assert "En En" not in corrected.text
    # La editorial pegada al nombre de las actas tampoco se repite.
    glued = replace(fields, container="Congreso de Educación Superior (CIE). IEEE", pages=None)
    text = text.replace(" (pp. 1–6)", "")
    corrected = correct(text, glued, replace(record, pages=None), by="doi")
    assert "IEEE. IEEE" not in corrected.text
    assert "En Congreso de Educación Superior (CIE). IEEE." in corrected.text


def test_libro_conserva_los_editores_escritos_despues_del_titulo() -> None:
    text = (
        "Rivas, L. (2021). Redes neuronales en el aula (A. Mora & S. Vera, Eds.). "
        "Editorial Andina. https://doi.org/10.5555/libro.2021"
    )
    fields = ExtractedFields(
        authors=(Author("Rivas", "L."),),
        year=2021,
        title="Redes neuronales en el aula",
        publisher="Editorial Andina",
        doi="10.5555/libro.2021",
    )
    record = SourceRecord(
        source=Source.CROSSREF,
        doi="10.5555/libro.2021",
        title="Redes neuronales en el aula",
        authors=(Author("Rivas", "Luis"),),
        year=2021,
        publisher="Editorial Andina",
        work_type="monograph",
    )

    corrected = correct(text, fields, record, by="doi")

    assert "Redes neuronales en el aula (A. Mora & S. Vera, Eds.). Editorial" in corrected.text


def test_palabras_pegadas_en_el_titulo_si_se_corrigen() -> None:
    title = "Redes neuronales en la educaciónsuperior"
    text = APA_WRONG.replace("Redes neuronales en la educación superior", title)
    fields = replace(APA_WRONG_FIELDS, title=title)

    corrected = correct(text, fields)

    assert "Redes neuronales en la educación superior." in corrected.text
    assert CheckedField.TITLE in corrected.changed_fields


def test_apa_conserva_el_numero_de_articulo_que_el_registro_da_como_paginas() -> None:
    # ACM registra las páginas dentro del artículo (1-26): no reemplazan al número.
    text = APA_WRONG.replace("9(1), 10-25.", "8(1), Artículo 66.").replace("2019", "2021")
    fields = replace(APA_WRONG_FIELDS, year=2021, volume="8", pages="66")
    record = replace(ARTICLE, pages="1-26")

    corrected = correct(text, fields, record)

    assert "Revista Andina, 8(1), 66. https://doi.org/" in corrected.text
    assert CheckedField.PAGES not in corrected.changed_fields


def test_sin_referencia_corregida_si_el_doi_es_del_libro_y_no_del_capitulo() -> None:
    text = (
        "Vera, A. (2025). Un capítulo sobre redes. En L. Mora (Ed.), Redes en la educación "
        "(pp. 73-89). Editorial UNEMI. https://doi.org/10.5555/libro"
    )
    fields = ExtractedFields(
        authors=(Author("Vera", "A."),),
        year=2025,
        title="Un capítulo sobre redes",
        container="Redes en la educación",
        pages="73-89",
        doi="10.5555/libro",
    )
    book = SourceRecord(
        source=Source.CROSSREF,
        doi="10.5555/libro",
        title="Redes en la educación",
        authors=(Author("Mora", "Luis"), Author("Vera", "Andrea"), Author("Rivas", "Ana")),
        year=2025,
        work_type="edited-book",
    )
    verification = decide(text, fields, by_doi(book), FakeNli())

    assert corrected_reference(text, Norm.APA, fields, verification) is None


def test_ieee_numero_de_articulo_despues_del_anio_y_una_sola_pagina_con_p() -> None:
    # IEEE Reference Guide: "vol. 5, no. 2, Apr. 2013, Art. no. 2600111" y "p. 475".
    text = IEEE_WRONG.replace("pp. 30–45", "pp. 100463")
    fields = replace(IEEE_WRONG_FIELDS, pages="100463")
    with_number = correct(text, fields, record=replace(ARTICLE, pages="100463"), norm=Norm.IEEE)
    assert "vol. 8, no. 1, 2021, Art. no. 100463, doi:" in with_number.text

    fields = replace(IEEE_WRONG_FIELDS, pages="475")
    one_page = correct(text, fields, record=replace(ARTICLE, pages="475"), norm=Norm.IEEE)
    assert "no. 1, p. 475, 2021" in one_page.text


def test_actas_en_ieee() -> None:
    paper = replace(
        BOOK,
        title="Redes",
        container="Proc. Congr. Int. Ing.",
        pages="10-20",
        work_type="proceedings-article",
    )
    fields = replace(BOOK_FIELDS, title="Redes", year=2020)

    corrected = correct("[2] A. Rivas, “Redes,” 2020.", fields, paper, norm=Norm.IEEE)

    assert corrected.text == (
        "[2] A. Rivas, “Redes,” in Proc. Congr. Int. Ing., 2020, pp. 10-20, doi: 10.5555/libro."
    )


def test_conserva_el_doi_citado_que_la_fuente_reconoce() -> None:
    record = replace(ARTICLE, doi="10.1145/publicado.2021")
    fields = replace(APA_WRONG_FIELDS, year=2021, volume="8", doi=DOI)

    corrected = correct(APA_WRONG, fields, record=record, by="doi")

    assert f"https://doi.org/{DOI}" in corrected.text
    assert CheckedField.DOI not in corrected.changed_fields


def test_usa_el_dato_oficial_si_el_estudiante_lo_escribio_completo() -> None:
    # El extractor perdió la letra del número de artículo, que el texto sí trae.
    text = APA_WRONG.replace("10-25.", "e289.")
    fields = replace(APA_WRONG_FIELDS, pages="289")

    corrected = correct(text, fields, record=replace(ARTICLE, pages="e289"))

    assert ", e289." in corrected.text
    assert CheckedField.PAGES not in corrected.changed_fields


def test_el_subtitulo_devuelto_al_titulo_no_se_repite_en_la_revista() -> None:
    record = replace(ARTICLE, title="Redes neuronales: en la educación superior")
    fields = replace(
        APA_WRONG_FIELDS,
        title="Redes neuronales",
        container="En la educación superior. Revista Andina",
    )
    verification = decide(APA_WRONG, fields, by_search(record), FakeNli())
    assert verification.cited is not None

    corrected = corrected_reference(APA_WRONG, Norm.APA, verification.cited, verification)

    assert corrected is not None
    assert corrected.text.count("educación superior") == 1


# --- Cuándo no hay referencia corregida -----------------------------------------------------


def test_sin_registro_de_la_obra_no_hay_referencia_corregida() -> None:
    unsupported = decide(APA_WRONG, APA_WRONG_FIELDS, by_search(), FakeNli())

    assert corrected_reference(APA_WRONG, Norm.APA, APA_WRONG_FIELDS, unsupported) is None


def test_norma_desconocida_no_tiene_referencia_corregida() -> None:
    verification = decide(APA_WRONG, APA_WRONG_FIELDS, by_search(ARTICLE), FakeNli())

    assert corrected_reference(APA_WRONG, Norm.UNKNOWN, APA_WRONG_FIELDS, verification) is None


# --- Casos vistos con PDF reales ------------------------------------------------------------


def test_conserva_la_coma_antes_del_ampersand() -> None:
    text = APA_WRONG.replace(" y ", ", & ")

    assert correct(text, APA_WRONG_FIELDS).text.startswith("Pérez, M., & López Vera, J. (2021)")


def test_no_cruza_autores_que_comparten_el_primer_apellido() -> None:
    cited = (Author("Huertas-Tato", "J."), Author("Huertas-García", "Á."))
    fields = replace(APA_WRONG_FIELDS, authors=cited)
    record = replace(
        ARTICLE, authors=(Author("Huertas-Tato", "Javier"), Author("Huertas-García", "Álvaro"))
    )

    corrected = correct(
        "Huertas-Tato, J. y Huertas-García, Á. (2019). Redes.", fields, record=record
    )

    assert corrected.text.startswith("Huertas-Tato, J. y Huertas-García, Á. (2021)")
    assert CheckedField.AUTHORS not in corrected.changed_fields


def test_descarta_afiliaciones_que_crossref_registro_como_autores() -> None:
    record = replace(
        ARTICLE,
        authors=(
            Author("Pérez", "María"),
            Author("MS in Information Systems, Universidad Andina, Quito, Ecuador"),
            Author("López Vera", "Juan"),
        ),
    )

    corrected = correct(APA_WRONG, APA_WRONG_FIELDS, record=record)

    assert corrected.text.startswith("Pérez, M. y López Vera, J. (2021)")


def test_sin_certeza_de_que_sea_la_obra_no_se_ofrece_corregirla() -> None:
    # La búsqueda halló otra obra de los mismos autores con un título solo parecido.
    record = replace(ARTICLE, title="Redes neuronales profundas para la educación universitaria")
    fields = replace(APA_WRONG_FIELDS, year=2021)
    verification = decide(APA_WRONG, fields, by_search(record), FakeNli())

    assert verification.record == record  # el motor la acepta como la misma obra
    assert corrected_reference(APA_WRONG, Norm.APA, fields, verification) is None


def test_capitulo_que_la_fuente_no_identifica_se_deduce_de_la_cita() -> None:
    record = replace(
        BOOK, title="Redes", container="Manual de IA", pages="71-86", work_type="other"
    )
    fields = replace(BOOK_FIELDS, title="Redes", year=2020, pages="pp.71-86,")
    text = "[2] A. Rivas, “Redes,” in Manual de IA, Editorial UNEMI, 2020, pp.71-86."

    corrected = correct(text, fields, record, norm=Norm.IEEE)

    assert corrected.text == (
        "[2] A. Rivas, “Redes,” in Manual de IA, Editorial UNEMI, 2020, pp. 71-86, "
        "doi: 10.5555/libro."
    )
