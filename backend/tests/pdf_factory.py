"""PDF sintéticos para las pruebas: no se suben PDF de terceros al repositorio."""

from dataclasses import dataclass, field

import pymupdf

LEFT_MARGIN = 72.0
LINE_HEIGHT = 16.0
TOP = 90.0
HEADER_Y = 40.0
FOOTER_Y = 770.0


@dataclass
class PageSpec:
    """Líneas del cuerpo de una página; cada una es texto o (sangría, texto)."""

    lines: list[str | tuple[float, str]] = field(default_factory=list)


def make_pdf(
    pages: list[PageSpec],
    header: str | None = None,
    page_numbers: bool = False,
) -> bytes:
    document = pymupdf.open()
    for number, spec in enumerate(pages, start=1):
        page = document.new_page()
        if header:
            page.insert_text((LEFT_MARGIN, HEADER_Y), header, fontsize=9)
        y = TOP
        for item in spec.lines:
            indent, text = item if isinstance(item, tuple) else (0.0, item)
            page.insert_text((LEFT_MARGIN + indent, y), text, fontsize=11)
            y += LINE_HEIGHT
        if page_numbers:
            page.insert_text((300, FOOTER_Y), f"Página {number} de {len(pages)}", fontsize=9)
    return document.tobytes()


def make_scanned_pdf() -> bytes:
    """PDF con solo una imagen, como el de un documento escaneado."""
    document = pymupdf.open()
    page = document.new_page()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 60), False)
    pixmap.clear_with(200)
    page.insert_image(pymupdf.Rect(72, 72, 500, 700), pixmap=pixmap)
    return document.tobytes()


def make_encrypted_pdf() -> bytes:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Documento protegido " * 5)
    return document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="clave", owner_pw="dueno"
    )
