"use client";

import { buttonStyles } from "@/shared/components/ui/button-styles";
import {
  DataTable,
  numericClass,
  tableHeadClass,
  tdClass,
  thClass,
} from "@/shared/components/ui/data-table";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { StatCard, StatRow, StatRowSkeleton } from "@/shared/components/ui/stat-card";
import { formatDateTime, formatDecimal } from "@/shared/lib/format";
import { fieldLabel } from "@/shared/lib/reference-fields";
import {
  ENGINE_NAMES,
  type BenchmarkOverview,
  type BenchmarkRun,
  type EngineScores,
} from "../types";
import { useBenchmark } from "../use-benchmark";
import { BenchmarkChart } from "./benchmark-chart";

const SLOW_MESSAGE = "Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.";

function points(difference: number): string {
  return formatDecimal(difference * 100, 1);
}

function DecisionRule({
  overview,
  latest,
}: {
  overview: BenchmarkOverview;
  latest?: BenchmarkRun;
}) {
  const fields = new Intl.ListFormat("es", { type: "conjunction" }).format(
    overview.keyFields.map(fieldLabel),
  );
  return (
    <section
      aria-labelledby="titulo-regla"
      className="flex flex-col gap-1 rounded-card border border-hairline bg-canvas px-5 py-4 text-small"
    >
      <h3 id="titulo-regla" className="text-small font-semibold tracking-normal text-ink">
        Regla de decisión
      </h3>
      <p>
        Gana el motor con mayor F1 promedio en {fields}, los campos con los que se busca cada
        referencia en Crossref y OpenAlex. Si la diferencia es menor de{" "}
        {Math.round(overview.tieMargin * 100)} puntos, se declara empate y se mantiene AnyStyle.
      </p>
      {latest ? (
        <p className="font-semibold text-ink">
          {latest.tie
            ? `Última medición: empate con ${points(latest.difference)} puntos de diferencia; se mantiene ${ENGINE_NAMES[latest.selectedEngine]}.`
            : `Última medición: gana ${ENGINE_NAMES[latest.selectedEngine]} con ${points(latest.difference)} puntos de diferencia.`}
        </p>
      ) : null}
    </section>
  );
}

function bestOf(first: number, second: number, engines: EngineScores[]): string {
  if (first === second) return "Empate";
  return ENGINE_NAMES[first > second ? engines[0].engine : engines[1].engine];
}

/** Precisión, exhaustividad y F1 de cada motor por campo (HU-12 CA01). */
function ScoresTable({ run, keyFields }: { run: BenchmarkRun; keyFields: string[] }) {
  const [first, second] = run.engines;
  if (!first || !second) return null;
  return (
    <div className="flex flex-col gap-2">
      <DataTable caption="Precisión, exhaustividad y F1 por campo de cada motor">
        <thead className={tableHeadClass}>
          <tr>
            <th scope="col" className={thClass}>
              Campo
            </th>
            {run.engines.flatMap((engine) =>
              ["P", "R", "F1"].map((metric) => (
                <th
                  key={`${engine.engine}-${metric}`}
                  scope="col"
                  className={`${thClass} ${numericClass}`}
                >
                  {ENGINE_NAMES[engine.engine]} {metric}
                </th>
              )),
            )}
            <th scope="col" className={thClass}>
              Mejor F1
            </th>
          </tr>
        </thead>
        <tbody>
          {first.fields.map((score, position) => {
            const other = second.fields[position];
            return (
              <tr key={score.field}>
                <td className={tdClass}>
                  <span className={keyFields.includes(score.field) ? "font-semibold" : ""}>
                    {fieldLabel(score.field)}
                  </span>
                </td>
                {[score, other].flatMap((item, side) =>
                  [item.precision, item.recall, item.f1].map((value, metric) => (
                    <td key={`${side}-${metric}`} className={`${tdClass} ${numericClass}`}>
                      {formatDecimal(value)}
                    </td>
                  )),
                )}
                <td className={`${tdClass} font-semibold`}>
                  {bestOf(score.f1, other.f1, run.engines)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </DataTable>
      <p className="text-caption text-body">
        P: precisión. R: exhaustividad. En negrita, los campos que deciden el motor. Medido con{" "}
        {first.samples} referencias reales.
      </p>
      <ul className="flex flex-col text-caption text-body">
        {run.engines.map((engine) => (
          <li key={engine.engine}>
            Versión de {ENGINE_NAMES[engine.engine]}: {engine.version ?? "no disponible"}
          </li>
        ))}
      </ul>
    </div>
  );
}

function f1Of(run: BenchmarkRun, position: number): string {
  const engine = run.engines[position];
  return engine ? formatDecimal(engine.keyF1) : "—";
}

/** Mediciones anteriores: permiten ver si un cambio en un motor empeoró la extracción. */
function RunHistory({ runs }: { runs: BenchmarkRun[] }) {
  return (
    <section aria-labelledby="titulo-historial" className="flex flex-col gap-3">
      <h3 id="titulo-historial" className="text-small font-semibold tracking-normal text-ink">
        Mediciones anteriores
      </h3>
      <DataTable caption="Mediciones anteriores del benchmark">
        <thead className={tableHeadClass}>
          <tr>
            <th scope="col" className={thClass}>
              Fecha
            </th>
            <th scope="col" className={`${thClass} ${numericClass}`}>
              F1 medio AnyStyle
            </th>
            <th scope="col" className={`${thClass} ${numericClass}`}>
              F1 medio spaCy
            </th>
            <th scope="col" className={thClass}>
              Motor seleccionado
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.executedAt}>
              <td className={tdClass}>{formatDateTime(run.executedAt)}</td>
              <td className={`${tdClass} ${numericClass}`}>{f1Of(run, 0)}</td>
              <td className={`${tdClass} ${numericClass}`}>{f1Of(run, 1)}</td>
              <td className={tdClass}>{ENGINE_NAMES[run.selectedEngine]}</td>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </section>
  );
}

type BenchmarkViewProps = {
  overview: BenchmarkOverview;
  running: boolean;
  slow: boolean;
  runError: string | null;
  onRun: () => void;
};

/** Estándar de oro, resultados, motor en uso y regla de decisión (maqueta 18, HU-12). */
export function BenchmarkView({ overview, running, slow, runError, onRun }: BenchmarkViewProps) {
  const { goldSet, runs, engineInUse, keyFields } = overview;
  const [latest, ...previous] = runs;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-hairline bg-canvas px-5 py-3">
        <p className="flex flex-col text-small">
          <span className="font-semibold text-ink">
            Estándar de oro: {goldSet.total} referencias
          </span>
          <span>
            Se miden las {goldSet.real} reales ({goldSet.apa} APA · {goldSet.ieee} IEEE)
            {latest ? ` · última ejecución: ${formatDateTime(latest.executedAt)}` : ""}
          </span>
        </p>
        <button
          type="button"
          onClick={onRun}
          disabled={running}
          aria-busy={running}
          className={`${buttonStyles({ fullWidth: true })} md:w-auto`}
        >
          {running ? "Midiendo los motores…" : "Ejecutar benchmark"}
        </button>
      </div>

      <div aria-live="polite" className="flex flex-col gap-1 text-small empty:hidden">
        {slow ? <p>{SLOW_MESSAGE}</p> : null}
        {runError ? (
          <p role="alert" className="text-verdict-contradiction-text">
            {runError}
          </p>
        ) : null}
      </div>

      {latest ? (
        <>
          <StatRow>
            {latest.engines.map((engine) => (
              <StatCard
                key={engine.engine}
                value={formatDecimal(engine.keyF1)}
                label={`F1 medio · ${ENGINE_NAMES[engine.engine]}`}
              />
            ))}
            <StatCard value={ENGINE_NAMES[latest.selectedEngine]} label="Motor seleccionado" />
            <StatCard value={ENGINE_NAMES[engineInUse]} label="Motor en uso" />
          </StatRow>
          {latest.selectedEngine !== engineInUse ? (
            <p role="status" className="text-small text-verdict-discrepancy-text">
              El análisis usa {ENGINE_NAMES[engineInUse]}, pero la última medición seleccionó{" "}
              {ENGINE_NAMES[latest.selectedEngine]}. Revisa la instalación de AnyStyle o la
              configuración del motor.
            </p>
          ) : null}
        </>
      ) : (
        <p className="text-small">
          Todavía no hay mediciones guardadas. Motor en uso: {ENGINE_NAMES[engineInUse]}. Ejecuta el
          benchmark para comparar los motores.
        </p>
      )}

      <DecisionRule overview={overview} latest={latest} />

      {latest ? (
        <>
          <BenchmarkChart engines={latest.engines} />
          <ScoresTable run={latest} keyFields={keyFields} />
        </>
      ) : null}
      {previous.length > 0 ? <RunHistory runs={previous} /> : null}
    </div>
  );
}

/** Carga el panel y muestra el motivo si no está disponible. */
export function BenchmarkPanel() {
  const { state, slow, running, runError, run } = useBenchmark();

  if (state.kind === "loading") {
    return (
      <div className="flex flex-col gap-4">
        <p role="status" className="sr-only">
          Cargando el benchmark…
        </p>
        {slow ? <p className="text-small">{SLOW_MESSAGE}</p> : null}
        <Skeleton className="h-16 w-full rounded-card" />
        <StatRowSkeleton count={4} />
        <Skeleton className="h-40 w-full rounded-card" />
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <p role="alert" className="text-small text-verdict-contradiction-text">
        {state.message}
      </p>
    );
  }
  return (
    <BenchmarkView
      overview={state.overview}
      running={running}
      slow={slow}
      runError={runError}
      onRun={() => void run()}
    />
  );
}
