import { formatDecimal } from "@/shared/lib/format";
import { fieldLabel } from "@/shared/lib/reference-fields";
import { ENGINE_NAMES, type EngineId, type EngineScores } from "../types";

/** El color sigue al motor: el mismo en la leyenda y en todas las filas. */
const ENGINE_DOTS: Record<EngineId, string> = {
  anystyle: "bg-engine-anystyle",
  spacy: "bg-engine-spacy",
};

/** Mismo ancho en el nombre del campo y en el eje, para que la escala quede alineada. */
const LABEL_WIDTH = "w-20 shrink-0 md:w-32";

/** Con dos motores en el mismo valor, cada punto se corre a un lado para que se vean ambos. */
const TIED_OFFSET = ["-translate-x-full", "translate-x-0"];
const CENTERED = "-translate-x-1/2";

/** Escala de 0,5 a 1 cuando todos los valores caben; de lo contrario, de 0 a 1. */
function axisFor(values: number[]): { min: number; ticks: number[] } {
  const min = values.every((value) => value >= 0.5) ? 0.5 : 0;
  const step = min === 0.5 ? 0.1 : 0.2;
  const count = Math.round((1 - min) / step);
  return {
    min,
    ticks: Array.from({ length: count + 1 }, (_, index) => Number((min + index * step).toFixed(1))),
  };
}

/**
 * F1 de cada motor por campo (HU-12 CA05). Cada fila une los dos valores, de modo que la
 * distancia entre los puntos muestra cuánto difieren los motores en ese campo.
 */
export function BenchmarkChart({
  engines,
  keyFields,
}: {
  engines: EngineScores[];
  keyFields: string[];
}) {
  const fields = engines[0]?.fields.map((item) => item.field) ?? [];
  const f1Of = (engine: EngineScores, field: string) =>
    engine.fields.find((item) => item.field === field)?.f1 ?? 0;

  const axis = axisFor(engines.flatMap((engine) => engine.fields.map((item) => item.f1)));
  const position = (value: number) => ((value - axis.min) / (1 - axis.min)) * 100;
  const percent = (value: number) => `${value.toFixed(2)}%`;

  return (
    <figure className="flex flex-col gap-3 rounded-card border border-hairline bg-canvas px-5 py-4">
      <figcaption className="flex flex-col gap-2">
        <span className="text-small font-semibold text-ink">F1 por campo de cada motor</span>
        <span className="text-caption text-body">
          Un valor más alto indica mejor desempeño. En negrita, los campos de la regla de decisión.
        </span>
        <span className="flex flex-wrap gap-4 text-caption text-body">
          {engines.map((engine) => (
            <span key={engine.engine} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`size-3 rounded-pill ${ENGINE_DOTS[engine.engine]}`}
              />
              {ENGINE_NAMES[engine.engine]}
            </span>
          ))}
        </span>
      </figcaption>

      {/* Los valores exactos están en la tabla de abajo, también para lectores de pantalla. */}
      <div aria-hidden="true" className="flex flex-col">
        {fields.map((field) => {
          const values = engines.map((engine) => f1Of(engine, field));
          const low = Math.min(...values);
          const high = Math.max(...values);
          const tied = high - low < 0.005;
          return (
            <div
              key={field}
              title={`${fieldLabel(field)}: ${engines
                .map(
                  (engine) =>
                    `${ENGINE_NAMES[engine.engine]} ${formatDecimal(f1Of(engine, field))}`,
                )
                .join(" · ")}`}
              className="flex items-center gap-3"
            >
              <span
                className={`${LABEL_WIDTH} text-caption ${
                  keyFields.includes(field) ? "font-semibold text-ink" : "text-body"
                }`}
              >
                {fieldLabel(field)}
              </span>
              <span className="relative min-h-8 flex-1 self-stretch">
                {axis.ticks.map((tick) => (
                  <span
                    key={tick}
                    className="absolute inset-y-0 w-px bg-hairline"
                    style={{ left: percent(position(tick)) }}
                  />
                ))}
                <span
                  className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-hairline-strong"
                  style={{
                    left: percent(position(low)),
                    width: percent(position(high) - position(low)),
                  }}
                />
                {engines.map((engine, index) => (
                  <span
                    key={engine.engine}
                    data-testid={`${engine.engine}-${field}`}
                    className={`absolute top-1/2 size-3 -translate-y-1/2 rounded-pill ring-2 ring-canvas ${
                      tied ? (TIED_OFFSET[index] ?? CENTERED) : CENTERED
                    } ${ENGINE_DOTS[engine.engine]}`}
                    style={{ left: percent(position(f1Of(engine, field))) }}
                  />
                ))}
              </span>
            </div>
          );
        })}
        <div className="flex gap-3 pt-1 text-caption text-muted">
          <span className={LABEL_WIDTH} />
          <span className="relative h-5 flex-1">
            {axis.ticks.map((tick) => (
              <span
                key={tick}
                className="absolute -translate-x-1/2 tabular-nums"
                style={{ left: percent(position(tick)) }}
              >
                {formatDecimal(tick, 1)}
              </span>
            ))}
          </span>
        </div>
      </div>
    </figure>
  );
}
