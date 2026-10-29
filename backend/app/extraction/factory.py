"""Elige el extractor de campos según la configuración."""

import logging
import shutil

from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import Engine, ReferenceExtractor
from app.extraction.spacy_rules import SpacyExtractor

logger = logging.getLogger(__name__)


def create_extractor(engine: Engine, anystyle_command: str = "anystyle") -> ReferenceExtractor:
    """El extractor pedido; si AnyStyle no está instalado, spaCy.

    Así el análisis funciona en una máquina sin Ruby. El motor que se usó de
    verdad queda en analisis.extractor_principal.
    """
    if engine is Engine.ANYSTYLE:
        if shutil.which(anystyle_command):
            return AnyStyleExtractor(command=anystyle_command)
        logger.warning("No se encontró %s (anystyle-cli): se usa spaCy", anystyle_command)
    return SpacyExtractor()
