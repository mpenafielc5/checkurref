import type { ReactNode } from "react";

export type ChipTone = "success" | "warning" | "danger" | "unsupported" | "neutral" | "info";

/** Colores de las maquetas: fondo suave y texto oscuro del mismo tono. */
const TONES: Record<ChipTone, string> = {
  success: "bg-verdict-verified-soft text-verdict-verified-text",
  warning: "bg-verdict-discrepancy-soft text-verdict-discrepancy-text",
  danger: "bg-verdict-contradiction-soft text-verdict-contradiction-text",
  unsupported: "bg-verdict-unsupported-soft text-verdict-unsupported-text",
  neutral: "bg-hairline-soft text-ink",
  info: "bg-info-soft text-info",
};

/** Etiqueta de estado en forma de píldora. */
export function StatusChip({ tone, children }: { tone: ChipTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-pill px-3 py-0.5 text-caption font-semibold whitespace-nowrap ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}
