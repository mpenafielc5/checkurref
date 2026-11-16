"""Limpieza de cada renglón al leer el texto del PDF."""

from app.pipeline.pdf_text import clean_line


def test_quita_el_caracter_nulo_que_dejan_algunos_pdf_de_word() -> None:
    # Caso real: la última referencia terminaba en "\x00"; PostgreSQL no la guardaba.
    text = "Zamora, B. J. (2002). Revista de Pedagogía, 41(2), 64-70.\x00"

    assert clean_line(text) == "Zamora, B. J. (2002). Revista de Pedagogía, 41(2), 64-70."


def test_quita_otros_caracteres_de_control_y_normaliza_los_espacios() -> None:
    assert clean_line("Pérez,\x01 M.\x7f  (2021).\t Título") == "Pérez, M. (2021). Título"


def test_conserva_tildes_guiones_y_comillas() -> None:
    text = "Gómez, Á. (2020). «Señales» — análisis 64–70."

    assert clean_line(text) == text
