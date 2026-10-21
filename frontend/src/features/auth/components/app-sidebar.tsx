import { Wordmark } from "@/shared/components/ui/wordmark";
import { getCurrentProfile } from "../api";
import { homePathForRole, navItemsForRole } from "../rules";
import { SidebarNav } from "./sidebar-nav";
import { UserBadge, UserBadgeCompact } from "./user-badge";

const SIDEBAR_CLASSES =
  "flex flex-col gap-3 border-b border-hairline bg-canvas px-4 py-3 md:sticky md:top-0 md:h-dvh md:w-sidebar md:shrink-0 md:gap-2 md:border-r md:border-b-0 md:py-6";

/**
 * Navegación de las pantallas internas (HU-02): barra lateral en pantallas
 * grandes y barra superior compacta en el celular.
 */
export async function AppSidebar() {
  const profile = await getCurrentProfile();
  if (!profile) return <AppSidebarSkeleton />;

  const homeHref = homePathForRole(profile.role);

  return (
    <aside className={SIDEBAR_CLASSES}>
      <div className="flex items-center justify-between md:px-1 md:pb-4">
        <Wordmark href={homeHref} />
        <div className="md:hidden">
          <UserBadgeCompact profile={profile} />
        </div>
      </div>

      <SidebarNav items={navItemsForRole(profile.role)} homeHref={homeHref} />

      <div className="hidden md:flex md:flex-1" />
      <div className="hidden md:flex md:flex-col">
        <UserBadge profile={profile} />
      </div>
    </aside>
  );
}

/** Marcador de posición mientras se carga el perfil. */
export function AppSidebarSkeleton() {
  return (
    <aside className={SIDEBAR_CLASSES}>
      <div className="flex items-center md:px-1 md:pb-4">
        <Wordmark />
      </div>
    </aside>
  );
}
