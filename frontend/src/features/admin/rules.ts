import { displayFullName } from "@/shared/lib/names";
import type { RoleFilter, UserChange, UserRole, UserRow } from "./types";

export const ROLE_PARAM = "rol";
export const SEARCH_PARAM = "buscar";

export const ROLE_LABELS: Record<UserRole, string> = {
  estudiante: "Estudiante",
  docente: "Docente",
  admin: "Admin",
};

const FILTERS: RoleFilter[] = ["todos", "estudiante", "docente", "admin"];

/** Lee el filtro de la dirección; cualquier valor desconocido es "todos". */
export function parseRoleFilter(raw: string | null | undefined): RoleFilter {
  return FILTERS.find((filter) => filter === raw) ?? "todos";
}

/**
 * Las cuentas de administrador no se modifican desde esta pantalla, y eso incluye
 * la propia (HU-11 CA04). La API aplica la misma regla.
 */
export function canManage(user: UserRow): boolean {
  return user.role !== "admin";
}

export function roleChangeOf(user: UserRow): UserChange {
  return { kind: "role", role: user.role === "estudiante" ? "docente" : "estudiante" };
}

export function activeChangeOf(user: UserRow): UserChange {
  return { kind: "active", active: !user.active };
}

export type Confirmation = {
  title: string;
  message: string;
  confirmLabel: string;
};

/** Qué se pregunta antes de aplicar un cambio (HU-11 CA02 y CA03). */
export function confirmationOf(user: UserRow, change: UserChange): Confirmation {
  const name = displayFullName(user.name);
  if (change.kind === "role") {
    return {
      title: "Cambiar el rol",
      message:
        change.role === "docente"
          ? `${name} pasará de Estudiante a Docente y tendrá acceso a las funciones del docente.`
          : `${name} pasará de Docente a Estudiante. Sus lotes se conservan, pero no podrá consultarlos mientras tenga este rol.`,
      confirmLabel: "Cambiar rol",
    };
  }
  return change.active
    ? {
        title: "Reactivar la cuenta",
        message: `${name} podrá iniciar sesión nuevamente con el rol de ${ROLE_LABELS[user.role]}.`,
        confirmLabel: "Reactivar",
      }
    : {
        title: "Desactivar la cuenta",
        message: `${name} no podrá iniciar sesión. Sus trabajos se conservan.`,
        confirmLabel: "Desactivar",
      };
}
