import type { Verdict } from "@/shared/lib/verdicts";

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
  /** en_cola, extrayendo, segmentando, verificando, completado o error. */
  status: string;
  progress: number;
  references: number | null;
  index: number | null;
  alerts: number;
  /** null mientras se analiza o si no hay con qué calcularlo. */
  risk: RiskLevel | null;
  errorMessage: string | null;
};

/** Un campo y en cuántas referencias difiere del registro. */
export type FieldDifference = {
  field: string;
  references: number;
};

/** El tablero del lote (HU-09); los indicadores cuentan solo los trabajos terminados. */
export type BatchDetail = {
  id: string;
  name: string;
  period: string | null;
  totalWorks: number;
  finished: number;
  inProgress: number;
  failed: number;
  references: number;
  counts: Record<Verdict, number>;
  /** Referencias sin veredicto porque una fuente no respondió. */
  queryErrors: number;
  mostDifferentFields: FieldDifference[];
  works: BatchWork[];
};

/** Una referencia en el archivo exportado; los campos llegan como códigos de la base. */
export type ExportReference = {
  order: number;
  text: string;
  /** null: sin veredicto, porque una fuente no respondió. */
  verdict: string | null;
  differentFields: string[];
};

export type ExportWork = {
  fileName: string;
  authors: string[];
  status: string;
  errorMessage: string | null;
  references: ExportReference[];
};

/** Lo que necesita el CSV del lote (HU-10). */
export type BatchExport = {
  name: string;
  works: ExportWork[];
};

/** Estado de un archivo del lote, desde que se elige hasta que termina su análisis. */
export type UploadState =
  | { kind: "en_espera" }
  | { kind: "subiendo" }
  /**
   * No se analiza y no se reintenta (HU-08 CA02). El navegador rechaza lo que no es PDF
   * o supera el límite; la API (`byApi`), el PDF que no podría leerse o no tiene sección
   * de referencias.
   */
  | { kind: "rechazado"; reason: string; byApi?: boolean }
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
