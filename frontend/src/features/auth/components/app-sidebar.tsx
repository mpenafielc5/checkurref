import { Skeleton, SkeletonText } from "@/shared/components/ui/skeleton";
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

/** Esqueleto mientras se carga el perfil: menú y bloque del usuario. */
export function AppSidebarSkeleton() {
  return (
    <aside className={SIDEBAR_CLASSES}>
      <div className="flex items-center justify-between md:px-1 md:pb-4">
        <Wordmark />
        <div className="flex items-center gap-2 md:hidden">
          <Skeleton className="size-avatar rounded-pill" />
          <Skeleton className="size-9 rounded-control" />
        </div>
      </div>

      <div className="flex gap-1 md:flex-col">
        {[0, 1, 2].map((item) => (
          <span key={item} className="flex px-3 py-2">
            <SkeletonText textClass="text-small" widthClass="w-20" />
          </span>
        ))}
      </div>

      <div className="hidden md:flex md:flex-1" />
      <div className="hidden md:flex md:flex-col md:gap-3 md:border-t md:border-hairline md:px-1 md:pt-4">
        <div className="flex items-center gap-3">
          <Skeleton className="size-avatar shrink-0 rounded-pill" />
          <span className="flex flex-1 flex-col">
            <SkeletonText textClass="text-small" widthClass="w-24" />
            <SkeletonText textClass="text-caption" widthClass="w-16" />
          </span>
        </div>
        <span className="flex px-3 py-2">
          <SkeletonText textClass="text-small" widthClass="w-14" />
        </span>
      </div>
    </aside>
  );
}
