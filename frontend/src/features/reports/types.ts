import type { Verdict } from "@/shared/lib/verdicts";

/** Campo extraído de una referencia; define su color en el texto original. */
export type ExtractedField = "authors" | "year" | "title" | "container";

export type ReferenceSegment = { text: string; field?: ExtractedField };

export type FieldComparison = {
  label: string;
  given: string;
  official: string;
  matches: boolean;
};

export type NliResult = {
  field: string;
  entailment: number;
  neutral: number;
  contradiction: number;
};

/**
 * Problema de escritura según la norma APA o IEEE (tabla hallazgos, tipo
 * "formato"): qué está mal, cómo aparece en el trabajo y cómo debería ir.
 */
export type FormatFinding = {
  message: string;
  given: string;
  expected: string;
};

export type ReferenceResult = {
  order: number;
  verdict: Verdict;
  page: number;
  formatFindings: FormatFinding[];
  segments: ReferenceSegment[];
  comparisons: FieldComparison[];
  nli: NliResult | null;
};

export type Report = {
  analysisId: string;
  fileName: string;
  standard: "APA" | "IEEE";
  index: number;
  counts: Record<Verdict, number>;
  references: ReferenceResult[];
};
