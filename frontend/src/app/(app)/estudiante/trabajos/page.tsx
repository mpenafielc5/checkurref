import { RolePage } from "@/features/auth/components/role-page";
import { WorkHistorySkeleton } from "@/features/documents/components/work-history";
import { WorkHistoryLoader } from "@/features/documents/components/work-history-loader";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

/** Mis trabajos: historial sin versiones (maqueta 13, Asesoría 1, HU-07). */
export default function StudentWorksPage() {
  return (
    <RolePage
      allow={["estudiante"]}
      skeleton={
        <PageSectionSkeleton>
          <WorkHistorySkeleton />
        </PageSectionSkeleton>
      }
    >
      <PageSection eyebrow="Estudiante" title="Mis trabajos">
        <WorkHistoryLoader />
      </PageSection>
    </RolePage>
  );
}
