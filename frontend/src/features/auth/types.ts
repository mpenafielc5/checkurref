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

export type NavItem = {
  label: string;
  href: string;
};
