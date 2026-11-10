import { apiGet, apiPost, wakeApi } from "@/shared/lib/api-client";
import type { PageSlice } from "@/shared/lib/pagination";
import { detailOf, uploadPdf, type UploadOutcome } from "@/shared/lib/pdf-upload";
import {
  isBatchesPageDto,
  isBatchSummaryDto,
  toBatchDetail,
  toBatchExport,
  toBatchPage,
  toWorksProgress,
} from "./batch-mapper";
import type { BatchDetail, BatchExport, BatchSummary, CreatedBatch, WorkProgress } from "./types";

export { wakeApi };

const SESSION_ERROR = "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo.";
const NETWORK_ERROR =
  "No se pudo conectar con el motor de análisis. Revisa tu conexión e intenta de nuevo.";

export type CreateBatchOutcome =
  { kind: "created"; batch: CreatedBatch } | { kind: "error"; message: string };

/** Crea el lote (HU-08 CA01). Los archivos se envían después, uno por uno. */
export async function createBatch(
  name: string,
  period: string,
  onSlow: () => void,
): Promise<CreateBatchOutcome> {
  const response = await apiPost("/lotes", { name, period }, onSlow);
  if (response.kind === "failed") {
    return {
      kind: "error",
      message: response.reason === "session" ? SESSION_ERROR : NETWORK_ERROR,
    };
  }
  if (response.status === 201 && isBatchSummaryDto(response.body)) {
    const { id, name: savedName, period: savedPeriod } = response.body;
    return { kind: "created", batch: { id, name: savedName, period: savedPeriod } };
  }
  return {
    kind: "error",
    message:
      detailOf(response.body) ?? "No se pudo crear el lote. Intenta de nuevo en unos minutos.",
  };
}

/** Sube un PDF al lote, con la misma función que la subida del estudiante (HU-08 CA04). */
export function submitBatchWork(
  batchId: string,
  file: File,
  onSlow: () => void,
): Promise<UploadOutcome> {
  return uploadPdf(`/lotes/${encodeURIComponent(batchId)}/trabajos`, file, onSlow);
}

export type BatchesOutcome =
  { kind: "ready"; page: PageSlice<BatchSummary> } | { kind: "error"; message: string };

/** Una página de los lotes del docente, del más reciente al más antiguo. */
export async function fetchBatches(page: number, onSlow: () => void): Promise<BatchesOutcome> {
  const response = await apiGet(`/lotes?pagina=${page}`, onSlow);
  if (response.kind === "response" && response.status === 200 && isBatchesPageDto(response.body)) {
    return { kind: "ready", page: toBatchPage(response.body) };
  }
  return {
    kind: "error",
    message:
      response.kind === "failed" && response.reason === "session"
        ? SESSION_ERROR
        : "No se pudo cargar la lista de lotes. Intenta de nuevo en unos minutos.",
  };
}

export type BatchDetailOutcome =
  { kind: "ready"; batch: BatchDetail } | { kind: "error"; message: string };

const BATCH_LOAD_ERROR = "No se pudo cargar el lote. Intenta de nuevo en unos minutos.";

/** El tablero del lote. Uno ajeno responde igual que uno inexistente. */
export async function fetchBatchDetail(
  batchId: string,
  onSlow?: () => void,
): Promise<BatchDetailOutcome> {
  const response = await apiGet(`/lotes/${encodeURIComponent(batchId)}`, onSlow);
  if (response.kind === "failed") {
    return {
      kind: "error",
      message: response.reason === "session" ? SESSION_ERROR : BATCH_LOAD_ERROR,
    };
  }
  // 422: la dirección no contiene un identificador válido.
  if (response.status === 404 || response.status === 422) {
    return { kind: "error", message: "No se encontró este lote." };
  }
  const batch = response.status === 200 ? toBatchDetail(response.body) : null;
  return batch ? { kind: "ready", batch } : { kind: "error", message: BATCH_LOAD_ERROR };
}

export type BatchExportOutcome =
  { kind: "ready"; batch: BatchExport } | { kind: "error"; message: string };

const EXPORT_ERROR = "No se pudo preparar el archivo. Intenta de nuevo en unos minutos.";

/** Los resultados de cada referencia del lote, para el archivo CSV (HU-10). */
export async function fetchBatchExport(batchId: string): Promise<BatchExportOutcome> {
  const response = await apiGet(`/lotes/${encodeURIComponent(batchId)}/exportacion`);
  if (response.kind === "failed") {
    return {
      kind: "error",
      message: response.reason === "session" ? SESSION_ERROR : EXPORT_ERROR,
    };
  }
  const batch = response.status === 200 ? toBatchExport(response.body) : null;
  return batch ? { kind: "ready", batch } : { kind: "error", message: EXPORT_ERROR };
}

/** Avance de los trabajos del lote; null si no se pudo consultar: se reintenta luego. */
export async function fetchBatchProgress(batchId: string): Promise<WorkProgress[] | null> {
  const response = await apiGet(`/lotes/${encodeURIComponent(batchId)}`);
  return response.kind === "response" && response.status === 200
    ? toWorksProgress(response.body)
    : null;
}
