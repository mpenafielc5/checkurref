import Link from "next/link";
import { BrandLogo } from "@/shared/components/ui/brand-logo";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Wordmark } from "@/shared/components/ui/wordmark";
import { getCurrentProfile } from "../api";
import { accountPathForRole, homePathForRole, navItemsForRole } from "../rules";
import type { Profile } from "../types";
import { BottomNav } from "./bottom-nav";
import { SidebarNav } from "./sidebar-nav";
import { REVEAL_ON_EXPAND } from "./sidebar-reveal";
import { Avatar, UserBadge } from "./user-badge";

/** Pantallas táctiles: arriba solo el logotipo (no queda fija); el menú y la cuenta van abajo, en BottomNav. */
const MOBILE_BAR_CLASSES =
  "flex h-nav items-center border-b border-hairline bg-canvas px-4 short-screen:h-nav-compact desktop-nav:hidden";

/** Escritorio (desktop-nav): reserva el ancho de la barra contraída para que el contenido no quede debajo. */
const RAIL_CLASSES = "hidden w-sidebar-rail shrink-0 desktop-nav:flex";

/**
 * La barra en sí: fija a la izquierda y contraída (solo íconos). Al pasar el
 * mouse, tras una breve espera, se ensancha encima del contenido sin moverlo;
 * si el mouse solo cruza por el borde, no llega a abrirse. Con el teclado se
 * despliega mientras el foco (visible) está dentro; se usa :focus-visible y no
 * :focus-within para que no quede abierta después de un clic.
 */
const PANEL_CLASSES =
  "group/sidebar fixed inset-y-0 left-0 z-(--cr-z-sidebar) flex w-sidebar-rail flex-col gap-2 overflow-hidden border-r border-hairline bg-canvas px-4 py-6 transition-[width] duration-(--cr-duration-fast) hover:w-sidebar hover:delay-(--cr-sidebar-expand-delay) has-[:focus-visible]:w-sidebar";

/**
 * Logotipo de la barra: el isotipo siempre visible y del mismo tamaño (centrado
 * sobre la columna de íconos del menú con px-2); el nombre aparece al desplegar.
 */
function SidebarLogo({ href }: { href: string }) {
  return (
    <Link href={href} className="mb-4 flex rounded-control px-2">
      <BrandLogo variant="expanded" nameClass={REVEAL_ON_EXPAND} />
    </Link>
  );
}

/**
 * Navegación de las pantallas internas (HU-02, HU-17): barra lateral
 * contraíble en pantallas grandes; en el celular, el logotipo arriba y el
 * menú con la cuenta en una barra inferior.
 */
export async function AppSidebar() {
  const profile = await getCurrentProfile();
  if (!profile) return <AppSidebarSkeleton />;
  return <AppSidebarView profile={profile} />;
}

/** La barra ya con el perfil cargado. */
function AppSidebarView({ profile }: { profile: Profile }) {
  const homeHref = homePathForRole(profile.role);
  const accountHref = accountPathForRole(profile.role);
  const items = navItemsForRole(profile.role);

  return (
    <>
      <header className={MOBILE_BAR_CLASSES}>
        <Wordmark href={homeHref} />
      </header>
      <BottomNav
        items={items}
        homeHref={homeHref}
        account={{ href: accountHref, avatar: <Avatar profile={profile} small /> }}
      />

      <aside className={RAIL_CLASSES}>
        <div className={PANEL_CLASSES}>
          <SidebarLogo href={homeHref} />
          <SidebarNav items={items} homeHref={homeHref} />
          <div className="flex flex-1" />
          <UserBadge profile={profile} />
        </div>
      </aside>
    </>
  );
}

/** Esqueleto mientras se carga el perfil: íconos del menú y avatar. */
export function AppSidebarSkeleton() {
  const iconSlots = [0, 1, 2];
  const tabSlots = [0, 1, 2, 3];

  return (
    <>
      <div className={MOBILE_BAR_CLASSES}>
        <BrandLogo variant="expanded" />
      </div>
      <div className="fixed inset-x-0 bottom-0 flex h-nav border-t border-hairline bg-canvas short-screen:h-nav-compact desktop-nav:hidden">
        {tabSlots.map((slot) => (
          <span key={slot} className="flex flex-1 items-center justify-center">
            <Skeleton className="size-5 rounded-row" />
          </span>
        ))}
      </div>

      <div className={RAIL_CLASSES}>
        <div className={PANEL_CLASSES}>
          <span className="mb-4 flex px-2">
            <BrandLogo variant="collapsed" />
          </span>
          <div className="flex flex-col gap-1">
            {iconSlots.map((slot) => (
              <span key={slot} className="flex px-3 py-2">
                <Skeleton className="size-5 rounded-row" />
              </span>
            ))}
          </div>
          <div className="flex flex-1" />
          <div className="flex flex-col gap-3 border-t border-hairline px-0.5 pt-4">
            <Skeleton className="size-avatar rounded-pill" />
            <span className="flex px-2.5 py-2">
              <Skeleton className="size-5 rounded-row" />
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
