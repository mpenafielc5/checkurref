import { StatusChip } from "@/shared/components/ui/status-chip";
import type { Work } from "../types";
import { formatIndex } from "@/shared/lib/format";
import { INDEX_LEVELS } from "@/shared/lib/truthfulness";

/**
 * Estado de un trabajo: índice si terminó, avance si sigue en análisis, o error.
 * El índice toma el color de su nivel, que calcula el backend (como el anillo del informe).
 */
export function WorkStatusChip({ work }: { work: Work }) {
  if (work.status === "en_proceso") {
    return <StatusChip tone="warning">Analizando {work.progress} %</StatusChip>;
  }
  if (work.status === "error") {
    return <StatusChip tone="danger">Error</StatusChip>;
  }
  return (
    <StatusChip tone={work.indexLevel ? INDEX_LEVELS[work.indexLevel].tone : "neutral"}>
      Índice {work.index === null ? "—" : formatIndex(work.index)}
    </StatusChip>
  );
}
