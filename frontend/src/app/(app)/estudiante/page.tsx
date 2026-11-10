import { RolePage } from "@/features/auth/components/role-page";
import { RecentWorksLoader } from "@/features/documents/components/recent-works-loader";
import { StudentUpload } from "@/features/documents/components/student-upload";
import { StatisticsLoader } from "@/features/stats/components/statistics-loader";
import { PageSection } from "@/shared/components/page-section";

/** Inicio del estudiante y subida del trabajo (maqueta 10, HU-04 y HU-18). */
export default function StudentHomePage() {
  return (
    <RolePage allow={["estudiante"]}>
      <PageSection eyebrow="Estudiante" title="Revisa tus referencias antes de entregar">
        <StudentUpload />
        <RecentWorksLoader />
        <StatisticsLoader quiet />
      </PageSection>
    </RolePage>
  );
}
