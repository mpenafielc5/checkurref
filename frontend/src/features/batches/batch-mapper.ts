/*
 * Lotes del docente (HU-08): traduce las respuestas de /lotes (BatchSummary,
 * BatchesPage y BatchDetail del backend) a los tipos de la pantalla.
 */
import type { PageSlice } from "@/shared/lib/pagination";
import type { BatchStatus, BatchSummary, WorkProgress } from "./types";

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
