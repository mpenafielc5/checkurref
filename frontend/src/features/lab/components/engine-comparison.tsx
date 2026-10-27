import { buttonStyles } from "@/shared/components/ui/button-styles";
import type { EngineResult } from "../sample-data";

/** Salida de cada motor lado a lado para una referencia (maqueta 17). */
export function EngineComparison({
  reference,
  engines,
  agreement,
}: {
  reference: string;
  engines: EngineResult[];
  agreement: string;
}) {
  return (
    <div className="flex flex-col gap-4">
      <label className="flex flex-col gap-1.5 text-small">
        Referencia de prueba
        <textarea
          defaultValue={reference}
          rows={3}
          className="rounded-control border border-hairline-strong bg-surface px-4 py-3 text-small text-ink outline-none focus:border-ink"
        />
      </label>
      <div className="flex justify-end">
        <button type="button" disabled className={`${buttonStyles({ fullWidth: true })} md:w-auto`}>
          Comparar motores
        </button>
      </div>

      <div className="flex flex-col gap-4 md:flex-row">
        {engines.map((engine) => (
          <section
            key={engine.engine}
            aria-label={engine.engine}
            className="flex flex-1 flex-col gap-3 rounded-card border border-hairline bg-canvas px-5 py-4"
          >
            <header className="flex items-center justify-between gap-2">
              <h3 className="text-small font-semibold tracking-normal text-ink">{engine.engine}</h3>
              <span className="font-mono text-caption text-body">{engine.timeMs} ms</span>
            </header>
            <dl className="flex flex-col gap-2">
              {engine.fields.map((field) => (
                <div key={field.label} className="flex flex-col">
                  <dt className="font-mono text-caption text-muted uppercase">{field.label}</dt>
                  <dd
                    className={`text-small ${
                      field.missing ? "text-verdict-contradiction-text" : "text-ink"
                    }`}
                  >
                    {field.value}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>

      <p className="text-small font-semibold text-ink">Concordancia: {agreement}</p>
    </div>
  );
}
