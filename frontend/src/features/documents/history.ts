/*
 * Historial de trabajos (HU-07): traduce GET /analisis (HistoryPage del backend)
 * a los tipos de la pantalla y decide a dónde lleva cada trabajo.
 */
import { formatDate } from "@/shared/lib/format";
import type { PageSlice } from "@/shared/lib/pagination";
import type { AnalysisStatus, Work } from "./types";

type AnalysisItemDto = {
  analysis_id: string;
  file_name: string;
  created_at: string;
  status: string;
  progress: number;
  total_references: number | null;
  index: number | null;
};

export type HistoryDto = {
  items: AnalysisItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export function isHistoryDto(body: unknown): body is HistoryDto {
  return (
    typeof body === "object" &&
    body !== null &&
    "items" in body &&
    Array.isArray(body.items) &&
    "total_pages" in body
  );
}

function statusOf(status: string): AnalysisStatus {
  if (status === "completado") return "listo";
  return status === "error" ? "error" : "en_proceso";
}

export function toWork(item: AnalysisItemDto): Work {
  return {
    analysisId: item.analysis_id,
    fileName: item.file_name,
    date: formatDate(item.created_at),
    references: item.total_references ?? 0,
    index: item.index === null ? null : Math.round(item.index),
    status: statusOf(item.status),
    progress: item.progress,
  };
}

/** Página del historial con el rango mostrado, para el componente de paginación. */
export function toWorkPage(dto: HistoryDto): PageSlice<Work> {
  const first = dto.items.length > 0 ? (dto.page - 1) * dto.page_size + 1 : 0;
  return {
    items: dto.items.map(toWork),
    page: dto.page,
    totalPages: dto.total_pages,
    total: dto.total,
    first,
    last: first > 0 ? first + dto.items.length - 1 : 0,
  };
}

/**
 * Un trabajo terminado abre su informe y uno en proceso, su progreso (HU-07
 * CA03). Uno con error abre el informe, que explica el motivo.
 */
export function workHref(work: Work): string {
  return work.status === "en_proceso"
    ? `/estudiante/trabajos/${work.analysisId}/progreso`
    : `/estudiante/trabajos/${work.analysisId}`;
}
