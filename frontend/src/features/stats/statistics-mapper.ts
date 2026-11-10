/* Traduce la respuesta de GET /estadisticas, que depende del rol de la sesión. */
import { VERDICT_ORDER, type Verdict } from "@/shared/lib/verdicts";
import type { Statistics } from "./types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function numberOf(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function verdictsOf(raw: Record<string, unknown>) {
  const counts: Record<Verdict, number> = {
    verificada: 0,
    discrepancia: 0,
    contradiccion: 0,
    sin_respaldo: 0,
    no_verificable: 0,
  };
  for (const verdict of VERDICT_ORDER) counts[verdict] = numberOf(raw[verdict]) ?? 0;
  return { counts, queryErrors: numberOf(raw.error_consulta) ?? 0 };
}

/** Las cifras del rol; null si la respuesta no es la esperada. */
export function toStatistics(body: unknown): Statistics | null {
  if (!isRecord(body) || !isRecord(body.counts)) return null;
  const references = numberOf(body.references);
  if (references === null) return null;
  const verdicts = verdictsOf(body.counts);

  if (body.role === "estudiante") {
    const works = numberOf(body.works);
    if (works === null) return null;
    return {
      role: "estudiante",
      ...verdicts,
      works,
      references,
      averageIndex: numberOf(body.average_index),
      mostDifferentField:
        typeof body.most_different_field === "string" ? body.most_different_field : null,
    };
  }
  if (body.role === "docente") {
    const works = numberOf(body.works);
    const batches = numberOf(body.batches);
    const highRiskWorks = numberOf(body.high_risk_works);
    if (works === null || batches === null || highRiskWorks === null) return null;
    return { role: "docente", ...verdicts, batches, works, references, highRiskWorks };
  }
  if (body.role === "admin" && isRecord(body.users)) {
    const documents = numberOf(body.documents);
    if (documents === null) return null;
    return {
      role: "admin",
      ...verdicts,
      users: {
        estudiante: numberOf(body.users.estudiante) ?? 0,
        docente: numberOf(body.users.docente) ?? 0,
        admin: numberOf(body.users.admin) ?? 0,
      },
      documents,
      references,
    };
  }
  return null;
}
