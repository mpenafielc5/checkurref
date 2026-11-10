import { shareLabel } from "@/shared/lib/format";
import { VERDICT_ORDER, VERDICTS, type Verdict } from "@/shared/lib/verdicts";

type VerdictBreakdownProps = {
  counts: Record<Verdict, number>;
  /** Base del porcentaje: todas las referencias, también las que quedaron sin veredicto. */
  total: number;
};

/**
 * Veredictos en una barra dividida por colores, con su nombre, porcentaje y
 * cantidad al lado: el color nunca informa solo. La barra usa flexbox y ocupa el
 * ancho disponible, así que se ve completa en cualquier pantalla (HU-18 CA05).
 */
export function VerdictBreakdown({ counts, total }: VerdictBreakdownProps) {
  const present = VERDICT_ORDER.filter((verdict) => counts[verdict] > 0);

  return (
    <div className="flex flex-col gap-3">
      <div aria-hidden="true" className="flex h-4 w-full gap-0.5 overflow-hidden rounded-control">
        {present.map((verdict) => (
          <span
            key={verdict}
            className={`min-w-1 ${VERDICTS[verdict].swatchClass}`}
            style={{ flexGrow: counts[verdict] }}
          />
        ))}
      </div>
      <ul className="flex flex-col gap-1 text-small">
        {VERDICT_ORDER.map((verdict) => (
          <li key={verdict} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className={`size-3 shrink-0 rounded-row ${VERDICTS[verdict].swatchClass}`}
            />
            <span className="flex-1 text-ink">{VERDICTS[verdict].label}</span>
            <span className="tabular-nums">
              {shareLabel(counts[verdict], total)} ({counts[verdict]})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
