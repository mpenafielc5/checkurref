import type { BatchWork, RiskLevel } from "./types";

const RISK_WEIGHT: Record<RiskLevel, number> = { alto: 3, medio: 2, bajo: 1 };

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
      diff = a.name.localeCompare(b.name, "es");
    } else {
      diff = a[key] - b[key];
    }
    return diff * factor;
  });
}
