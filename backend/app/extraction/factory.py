"""Elige el extractor de campos según la configuración."""

from app.extraction.anystyle import AnyStyleExtractor
from app.extraction.base import Engine, ReferenceExtractor
from app.extraction.spacy_rules import SpacyExtractor


def create_extractor(engine: Engine, anystyle_command: str = "anystyle") -> ReferenceExtractor:
    if engine is Engine.ANYSTYLE:
        return AnyStyleExtractor(command=anystyle_command)
    return SpacyExtractor()
