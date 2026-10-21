import { RolePage } from "@/features/auth/components/role-page";
import { ReportView } from "@/features/reports/components/report-view";
import { SAMPLE_REPORT } from "@/features/reports/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Informe de un trabajo del estudiante (maqueta 12). */
export default function StudentReportPage() {
  return (
    <RolePage allow={["estudiante"]} skeleton={<PageSectionSkeleton back />}>
      <PageSection
        eyebrow="Informe"
        title="Diagnóstico de veracidad"
        back={{ href: "/estudiante/trabajos", label: "Mis trabajos" }}
      >
        <SampleDataNotice story="la HU-06" />
        <ReportView report={SAMPLE_REPORT} />
      </PageSection>
    </RolePage>
  );
}
