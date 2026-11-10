import { RolePage } from "@/features/auth/components/role-page";
import { BatchDashboard } from "@/features/batches/components/batch-dashboard";
import { PageSectionSkeleton } from "@/shared/components/page-section";

/** Tablero del lote: trabajos ordenados por riesgo (maqueta 16, HU-09). */
export default function BatchDashboardPage() {
  return (
    <RolePage allow={["docente"]} skeleton={<PageSectionSkeleton back action />}>
      <BatchDashboard />
    </RolePage>
  );
}
