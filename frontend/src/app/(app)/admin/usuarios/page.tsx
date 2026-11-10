import { UserTable, UserTableSkeleton } from "@/features/admin/components/user-table";
import { RolePage } from "@/features/auth/components/role-page";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";

/** Usuarios y roles (maqueta 19, HU-11). */
export default function UsersPage() {
  return (
    <RolePage
      allow={["admin"]}
      skeleton={
        <PageSectionSkeleton description>
          <UserTableSkeleton />
        </PageSectionSkeleton>
      }
    >
      <PageSection
        eyebrow="Administración"
        title="Usuarios"
        description="Las cuentas nuevas se registran con el rol de estudiante. Asigna el rol de docente únicamente al personal verificado."
      >
        <UserTable />
      </PageSection>
    </RolePage>
  );
}
