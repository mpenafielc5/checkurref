import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { AccessCard } from "@/features/auth/components/access-card";
import { Wordmark } from "@/shared/components/ui/wordmark";

export const metadata: Metadata = {
  title: "Ingresar · CheckUrRef",
};

/**
 * Acceso con la cuenta institucional. También es el destino cuando el ingreso
 * falla (?error=…): desde aquí se reintenta o se vuelve a la página pública.
 */
export default function LoginPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 bg-surface px-4 py-12">
      <Wordmark />
      <AccessCard headingLevel="h1" />
      <Link href="/" className="flex items-center gap-1.5 text-small text-body hover:text-ink">
        <ArrowLeft aria-hidden="true" className="size-4" />
        Volver a la página principal
      </Link>
    </main>
  );
}
