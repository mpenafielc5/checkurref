import { StatusChip } from "@/shared/components/ui/status-chip";
import { verifiedCount } from "@/shared/lib/analysis-progress";

type AnalysisStatusChipProps = {
  status: string;
  progress: number;
  totalReferences: number | null;
};

/** Etapa de un análisis en curso, igual en el avance de la subida y en el tablero. */
export function AnalysisStatusChip({ status, progress, totalReferences }: AnalysisStatusChipProps) {
  if (status === "en_cola") return <StatusChip tone="neutral">En cola</StatusChip>;
  if (status !== "verificando" || !totalReferences) {
    return <StatusChip tone="warning">Analizando</StatusChip>;
  }
  return (
    <StatusChip tone="warning">
      Verificando {verifiedCount(progress, totalReferences)}/{totalReferences}
    </StatusChip>
  );
}
