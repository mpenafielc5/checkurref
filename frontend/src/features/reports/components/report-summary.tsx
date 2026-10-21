import { VERDICT_ORDER, VERDICTS, type Verdict } from "@/shared/lib/verdicts";

const RING_RADIUS = 40;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

const LEGEND_LABELS: Record<Verdict, string> = {
  verificada: "verificadas",
  discrepancia: "con discrepancias",
  contradiccion: "contradicción",
  sin_respaldo: "sin respaldo",
  no_verificable: "no verificables",
};

/** Anillo con el índice de veracidad de 0 a 100. */
function IndexRing({ index }: { index: number }) {
  const filled = (index / 100) * RING_CIRCUMFERENCE;
  return (
    <div className="relative flex size-24 shrink-0 items-center justify-center">
      <svg
        viewBox="0 0 96 96"
        role="img"
        aria-label={`Índice de veracidad: ${index} de 100`}
        className="absolute inset-0 size-24"
      >
        <circle
          cx="48"
          cy="48"
          r={RING_RADIUS}
          fill="none"
          strokeWidth="10"
          className="stroke-hairline"
        />
        <circle
          cx="48"
          cy="48"
          r={RING_RADIUS}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${RING_CIRCUMFERENCE}`}
          transform="rotate(-90 48 48)"
          className="stroke-verdict-verified"
        />
      </svg>
      <span aria-hidden="true" className="text-display-sm font-bold tracking-normal text-ink">
        {index}
      </span>
    </div>
  );
}

/** Índice y distribución de veredictos del documento (maqueta 12). */
export function ReportSummary({
  index,
  counts,
}: {
  index: number;
  counts: Record<Verdict, number>;
}) {
  return (
    <section
      aria-label="Resumen del informe"
      className="flex flex-col items-start gap-6 rounded-panel border border-hairline bg-canvas px-6 py-4 sm:flex-row sm:items-center"
    >
      <IndexRing index={index} />
      <div className="flex w-full flex-1 flex-col gap-3">
        <div aria-hidden="true" className="flex h-4 overflow-hidden rounded-control">
          {VERDICT_ORDER.map((verdict) => (
            <span
              key={verdict}
              className={VERDICTS[verdict].swatchClass}
              style={{ flexGrow: counts[verdict] }}
            />
          ))}
        </div>
        <ul className="flex flex-wrap gap-x-6 gap-y-2 text-small text-ink">
          {VERDICT_ORDER.map((verdict) => (
            <li key={verdict} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`size-4 rounded-row ${VERDICTS[verdict].swatchClass}`}
              />
              {counts[verdict]} {LEGEND_LABELS[verdict]}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
