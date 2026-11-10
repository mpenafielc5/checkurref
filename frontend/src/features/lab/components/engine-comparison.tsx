"use client";

import { useState, type FormEvent } from "react";
import { buttonStyles } from "@/shared/components/ui/button-styles";
import { fieldLabel } from "@/shared/lib/reference-fields";
import { compareEngines } from "../api";
import { comparedFieldsOf } from "../comparison-mapper";
import { ENGINE_LABELS, type EngineOutput, type LabComparison } from "../types";

/** Los mismos límites del backend: fuera de ellos ya no es una referencia. */
const MIN_REFERENCE_LENGTH = 10;
const MAX_REFERENCE_LENGTH = 2000;

const SLOW_MESSAGE = "Iniciando el motor de análisis; este proceso puede tardar hasta un minuto.";
const NOT_DETECTED = "No detectado";

type EngineCardProps = {
  output: EngineOutput;
  fields: string[];
  different: string[];
};

/** Salida de un motor. Sus campos van en el mismo orden que los del otro, para compararlos. */
function EngineCard({ output, fields, different }: EngineCardProps) {
  return (
    <section
      aria-label={ENGINE_LABELS[output.engine]}
      className="flex flex-1 flex-col gap-3 rounded-card border border-hairline bg-canvas px-5 py-4"
    >
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-small font-semibold tracking-normal text-ink">
          {ENGINE_LABELS[output.engine]}
        </h2>
        <span className="font-mono text-caption text-body">{output.elapsedMs} ms</span>
      </header>

      {output.fields ? null : (
        <p role="alert" className="text-small text-verdict-contradiction-text">
          Este motor no pudo procesar la referencia: {output.error}
        </p>
      )}

      {output.fields ? (
        <dl className="flex flex-col gap-2">
          {fields.map((field) => {
            const value = output.fields?.[field] ?? null;
            const differs = different.includes(field);
            return (
              <div
                key={field}
                className={`flex flex-col rounded-row px-2 py-1 ${differs ? "bg-verdict-discrepancy-soft" : ""}`}
              >
                <dt className="flex flex-wrap items-center justify-between gap-2 font-mono text-caption text-muted uppercase">
                  {fieldLabel(field)}
                  {differs ? (
                    <span className="font-semibold text-verdict-discrepancy-text">No coincide</span>
                  ) : null}
                </dt>
                <dd
                  className={`text-small break-words ${value ? "text-ink" : "text-muted italic"}`}
                >
                  {value ?? NOT_DETECTED}
                </dd>
              </div>
            );
          })}
        </dl>
      ) : null}
    </section>
  );
}

function concordanceOf(comparison: LabComparison): string {
  if (comparison.engines.some((engine) => !engine.fields)) {
    return "Sin el resultado de los dos motores no hay concordancia que calcular.";
  }
  if (comparison.comparedFields === 0) return "Ningún motor reconoció campos en este texto.";
  return `Concordancia: ${comparison.matchingFields} de ${comparison.comparedFields} campos`;
}

/** Campos de cada motor lado a lado, con los que no coinciden resaltados (HU-13). */
export function ComparisonResults({ comparison }: { comparison: LabComparison }) {
  const fields = comparedFieldsOf(comparison);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 md:flex-row">
        {comparison.engines.map((output) => (
          <EngineCard
            key={output.engine}
            output={output}
            fields={fields}
            different={comparison.differentFields}
          />
        ))}
      </div>
      <p className="text-small font-semibold text-ink">{concordanceOf(comparison)}</p>
    </div>
  );
}

/** Pega una referencia y compara la salida de AnyStyle y spaCy (maqueta 17). */
export function EngineComparison() {
  const [reference, setReference] = useState("");
  const [comparison, setComparison] = useState<LabComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [slow, setSlow] = useState(false);

  const canCompare = reference.trim().length >= MIN_REFERENCE_LENGTH && !comparing;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canCompare) return;
    setComparing(true);
    setSlow(false);
    setError(null);
    setComparison(null);
    const outcome = await compareEngines(reference.trim(), () => setSlow(true));
    setComparing(false);
    setSlow(false);
    if (outcome.kind === "ready") setComparison(outcome.comparison);
    else setError(outcome.message);
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-small">
          Referencia de prueba
          <textarea
            value={reference}
            name="referencia"
            autoComplete="off"
            rows={3}
            maxLength={MAX_REFERENCE_LENGTH}
            disabled={comparing}
            onChange={(event) => {
              setReference(event.target.value);
              // Un resultado solo vale para el texto con el que se obtuvo.
              setComparison(null);
              setError(null);
            }}
            placeholder="Ej.: Pérez, M. y López, J. (2021). Redes neuronales en la educación superior. Revista Ciencia y Tecnología, 14(2), 45–60."
            className="rounded-control border border-hairline-strong bg-surface px-4 py-3 text-small text-ink outline-none placeholder:text-muted focus:border-ink"
          />
        </label>
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!canCompare}
            aria-busy={comparing}
            className={`${buttonStyles({ fullWidth: true })} md:w-auto`}
          >
            {comparing ? "Comparando…" : "Comparar motores"}
          </button>
        </div>
      </form>

      <div aria-live="polite" className="flex flex-col gap-1 text-small empty:hidden">
        {slow ? <p>{SLOW_MESSAGE}</p> : null}
        {error ? (
          <p role="alert" className="text-verdict-contradiction-text">
            {error}
          </p>
        ) : null}
      </div>

      {comparison ? <ComparisonResults comparison={comparison} /> : null}
    </div>
  );
}
