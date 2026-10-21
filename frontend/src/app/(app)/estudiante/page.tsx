import { Suspense } from "react";
import { RoleGuard } from "@/features/auth/components/role-guard";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

export default function StudentHomePage() {
  return (
    <Suspense fallback={<PageSectionSkeleton />}>
      <RoleGuard allow={["estudiante"]}>
        <PageSection
          eyebrow="Estudiante"
          title="Inicio"
          description="Sube el PDF de tu trabajo para verificar sus referencias antes de entregarlo."
        />
      </RoleGuard>
    </Suspense>
  );
}
