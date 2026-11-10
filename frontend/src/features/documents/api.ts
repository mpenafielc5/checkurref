import { apiGet, wakeApi } from "@/shared/lib/api-client";
import type { PageSlice } from "@/shared/lib/pagination";
import { uploadPdf, type UploadOutcome } from "@/shared/lib/pdf-upload";
import { isHistoryDto, toWorkPage } from "./history";
import { isAnalysisItemDto, toAnalysisInfo, type AnalysisInfo } from "./progress";
import type { Work } from "./types";

/** Sube el PDF del estudiante (HU-04). La norma (APA o IEEE) la detecta el análisis. */
export function submitDocument(file: File, onSlow: () => void): Promise<UploadOutcome> {
  return uploadPdf("/analisis", file, onSlow);
}

export { wakeApi };

export type HistoryOutcome =
  { kind: "ready"; page: PageSlice<Work> } | { kind: "error"; message: string };

/** Una página del historial del estudiante (HU-07), con la búsqueda por nombre. */
export async function fetchHistory(
  page: number,
  search: string,
  onSlow: () => void,
): Promise<HistoryOutcome> {
  const params = new URLSearchParams({ pagina: String(page) });
  if (search) params.set("buscar", search);
  const response = await apiGet(`/analisis?${params.toString()}`, onSlow);
  if (response.kind === "response" && response.status === 200 && isHistoryDto(response.body)) {
    return { kind: "ready", page: toWorkPage(response.body) };
  }
  return {
    kind: "error",
    message:
      response.kind === "failed" && response.reason === "session"
        ? "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo."
        : "No se pudo cargar la lista de tus trabajos. Intenta de nuevo en unos minutos.",
  };
}

export type AnalysisOutcome =
  { kind: "ready"; analysis: AnalysisInfo } | { kind: "error"; message: string };

/** Estado actual de un análisis, para abrir la pantalla de progreso (HU-05). */
export async function fetchAnalysis(
  analysisId: string,
  onSlow: () => void,
): Promise<AnalysisOutcome> {
  const response = await apiGet(`/analisis/${encodeURIComponent(analysisId)}`, onSlow);
  if (response.kind === "failed") {
    return {
      kind: "error",
      message:
        response.reason === "session"
          ? "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo."
          : "No se pudo conectar con el motor de análisis. Revisa tu conexión e intenta de nuevo.",
    };
  }
  if (response.status === 200 && isAnalysisItemDto(response.body)) {
    return { kind: "ready", analysis: toAnalysisInfo(response.body) };
  }
  if (response.status === 404 || response.status === 422) {
    return {
      kind: "error",
      message: "No se encontró este análisis. Vuelve a la lista de tus trabajos.",
    };
  }
  return {
    kind: "error",
    message: "No se pudo consultar el análisis. Intenta de nuevo en unos minutos.",
  };
}
