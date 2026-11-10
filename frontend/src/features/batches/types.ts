export type BatchStatus =
  | { kind: "empty" }
  | { kind: "analyzing"; done: number }
  /** Terminó y ningún trabajo se pudo analizar: no hay riesgo que informar. */
  | { kind: "failed" }
  | { kind: "reviewed"; highRisk: number };

export type BatchSummary = {
  id: string;
  name: string;
  works: number;
  period: string | null;
  /** Trabajos cuyo análisis terminó con error. */
  failed: number;
  status: BatchStatus;
};

export type RiskLevel = "alto" | "medio" | "bajo";

/**
 * Un trabajo del lote. Se identifica por los autores leídos de la portada; si
 * la portada no se reconoce, la lista queda vacía y se usa el nombre del archivo.
 */
export type BatchWork = {
  analysisId: string;
  fileName: string;
  authors: string[];
  references: number;
  index: number;
  alerts: number;
  risk: RiskLevel;
};

/** Estado de un archivo del lote, desde que se elige hasta que termina su análisis. */
export type UploadState =
  | { kind: "en_espera" }
  | { kind: "subiendo" }
  /** No es PDF o supera el límite: nunca se envía (HU-08 CA02). */
  | { kind: "rechazado"; reason: string }
  /** La subida falló, por ejemplo sin conexión: se puede reintentar. */
  | { kind: "fallo_subida"; reason: string }
  /** El mismo PDF ya estaba en el lote: no se analiza de nuevo. */
  | { kind: "repetido" }
  | {
      kind: "en_analisis";
      analysisId: string;
      status: string;
      progress: number;
      totalReferences: number | null;
    }
  | { kind: "listo" }
  | { kind: "error_analisis"; reason: string };

export type BatchUpload = {
  key: string;
  file: File;
  state: UploadState;
};

/** El lote recién creado, para mostrarlo sobre el avance de sus archivos. */
export type CreatedBatch = {
  id: string;
  name: string;
  period: string | null;
};

/** Avance de un análisis del lote, según GET /lotes/{id}. */
export type WorkProgress = {
  analysisId: string;
  status: string;
  progress: number;
  totalReferences: number | null;
  errorMessage: string | null;
};
