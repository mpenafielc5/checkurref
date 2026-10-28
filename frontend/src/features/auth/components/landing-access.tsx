import Link from "next/link";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { getCurrentProfile } from "../api";
import { homePathForRole, ROLE_LABELS } from "../rules";
import { AccessCard } from "./access-card";
import { GoogleSignInButton } from "./google-sign-in-button";
import { SignOutButton } from "./user-badge";

/**
 * Tarjeta de acceso de la página pública. Si ya hay sesión, muestra la cuenta
 * y un enlace al inicio en lugar del botón de Google.
 */
export async function LandingAccessCard() {
  const profile = await getCurrentProfile();
  if (!profile) return <AccessCard />;

  return (
    <section
      id="ingresar"
      aria-labelledby="titulo-cuenta"
      className="flex w-full flex-col gap-4 rounded-panel border border-hairline bg-canvas p-6 md:max-w-sm"
    >
      <h2 id="titulo-cuenta" className="text-title font-semibold tracking-normal">
        Sesión iniciada
      </h2>
      <p className="text-small">
        Ingresaste como <strong className="text-ink">{profile.fullName}</strong> (
        {ROLE_LABELS[profile.role]}).
      </p>
      <Link href={homePathForRole(profile.role)} className={buttonStyles({ fullWidth: true })}>
        Ir al inicio
      </Link>
      <SignOutButton />
    </section>
  );
}

/**
 * "Revisar mi trabajo": con sesión lleva al inicio del rol; sin sesión abre
 * directamente el acceso con Google, sin pasar por la tarjeta.
 */
export async function ReviewWorkAction({ children }: { children: string }) {
  const profile = await getCurrentProfile();
  if (!profile) return <ReviewWorkActionFallback>{children}</ReviewWorkActionFallback>;

  return (
    <Link href={homePathForRole(profile.role)} className={buttonStyles()}>
      {children}
    </Link>
  );
}

/** Versión sin sesión, también usada mientras se comprueba la sesión. */
export function ReviewWorkActionFallback({ children }: { children: string }) {
  return (
    <GoogleSignInButton label={children} variant="primary" fullWidth={false} withIcon={false} />
  );
}
