"""Los editores de un libro no cuentan como autores de su capítulo."""

from app.extraction.base import Author, ExtractedFields, close_title_parenthesis
from app.extraction.editors import drop_editors

CHAPTER = (
    "Lara, A., & Prado, S. (2022). Referencias estructuradas desde artículos en PDF. En "
    "G. Salinas, O. Cordero, P. Mena, G. M. Di Nardo, K. Gómez, N. Fierro, & A. Pozo (Eds.), "
    "Teoría y práctica de bibliotecas digitales (Vol. 13541, pp. 425–432). Editorial Andina."
)
# Caso real (datos cambiados): el extractor tomó a los editores como autores por el
# "En" en español.
MIXED = ExtractedFields(
    authors=(
        Author("Lara", "A."),
        Author("Prado", "S."),
        Author("Salinas", "G."),
        Author("Cordero", "O."),
        Author("Nardo", "G. M. Di"),
    )
)


def test_quita_a_los_editores_que_van_despues_del_anio() -> None:
    fields = drop_editors(CHAPTER, MIXED)

    assert [author.family for author in fields.authors] == ["Lara", "Prado"]


def test_sin_marca_de_editores_no_toca_nada() -> None:
    text = CHAPTER.replace(" (Eds.)", "")

    assert drop_editors(text, MIXED) is MIXED


def test_el_autor_que_es_editor_del_libro_completo_se_conserva() -> None:
    text = "Salas, D. (Ed.). (2012). Marco de autorización para servicios web (RFC 9999)."
    fields = ExtractedFields(authors=(Author("Salas", "D."),))

    assert drop_editors(text, fields) is fields


def test_sin_anio_entre_parentesis_no_toca_nada() -> None:
    text = "[3] A. Lara and S. Prado, in G. Salinas (Eds.), Teoría y práctica, 2022."

    assert drop_editors(text, MIXED) is MIXED


REPORT = (
    "Salas, D. (Ed.). (2012). Marco de autorización para servicios web (RFC 9999). "
    "Editorial Técnica. https://doi.org/10.5555/RFC9999"
)


def test_cierra_el_parentesis_que_el_extractor_dejo_fuera_del_titulo() -> None:
    # Caso real (datos cambiados): el extractor cortó el título antes del cierre del
    # número de informe.
    fields = ExtractedFields(title="Marco de autorización para servicios web (RFC 9999")

    closed = close_title_parenthesis(REPORT, fields)

    assert closed.title == "Marco de autorización para servicios web (RFC 9999)"


def test_no_agrega_un_cierre_que_la_referencia_no_trae() -> None:
    fields = ExtractedFields(title="Redes (una revisión")

    assert close_title_parenthesis("Pérez, M. (2020). Redes (una revisión. Ed.", fields) is fields
