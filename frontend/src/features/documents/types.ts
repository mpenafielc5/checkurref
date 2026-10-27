export type AnalysisStatus = "listo" | "en_proceso";

/**
 * Un trabajo subido y el estado de su análisis. Cada archivo es un trabajo
 * independiente: no hay versiones, aunque el nombre coincida.
 */
export type Work = {
  analysisId: string;
  fileName: string;
  date: string;
  references: number;
  /** Índice de veracidad de 0 a 100; null mientras se analiza. */
  index: number | null;
  status: AnalysisStatus;
  /** Referencias verificadas hasta ahora, si el análisis sigue en curso. */
  verified?: number;
};

export type ProgressStepState = "done" | "current" | "pending";

export type ProgressStep = {
  title: string;
  detail: string;
  state: ProgressStepState;
};
