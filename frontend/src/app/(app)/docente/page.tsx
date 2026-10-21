import { Suspense } from "react";
import { RoleGuard } from "@/features/auth/components/role-guard";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

export default function TeacherHomePage() {
  return (
    <Suspense fallback={<PageSectionSkeleton />}>
      <RoleGuard allow={["docente"]}>
        <PageSection
          eyebrow="Docente"
          title="Inicio"
          description="Revisa los trabajos de tus cursos por lotes, ordenados por riesgo."
        />
      </RoleGuard>
    </Suspense>
  );
}
