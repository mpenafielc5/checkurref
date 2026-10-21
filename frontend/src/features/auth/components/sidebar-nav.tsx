"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavItem } from "../types";

type SidebarNavProps = {
  items: NavItem[];
  homeHref: string;
};

/** Menú del rol; resalta la sección en la que está el usuario. */
export function SidebarNav({ items, homeHref }: SidebarNavProps) {
  const pathname = usePathname();

  function isActive(href: string): boolean {
    if (pathname === href) return true;
    // "Inicio" solo se marca en su propia página, no en las secciones internas.
    return href !== homeHref && pathname.startsWith(`${href}/`);
  }

  return (
    <nav aria-label="Principal">
      <ul className="flex gap-1 overflow-x-auto md:flex-col">
        {items.map((item) => {
          const active = isActive(item.href);
          return (
            <li key={item.href} className="flex shrink-0">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "flex w-full rounded-control bg-surface-strong px-3 py-2 text-small font-semibold text-ink"
                    : "flex w-full rounded-control px-3 py-2 text-small text-body hover:bg-hairline-soft hover:text-ink"
                }
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
