import { RolePage } from "@/features/auth/components/role-page";
import { RecentWorks } from "@/features/documents/components/recent-works";
import { StudentUpload } from "@/features/documents/components/student-upload";
import { SAMPLE_RECENT_WORKS } from "@/features/documents/sample-data";
import { PageSection } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Inicio del estudiante y subida del trabajo (maqueta 10, HU-04). */
export default function StudentHomePage() {
  return (
    <RolePage allow={["estudiante"]}>
      <PageSection eyebrow="Estudiante" title="Revisa tus referencias antes de entregar">
        <StudentUpload />
        <SampleDataNotice story="la HU-07" />
        <RecentWorks works={SAMPLE_RECENT_WORKS} />
      </PageSection>
    </RolePage>
  );
}
