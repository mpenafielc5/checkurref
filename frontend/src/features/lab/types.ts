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
