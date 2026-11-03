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

/** Parte de la referencia corregida (HU-19); `changed` marca lo que se resalta. */
export type CorrectedSegment = { text: string; italic: boolean; changed: boolean };

/** Referencia corregida en APA 7 o IEEE con los datos del registro. */
export type CorrectedReference = {
  /** Texto plano que se copia al portapapeles. */
  text: string;
  segments: CorrectedSegment[];
};

export type ReferenceResult = {
  order: number;
  /** null: no se pudo verificar (una fuente no respondió); no cuenta en el índice. */
  verdict: Verdict | null;
  /** Página del PDF donde está la referencia; null si no se conoce. */
  page: number | null;
  formatFindings: FormatFinding[];
  segments: ReferenceSegment[];
  comparisons: FieldComparison[];
  nli: NliResult | null;
  /** Aviso del sistema sobre la referencia: por qué no se verificó o a qué obra lleva su DOI. */
  notice: string | null;
  corrected: CorrectedReference | null;
};

export type Report = {
  analysisId: string;
  fileName: string;
  /** Norma detectada, como se muestra: "APA", "IEEE", "APA e IEEE" o "Norma no identificada". */
  standard: string;
  /** Índice de veracidad de 0 a 100; null si ninguna referencia se pudo contar. */
  index: number | null;
  counts: Record<Verdict, number>;
  /** Referencias sin veredicto por un error de consulta. */
  queryErrors: number;
  references: ReferenceResult[];
};
