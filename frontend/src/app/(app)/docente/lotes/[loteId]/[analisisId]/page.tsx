import { RolePage } from "@/features/auth/components/role-page";
import { SAMPLE_BATCH_DETAIL } from "@/features/batches/sample-data";
import { ReportView } from "@/features/reports/components/report-view";
import { SAMPLE_REPORT } from "@/features/reports/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Informe de un trabajo del lote (maqueta 12, vista del docente). */
export default function BatchReportPage() {
  return (
    <RolePage allow={["docente"]} skeleton={<PageSectionSkeleton back />}>
      <PageSection
        eyebrow="Informe"
        title="Diagnóstico de veracidad"
        back={{ href: `/docente/lotes/${SAMPLE_BATCH_DETAIL.id}`, label: "Tablero del lote" }}
      >
        <SampleDataNotice story="la HU-06" />
        <ReportView report={SAMPLE_REPORT} />
      </PageSection>
    </RolePage>
  );
}
