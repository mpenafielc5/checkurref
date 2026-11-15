import Link from "next/link";
import { formatIndex } from "@/shared/lib/format";
import { INDEX_LEVELS, type IndexLevel, indexExplanation } from "@/shared/lib/truthfulness";
import { VERDICT_ORDER, VERDICTS, type Verdict } from "@/shared/lib/verdicts";
import { Notice } from "@/shared/components/ui/notice";
import { StatusChip } from "@/shared/components/ui/status-chip";
import { cardStyles } from "@/shared/components/ui/card-styles";

const RING_RADIUS = 40;
// Largo del trazo del anillo en las mismas unidades que el índice: 40 es 40 de 100.
const RING_LENGTH = 100;

/** Cada filtro con su cantidad, que concuerda en número: [una, varias o ninguna]. */
const LEGEND_LABELS: Record<Verdict, [string, string]> = {
  verificada: ["verificada", "verificadas"],
  discrepancia: ["con discrepancias", "con discrepancias"],
  contradiccion: ["contradicción", "contradicciones"],
  sin_respaldo: ["sin respaldo", "sin respaldo"],
  no_verificable: ["no verificable", "no verificables"],
};

/**
 * Anillo con el índice de veracidad de 0 a 100, del color de su nivel: verde,
 * ámbar o rojo. Sin índice, vacío y con una raya.
 */
function IndexRing({ index, level }: { index: number | null; level: IndexLevel | null }) {
  // Sin nivel (un informe anterior a que la API lo enviara), un trazo neutro.
  const strokeClass = level ? INDEX_LEVELS[level].strokeClass : "stroke-hairline-strong";
  return (
    <div className="relative flex size-24 shrink-0 items-center justify-center">
      <svg
        viewBox="0 0 96 96"
        role="img"
        aria-label={
          index === null
            ? "Sin índice de veracidad"
            : `Índice de veracidad: ${formatIndex(index)} de 100`
        }
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
          pathLength={RING_LENGTH}
          strokeDasharray={`${index ?? 0} ${RING_LENGTH}`}
          transform="rotate(-90 48 48)"
          className={`${strokeClass} animate-ring-fill`}
        />
      </svg>
      <span aria-hidden="true" className="text-display-sm font-bold tracking-normal text-ink">
        {index === null ? "—" : formatIndex(index)}
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

/** Qué significa el número: nivel, cuántas verificadas sobre cuántas y qué hacer. */
function IndexMeaning({ level, counts }: { level: IndexLevel; counts: Record<Verdict, number> }) {
  const info = INDEX_LEVELS[level];
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-small">
      <StatusChip tone={info.tone}>{info.label}</StatusChip>
      <span>
        {indexExplanation(counts)} {info.advice}
      </span>
    </p>
  );
}

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
  index: number | null;
  /** Nivel del índice que calcula el backend. */
  level: IndexLevel | null;
  counts: Record<Verdict, number>;
  /** Referencias sin veredicto por un error de consulta: están en la lista, no en el índice. */
  queryErrors?: number;
  /** Veredicto filtrado; null muestra todas. */
  active: Verdict | null;
  /** Dirección del informe con ese filtro (null: sin filtro). */
  filterHref: (verdict: Verdict | null) => string;
};

/**
 * Índice y distribución de veredictos del documento (maqueta 12). La leyenda
 * sirve también de filtro: tocar "1 contradicción" deja solo esa referencia.
 */
export function ReportSummary({
  index,
  level,
  counts,
  queryErrors = 0,
  active,
  filterHref,
}: ReportSummaryProps) {
  const total = VERDICT_ORDER.reduce((sum, verdict) => sum + counts[verdict], queryErrors);

  return (
    <section
      aria-label="Resumen del informe"
      className={`flex flex-col items-start gap-6 ${cardStyles({ size: "panel" })} px-6 py-4 sm:flex-row sm:items-center`}
    >
      <IndexRing index={index} level={level} />
      <div className="flex w-full flex-1 flex-col gap-3">
        {level ? <IndexMeaning level={level} counts={counts} /> : null}
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
                  label={`${counts[verdict]} ${LEGEND_LABELS[verdict][counts[verdict] === 1 ? 0 : 1]}`}
                  href={filterHref(verdict)}
                  selected={active === verdict}
                  empty={counts[verdict] === 0}
                  swatchClass={VERDICTS[verdict].swatchClass}
                />
              </li>
            ))}
          </ul>
        </nav>
        {queryErrors > 0 ? (
          <Notice tone="warning">
            {queryErrors === 1
              ? "1 referencia quedó sin verificar porque una fuente no respondió; no cuenta en el índice."
              : `${queryErrors} referencias quedaron sin verificar porque una fuente no respondió; no cuentan en el índice.`}
          </Notice>
        ) : null}
      </div>
    </section>
  );
}
