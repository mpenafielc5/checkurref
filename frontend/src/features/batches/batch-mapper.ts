/*
 * Lotes del docente (HU-08 y HU-09): traduce las respuestas de /lotes (BatchSummary,
 * BatchesPage y BatchDetail del backend) a los tipos de la pantalla.
 */
import { displayFullName } from "@/shared/lib/names";
import type { PageSlice } from "@/shared/lib/pagination";
import { VERDICT_ORDER, type Verdict } from "@/shared/lib/verdicts";
import type {
  BatchDetail,
  BatchExport,
  BatchStatus,
  BatchSummary,
  BatchWork,
  RiskLevel,
  WorkProgress,
} from "./types";

export type BatchSummaryDto = {
  id: string;
  name: string;
  period: string | null;
  total_works: number;
  finished: number;
  in_progress: number;
  failed: number;
  high_risk: number;
};

type BatchesPageDto = {
  items: BatchSummaryDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

type WorkProgressDto = {
  analysis_id: string;
  status: string;
  progress: number;
  total_references: number | null;
  error_message: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isBatchSummaryDto(body: unknown): body is BatchSummaryDto {
  return isRecord(body) && typeof body.id === "string" && typeof body.name === "string";
}

export function isBatchesPageDto(body: unknown): body is BatchesPageDto {
  return isRecord(body) && Array.isArray(body.items) && typeof body.total_pages === "number";
}

function isWorkProgressDto(value: unknown): value is WorkProgressDto {
  return (
    isRecord(value) &&
    typeof value.analysis_id === "string" &&
    typeof value.status === "string" &&
    typeof value.progress === "number"
  );
}

function statusOf(dto: BatchSummaryDto): BatchStatus {
  if (dto.total_works === 0) return { kind: "empty" };
  if (dto.in_progress > 0) return { kind: "analyzing", done: dto.finished + dto.failed };
  if (dto.finished === 0) return { kind: "failed" };
  return { kind: "reviewed", highRisk: dto.high_risk };
}

export function toBatchSummary(dto: BatchSummaryDto): BatchSummary {
  return {
    id: dto.id,
    name: dto.name,
    works: dto.total_works,
    period: dto.period,
    failed: dto.failed,
    status: statusOf(dto),
  };
}

/** Página de lotes con el rango mostrado, para el componente de paginación. */
export function toBatchPage(dto: BatchesPageDto): PageSlice<BatchSummary> {
  const first = dto.items.length > 0 ? (dto.page - 1) * dto.page_size + 1 : 0;
  return {
    items: dto.items.map(toBatchSummary),
    page: dto.page,
    totalPages: dto.total_pages,
    total: dto.total,
    first,
    last: first > 0 ? first + dto.items.length - 1 : 0,
  };
}

/** Avance de los trabajos de un lote; null si la respuesta no es la esperada. */
export function toWorksProgress(body: unknown): WorkProgress[] | null {
  if (!isRecord(body) || !Array.isArray(body.works)) return null;
  return body.works.filter(isWorkProgressDto).map((work) => ({
    analysisId: work.analysis_id,
    status: work.status,
    progress: work.progress,
    totalReferences: work.total_references ?? null,
    errorMessage: work.error_message ?? null,
  }));
}

type BatchWorkDto = WorkProgressDto & {
  file_name: string;
  authors?: string[];
  index?: number | null;
  alerts?: number;
  risk?: string | null;
};

type BatchDetailDto = BatchSummaryDto & {
  references: number;
  counts: Partial<Record<Verdict | "error_consulta", number>>;
  most_different_fields: { field: string; references: number }[];
  works: unknown[];
};

const RISK_LEVELS: RiskLevel[] = ["alto", "medio", "bajo"];

function isBatchDetailDto(body: unknown): body is BatchDetailDto {
  return (
    isBatchSummaryDto(body) &&
    "works" in body &&
    Array.isArray(body.works) &&
    "counts" in body &&
    isRecord(body.counts) &&
    "most_different_fields" in body &&
    Array.isArray(body.most_different_fields)
  );
}

function isBatchWorkDto(value: unknown): value is BatchWorkDto {
  return isWorkProgressDto(value) && "file_name" in value && typeof value.file_name === "string";
}

function toBatchWork(dto: BatchWorkDto): BatchWork {
  return {
    analysisId: dto.analysis_id,
    fileName: dto.file_name,
    // La portada puede traer los nombres en mayúsculas: se muestran todos con el mismo formato.
    authors: (dto.authors ?? []).map(displayFullName),
    status: dto.status,
    progress: dto.progress,
    references: dto.total_references ?? null,
    index: dto.index ?? null,
    alerts: dto.alerts ?? 0,
    risk: RISK_LEVELS.find((level) => level === dto.risk) ?? null,
    errorMessage: dto.error_message ?? null,
  };
}

/** El tablero del lote; null si la respuesta no es la esperada. */
export function toBatchDetail(body: unknown): BatchDetail | null {
  if (!isBatchDetailDto(body)) return null;
  const counts: Record<Verdict, number> = {
    verificada: 0,
    discrepancia: 0,
    contradiccion: 0,
    sin_respaldo: 0,
    no_verificable: 0,
  };
  for (const verdict of VERDICT_ORDER) counts[verdict] = body.counts[verdict] ?? 0;
  return {
    id: body.id,
    name: body.name,
    period: body.period,
    totalWorks: body.total_works,
    finished: body.finished,
    inProgress: body.in_progress,
    failed: body.failed,
    references: body.references,
    counts,
    queryErrors: body.counts.error_consulta ?? 0,
    mostDifferentFields: body.most_different_fields,
    works: body.works.filter(isBatchWorkDto).map(toBatchWork),
  };
}

type ExportReferenceDto = {
  order: number;
  text: string;
  verdict: string | null;
  different_fields: string[];
};

type ExportWorkDto = {
  file_name: string;
  authors: string[];
  status: string;
  error_message: string | null;
  references: ExportReferenceDto[];
};

function isExportWorkDto(value: unknown): value is ExportWorkDto {
  return (
    isRecord(value) &&
    typeof value.file_name === "string" &&
    typeof value.status === "string" &&
    Array.isArray(value.authors) &&
    Array.isArray(value.references)
  );
}

/** Los datos del CSV; null si la respuesta no es la esperada: un archivo incompleto no sirve. */
export function toBatchExport(body: unknown): BatchExport | null {
  if (!isRecord(body) || typeof body.name !== "string" || !Array.isArray(body.works)) return null;
  if (!body.works.every(isExportWorkDto)) return null;
  return {
    name: body.name,
    works: body.works.map((work) => ({
      fileName: work.file_name,
      authors: work.authors.map(displayFullName),
      status: work.status,
      errorMessage: work.error_message ?? null,
      references: work.references.map((reference) => ({
        order: reference.order,
        text: reference.text,
        verdict: reference.verdict ?? null,
        differentFields: reference.different_fields,
      })),
    })),
  };
}
