import { Info } from "lucide-react";

/**
 * Aviso visible en las pantallas que todavía muestran datos de ejemplo.
 * Indica en qué historia de usuario se conectan los datos reales.
 */
export function SampleDataNotice({ story }: { story: string }) {
  return (
    <p className="flex w-full items-start gap-2 rounded-card border border-info-soft bg-info-soft px-4 py-2 text-small text-info">
      <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span>
        <strong>Datos de ejemplo.</strong> Esta pantalla se conecta con datos reales en {story}.
      </span>
    </p>
  );
}
