import { RolePage } from "@/features/auth/components/role-page";
import { RecentWorksLoader } from "@/features/documents/components/recent-works-loader";
import { RecentWorksSkeleton } from "@/features/documents/components/recent-works";
import { StudentUpload } from "@/features/documents/components/student-upload";
import {
  StatisticsLoader,
  StatisticsSkeleton,
} from "@/features/stats/components/statistics-loader";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { Skeleton } from "@/shared/components/ui/skeleton";

/**
 * Inicio del estudiante y subida del trabajo (maqueta 10, HU-04 y HU-18). Mismo orden
 * que el inicio del docente: la acción, el resumen y al final la lista reciente.
 */
export default function StudentHomePage() {
  return (
    <RolePage
      allow={["estudiante"]}
      skeleton={
        <PageSectionSkeleton>
          <Skeleton className="min-h-dropzone w-full rounded-panel md:min-h-dropzone-wide" />
          <StatisticsSkeleton />
          <RecentWorksSkeleton rows={3} />
        </PageSectionSkeleton>
      }
    >
      <PageSection eyebrow="Estudiante" title="Revisa tus referencias antes de entregar">
        <StudentUpload />
        <StatisticsLoader quiet />
        <RecentWorksLoader />
      </PageSection>
    </RolePage>
  );
}
