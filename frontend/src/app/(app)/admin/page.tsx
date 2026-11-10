import { RolePage } from "@/features/auth/components/role-page";
import {
  StatisticsLoader,
  StatisticsSkeleton,
} from "@/features/stats/components/statistics-loader";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

/**
 * Inicio del administrador (HU-18 CA03): solo las estadísticas generales. Usuarios y
 * Laboratorio se abren desde el menú lateral, sin accesos repetidos aquí.
 */
export default function AdminHomePage() {
  return (
    <RolePage
      allow={["admin"]}
      skeleton={
        <PageSectionSkeleton>
          <StatisticsSkeleton cards={6} thirds />
        </PageSectionSkeleton>
      }
    >
      <PageSection eyebrow="Administración" title="Inicio">
        <StatisticsLoader cards={6} thirds />
      </PageSection>
    </RolePage>
  );
}
