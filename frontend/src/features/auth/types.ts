import type { UserRole } from "@/shared/lib/supabase/database.types";

export type { UserRole };

export type Profile = {
  id: string;
  fullName: string;
  email: string;
  role: UserRole;
  career: string | null;
  active: boolean;
  /** Foto de la cuenta de Google; null si no tiene o no es de Google. */
  avatarUrl: string | null;
};

/** Ícono de cada opción del menú; SidebarNav lo traduce a su dibujo. */
export type NavIcon = "home" | "works" | "batches" | "help" | "lab" | "users";

export type NavItem = {
  label: string;
  href: string;
  icon: NavIcon;
};
