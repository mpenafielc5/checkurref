"use client";

import { Search } from "lucide-react";
import { useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import {
  DataTable,
  DataTableSkeleton,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import type { UserRole } from "@/shared/lib/supabase/database.types";
import type { UserRow } from "../sample-data";

type RoleFilter = UserRole | "todos";

const FILTERS: { id: RoleFilter; label: string }[] = [
  { id: "todos", label: "Todos" },
  { id: "estudiante", label: "Estudiantes" },
  { id: "docente", label: "Docentes" },
  { id: "admin", label: "Admin" },
];

const ROLE_LABELS: Record<UserRole, string> = {
  estudiante: "Estudiante",
  docente: "Docente",
  admin: "Admin",
};

/** Clases compartidas con el esqueleto, para que ambos midan lo mismo. */
const TOOLBAR_CLASSES = "flex w-full flex-wrap items-center justify-between gap-4";
const FILTER_CLASSES = "rounded-pill border px-4 py-1.5 text-small font-semibold";
const SEARCH_CLASSES =
  "flex h-input w-full items-center gap-2 rounded-control border border-hairline-strong bg-canvas px-4 md:w-auto md:max-w-xs md:flex-1";

/** Usuarios con búsqueda por correo y filtro por rol (maqueta 19). */
export function UserTable({
  users,
  counts,
}: {
  users: UserRow[];
  counts: Record<RoleFilter, number>;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<RoleFilter>("todos");

  const visible = users.filter(
    (user) =>
      (filter === "todos" || user.role === filter) &&
      user.email.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <div className="flex flex-col gap-4">
      <div className={TOOLBAR_CLASSES}>
        <div role="group" aria-label="Filtrar por rol" className="flex flex-wrap gap-2">
          {FILTERS.map((item) => {
            const selected = item.id === filter;
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={selected}
                onClick={() => setFilter(item.id)}
                className={`${FILTER_CLASSES} ${
                  selected
                    ? "border-action bg-action text-on-action"
                    : "border-hairline-strong text-ink hover:border-ink"
                }`}
              >
                {item.label} <span className="font-normal">{counts[item.id]}</span>
              </button>
            );
          })}
        </div>
        <label className={SEARCH_CLASSES}>
          <Search aria-hidden="true" className="size-5 text-muted" />
          <span className="sr-only">Buscar por correo</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por correo…"
            className="w-full bg-transparent text-small text-ink outline-none placeholder:text-muted"
          />
        </label>
      </div>

      <DataTable caption="Usuarios del sistema">
        <thead className={tableHeadClass}>
          <tr>
            <th scope="col" className={thClass}>
              Usuario
            </th>
            <th scope="col" className={thClass}>
              Correo
            </th>
            <th scope="col" className={thClass}>
              Rol
            </th>
            <th scope="col" className={thClass}>
              Acción
            </th>
          </tr>
        </thead>
        <tbody>
          {visible.map((user) => (
            <tr key={user.id}>
              <td className={tdClass}>{user.name}</td>
              <td className={`${tdClass} text-body`}>{user.email}</td>
              <td className={tdClass}>{ROLE_LABELS[user.role]}</td>
              <td className={tdClass}>
                {user.role === "admin" ? (
                  <span className="text-muted">—</span>
                ) : (
                  <button type="button" disabled className={buttonStyles({ variant: "secondary" })}>
                    Cambiar rol
                  </button>
                )}
              </td>
            </tr>
          ))}
          {visible.length === 0 ? (
            <tr>
              <td colSpan={4} className={`${tdClass} text-body`}>
                Ninguna cuenta coincide con el filtro.
              </td>
            </tr>
          ) : null}
        </tbody>
      </DataTable>
    </div>
  );
}

/** Esqueleto de UserTable: filtros, buscador y tabla con el botón por fila. */
export function UserTableSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className={TOOLBAR_CLASSES}>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((item) => (
            <span key={item.id} className={`flex ${FILTER_CLASSES} border-hairline`}>
              <SkeletonText widthClass="w-16" />
            </span>
          ))}
        </div>
        <span className={SEARCH_CLASSES}>
          <SkeletonText textClass="text-small" widthClass="w-32" />
        </span>
      </div>
      <DataTableSkeleton columns={4} rows={5} withAction />
    </div>
  );
}
