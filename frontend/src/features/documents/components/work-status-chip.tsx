import { StatusChip } from "@/shared/components/ui/status-chip";
import type { WorkVersion } from "../types";

/** Estado de un trabajo: índice si terminó, avance si sigue en análisis. */
export function WorkStatusChip({ work }: { work: WorkVersion }) {
  if (work.status === "en_proceso") {
    return (
      <StatusChip tone="warning">
        Analizando {work.verified ?? 0}/{work.references}
      </StatusChip>
    );
  }
  return <StatusChip tone="success">Índice {work.index}</StatusChip>;
}
