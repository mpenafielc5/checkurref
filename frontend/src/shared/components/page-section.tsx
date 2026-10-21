import type { ReactNode } from "react";
import { Eyebrow } from "./ui/eyebrow";

type PageSectionProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
};

/** Encabezado y contenedor estándar de una pantalla interna. */
export function PageSection({ title, eyebrow, description, actions, children }: PageSectionProps) {
  return (
    <section
      aria-labelledby="titulo-pagina"
      className="flex w-full max-w-content flex-col gap-6 px-4 py-6 md:px-8 md:py-10"
    >
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-2">
          {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
          <h1 id="titulo-pagina" className="text-display-sm md:text-display-md">
            {title}
          </h1>
          {description ? <p className="max-w-2xl">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}

/** Marcador de posición mientras se verifica la sesión. */
export function PageSectionSkeleton() {
  return (
    <section className="flex w-full max-w-content flex-col gap-2 px-4 py-6 md:px-8 md:py-10">
      <p className="text-small text-muted">Cargando…</p>
    </section>
  );
}
