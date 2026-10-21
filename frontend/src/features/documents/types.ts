export type AnalysisStatus = "listo" | "en_proceso";

/** Una versión de un trabajo y el estado de su análisis. */
export type WorkVersion = {
  analysisId: string;
  fileName: string;
  version: number;
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
