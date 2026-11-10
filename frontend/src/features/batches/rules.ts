import { formatPercent } from "@/shared/lib/format";
import type { BatchWork, RiskLevel } from "./types";

const COMPLETED = "completado";
const RISK_WEIGHT: Record<RiskLevel, number> = { alto: 3, medio: 2, bajo: 1 };

/** Solo un trabajo terminado tiene informe e indicadores que mostrar. */
export function isWorkCompleted(work: BatchWork): boolean {
  return work.status === COMPLETED;
}

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

type NumericKey = Exclude<SortKey, "name">;

/** Valor con el que se ordena; null si el trabajo aún no lo tiene. */
function sortValue(work: BatchWork, key: NumericKey): number | null {
  if (!isWorkCompleted(work)) return null;
  if (key === "risk") return work.risk ? RISK_WEIGHT[work.risk] : null;
  return work[key];
}

/**
 * Ordena los trabajos del lote. Por defecto, los de mayor riesgo primero y,
 * a igual riesgo, los de menor índice de veracidad. Los que no tienen el dato
 * (en análisis o con error) quedan al final en ambos sentidos, en su orden.
 */
export function sortBatchWorks(
  works: BatchWork[],
  key: SortKey = "risk",
  direction: SortDirection = "desc",
): BatchWork[] {
  const factor = direction === "desc" ? -1 : 1;
  return [...works].sort((a, b) => {
    if (key === "name") return compareByName(a, b) * factor;
    const valueA = sortValue(a, key);
    const valueB = sortValue(b, key);
    if (valueA === null || valueB === null) {
      return Number(valueA === null) - Number(valueB === null);
    }
    const diff = valueA - valueB;
    if (diff !== 0 || key !== "risk") return diff * factor;
    return ((b.index ?? 0) - (a.index ?? 0)) * factor;
  });
}

/**
 * Parte de las referencias del lote con un veredicto. Lo que apenas existe no se
 * redondea a 0 % ni a 100 %: daría a entender que no hay ninguna o que son todas.
 */
export function shareLabel(count: number, total: number): string {
  if (total === 0) return "—";
  const percent = (count / total) * 100;
  if (count > 0 && percent < 1) return "< 1 %";
  if (count < total && percent > 99) return "> 99 %";
  return formatPercent(percent);
}
