import { RolePage } from "@/features/auth/components/role-page";
import { PageSectionSkeleton } from "@/shared/components/page-section";
import { BatchReportSection } from "./batch-report-section";

/** Informe de un trabajo del lote (maqueta 12, vista del docente; HU-09 RF20-CA04). */
export default function BatchReportPage() {
  return (
    <RolePage allow={["docente"]} skeleton={<PageSectionSkeleton back />}>
      <BatchReportSection />
    </RolePage>
  );
}
