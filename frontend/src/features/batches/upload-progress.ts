/*
 * Avance de los archivos de un lote (HU-08 CA03). Cada archivo tiene su propio
 * estado: el error de uno no detiene a los demás.
 */
import type { RejectedPdf } from "@/shared/components/pdf-dropzone";
import type { UploadOutcome } from "@/shared/lib/pdf-upload";
import type { BatchUpload, UploadState, WorkProgress } from "./types";

export const ANALYSIS_FAILED = "El análisis no pudo completarse.";

function keyOf(file: File, position: number): string {
  return `${position}·${file.name}·${file.size}`;
}

/** Lista inicial: primero los archivos por enviar y, al final, los rechazados con su motivo. */
export function initialUploads(files: File[], rejected: RejectedPdf[]): BatchUpload[] {
  const waiting: BatchUpload[] = files.map((file, position) => ({
    key: keyOf(file, position),
    file,
    state: { kind: "en_espera" },
  }));
  const invalid: BatchUpload[] = rejected.map(({ file, reason }, position) => ({
    key: keyOf(file, files.length + position),
    file,
    state: { kind: "rechazado", reason },
  }));
  return [...waiting, ...invalid];
}

/**
 * Estado de un archivo según la respuesta de la API a su subida. Un archivo que la
 * API rechaza tras revisarlo queda como los inválidos del navegador: sin reintento.
 */
export function stateAfterUpload(outcome: UploadOutcome): UploadState {
  if (outcome.kind === "error") {
    return outcome.rejected
      ? { kind: "rechazado", reason: outcome.message, byApi: true }
      : { kind: "fallo_subida", reason: outcome.message };
  }
  if (outcome.kind === "duplicate") return { kind: "repetido" };
  return {
    kind: "en_analisis",
    analysisId: outcome.analysisId,
    status: "en_cola",
    progress: 0,
    totalReferences: null,
  };
}

function stateFromWork(work: WorkProgress): UploadState {
  if (work.status === "completado") return { kind: "listo" };
  if (work.status === "error") {
    return { kind: "error_analisis", reason: work.errorMessage ?? ANALYSIS_FAILED };
  }
  return {
    kind: "en_analisis",
    analysisId: work.analysisId,
    status: work.status,
    progress: work.progress,
    totalReferences: work.totalReferences,
  };
}

/** Aplica el avance consultado a los archivos en análisis; los demás no cambian. */
export function applyWorksProgress(uploads: BatchUpload[], works: WorkProgress[]): BatchUpload[] {
  const byAnalysis = new Map(works.map((work) => [work.analysisId, work]));
  return uploads.map((upload) => {
    if (upload.state.kind !== "en_analisis") return upload;
    const work = byAnalysis.get(upload.state.analysisId);
    return work ? { ...upload, state: stateFromWork(work) } : upload;
  });
}

export function isAnalyzing(uploads: BatchUpload[]): boolean {
  return uploads.some((upload) => upload.state.kind === "en_analisis");
}

/**
 * Todos los archivos llegaron a la API sin nada que explicar: no hay rechazados,
 * fallidos ni repetidos. Entonces el avance se sigue mejor en el tablero del lote.
 */
export function allSentCleanly(uploads: BatchUpload[]): boolean {
  return (
    uploads.length > 0 &&
    uploads.every((upload) => upload.state.kind === "en_analisis" || upload.state.kind === "listo")
  );
}

export function analyzedCount(uploads: BatchUpload[]): number {
  return uploads.filter((upload) => upload.state.kind === "listo").length;
}

/** Los archivos que no llegaron a la API por un fallo de la subida. */
export function failedUploads(uploads: BatchUpload[]): BatchUpload[] {
  return uploads.filter((upload) => upload.state.kind === "fallo_subida");
}

/** Cuántos archivos llegaron a su turno de envío: para "Enviando 3 de 12". */
export function sendProgress(uploads: BatchUpload[]): { current: number; total: number } {
  // Los que rechazó el navegador nunca se envían; los que rechazó la API sí tuvieron su turno.
  const toSend = uploads.filter(
    (upload) => upload.state.kind !== "rechazado" || upload.state.byApi === true,
  );
  const waiting = toSend.filter((upload) => upload.state.kind === "en_espera").length;
  return { current: toSend.length - waiting, total: toSend.length };
}
