import type { ReactNode } from "react";

/** Etiqueta corta sobre un título: tipografía de código, mayúsculas, naranja oscuro. */
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono text-caption tracking-label text-accent-text uppercase">{children}</p>
  );
}
