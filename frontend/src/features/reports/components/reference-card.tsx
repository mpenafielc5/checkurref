import { VerdictBadge } from "@/shared/components/ui/verdict-badge";
import type { ExtractedField, NliResult, ReferenceResult } from "../types";

/** Color de cada campo extraído en el texto original (maqueta 12). */
const FIELD_CLASSES: Record<ExtractedField, string> = {
  authors: "text-info",
  year: "text-verdict-contradiction-text",
  title: "text-verdict-unsupported-text",
  container: "italic text-verdict-verified-text",
};

function NliBox({ nli }: { nli: NliResult }) {
  return (
    <aside className="flex flex-col gap-2 rounded-card bg-canvas px-4 py-3 text-small md:w-64">
      <p className="font-semibold text-ink">NLI · {nli.field}</p>
      <div aria-hidden="true" className="flex h-5 overflow-hidden rounded-row">
        <span className="bg-verdict-verified" style={{ flexGrow: nli.entailment }} />
        <span className="bg-verdict-unverifiable" style={{ flexGrow: nli.neutral }} />
        <span className="bg-verdict-contradiction" style={{ flexGrow: nli.contradiction }} />
      </div>
      <p className="text-verdict-verified-text">Implicación {nli.entailment} %</p>
      <p>Neutral {nli.neutral} %</p>
      <p className="text-verdict-contradiction-text">Contradicción {nli.contradiction} %</p>
    </aside>
  );
}

/** Tarjeta de una referencia: veredicto, texto, comparación y NLI. */
export function ReferenceCard({ reference }: { reference: ReferenceResult }) {
  return (
    <article className="flex flex-col gap-3 rounded-panel border border-hairline-strong bg-surface px-6 py-4">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="font-mono text-small text-body">[{reference.order}]</span>
        <VerdictBadge verdict={reference.verdict} />
        <span className="flex-1" />
        <p className="text-small">
          <span className="text-accent-text underline">Página {reference.page}</span>
          {reference.formatFindings > 0
            ? ` · ${reference.formatFindings} hallazgo de formato`
            : null}
        </p>
      </header>

      <p className="text-ink">
        {reference.segments.map((segment, index) =>
          segment.field ? (
            <span key={index} className={FIELD_CLASSES[segment.field]}>
              {segment.text}
            </span>
          ) : (
            <span key={index}>{segment.text}</span>
          ),
        )}
      </p>

      {reference.comparisons.length > 0 || reference.nli ? (
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          {reference.comparisons.length > 0 ? (
            <table className="flex-1 border-collapse text-small text-ink">
              <caption className="sr-only">Comparación con el registro de Crossref</caption>
              <thead className="bg-canvas text-left">
                <tr>
                  <th scope="col" className="px-3 py-1.5 font-semibold">
                    Campo
                  </th>
                  <th scope="col" className="px-3 py-1.5 font-semibold">
                    Referencia → registro
                  </th>
                  <th scope="col" className="px-3 py-1.5 font-semibold">
                    Estado
                  </th>
                </tr>
              </thead>
              <tbody>
                {reference.comparisons.map((row) => (
                  <tr key={row.label}>
                    <td className="px-3 py-1.5">{row.label}</td>
                    <td className="px-3 py-1.5">
                      {row.given} → {row.official}
                    </td>
                    <td
                      className={`px-3 py-1.5 ${
                        row.matches
                          ? "text-verdict-verified-text"
                          : "text-verdict-contradiction-text"
                      }`}
                    >
                      {row.matches ? "Coincide" : "Discrepancia"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {reference.nli ? <NliBox nli={reference.nli} /> : null}
        </div>
      ) : (
        <p className="text-small">
          No se encontró ninguna obra candidata en Crossref ni en OpenAlex. Revisa que la referencia
          exista: podría ser fabricada.
        </p>
      )}
    </article>
  );
}
