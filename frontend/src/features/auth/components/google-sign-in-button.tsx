"use client";

import { LogIn } from "lucide-react";
import { useState } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { createSupabaseBrowserClient } from "@/shared/lib/supabase/client";
import { INSTITUTIONAL_DOMAIN } from "../rules";

type GoogleSignInButtonProps = {
  label?: string;
  variant?: "primary" | "secondary";
  fullWidth?: boolean;
  withIcon?: boolean;
};

/**
 * Inicia el acceso con Google. La tarjeta "Ingresar" lo usa con su estilo por
 * defecto; el botón "Revisar mi trabajo" de la página pública, como acción
 * principal.
 */
export function GoogleSignInButton({
  label = "Continuar con Google",
  variant = "secondary",
  fullWidth = true,
  withIcon = true,
}: GoogleSignInButtonProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setPending(true);
    setError(null);

    const supabase = createSupabaseBrowserClient();
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        // hd hace que Google muestre solo cuentas del dominio institucional.
        queryParams: { hd: INSTITUTIONAL_DOMAIN, prompt: "select_account" },
      },
    });

    if (signInError) {
      setError("No se pudo conectar con Google. Intenta de nuevo.");
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        aria-busy={pending}
        className={buttonStyles({ variant, fullWidth })}
      >
        {withIcon ? <LogIn aria-hidden="true" className="size-5" /> : null}
        {pending ? "Redirigiendo a Google…" : label}
      </button>
      {error ? (
        <p role="alert" className="text-small text-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
