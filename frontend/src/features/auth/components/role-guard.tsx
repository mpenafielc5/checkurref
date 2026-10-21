import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { getCurrentProfile } from "../api";
import { homePathForRole } from "../rules";
import type { UserRole } from "../types";

type RoleGuardProps = {
  allow: UserRole[];
  children: ReactNode;
};

/**
 * Muestra su contenido solo si el usuario tiene uno de los roles permitidos.
 * Si no, lo envía a la página de inicio de su propio rol.
 */
export async function RoleGuard({ allow, children }: RoleGuardProps) {
  const profile = await getCurrentProfile();

  if (!profile || !profile.active) {
    redirect("/inicio");
  }

  if (!allow.includes(profile.role)) {
    redirect(homePathForRole(profile.role));
  }

  return children;
}
