"""Lee los autores de un trabajo desde la portada del PDF (T23, RF19).

En un lote, muchos estudiantes suben el archivo con el nombre de la tarea: los
autores son lo que permite distinguirlos. Se buscan en la primera página, después
de una etiqueta conocida, y el dato termina en la siguiente etiqueta. Las dos
listas de etiquetas están aquí, para agregar variantes con facilidad.

No se usan los metadatos del PDF: guardan al creador de la plantilla de Word, no
al autor real. Si no se reconoce la portada, el trabajo queda sin autores; nunca
se pide escribirlos a mano. Un error al leerla nunca impide subir el trabajo.
"""

import logging
import re
import unicodedata

import pymupdf

from app.pipeline.pdf_text import first_page_lines

logger = logging.getLogger(__name__)

# Se comparan sin mayúsculas ni tildes, y con o sin plural: "Autores", "Autor(es)".
AUTHOR_LABELS = ("autor", "estudiante", "integrante", "alumno", "alumna")
AUTHOR_PHRASES = ("elaborado por", "realizado por", "presentado por")
NEXT_LABELS = (
    "tema",
    "titulo",
    "asignatura",
    "materia",
    "docente",
    "profesor",
    "tutor",
    "curso",
    "paralelo",
    "fecha",
    "periodo",
    "carrera",
    "facultad",
)

_PLURAL = r"(?:es|s|\(es\)|\(s\)|\(a\)|\(as\))?"
# La etiqueta sola en su línea o con dos puntos. Sin ellos, una palabra suelta sería
# otra cosa ("Estudiante de la carrera..."); una frase como "elaborado por" no lo es.
AUTHOR_LABEL = re.compile(
    rf"^(?:(?:{'|'.join(AUTHOR_LABELS)}){_PLURAL}\s*(?::|$)"
    rf"|(?:{'|'.join(AUTHOR_PHRASES)})\s*:?)\s*",
)
# "Carrera" también es un apellido: como etiqueta va sola, con dos puntos o con "de".
NEXT_LABEL = re.compile(rf"^(?:{'|'.join(NEXT_LABELS)}){_PLURAL}\s*(?::|$|de\b)")
LIST_MARK = re.compile(r"^(?:\d+[.)]|[-•–])\s*")
# Títulos y signos que rodean al nombre en algunas plantillas: "Ing. Ana Vera", "[Ana Vera]".
PERSON_TITLE = re.compile(
    r"^(?:sr|sra|srta|ing|lic|eco|econ|dr|dra|msc|mgs|mgtr|abg|arq|tnlg)\.\s*", re.IGNORECASE
)
AROUND_NAME = " []().,;"
# Lo que no puede ser el nombre de una persona: la lista de autores ya terminó. Al pie
# de muchas portadas va el lugar: "Guayaquil - Ecuador", "MILAGRO-ECUADOR".
NOT_A_NAME = re.compile(r"[\d:@/]|\s[-–—]\s|\b(?:ecuador|universidad|escuela)\b", re.IGNORECASE)

MAX_WORDS_IN_NAME = 8
MAX_NAME_LENGTH = 120
MAX_AUTHORS = 20


def cover_authors(pdf_bytes: bytes) -> tuple[str, ...]:
    """Autores de la portada; vacío si no se reconocen o si el PDF no se puede leer."""
    try:
        lines = first_page_lines(pdf_bytes)
    except (pymupdf.FileDataError, pymupdf.EmptyFileError, RuntimeError, ValueError):
        logger.info("No se pudo leer la portada del PDF")
        return ()
    return authors_in(lines)


def authors_in(lines: list[str]) -> tuple[str, ...]:
    """Autores en las líneas de una portada, sin repetir y en el orden en que aparecen."""
    found: dict[str, None] = {}
    collecting = False
    for raw in lines:
        line = _visible(raw)
        comparable = _comparable(line)
        if NEXT_LABEL.match(comparable):
            collecting = False
            continue
        label = AUTHOR_LABEL.match(comparable)
        if label:
            collecting = True
            # El dato puede venir en la misma línea: "Autor: Ana Vera".
            line = _after_label(line, comparable, label.end())
            if not line:
                continue
        elif not collecting:
            continue
        name = _clean_name(line)
        if not _is_name(name):
            collecting = False
            continue
        found[name] = None
    return tuple(found)[:MAX_AUTHORS]


def _visible(text: str) -> str:
    """Sin caracteres invisibles: algunas portadas traen U+200B después de la etiqueta."""
    cleaned = "".join(char for char in text if unicodedata.category(char) != "Cf")
    return " ".join(cleaned.split())


def _comparable(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _after_label(line: str, comparable: str, end: int) -> str:
    """El resto de la línea original. Sin tildes, "é" puede ocupar otro largo, así que se
    mide desde el final de la línea."""
    return line[len(line) - (len(comparable) - end) :].strip() if end < len(comparable) else ""


def _clean_name(line: str) -> str:
    return PERSON_TITLE.sub("", LIST_MARK.sub("", line).strip(AROUND_NAME)).strip(AROUND_NAME)


def _is_name(text: str) -> bool:
    return (
        bool(text)
        and len(text) <= MAX_NAME_LENGTH
        and len(text.split()) <= MAX_WORDS_IN_NAME
        and not NOT_A_NAME.search(text)
    )
