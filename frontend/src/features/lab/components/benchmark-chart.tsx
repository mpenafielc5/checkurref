import { formatDecimal } from "@/shared/lib/format";
import { fieldLabel } from "@/shared/lib/reference-fields";
import { ENGINE_NAMES, type EngineId, type EngineScores } from "../types";

/** El color sigue al motor: el mismo en la leyenda y en todas las filas. */
const ENGINE_BARS: Record<EngineId, string> = {
  anystyle: "bg-engine-anystyle",
  spacy: "bg-engine-spacy",
};

const AXIS_TICKS = [0, 0.5, 1];
/** Mismo ancho en el nombre del campo y en el eje, para que el cero quede alineado. */
const LABEL_WIDTH = "w-20 shrink-0 md:w-32";

/** F1 de cada motor por campo, en barras con una escala común de 0 a 1 (HU-12 CA05). */
export function BenchmarkChart({ engines }: { engines: EngineScores[] }) {
  const fields = engines[0]?.fields.map((item) => item.field) ?? [];
  const f1Of = (engine: EngineScores, field: string) =>
    engine.fields.find((item) => item.field === field)?.f1 ?? 0;

  return (
    <figure className="flex flex-col gap-3 rounded-card border border-hairline bg-canvas px-5 py-4">
      <figcaption className="flex flex-col gap-2">
        <span className="text-small font-semibold text-ink">F1 por campo de cada motor</span>
        <span className="flex flex-wrap gap-4 text-caption text-body">
          {engines.map((engine) => (
            <span key={engine.engine} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`size-3 rounded-row ${ENGINE_BARS[engine.engine]}`}
              />
              {ENGINE_NAMES[engine.engine]}
            </span>
          ))}
        </span>
      </figcaption>

      {/* Los valores exactos están en la tabla de abajo, también para lectores de pantalla. */}
      <div aria-hidden="true" className="flex flex-col gap-2">
        {fields.map((field) => (
          <div key={field} className="flex items-center gap-3">
            <span className={`${LABEL_WIDTH} text-caption text-body`}>{fieldLabel(field)}</span>
            <span className="flex flex-1 flex-col gap-0.5 border-l border-hairline-strong">
              {engines.map((engine) => {
                const f1 = f1Of(engine, field);
                return (
                  <span
                    key={engine.engine}
                    title={`${ENGINE_NAMES[engine.engine]} · ${fieldLabel(field)}: F1 ${formatDecimal(f1)}`}
                    className={`h-3 rounded-r-row ${ENGINE_BARS[engine.engine]}`}
                    style={{ width: `${f1 * 100}%` }}
                  />
                );
              })}
            </span>
          </div>
        ))}
        <div className="flex gap-3 text-caption text-muted">
          <span className={LABEL_WIDTH} />
          <span className="flex flex-1 justify-between">
            {AXIS_TICKS.map((tick) => (
              <span key={tick}>{formatDecimal(tick, tick === 0.5 ? 1 : 0)}</span>
            ))}
          </span>
        </div>
      </div>
    </figure>
  );
}
