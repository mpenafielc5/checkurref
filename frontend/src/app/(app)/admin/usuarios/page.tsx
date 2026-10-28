import { UserTable, UserTableSkeleton } from "@/features/admin/components/user-table";
import { SAMPLE_ROLE_COUNTS, SAMPLE_USERS } from "@/features/admin/sample-data";
import { RolePage } from "@/features/auth/components/role-page";
import { PageSection, PageSectionSkeleton } from "@/shared/components/page-section";
import { SampleDataNotice } from "@/shared/components/ui/sample-data-notice";

/** Usuarios y roles (maqueta 19). */
export default function UsersPage() {
  return (
    <RolePage
      allow={["admin"]}
      skeleton={
        <PageSectionSkeleton description>
          <SampleDataNotice story="la HU-11" />
          <UserTableSkeleton />
        </PageSectionSkeleton>
      }
    >
      <PageSection
        eyebrow="Administración"
        title="Usuarios"
        description="Las cuentas nuevas se registran con el rol de estudiante. Asigna el rol de docente únicamente al personal verificado."
      >
        <SampleDataNotice story="la HU-11" />
        <UserTable users={SAMPLE_USERS} counts={SAMPLE_ROLE_COUNTS} />
      </PageSection>
    </RolePage>
  );
}
