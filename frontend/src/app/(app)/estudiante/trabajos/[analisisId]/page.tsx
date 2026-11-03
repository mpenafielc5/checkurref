import { RolePage } from "@/features/auth/components/role-page";
import { ReportLoader } from "@/features/reports/components/report-loader";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

/** Informe de un trabajo del estudiante (maqueta 12, HU-06). */
export default function StudentReportPage() {
  return (
    <RolePage allow={["estudiante"]} skeleton={<PageSectionSkeleton back />}>
      <PageSection
        eyebrow="Informe"
        title="Diagnóstico de veracidad"
        back={{ href: "/estudiante/trabajos", label: "Mis trabajos" }}
      >
        <ReportLoader listHref="/estudiante/trabajos" />
      </PageSection>
    </RolePage>
  );
}
