export type EngineId = "anystyle" | "spacy";

export const ENGINE_NAMES: Record<EngineId, string> = {
  anystyle: "AnyStyle",
  spacy: "spaCy",
};

export type FieldScore = {
  field: string;
  precision: number;
  recall: number;
  f1: number;
};

export type EngineScores = {
  engine: EngineId;
  version: string | null;
  samples: number;
  keyF1: number;
  fields: FieldScore[];
};

export type BenchmarkRun = {
  executedAt: string;
  engines: EngineScores[];
  selectedEngine: EngineId;
  tie: boolean;
  /** En puntos de F1, de 0 a 1. */
  difference: number;
};

export type GoldSetSummary = {
  total: number;
  real: number;
  apa: number;
  ieee: number;
};

export type BenchmarkOverview = {
  goldSet: GoldSetSummary;
  /** De la más reciente a la más antigua. */
  runs: BenchmarkRun[];
  engineInUse: EngineId;
  keyFields: string[];
  tieMargin: number;
};

/** Nombre de cada motor en la comparación de una referencia (maqueta 17). */
export const ENGINE_LABELS: Record<EngineId, string> = {
  anystyle: "AnyStyle (CRF)",
  spacy: "spaCy + reglas",
};

export type EngineOutput = {
  engine: EngineId;
  elapsedMs: number;
  /** El motivo si el motor no pudo procesar la referencia. */
  error: string | null;
  /** Por código de campo; null si el motor no pudo procesarla. */
  fields: Record<string, string | null> | null;
};

export type LabComparison = {
  engines: EngineOutput[];
  /** Campos en los que los motores no coinciden. */
  differentFields: string[];
  comparedFields: number;
  matchingFields: number;
};
