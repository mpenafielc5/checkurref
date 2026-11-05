import { StatusChip } from "@/shared/components/ui/status-chip";
import type { Work } from "../types";

/** Estado de un trabajo: índice si terminó, avance si sigue en análisis, o error. */
export function WorkStatusChip({ work }: { work: Work }) {
  if (work.status === "en_proceso") {
    return <StatusChip tone="warning">Analizando {work.progress} %</StatusChip>;
  }
  if (work.status === "error") {
    return <StatusChip tone="danger">Error</StatusChip>;
  }
  return <StatusChip tone="success">Índice {work.index ?? "—"}</StatusChip>;
}
