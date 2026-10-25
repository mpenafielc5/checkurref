import { AccountView } from "@/features/auth/components/account-view";
import { RolePage } from "@/features/auth/components/role-page";

/** Mi cuenta dentro de la sección del administrador (contenido en AccountView). */
export default function AdminAccountPage() {
  return (
    <RolePage allow={["admin"]}>
      <AccountView />
    </RolePage>
  );
}
