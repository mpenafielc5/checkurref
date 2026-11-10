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

type StatusChipProps = {
  tone: ChipTone;
  /** Ancho fijo, para que los estados de una misma columna midan lo mismo. */
  widthClass?: string;
  children: ReactNode;
};

/** Etiqueta de estado en forma de píldora. */
export function StatusChip({ tone, widthClass = "", children }: StatusChipProps) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-pill px-3 py-0.5 text-caption font-semibold whitespace-nowrap ${widthClass} ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}
