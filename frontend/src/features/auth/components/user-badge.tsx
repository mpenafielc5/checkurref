import { LogOut } from "lucide-react";
import { initialsOf, ROLE_LABELS, shortDisplayName } from "../rules";
import type { Profile, UserRole } from "../types";
import { AvatarPhoto } from "./avatar-photo";
import { REVEAL_ON_EXPAND } from "./sidebar-reveal";

/** Color del avatar según el rol, como en las maquetas. */
const AVATAR_BY_ROLE: Record<UserRole, string> = {
  estudiante: "bg-accent-soft text-accent-text",
  docente: "bg-info-soft text-info",
  admin: "bg-surface-strong text-ink",
};

export function SignOutButton({ labelClass }: { labelClass?: string }) {
  return (
    <form action="/auth/signout" method="post" className="flex">
      <button
        type="submit"
        className="flex w-full items-center gap-3 rounded-control px-3 py-2 text-small text-body transition-colors hover:bg-hairline-soft hover:text-ink"
      >
        <LogOut aria-hidden="true" className="size-5 shrink-0" />
        <span className={labelClass}>Salir</span>
      </button>
    </form>
  );
}

/** small: del tamaño de los íconos del menú (pestaña Cuenta del celular). */
export function Avatar({ profile, small = false }: { profile: Profile; small?: boolean }) {
  const sizeClass = small ? "size-6" : "size-avatar";
  const initials = (
    <span
      aria-hidden="true"
      className={`flex ${sizeClass} shrink-0 items-center justify-center rounded-pill font-semibold ${
        small ? "text-label" : "text-small"
      } ${AVATAR_BY_ROLE[profile.role]}`}
    >
      {initialsOf(profile.fullName)}
    </span>
  );

  return profile.avatarUrl ? (
    <AvatarPhoto src={profile.avatarUrl} fallback={initials} sizeClass={sizeClass} />
  ) : (
    initials
  );
}

/** Nombre corto y rol, uno debajo del otro. */
function NameAndRole({ profile, className = "" }: { profile: Profile; className?: string }) {
  return (
    <p className={`flex min-w-0 flex-col ${className}`}>
      <span className="truncate text-small font-semibold text-ink" title={profile.fullName}>
        {shortDisplayName(profile.fullName)}
      </span>
      <span className="text-caption text-body">{ROLE_LABELS[profile.role]}</span>
    </p>
  );
}

/**
 * Bloque del usuario al pie de la barra lateral: avatar, nombre, rol y Salir.
 * Contraída, solo se ven el avatar y el ícono de Salir. En el celular, lo
 * mismo está en la pantalla Mi cuenta (AccountView).
 */
export function UserBadge({ profile }: { profile: Profile }) {
  return (
    <div className="flex flex-col gap-3 border-t border-hairline pt-4">
      {/* px-0.5: el centro del avatar coincide con el de los íconos del menú */}
      <div className="flex items-center gap-3 px-0.5">
        <Avatar profile={profile} />
        <NameAndRole profile={profile} className={REVEAL_ON_EXPAND} />
      </div>
      <SignOutButton labelClass={REVEAL_ON_EXPAND} />
    </div>
  );
}
