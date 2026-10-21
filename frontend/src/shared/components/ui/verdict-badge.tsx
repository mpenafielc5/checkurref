import { VERDICTS, type Verdict } from "@/shared/lib/verdicts";

/** Etiqueta de veredicto. El color siempre va acompañado del nombre. */
export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const info = VERDICTS[verdict];
  return (
    <span
      className={`inline-flex items-center rounded-pill px-3 py-0.5 text-caption font-semibold ${info.badgeClass}`}
    >
      {info.label}
    </span>
  );
}
