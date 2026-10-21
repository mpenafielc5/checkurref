import type { NavItem, UserRole } from "./types";

/** Dominio institucional permitido. La base de datos aplica la misma regla. */
export const INSTITUTIONAL_DOMAIN = "unemi.edu.ec";

export function isInstitutionalEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  return email.trim().toLowerCase().endsWith(`@${INSTITUTIONAL_DOMAIN}`);
}

const HOME_BY_ROLE: Record<UserRole, string> = {
  estudiante: "/estudiante",
  docente: "/docente",
  admin: "/admin",
};

export function homePathForRole(role: UserRole): string {
  return HOME_BY_ROLE[role];
}

export const ROLE_LABELS: Record<UserRole, string> = {
  estudiante: "Estudiante",
  docente: "Docente",
  admin: "Administrador",
};

/** Menú principal de cada rol (decisión 12 del documento de decisiones). */
const NAV_BY_ROLE: Record<UserRole, NavItem[]> = {
  estudiante: [
    { label: "Inicio", href: "/estudiante" },
    { label: "Mis trabajos", href: "/estudiante/trabajos" },
    { label: "Ayuda", href: "/ayuda" },
  ],
  docente: [
    { label: "Inicio", href: "/docente" },
    { label: "Lotes", href: "/docente/lotes" },
    { label: "Ayuda", href: "/ayuda" },
  ],
  admin: [
    { label: "Inicio", href: "/admin" },
    { label: "Laboratorio", href: "/admin/laboratorio" },
    { label: "Usuarios", href: "/admin/usuarios" },
  ],
};

export function navItemsForRole(role: UserRole): NavItem[] {
  return NAV_BY_ROLE[role];
}

function capitalize(word: string): string {
  const lower = word.toLocaleLowerCase("es");
  return lower.charAt(0).toLocaleUpperCase("es") + lower.slice(1);
}

/**
 * Separa el nombre completo en nombre y primer apellido.
 * Con cuatro palabras (dos nombres y dos apellidos) el apellido es la tercera;
 * con dos o tres, la segunda.
 */
function splitName(fullName: string): { first: string; surname: string | null } {
  const words = fullName.trim().split(/\s+/).filter(Boolean).map(capitalize);
  const first = words[0] ?? "";
  if (words.length >= 4) return { first, surname: words[2] };
  if (words.length >= 2) return { first, surname: words[1] };
  return { first, surname: null };
}

/** Nombre corto para la barra lateral, por ejemplo "Miguel P.". */
export function shortDisplayName(fullName: string): string {
  const { first, surname } = splitName(fullName);
  return surname ? `${first} ${surname.charAt(0)}.` : first;
}

/** Iniciales para el avatar, por ejemplo "MP". */
export function initialsOf(fullName: string): string {
  const { first, surname } = splitName(fullName);
  return `${first.charAt(0)}${surname?.charAt(0) ?? ""}`;
}

/** Dominio desde el que Google sirve las fotos de perfil (permitido en next.config.ts). */
const GOOGLE_PHOTO_HOST = "googleusercontent.com";

/**
 * Devuelve la URL de la foto solo si es una dirección https de Google.
 * Cualquier otro valor se descarta y se muestran las iniciales.
 */
export function safeAvatarUrl(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  try {
    const url = new URL(raw);
    const fromGoogle =
      url.hostname === GOOGLE_PHOTO_HOST || url.hostname.endsWith(`.${GOOGLE_PHOTO_HOST}`);
    return url.protocol === "https:" && fromGoogle ? url.toString() : null;
  } catch {
    return null;
  }
}

export type LoginErrorCode = "dominio" | "inactiva" | "oauth";

export const LOGIN_ERROR_MESSAGES: Record<LoginErrorCode, string> = {
  dominio: "Solo se permiten cuentas institucionales @unemi.edu.ec.",
  inactiva: "Tu cuenta está desactivada. Comunícate con el administrador.",
  oauth: "No se pudo iniciar sesión con Google. Intenta de nuevo.",
};

export function loginErrorMessage(code: string | null): string | null {
  if (code && code in LOGIN_ERROR_MESSAGES) {
    return LOGIN_ERROR_MESSAGES[code as LoginErrorCode];
  }
  return null;
}

/**
 * Supabase cancela el registro cuando el disparador de la base de datos
 * rechaza el dominio; en ese caso devuelve este mensaje genérico.
 */
export function errorCodeFromOAuthFailure(description: string | null): LoginErrorCode {
  return description?.includes("Database error saving new user") ? "dominio" : "oauth";
}
