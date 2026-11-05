"""Casos de uso: consultar el historial (CU-05), el estado de un análisis y su
informe de verificación (CU-04).

Cada usuario ve solo sus análisis. Uno ajeno responde igual que uno inexistente,
para no revelar que existe. El acceso del docente a los trabajos de sus lotes
llega con HU-08.
"""

import math
from collections import Counter
from uuid import UUID

from app.reports.highlight import highlight
from app.repositories.reports import (
    AnalysisRecord,
    ReportRepository,
    StoredFinding,
    StoredReference,
    StoredVerification,
)
from app.schemas.report import (
    AnalysisItem,
    CorrectedReference,
    CorrectedSegment,
    FieldComparison,
    FieldDifference,
    Finding,
    HistoryPage,
    NliResult,
    ReferenceReport,
    ReportResponse,
    TextSegment,
    VerdictCounts,
)
from app.verification.decision import CheckedField
from app.verification.findings import MISMATCH_CODES

HISTORY_PAGE_SIZE = 20  # HU-07 CA02
COMPLETED = "completado"

# Orden de los campos en la tabla de comparación del informe.
FIELD_ORDER = [
    CheckedField.TITLE,
    CheckedField.AUTHORS,
    CheckedField.YEAR,
    CheckedField.DOI,
    CheckedField.CONTAINER,
    CheckedField.VOLUME,
    CheckedField.PAGES,
]


class AnalysisNotFoundError(Exception):
    """El análisis no existe o no es del usuario."""


class AnalysisNotFinishedError(Exception):
    """El análisis sigue en curso o terminó con error: todavía no hay informe."""

    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.status = status


class ReportService:
    def __init__(self, reports: ReportRepository) -> None:
        self._reports = reports

    def history(self, owner_id: UUID, page: int, search: str = "") -> HistoryPage:
        page = max(page, 1)
        result = self._reports.list_analyses(
            owner_id, (page - 1) * HISTORY_PAGE_SIZE, HISTORY_PAGE_SIZE, search
        )
        return HistoryPage(
            items=[_item(analysis) for analysis in result.items],
            page=page,
            page_size=HISTORY_PAGE_SIZE,
            total=result.total,
            total_pages=max(1, math.ceil(result.total / HISTORY_PAGE_SIZE)),
        )

    def status(self, owner_id: UUID, analysis_id: UUID) -> AnalysisItem:
        return _item(self._owned(owner_id, analysis_id))

    def report(self, owner_id: UUID, analysis_id: UUID) -> ReportResponse:
        analysis = self._owned(owner_id, analysis_id)
        if analysis.status != COMPLETED:
            raise AnalysisNotFinishedError(analysis.status)
        references = [
            _reference(item)
            for item in self._reports.references(analysis.analysis_id, analysis.engine)
        ]
        return ReportResponse(
            analysis_id=analysis.analysis_id,
            document_id=analysis.document_id,
            file_name=analysis.file_name,
            created_at=analysis.created_at,
            finished_at=analysis.finished_at,
            duration_ms=analysis.duration_ms,
            norm=analysis.norm,
            engine=analysis.engine,
            total_references=len(references),
            index=analysis.index,
            counts=_counts(references),
            most_different_fields=_most_different(references),
            references=references,
        )

    def _owned(self, owner_id: UUID, analysis_id: UUID) -> AnalysisRecord:
        analysis = self._reports.get_analysis(analysis_id)
        if analysis is None or analysis.owner_id != owner_id:
            raise AnalysisNotFoundError(str(analysis_id))
        return analysis


def _item(analysis: AnalysisRecord) -> AnalysisItem:
    return AnalysisItem(
        analysis_id=analysis.analysis_id,
        document_id=analysis.document_id,
        file_name=analysis.file_name,
        created_at=analysis.created_at,
        status=analysis.status,
        progress=analysis.progress,
        total_references=analysis.total_references,
        norm=analysis.norm,
        index=analysis.index,
        error_message=analysis.error_message,
    )


def _reference(stored: StoredReference) -> ReferenceReport:
    verification = stored.verification
    veracity = [f for f in stored.findings if f.kind == "veracidad"]
    return ReferenceReport(
        order=stored.order,
        page=stored.page,
        norm=stored.norm,
        text=stored.text,
        segments=[
            TextSegment(text=s.text, field=s.field.value if s.field else None)
            for s in highlight(stored.text, stored.fields)
        ],
        verdict=verification.verdict if verification else None,
        strategy=verification.strategy if verification else None,
        comparisons=_comparisons(stored, verification, veracity),
        nli=[
            NliResult(
                field=item.field,
                entailment=item.entailment,
                neutral=item.neutral,
                contradiction=item.contradiction,
            )
            for item in (verification.inferences if verification else ())
        ],
        veracity_findings=[_finding(f) for f in veracity],
        format_findings=[_finding(f) for f in stored.findings if f.kind == "formato"],
        corrected=_corrected(verification),
    )


def _comparisons(
    stored: StoredReference,
    verification: StoredVerification | None,
    veracity: list[StoredFinding],
) -> list[FieldComparison]:
    """Cada campo comparado con el registro. Los que difieren traen el valor oficial
    de su hallazgo; los que coinciden muestran el valor citado en ambos lados."""
    if verification is None or stored.fields is None:
        return []
    fields = stored.fields
    mismatches = {f.field: f for f in veracity if f.code in MISMATCH_CODES and f.field}
    compared: dict[str, tuple[str, float | None]] = {}
    if verification.title_similarity is not None and fields.title:
        compared[CheckedField.TITLE.value] = (fields.title, verification.title_similarity)
    if verification.author_similarity is not None and fields.authors:
        authors = "; ".join(author.family for author in fields.authors if author.family)
        compared[CheckedField.AUTHORS.value] = (authors, verification.author_similarity)
    if verification.year_matches is not None and fields.year:
        compared[CheckedField.YEAR.value] = (str(fields.year), None)
    for field, finding in mismatches.items():
        if field not in compared:
            compared[field] = (finding.given or "", None)

    order = {field.value: position for position, field in enumerate(FIELD_ORDER)}
    return [
        FieldComparison(
            field=field,
            given=given,
            official=mismatches[field].official if field in mismatches else given,
            matches=field not in mismatches,
            similarity=similarity,
        )
        for field, (given, similarity) in sorted(
            compared.items(), key=lambda item: order.get(item[0], len(order))
        )
    ]


def _finding(finding: StoredFinding) -> Finding:
    return Finding(
        code=finding.code,
        severity=finding.severity,
        message=finding.message,
        field=finding.field,
        given=finding.given,
        official=finding.official,
    )


def _corrected(verification: StoredVerification | None) -> CorrectedReference | None:
    if verification is None or not verification.corrected:
        return None
    segments = [
        CorrectedSegment(
            text=item["texto"],
            field=item.get("campo"),
            italic=bool(item.get("cursiva")),
            changed=bool(item.get("cambiado")),
        )
        for item in verification.corrected
    ]
    changed = [s.field for s in segments if s.changed and s.field]
    return CorrectedReference(
        text="".join(segment.text for segment in segments),
        changed_fields=list(dict.fromkeys(changed)),
        segments=segments,
    )


def _counts(references: list[ReferenceReport]) -> VerdictCounts:
    tally = Counter(reference.verdict or "error_consulta" for reference in references)
    return VerdictCounts(**tally)


def _most_different(references: list[ReferenceReport]) -> list[FieldDifference]:
    tally = Counter(
        comparison.field
        for reference in references
        for comparison in reference.comparisons
        if not comparison.matches
    )
    return [
        FieldDifference(field=field, references=count)
        for field, count in sorted(tally.items(), key=lambda item: (-item[1], item[0]))
    ]
