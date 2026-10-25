"use client";

import {
  CircleHelp,
  FileText,
  FlaskConical,
  FolderOpen,
  House,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { isNavItemActive } from "../rules";
import type { NavIcon, NavItem } from "../types";
import { REVEAL_ON_EXPAND } from "./sidebar-reveal";

/** Dibujo de cada opción del menú; lo comparten la barra lateral y la inferior. */
export const NAV_ICONS: Record<NavIcon, LucideIcon> = {
  home: House,
  works: FileText,
  batches: FolderOpen,
  help: CircleHelp,
  lab: FlaskConical,
  users: Users,
};

type NavProps = {
  items: NavItem[];
  homeHref: string;
};

/**
 * Menú del rol en la barra lateral de escritorio; resalta la sección actual.
 * Con la barra contraída solo se ven los íconos.
 */
export function SidebarNav({ items, homeHref }: NavProps) {
  const pathname = usePathname();

  return (
    <nav aria-label="Principal">
      <ul className="flex flex-col gap-1">
        {items.map((item) => {
          const active = isNavItemActive(pathname, item.href, homeHref);
          const Icon = NAV_ICONS[item.icon];
          return (
            <li key={item.href} className="flex">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex w-full items-center gap-3 rounded-control px-3 py-2 text-small ${
                  active
                    ? "bg-surface-strong font-semibold text-ink"
                    : "text-body hover:bg-hairline-soft hover:text-ink"
                }`}
              >
                <Icon aria-hidden="true" className="size-5 shrink-0" />
                <span className={REVEAL_ON_EXPAND}>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
