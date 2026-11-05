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
    fields = replace(APA_WRONG_FIELDS, title="Redes nueronales en la educacion superior")

    corrected = correct(APA_WRONG, fields)

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
