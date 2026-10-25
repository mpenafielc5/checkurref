/*
 * Datos de ejemplo de la maqueta 19. Se reemplazan por los perfiles reales de
 * Supabase en HU-11.
 */
import type { UserRole } from "@/shared/lib/supabase/database.types";

export type UserRow = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
};

export const SAMPLE_ROLE_COUNTS: Record<UserRole | "todos", number> = {
  todos: 128,
  estudiante: 112,
  docente: 14,
  admin: 2,
};

export const SAMPLE_USERS: UserRow[] = [
  { id: "u1", name: "Ana Torres", email: "atorres@unemi.edu.ec", role: "docente" },
  { id: "u2", name: "Docente Demo", email: "docente.demo@unemi.edu.ec", role: "docente" },
  { id: "u3", name: "Luis Mendoza", email: "lmendoza@unemi.edu.ec", role: "estudiante" },
  { id: "u4", name: "Carla Ruiz", email: "cruiz@unemi.edu.ec", role: "estudiante" },
  { id: "u5", name: "Paola Rivas", email: "privas@unemi.edu.ec", role: "admin" },
];

export const SAMPLE_ADMIN_STATS = {
  users: "128",
  analysesToday: "37",
  goldSet: "150",
  lastBenchmark: "09/10",
};
