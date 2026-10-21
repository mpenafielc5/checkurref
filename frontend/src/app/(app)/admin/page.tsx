import { Suspense } from "react";
import { RoleGuard } from "@/features/auth/components/role-guard";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

export default function AdminHomePage() {
  return (
    <Suspense fallback={<PageSectionSkeleton />}>
      <RoleGuard allow={["admin"]}>
        <PageSection
          eyebrow="Administración"
          title="Inicio"
          description="Gestiona usuarios y roles, y compara los extractores en el Laboratorio."
        />
      </RoleGuard>
    </Suspense>
  );
}
