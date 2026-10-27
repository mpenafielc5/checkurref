import type { BatchWork, RiskLevel } from "./types";

const RISK_WEIGHT: Record<RiskLevel, number> = { alto: 3, medio: 2, bajo: 1 };

/** Autores leídos de la portada, separados por comas; null si no se reconoció. */
export function authorsLabel(work: BatchWork): string | null {
  return work.authors.length > 0 ? work.authors.join(", ") : null;
}

/**
 * Orden por nombre: los trabajos con autores, de la A a la Z; los de portada
 * no reconocida, después y por nombre de archivo.
 */
function compareByName(a: BatchWork, b: BatchWork): number {
  const authorsA = authorsLabel(a);
  const authorsB = authorsLabel(b);
  if (authorsA && authorsB) return authorsA.localeCompare(authorsB, "es");
  if (authorsA) return -1;
  if (authorsB) return 1;
  return a.fileName.localeCompare(b.fileName, "es");
}

export type SortKey = "risk" | "references" | "index" | "alerts" | "name";
export type SortDirection = "asc" | "desc";

/**
 * Ordena los trabajos del lote. Por defecto, los de mayor riesgo primero y,
 * a igual riesgo, los de menor índice de veracidad.
 */
export function sortBatchWorks(
  works: BatchWork[],
  key: SortKey = "risk",
  direction: SortDirection = "desc",
): BatchWork[] {
  const factor = direction === "desc" ? -1 : 1;
  return [...works].sort((a, b) => {
    let diff: number;
    if (key === "risk") {
      diff = RISK_WEIGHT[a.risk] - RISK_WEIGHT[b.risk] || b.index - a.index;
    } else if (key === "name") {
      diff = compareByName(a, b);
    } else {
      diff = a[key] - b[key];
    }
    return diff * factor;
  });
}
