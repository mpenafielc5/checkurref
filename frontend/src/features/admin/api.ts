import { apiGet, apiPatch } from "@/shared/lib/api-client";
import { detailOf } from "@/shared/lib/pdf-upload";
import { toUsersPage } from "./user-mapper";
import type { RoleFilter, UserChange, UsersPage } from "./types";

const SESSION_ERROR = "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo.";
const LOAD_ERROR = "No se pudo cargar la lista de usuarios. Intenta de nuevo en unos minutos.";
const UPDATE_ERROR = "No se pudo aplicar el cambio. Intenta de nuevo en unos minutos.";

export type UsersOutcome = { kind: "ready"; users: UsersPage } | { kind: "error"; message: string };

export async function fetchUsers(
  page: number,
  search: string,
  role: RoleFilter,
  onSlow: () => void,
): Promise<UsersOutcome> {
  const params = new URLSearchParams({ pagina: String(page) });
  if (search) params.set("buscar", search);
  if (role !== "todos") params.set("rol", role);

  const response = await apiGet(`/usuarios?${params.toString()}`, onSlow);
  if (response.kind === "failed") {
    return { kind: "error", message: response.reason === "session" ? SESSION_ERROR : LOAD_ERROR };
  }
  const users = response.status === 200 ? toUsersPage(response.body) : null;
  return users ? { kind: "ready", users } : { kind: "error", message: LOAD_ERROR };
}

export type UserUpdateOutcome = { kind: "updated" } | { kind: "error"; message: string };

/** Aplica el cambio. Una regla incumplida (409) llega con su motivo. */
export async function updateUser(userId: string, change: UserChange): Promise<UserUpdateOutcome> {
  const payload = change.kind === "role" ? { role: change.role } : { active: change.active };
  const response = await apiPatch(`/usuarios/${encodeURIComponent(userId)}`, payload);
  if (response.kind === "failed") {
    return {
      kind: "error",
      message: response.reason === "session" ? SESSION_ERROR : UPDATE_ERROR,
    };
  }
  if (response.status === 200) return { kind: "updated" };
  return { kind: "error", message: detailOf(response.body) ?? UPDATE_ERROR };
}
