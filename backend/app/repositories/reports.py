"""Lectura de los análisis y sus resultados para el informe y el historial (PostgREST).

El backend lee con la clave de servicio, que ignora RLS: quién puede ver cada
análisis lo decide el servicio del informe, que compara el propietario.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import TypeAdapter

from app.extraction.base import Author, ExtractedFields
from app.repositories.supabase_http import get_counted, send

ANALYSIS_COLUMNS = (
    "id,documento_id,estado,progreso,creado_en,finalizado_en,duracion_ms,norma_detectada,"
    "extractor_principal,total_referencias,indice_veracidad,mensaje_error"
)
EXTRACTION_COLUMNS = "motor,autores,anio,titulo,contenedor,editorial,volumen,numero,paginas,doi"
VERIFICATION_COLUMNS = (
    "veredicto,estrategia,crossref_doi,sim_titulo,sim_autores,coincide_anio,referencia_corregida,"
    "inferencias_nli(campo,p_implicacion,p_neutral,p_contradiccion)"
)
FINDING_COLUMNS = "tipo,codigo,severidad,campo,valor_dado,valor_oficial,mensaje"

# Comodines que el usuario no puede usar al buscar (* de PostgREST, % de SQL). El
# _ se deja: los nombres de archivo lo usan y como comodín también se coincide a sí mismo.
SEARCH_WILDCARDS = re.compile(r"[*%]")

# Postgres envía las fechas en ISO 8601 con 1 a 6 decimales; fromisoformat de
# Python 3.10 solo acepta 3 o 6.
DATETIME = TypeAdapter(datetime)


@dataclass(frozen=True)
class AnalysisRecord:
    analysis_id: UUID
    document_id: UUID
    owner_id: UUID
    file_name: str
    status: str
    progress: int
    created_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    norm: str | None
    engine: str
    total_references: int | None
    index: float | None
    error_message: str | None


@dataclass(frozen=True)
class StoredInference:
    field: str
    entailment: float
    neutral: float
    contradiction: float


@dataclass(frozen=True)
class StoredVerification:
    verdict: str
    strategy: str
    doi: str | None
    title_similarity: float | None
    author_similarity: float | None
    year_matches: bool | None
    corrected: list[dict[str, Any]] | None  # verificaciones.referencia_corregida
    inferences: tuple[StoredInference, ...] = ()


@dataclass(frozen=True)
class StoredFinding:
    kind: str  # formato o veracidad
    code: str
    severity: str
    message: str
    field: str | None = None
    given: str | None = None
    official: str | None = None


@dataclass(frozen=True)
class StoredReference:
    order: int
    page: int | None
    norm: str | None
    text: str
    fields: ExtractedFields | None  # None si el extractor no pudo con ella
    verification: StoredVerification | None  # None: error de consulta o interno
    findings: tuple[StoredFinding, ...] = ()


@dataclass(frozen=True)
class AnalysisPage:
    items: list[AnalysisRecord]
    total: int


class ReportRepository(Protocol):
    def get_analysis(self, analysis_id: UUID) -> AnalysisRecord | None: ...

    def references(self, analysis_id: UUID, engine: str) -> list[StoredReference]:
        """Referencias en orden, con la extracción del motor indicado."""
        ...

    def list_analyses(
        self, owner_id: UUID, offset: int, limit: int, search: str = ""
    ) -> AnalysisPage:
        """Análisis de los trabajos individuales del usuario, del más reciente al más
        antiguo; con `search`, solo los archivos cuyo nombre lo contiene."""
        ...


class SupabaseReportRepository:
    def __init__(self, rest_url: str, client: httpx.Client) -> None:
        self._rest_url = rest_url
        self._client = client

    def get_analysis(self, analysis_id: UUID) -> AnalysisRecord | None:
        rows = send(
            self._client,
            "GET",
            f"{self._rest_url}/analisis",
            params={
                "select": f"{ANALYSIS_COLUMNS},documentos(propietario_id,nombre_archivo)",
                "id": f"eq.{analysis_id}",
            },
        )
        return _analysis(rows[0]) if rows else None

    def references(self, analysis_id: UUID, engine: str) -> list[StoredReference]:
        rows = send(
            self._client,
            "GET",
            f"{self._rest_url}/referencias",
            params={
                "select": (
                    f"orden,pagina,norma,texto_crudo,extracciones({EXTRACTION_COLUMNS}),"
                    f"verificaciones({VERIFICATION_COLUMNS}),hallazgos({FINDING_COLUMNS})"
                ),
                "analisis_id": f"eq.{analysis_id}",
                "extracciones.motor": f"eq.{engine}",
                "order": "orden.asc",
            },
        )
        return [_reference(row) for row in rows]

    def list_analyses(
        self, owner_id: UUID, offset: int, limit: int, search: str = ""
    ) -> AnalysisPage:
        # Los trabajos de un lote (HU-08) se consultan desde el lote, no desde el historial.
        params = {
            "select": f"{ANALYSIS_COLUMNS},documentos!inner(propietario_id,nombre_archivo,lote_id)",
            "documentos.propietario_id": f"eq.{owner_id}",
            "documentos.lote_id": "is.null",
            "order": "creado_en.desc",
            "offset": str(offset),
            "limit": str(limit),
        }
        if pattern := SEARCH_WILDCARDS.sub("", search).strip():
            params["documentos.nombre_archivo"] = f"ilike.*{pattern}*"
        rows, total = get_counted(self._client, f"{self._rest_url}/analisis", params)
        return AnalysisPage([_analysis(row) for row in rows], total)


def _analysis(row: dict[str, Any]) -> AnalysisRecord:
    document = row["documentos"]
    return AnalysisRecord(
        analysis_id=UUID(row["id"]),
        document_id=UUID(row["documento_id"]),
        owner_id=UUID(document["propietario_id"]),
        file_name=document["nombre_archivo"],
        status=row["estado"],
        progress=row["progreso"],
        created_at=DATETIME.validate_python(row["creado_en"]),
        finished_at=_datetime(row.get("finalizado_en")),
        duration_ms=row.get("duracion_ms"),
        norm=row.get("norma_detectada"),
        engine=row["extractor_principal"],
        total_references=row.get("total_referencias"),
        index=_number(row.get("indice_veracidad")),
        error_message=row.get("mensaje_error"),
    )


def _reference(row: dict[str, Any]) -> StoredReference:
    extractions = row.get("extracciones") or []
    return StoredReference(
        order=row["orden"],
        page=row.get("pagina"),
        norm=row.get("norma"),
        text=row["texto_crudo"],
        fields=_fields(extractions[0]) if extractions else None,
        verification=_verification(_one(row.get("verificaciones"))),
        findings=tuple(_finding(item) for item in row.get("hallazgos") or []),
    )


def _fields(row: dict[str, Any]) -> ExtractedFields | None:
    # Una extracción sin ningún campo es la de una referencia con la que el motor falló.
    if not any(row.get(column) for column in ("autores", "anio", "titulo", "doi")):
        return None
    return ExtractedFields(
        authors=tuple(
            Author(a.get("family", ""), a.get("given", "")) for a in row["autores"] or []
        ),
        year=row.get("anio"),
        title=row.get("titulo"),
        container=row.get("contenedor"),
        publisher=row.get("editorial"),
        volume=row.get("volumen"),
        issue=row.get("numero"),
        pages=row.get("paginas"),
        doi=row.get("doi"),
    )


def _verification(row: dict[str, Any] | None) -> StoredVerification | None:
    if row is None:
        return None
    return StoredVerification(
        verdict=row["veredicto"],
        strategy=row["estrategia"],
        doi=row.get("crossref_doi"),
        title_similarity=_number(row.get("sim_titulo")),
        author_similarity=_number(row.get("sim_autores")),
        year_matches=row.get("coincide_anio"),
        corrected=row.get("referencia_corregida"),
        inferences=tuple(
            StoredInference(
                field=item["campo"],
                entailment=float(item["p_implicacion"]),
                neutral=float(item["p_neutral"]),
                contradiction=float(item["p_contradiccion"]),
            )
            for item in row.get("inferencias_nli") or []
        ),
    )


def _finding(row: dict[str, Any]) -> StoredFinding:
    return StoredFinding(
        kind=row["tipo"],
        code=row["codigo"],
        severity=row["severidad"],
        message=row["mensaje"],
        field=row.get("campo"),
        given=row.get("valor_dado"),
        official=row.get("valor_oficial"),
    )


def _one(value: Any) -> dict[str, Any] | None:
    """verificaciones es uno a uno: PostgREST lo devuelve como objeto (o como lista)."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None


def _datetime(value: str | None) -> datetime | None:
    return DATETIME.validate_python(value) if value else None
