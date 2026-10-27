import { RolePage } from "@/features/auth/components/role-page";
import { WorkHistory, WorkHistorySkeleton } from "@/features/documents/components/work-history";
import { SAMPLE_WORKS } from "@/features/documents/sample-data";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Mis trabajos: historial sin versiones (maqueta 13, Asesoría 1). */
export default function StudentWorksPage() {
  return (
    <RolePage
      allow={["estudiante"]}
      skeleton={
        <PageSectionSkeleton>
          <SampleDataNotice story="la HU-07" />
          <WorkHistorySkeleton />
        </PageSectionSkeleton>
      }
    >
      <PageSection eyebrow="Estudiante" title="Mis trabajos">
        <SampleDataNotice story="la HU-07" />
        <WorkHistory works={SAMPLE_WORKS} />
      </PageSection>
    </RolePage>
  );
}
