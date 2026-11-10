"use client";

import { Search } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { ConfirmDialog } from "@/shared/components/ui/confirm-dialog";
import {
  cardClass,
  cardListClass,
  DataTable,
  DataTableSkeleton,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { Pagination } from "@/shared/components/ui/pagination";
import { SkeletonText } from "@/shared/components/ui/skeleton";
import { StatusChip } from "@/shared/components/ui/status-chip";
import { displayFullName } from "@/shared/lib/names";
import { PAGE_PARAM, parsePage } from "@/shared/lib/pagination";
import { updateUser } from "../api";
import {
  activeChangeOf,
  canManage,
  confirmationOf,
  parseRoleFilter,
  ROLE_LABELS,
  ROLE_PARAM,
  roleChangeOf,
  SEARCH_PARAM,
} from "../rules";
import type { RoleCounts, RoleFilter, UserChange, UserRow } from "../types";
import { useUsers } from "../use-users";

const FILTERS: { id: RoleFilter; label: string }[] = [
  { id: "todos", label: "Todos" },
  { id: "estudiante", label: "Estudiantes" },
  { id: "docente", label: "Docentes" },
  { id: "admin", label: "Admin" },
];

/** Espera a que termine de escribir: cada búsqueda es una consulta a la API. */
const SEARCH_DELAY_MS = 400;
const LIST_ID = "usuarios";

/** Clases compartidas con el esqueleto, para que ambos midan lo mismo. */
const TOOLBAR_CLASSES = "flex w-full flex-wrap items-center justify-between gap-4";
const FILTER_CLASSES = "rounded-pill border px-4 py-1.5 text-small font-semibold";
const SEARCH_CLASSES =
  "flex h-input w-full items-center gap-2 rounded-control border border-hairline-strong bg-canvas px-4 md:w-auto md:max-w-xs md:flex-1";
const EMPTY_MESSAGE = "Ninguna cuenta coincide con el filtro.";

type PendingChange = { user: UserRow; change: UserChange };

function AccountStatus({ user }: { user: UserRow }) {
  return user.active ? (
    <StatusChip tone="success">Activa</StatusChip>
  ) : (
    <StatusChip tone="danger">Desactivada</StatusChip>
  );
}

type UserActionsProps = {
  user: UserRow;
  fullWidth?: boolean;
  onChoose: (pending: PendingChange) => void;
};

/** Cambiar el rol y desactivar; en las cuentas de administrador no aparecen. */
function UserActions({ user, fullWidth = false, onChoose }: UserActionsProps) {
  if (!canManage(user)) return <span className="text-muted">—</span>;
  const style = buttonStyles({ variant: "secondary", fullWidth });
  return (
    <span className="flex flex-col gap-2 md:flex-row">
      <button
        type="button"
        aria-label={`Cambiar el rol de ${user.email}`}
        onClick={() => onChoose({ user, change: roleChangeOf(user) })}
        className={style}
      >
        Cambiar rol
      </button>
      <button
        type="button"
        aria-label={`${user.active ? "Desactivar" : "Reactivar"} la cuenta de ${user.email}`}
        onClick={() => onChoose({ user, change: activeChangeOf(user) })}
        className={style}
      >
        {user.active ? "Desactivar" : "Reactivar"}
      </button>
    </span>
  );
}

type UserRowsProps = {
  users: UserRow[];
  onChoose: (pending: PendingChange) => void;
};

/** Tarjetas en el celular y tabla desde md. */
function UserRows({ users, onChoose }: UserRowsProps) {
  return (
    <>
      <ul className={cardListClass}>
        {users.map((user) => (
          <li key={user.id} className={cardClass}>
            <span className="flex items-start justify-between gap-3">
              <span className="flex min-w-0 flex-col">
                <span className="font-semibold text-ink">{displayFullName(user.name)}</span>
                <span className="text-small break-all">{user.email}</span>
              </span>
              <StatusChip tone="neutral">{ROLE_LABELS[user.role]}</StatusChip>
            </span>
            <span className="flex">
              <AccountStatus user={user} />
            </span>
            {canManage(user) ? <UserActions user={user} fullWidth onChoose={onChoose} /> : null}
          </li>
        ))}
        {users.length === 0 ? <li className="text-small">{EMPTY_MESSAGE}</li> : null}
      </ul>

      <DataTable caption="Usuarios del sistema" cardsOnMobile>
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
              Estado
            </th>
            <th scope="col" className={thClass}>
              Acción
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td className={tdClass}>{displayFullName(user.name)}</td>
              <td className={`${tdClass} text-body`}>{user.email}</td>
              <td className={tdClass}>{ROLE_LABELS[user.role]}</td>
              <td className={tdClass}>
                <AccountStatus user={user} />
              </td>
              <td className={tdClass}>
                <UserActions user={user} onChoose={onChoose} />
              </td>
            </tr>
          ))}
          {users.length === 0 ? (
            <tr>
              <td colSpan={5} className={`${tdClass} text-body`}>
                {EMPTY_MESSAGE}
              </td>
            </tr>
          ) : null}
        </tbody>
      </DataTable>
    </>
  );
}

type ConfirmChangeProps = {
  pending: PendingChange;
  onCancel: () => void;
  onDone: () => void;
};

/** Pide confirmar el cambio y lo aplica; si falla, muestra el motivo sin cerrarse. */
function ConfirmChange({ pending, onCancel, onDone }: ConfirmChangeProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { title, message, confirmLabel } = confirmationOf(pending.user, pending.change);

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    const outcome = await updateUser(pending.user.id, pending.change);
    if (outcome.kind === "updated") {
      onDone();
      return;
    }
    setBusy(false);
    setError(outcome.message);
  }

  return (
    <ConfirmDialog
      title={title}
      confirmLabel={busy ? "Aplicando…" : confirmLabel}
      busy={busy}
      error={error}
      onConfirm={() => void handleConfirm()}
      onCancel={onCancel}
    >
      <p>{message}</p>
      <p className="break-all">{pending.user.email}</p>
    </ConfirmDialog>
  );
}

/** Usuarios con búsqueda por correo, filtro por rol y paginación (maqueta 19, HU-11). */
export function UserTable() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const page = parsePage(searchParams.get(PAGE_PARAM));
  const filter = parseRoleFilter(searchParams.get(ROLE_PARAM));
  const search = searchParams.get(SEARCH_PARAM) ?? "";

  const { state, counts, reload } = useUsers(page, search, filter);
  const [query, setQuery] = useState(search);
  const [pending, setPending] = useState<PendingChange | null>(null);

  /** Otra búsqueda u otro filtro empieza desde la primera página. */
  function applyParams(changes: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    params.delete(PAGE_PARAM);
    for (const [name, value] of Object.entries(changes)) {
      if (value) params.set(name, value);
      else params.delete(name);
    }
    const nextQuery = params.toString();
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
  }

  useEffect(() => {
    const clean = query.trim();
    if (clean === search) return;
    const timer = setTimeout(() => applyParams({ [SEARCH_PARAM]: clean }), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo importa lo que se escribe.
  }, [query, search]);

  return (
    <div id={LIST_ID} className="flex scroll-mt-6 flex-col gap-4">
      <div className={TOOLBAR_CLASSES}>
        <div role="group" aria-label="Filtrar por rol" className="flex flex-wrap gap-2">
          {FILTERS.map((item) => {
            const selected = item.id === filter;
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={selected}
                onClick={() => applyParams({ [ROLE_PARAM]: item.id === "todos" ? null : item.id })}
                className={`${FILTER_CLASSES} ${
                  selected
                    ? "border-action bg-action text-on-action"
                    : "border-hairline-strong text-ink hover:border-ink"
                }`}
              >
                {item.label} <RoleCount counts={counts} filter={item.id} />
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
            maxLength={100}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por correo…"
            className="w-full bg-transparent text-small text-ink outline-none placeholder:text-muted"
          />
        </label>
      </div>

      {state.kind === "loading" ? (
        <div className="flex flex-col gap-4">
          <p role="status" className="sr-only">
            Cargando los usuarios…
          </p>
          {state.slow ? (
            <p className="text-small">
              Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.
            </p>
          ) : null}
          <DataTableSkeleton columns={5} rows={5} withAction cardsOnMobile />
        </div>
      ) : null}

      {state.kind === "error" ? (
        <p role="alert" className="text-small text-verdict-contradiction-text">
          {state.message}
        </p>
      ) : null}

      {state.kind === "ready" ? (
        <>
          <UserRows users={state.users.slice.items} onChoose={setPending} />
          <Pagination
            slice={state.users.slice}
            pathname={pathname}
            query={searchParams.toString()}
            noun="usuarios"
            anchorId={LIST_ID}
          />
        </>
      ) : null}

      {pending ? (
        <ConfirmChange
          key={pending.user.id}
          pending={pending}
          onCancel={() => setPending(null)}
          onDone={() => {
            setPending(null);
            reload();
          }}
        />
      ) : null}
    </div>
  );
}

/** Total de un filtro; todavía no se conoce en la primera carga. */
function RoleCount({ counts, filter }: { counts: RoleCounts | null; filter: RoleFilter }) {
  return counts ? <span className="font-normal">{counts[filter]}</span> : null;
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
      <DataTableSkeleton columns={5} rows={5} withAction cardsOnMobile />
    </div>
  );
}
