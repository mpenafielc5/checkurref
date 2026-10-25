import { AccountView } from "@/features/auth/components/account-view";
import { RolePage } from "@/features/auth/components/role-page";

/** Mi cuenta dentro de la sección del docente (contenido en AccountView). */
export default function TeacherAccountPage() {
  return (
    <RolePage allow={["docente"]}>
      <AccountView />
    </RolePage>
  );
}
