import { Suspense } from "react";
import { GoogleSignInButton } from "./google-sign-in-button";
import { LoginError } from "./login-error";
import { cardStyles } from "@/shared/components/ui/card-styles";

type AccessCardProps = {
  headingLevel?: "h1" | "h2";
};

/** Tarjeta de acceso con la cuenta institucional (maqueta 01). */
export function AccessCard({ headingLevel = "h2" }: AccessCardProps) {
  const Heading = headingLevel;

  return (
    <section
      id="ingresar"
      aria-labelledby="titulo-ingresar"
      className={`flex w-full flex-col gap-4 ${cardStyles({ size: "panel" })} p-6 md:max-w-sm`}
    >
      <Heading id="titulo-ingresar" className="text-title font-semibold tracking-normal">
        Ingresar
      </Heading>

      <Suspense>
        <LoginError />
      </Suspense>

      <GoogleSignInButton />

      <p className="text-caption text-body">
        Solo cuentas institucionales <strong className="text-ink">@unemi.edu.ec</strong>. En tu
        primer ingreso, la cuenta se crea automáticamente con el rol de estudiante.
      </p>
    </section>
  );
}
