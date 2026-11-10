import type { ConfirmTone } from "@/shared/components/ui/confirm-dialog";
import { displayFullName } from "@/shared/lib/names";
import type { RoleFilter, UserChange, UserRole, UserRow } from "./types";

export const ROLE_PARAM = "rol";
export const SEARCH_PARAM = "buscar";

export const ROLE_LABELS: Record<UserRole, string> = {
  estudiante: "Estudiante",
  docente: "Docente",
  admin: "Administrador",
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
  tone: ConfirmTone;
};

/** Qué se pregunta antes de aplicar un cambio: el efecto, en una frase (HU-11 CA02 y CA03). */
export function confirmationOf(user: UserRow, change: UserChange): Confirmation {
  const name = displayFullName(user.name);
  if (change.kind === "role") {
    return change.role === "docente"
      ? {
          title: "¿Cambiar a Docente?",
          message: `${name} podrá crear lotes de auditoría y dejará de ver Mis trabajos.`,
          confirmLabel: "Cambiar a Docente",
          tone: "default",
        }
      : {
          title: "¿Cambiar a Estudiante?",
          message: `${name} ya no podrá ver sus lotes. Se conservan por si vuelve a ser docente.`,
          confirmLabel: "Cambiar a Estudiante",
          tone: "default",
        };
  }
  return change.active
    ? {
        title: "¿Reactivar esta cuenta?",
        message: `${name} podrá iniciar sesión nuevamente.`,
        confirmLabel: "Reactivar cuenta",
        tone: "restore",
      }
    : {
        title: "¿Desactivar esta cuenta?",
        message: `${name} no podrá iniciar sesión. Sus trabajos se conservan y puedes reactivarla cuando lo necesites.`,
        confirmLabel: "Desactivar cuenta",
        tone: "danger",
      };
}
