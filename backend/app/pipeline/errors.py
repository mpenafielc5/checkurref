"""Errores de la etapa de extracción. Cada uno lleva un mensaje para el usuario."""


class PdfProcessingError(Exception):
    """Error que detiene el análisis del documento y se muestra tal cual al usuario."""

    message = "No se pudo procesar el PDF."

    def __init__(self) -> None:
        super().__init__(self.message)


class UnreadablePdfError(PdfProcessingError):
    message = "El archivo no es un PDF válido o está dañado."


class EncryptedPdfError(PdfProcessingError):
    message = "El PDF está protegido con contraseña. Súbelo sin protección."


class ScannedPdfError(PdfProcessingError):
    message = (
        "El PDF no tiene texto seleccionable (parece escaneado). "
        "Expórtalo desde Word o el editor original para que se pueda leer."
    )


class ReferencesNotFoundError(PdfProcessingError):
    message = (
        "No se encontró la sección de referencias. "
        "Revisa que tenga un título como Referencias o Bibliografía."
    )
