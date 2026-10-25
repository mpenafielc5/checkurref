"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { isNavItemActive } from "../rules";
import type { NavItem } from "../types";
import { NAV_ICONS } from "./sidebar-nav";

type AccountLink = {
  href: string;
  /** Avatar pequeño del usuario, en lugar de un ícono. */
  avatar: ReactNode;
};

type BottomNavProps = {
  items: NavItem[];
  homeHref: string;
  account: AccountLink;
};

const TAB_CLASSES = "flex flex-1 flex-col items-center justify-center gap-1 text-caption";

/** Texto de la pestaña y píldora detrás del ícono según si es la pantalla actual. */
function tabState(active: boolean) {
  return {
    tab: `${TAB_CLASSES} ${active ? "font-semibold text-ink" : "text-body"}`,
    pill: `flex rounded-pill px-4 ${active ? "bg-surface-strong" : ""}`,
  };
}

/**
 * Menú del rol en el celular (HU-17): barra fija abajo, al alcance del pulgar,
 * con las opciones siempre visibles y, al final, Cuenta (abajo, como el bloque
 * del usuario en la barra lateral de escritorio). Cada pestaña abre una
 * pantalla; la actual lleva una píldora detrás del ícono y el texto en negrita.
 */
export function BottomNav({ items, homeHref, account }: BottomNavProps) {
  const pathname = usePathname();
  const accountActive = isNavItemActive(pathname, account.href, homeHref);
  const accountState = tabState(accountActive);

  return (
    <nav
      aria-label="Principal"
      className="fixed inset-x-0 bottom-0 z-(--cr-z-sidebar) flex h-nav border-t border-hairline bg-canvas desktop-nav:hidden"
    >
      <ul className="flex flex-1">
        {items.map((item) => {
          const active = isNavItemActive(pathname, item.href, homeHref);
          const state = tabState(active);
          const Icon = NAV_ICONS[item.icon];
          return (
            <li key={item.href} className="flex flex-1">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={state.tab}
              >
                <span className={`${state.pill} py-1`}>
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                {item.label}
              </Link>
            </li>
          );
        })}
        <li className="flex flex-1">
          <Link
            href={account.href}
            aria-current={accountActive ? "page" : undefined}
            className={accountState.tab}
          >
            {/* py-0.5: el avatar de 24 px ocupa lo mismo que un ícono con py-1 */}
            <span className={`${accountState.pill} py-0.5`}>{account.avatar}</span>
            Cuenta
          </Link>
        </li>
      </ul>
    </nav>
  );
}
