import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description?: string;
  /** Acción para salir del estado vacío, por ejemplo subir el primer trabajo. */
  children?: ReactNode;
};

/**
 * Lo que se muestra cuando no hay nada que listar: un ícono, qué pasa y qué hacer.
 * Reemplaza a las líneas de texto sueltas, que se pierden en la pantalla.
 */
export function EmptyState({ icon: Icon, title, description, children }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-hairline bg-canvas px-6 py-10 text-center">
      <span className="flex size-12 items-center justify-center rounded-pill bg-accent-soft text-primary">
        <Icon aria-hidden="true" className="size-6" />
      </span>
      <p className="font-semibold text-ink">{title}</p>
      {description ? <p className="max-w-md text-small">{description}</p> : null}
      {children ? <div className="mt-1 flex flex-wrap justify-center gap-2">{children}</div> : null}
    </div>
  );
}
