/*
 * Traduce el informe de la API (GET /analisis/{id}/informe, ReportResponse del
 * backend) a los tipos de la pantalla. La API manda los campos como códigos de
 * la base (titulo, anio…); los nombres que ve el usuario se ponen aquí.
 */
import { standardLabel } from "@/shared/lib/standards";
import { VERDICT_ORDER, type Verdict } from "@/shared/lib/verdicts";
import type { ExtractedField, FieldComparison, NliResult, ReferenceResult, Report } from "./types";

type FindingDto = {
  code: string;
  severity: string;
  message: string;
  field: string | null;
  given: string | null;
  official: string | null;
};

type ReferenceDto = {
  order: number;
  page: number | null;
  norm: string | null;
  text: string;
  segments: { text: string; field: string | null }[];
  verdict: string | null;
  comparisons: {
    field: string;
    given: string;
    official: string | null;
    matches: boolean;
  }[];
  nli: { field: string; entailment: number; neutral: number; contradiction: number }[];
  veracity_findings: FindingDto[];
  format_findings: FindingDto[];
  corrected: {
    text: string;
    segments: { text: string; italic: boolean; changed: boolean }[];
  } | null;
};

export type ReportDto = {
  analysis_id: string;
  file_name: string;
  norm: string | null;
  index: number | null;
  counts: Record<Verdict | "error_consulta", number>;
  references: ReferenceDto[];
};

/** Comprobación mínima de la forma de la respuesta antes de usarla. */
export function isReportDto(body: unknown): body is ReportDto {
  return (
    typeof body === "object" &&
    body !== null &&
    "analysis_id" in body &&
    "references" in body &&
    Array.isArray(body.references) &&
    "counts" in body &&
    typeof body.counts === "object"
  );
}

const SEGMENT_FIELDS: Record<string, ExtractedField> = {
  titulo: "title",
  autores: "authors",
  anio: "year",
  contenedor: "container",
};

const FIELD_LABELS: Record<string, string> = {
  titulo: "Título",
  autores: "Autores",
  anio: "Año",
  doi: "DOI",
  contenedor: "Revista o libro",
  volumen: "Volumen",
  paginas: "Páginas",
  numero: "Número",
  editorial: "Editorial",
};

const UNKNOWN_STANDARD_NOTICE =
  "No se identificó si la lista de referencias sigue APA o IEEE, por lo que no se revisó su formato. La verificación de los datos de cada referencia no se ve afectada.";

/** El NLI del título es el más informativo: con autores, las iniciales lo confunden. */
const NLI_FIELD = "titulo";

function isVerdict(value: string | null): value is Verdict {
  return VERDICT_ORDER.some((verdict) => verdict === value);
}

function percent(probability: number): number {
  return Math.round(probability * 100);
}

function nliOf(reference: ReferenceDto): NliResult | null {
  const result = reference.nli.find((item) => item.field === NLI_FIELD) ?? reference.nli[0] ?? null;
  if (!result) return null;
  return {
    field: (FIELD_LABELS[result.field] ?? result.field).toLowerCase(),
    entailment: percent(result.entailment),
    neutral: percent(result.neutral),
    contradiction: percent(result.contradiction),
  };
}

function comparisonsOf(reference: ReferenceDto): FieldComparison[] {
  return reference.comparisons.map((comparison) => ({
    label: FIELD_LABELS[comparison.field] ?? comparison.field,
    given: comparison.given,
    official: comparison.official ?? "No registrado",
    matches: comparison.matches,
  }));
}

/**
 * Avisos que no son un campo distinto: por qué no se verificó, a qué obra lleva
 * el DOI o una separación dudosa. Los hallazgos de formato con "cómo debería
 * ir" se muestran aparte.
 */
function noticeOf(reference: ReferenceDto): string | null {
  const notices = [
    ...reference.veracity_findings.filter((finding) => finding.severity !== "advertencia"),
    ...reference.format_findings.filter((finding) => finding.official === null),
  ].map((finding) => finding.message);
  return notices.length > 0 ? notices.join(" ") : null;
}

function referenceOf(reference: ReferenceDto): ReferenceResult {
  return {
    order: reference.order,
    verdict: isVerdict(reference.verdict) ? reference.verdict : null,
    page: reference.page,
    formatFindings: reference.format_findings
      .filter((finding) => finding.official !== null)
      .map((finding) => ({
        message: finding.message,
        given: finding.given ?? "",
        expected: finding.official ?? "",
      })),
    segments: reference.segments.map((segment) => ({
      text: segment.text,
      field: segment.field ? SEGMENT_FIELDS[segment.field] : undefined,
    })),
    comparisons: comparisonsOf(reference),
    nli: nliOf(reference),
    notice: noticeOf(reference),
    corrected: reference.corrected
      ? {
          text: reference.corrected.text,
          segments: reference.corrected.segments.map(({ text, italic, changed }) => ({
            text,
            italic,
            changed,
          })),
        }
      : null,
  };
}

export function toReport(dto: ReportDto): Report {
  return {
    analysisId: dto.analysis_id,
    fileName: dto.file_name,
    standard: standardLabel(dto.norm) ?? "Norma no identificada",
    standardNotice: dto.norm === "DESCONOCIDA" ? UNKNOWN_STANDARD_NOTICE : null,
    index: dto.index === null ? null : Math.round(dto.index),
    counts: {
      verificada: dto.counts.verificada,
      discrepancia: dto.counts.discrepancia,
      contradiccion: dto.counts.contradiccion,
      sin_respaldo: dto.counts.sin_respaldo,
      no_verificable: dto.counts.no_verificable,
    },
    queryErrors: dto.counts.error_consulta,
    references: dto.references.map(referenceOf),
  };
}
