import { AccountView } from "@/features/auth/components/account-view";
import { RolePage } from "@/features/auth/components/role-page";

/** Mi cuenta dentro de la sección del estudiante (contenido en AccountView). */
export default function StudentAccountPage() {
  return (
    <RolePage allow={["estudiante"]}>
      <AccountView />
    </RolePage>
  );
}
