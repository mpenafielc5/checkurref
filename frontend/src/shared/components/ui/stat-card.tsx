import type { ReactNode } from "react";
import { SkeletonText } from "./skeleton";

type StatTone = "default" | "success" | "danger" | "warning";

const VALUE_TONES: Record<StatTone, string> = {
  default: "text-ink",
  success: "text-verdict-verified-text",
  danger: "text-verdict-contradiction-text",
  warning: "text-verdict-discrepancy-text",
};

/** Caja compartida por la tarjeta y su esqueleto, para que midan lo mismo. */
const CARD_CLASSES =
  "flex w-full flex-col gap-0.5 rounded-card border border-hairline bg-canvas px-5 py-3 md:w-stat-half lg:w-auto lg:flex-1 lg:basis-0";
const VALUE_TEXT = "text-display-sm font-bold tracking-normal";
const LABEL_TEXT = "text-small";

type StatCardProps = {
  value: string;
  label: string;
  tone?: StatTone;
};

/** Indicador numérico. Solo informa: no es clicable. */
export function StatCard({ value, label, tone = "default" }: StatCardProps) {
  return (
    <div className={CARD_CLASSES}>
      <p className={`${VALUE_TEXT} ${VALUE_TONES[tone]}`}>{value}</p>
      <p className={`${LABEL_TEXT} text-body`}>{label}</p>
    </div>
  );
}

/** Esqueleto de StatCard: mismo borde, mismo relleno y una línea por texto. */
export function StatCardSkeleton() {
  return (
    <div className={CARD_CLASSES}>
      <SkeletonText textClass={VALUE_TEXT} widthClass="w-16" />
      <SkeletonText textClass={LABEL_TEXT} widthClass="w-28" />
    </div>
  );
}

/**
 * Fila de indicadores con flexbox: una columna en el celular, dos en tableta y
 * todos en una fila con el mismo ancho en escritorio.
 */
export function StatRow({ children }: { children: ReactNode }) {
  return <div className="flex w-full flex-wrap gap-4">{children}</div>;
}

/** Fila de esqueletos con la cantidad de tarjetas que tendrá la pantalla. */
export function StatRowSkeleton({ count }: { count: number }) {
  return (
    <StatRow>
      {Array.from({ length: count }, (_, index) => (
        <StatCardSkeleton key={index} />
      ))}
    </StatRow>
  );
}
