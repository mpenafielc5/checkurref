import Link from "next/link";
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

const CHIP_CLASSES =
  "inline-flex items-center gap-2 rounded-pill border px-3 py-1 text-small whitespace-nowrap";
const CHIP_STATES = {
  selected: "border-action bg-action text-on-action",
  idle: "border-hairline-strong text-ink hover:border-ink",
  empty: "border-hairline text-muted-soft",
};

type FilterChipProps = {
  label: string;
  href: string;
  selected: boolean;
  /** Sin referencias con ese veredicto: se muestra, pero no se puede elegir. */
  empty?: boolean;
  swatchClass?: string;
};

/** Un filtro de la leyenda: enlace que cambia ?veredicto= sin mover la pantalla. */
function FilterChip({ label, href, selected, empty = false, swatchClass }: FilterChipProps) {
  const swatch = swatchClass ? (
    <span aria-hidden="true" className={`size-3 rounded-row ${swatchClass}`} />
  ) : null;

  if (empty) {
    return (
      <span aria-disabled="true" className={`${CHIP_CLASSES} ${CHIP_STATES.empty}`}>
        {swatch}
        {label}
      </span>
    );
  }
  return (
    <Link
      href={href}
      scroll={false}
      aria-current={selected ? "true" : undefined}
      className={`${CHIP_CLASSES} ${selected ? CHIP_STATES.selected : CHIP_STATES.idle}`}
    >
      {swatch}
      {label}
    </Link>
  );
}

type ReportSummaryProps = {
  index: number;
  counts: Record<Verdict, number>;
  /** Veredicto filtrado; null muestra todas. */
  active: Verdict | null;
  /** Dirección del informe con ese filtro (null: sin filtro). */
  filterHref: (verdict: Verdict | null) => string;
};

/**
 * Índice y distribución de veredictos del documento (maqueta 12). La leyenda
 * sirve también de filtro: tocar "1 contradicción" deja solo esa referencia.
 */
export function ReportSummary({ index, counts, active, filterHref }: ReportSummaryProps) {
  const total = VERDICT_ORDER.reduce((sum, verdict) => sum + counts[verdict], 0);

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
        <nav aria-label="Filtrar referencias por veredicto">
          <ul className="flex flex-wrap gap-2">
            <li className="flex">
              <FilterChip
                label={`Todas ${total}`}
                href={filterHref(null)}
                selected={active === null}
              />
            </li>
            {VERDICT_ORDER.map((verdict) => (
              <li key={verdict} className="flex">
                <FilterChip
                  label={`${counts[verdict]} ${LEGEND_LABELS[verdict]}`}
                  href={filterHref(verdict)}
                  selected={active === verdict}
                  empty={counts[verdict] === 0}
                  swatchClass={VERDICTS[verdict].swatchClass}
                />
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </section>
  );
}
