import { LogOut } from "lucide-react";
import { PageSection } from "@/shared/components/page-section";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { getCurrentProfile } from "../api";
import { displayFullName, homePathForRole, ROLE_LABELS } from "../rules";
import { LeaveOnDesktopNav } from "./leave-on-desktop-nav";
import { Avatar } from "./user-badge";

/**
 * Pantalla Mi cuenta (HU-17), para el celular: la abre la pestaña Cuenta de la
 * barra inferior. Muestra lo mismo que el pie de la barra lateral de
 * escritorio (avatar, nombre, rol y Salir), que por eso no enlaza aquí; si la
 * pantalla pasa a la navegación de escritorio, vuelve al inicio. Va dentro de
 * RolePage, que ya verificó la sesión.
 */
export async function AccountView() {
  const profile = await getCurrentProfile();
  if (!profile) return null;

  return (
    <PageSection eyebrow={ROLE_LABELS[profile.role]} title="Mi cuenta">
      <LeaveOnDesktopNav href={homePathForRole(profile.role)} />
      <div className="flex w-full flex-col gap-4 md:max-w-lg">
        <div className="flex items-center gap-4 rounded-card border border-hairline bg-canvas p-5">
          <Avatar profile={profile} />
          <p className="flex min-w-0 flex-col">
            <span className="truncate text-title font-semibold text-ink">
              {displayFullName(profile.fullName)}
            </span>
            <span className="text-small text-body">{ROLE_LABELS[profile.role]}</span>
          </p>
        </div>
        <form action="/auth/signout" method="post" className="flex">
          <button
            type="submit"
            className={`${buttonStyles({ variant: "secondary" })} w-full md:w-auto`}
          >
            <LogOut aria-hidden="true" className="size-4" />
            Salir
          </button>
        </form>
      </div>
    </PageSection>
  );
}
