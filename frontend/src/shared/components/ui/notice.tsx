import { AlertTriangle, CircleAlert, Hourglass, Info, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type NoticeTone = "info" | "warning" | "wait" | "error";

const TONES: Record<NoticeTone, { icon: LucideIcon; classes: string }> = {
  info: { icon: Info, classes: "bg-info-soft text-info" },
  wait: { icon: Hourglass, classes: "bg-info-soft text-info" },
  warning: {
    icon: AlertTriangle,
    classes: "bg-verdict-discrepancy-soft text-verdict-discrepancy-text",
  },
  error: {
    icon: CircleAlert,
    classes: "bg-verdict-contradiction-soft text-verdict-contradiction-text",
  },
};

/**
 * Aviso breve con su ícono, para que no se pierda como una línea de texto suelta.
 * Un error lleva role="alert" para que el lector de pantalla lo anuncie.
 */
export function Notice({
  tone = "info",
  role,
  children,
}: {
  tone?: NoticeTone;
  role?: "status";
  children: ReactNode;
}) {
  const { icon: Icon, classes } = TONES[tone];
  return (
    <p
      role={tone === "error" ? "alert" : role}
      className={`flex items-start gap-2 rounded-control px-3 py-2 text-left text-small ${classes}`}
    >
      <Icon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

/** El backend gratuito se duerme sin uso: se avisa que despierta para que no parezca un error. */
export function WakingNotice() {
  return <Notice tone="wait">Iniciando el motor de análisis; puede tardar hasta un minuto.</Notice>;
}
