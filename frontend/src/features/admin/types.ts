import type { PageSlice } from "@/shared/lib/pagination";
import type { UserRole } from "@/shared/lib/supabase/database.types";

export type { UserRole };

export type RoleFilter = UserRole | "todos";

export type RoleCounts = Record<RoleFilter, number>;

export type UserRow = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  active: boolean;
};

export type UsersPage = {
  slice: PageSlice<UserRow>;
  /** Totales por rol, sin el filtro de búsqueda. */
  counts: RoleCounts;
};

/** Solo se cambia entre estudiante y docente: nadie se vuelve administrador desde aquí. */
export type UserChange =
  { kind: "role"; role: "estudiante" | "docente" } | { kind: "active"; active: boolean };
