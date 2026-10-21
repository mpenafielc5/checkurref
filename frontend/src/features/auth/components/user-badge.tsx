import { LogOut } from "lucide-react";
import Image from "next/image";
import { initialsOf, ROLE_LABELS, shortDisplayName } from "../rules";
import type { Profile, UserRole } from "../types";

/** Color del avatar según el rol, como en las maquetas. */
const AVATAR_BY_ROLE: Record<UserRole, string> = {
  estudiante: "bg-accent-soft text-accent-text",
  docente: "bg-info-soft text-info",
  admin: "bg-surface-strong text-ink",
};

function SignOutButton({ compact = false }: { compact?: boolean }) {
  return (
    <form action="/auth/signout" method="post" className="flex">
      <button
        type="submit"
        aria-label="Cerrar sesión"
        className="flex items-center gap-2 rounded-control px-2 py-1 text-small text-body hover:text-ink"
      >
        <LogOut aria-hidden="true" className="size-5" />
        {compact ? null : <span>Salir</span>}
      </button>
    </form>
  );
}

function Avatar({ profile }: { profile: Profile }) {
  if (profile.avatarUrl) {
    return (
      <Image
        src={profile.avatarUrl}
        alt=""
        width={40}
        height={40}
        className="size-avatar shrink-0 rounded-pill object-cover"
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className={`flex size-avatar shrink-0 items-center justify-center rounded-pill text-small font-semibold ${AVATAR_BY_ROLE[profile.role]}`}
    >
      {initialsOf(profile.fullName)}
    </span>
  );
}

/** Bloque del usuario al pie de la barra lateral: avatar, nombre, rol y Salir. */
export function UserBadge({ profile }: { profile: Profile }) {
  return (
    <div className="flex flex-col gap-3 border-t border-hairline px-1 pt-4">
      <div className="flex items-center gap-3">
        <Avatar profile={profile} />
        <p className="flex min-w-0 flex-col">
          <span className="truncate text-small font-semibold text-ink" title={profile.fullName}>
            {shortDisplayName(profile.fullName)}
          </span>
          <span className="text-caption text-body">{ROLE_LABELS[profile.role]}</span>
        </p>
      </div>
      <SignOutButton />
    </div>
  );
}

/** Versión compacta para la barra superior en pantallas pequeñas. */
export function UserBadgeCompact({ profile }: { profile: Profile }) {
  return (
    <div className="flex items-center gap-2">
      <Avatar profile={profile} />
      <SignOutButton compact />
    </div>
  );
}
