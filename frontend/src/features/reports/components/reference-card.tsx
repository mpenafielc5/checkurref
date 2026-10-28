import { ChevronDown } from "lucide-react";
import { VerdictBadge } from "@/shared/components/ui/verdict-badge";
import type { Verdict } from "@/shared/lib/verdicts";
import { referenceText, startsCollapsed } from "../rules";
import type {
  ExtractedField,
  FieldComparison,
  FormatFinding,
  NliResult,
  ReferenceResult,
} from "../types";

/** Color de cada campo extraído en el texto original (maqueta 12). */
const FIELD_CLASSES: Record<ExtractedField, string> = {
  authors: "text-info",
  year: "text-verdict-contradiction-text",
  title: "text-verdict-unsupported-text",
  container: "italic text-verdict-verified-text",
};

/** Qué decir cuando no hay ninguna obra con la que comparar. */
function noMatchMessage(verdict: Verdict): string {
  return verdict === "no_verificable"
    ? "Crossref y OpenAlex no registran este tipo de obra, por lo que no fue posible comprobarla. Confirma los datos de la referencia en la obra original."
    : "No se encontró ninguna obra candidata en Crossref ni en OpenAlex. Revisa que la referencia exista: podría ser fabricada.";
}

function matchClass(matches: boolean): string {
  return matches ? "text-verdict-verified-text" : "text-verdict-contradiction-text";
}

function matchLabel(matches: boolean): string {
  return matches ? "Coincide" : "Discrepancia";
}

/** Comparación campo por campo en bloques apilados, para el celular. */
function ComparisonBlocks({ rows }: { rows: FieldComparison[] }) {
  return (
    <dl className="flex flex-col gap-2 text-small md:hidden">
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col gap-0.5 rounded-card bg-canvas px-4 py-2">
          <dt className="flex items-center justify-between gap-2">
            <span className="font-mono text-caption text-muted uppercase">{row.label}</span>
            <span className={`font-semibold ${matchClass(row.matches)}`}>
              {matchLabel(row.matches)}
            </span>
          </dt>
          <dd className="text-ink">
            <span className="text-body">En tu referencia:</span> {row.given}
          </dd>
          <dd className="text-ink">
            <span className="text-body">En el registro:</span> {row.official}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function findingsLabel(count: number): string {
  return `${count} ${count === 1 ? "hallazgo" : "hallazgos"} de formato`;
}

/** Cada problema de escritura: qué está mal, cómo aparece y cómo debería ir. */
function FormatFindings({ findings }: { findings: FormatFinding[] }) {
  return (
    <section
      aria-label={findingsLabel(findings.length)}
      className="flex flex-col gap-2 rounded-card bg-verdict-discrepancy-soft px-4 py-3 text-small"
    >
      <p className="font-mono text-caption text-verdict-discrepancy-text uppercase">
        {findingsLabel(findings.length)}
      </p>
      <ul className="flex flex-col gap-3">
        {findings.map((finding) => (
          <li key={finding.message} className="flex flex-col gap-0.5">
            <p className="font-semibold text-ink">{finding.message}</p>
            <p className="break-words text-ink">
              <span className="text-body">En tu referencia:</span> {finding.given}
            </p>
            <p className="break-words text-ink">
              <span className="text-body">Según la norma:</span> {finding.expected}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

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

/**
 * Tarjeta de una referencia: veredicto, texto, comparación y NLI. Es un
 * acordeón (details): las verificadas sin nada que corregir empiezan cerradas
 * en una sola línea, para que destaquen las que piden atención.
 */
export function ReferenceCard({ reference }: { reference: ReferenceResult }) {
  return (
    <article className="flex rounded-panel border border-hairline-strong bg-surface px-4 py-4 md:px-6">
      <details open={!startsCollapsed(reference)} className="group flex w-full flex-col">
        <summary className="flex list-none items-center gap-x-4 gap-y-2 group-open:flex-wrap [&::-webkit-details-marker]:hidden">
          <span className="font-mono text-small text-body">[{reference.order}]</span>
          <VerdictBadge verdict={reference.verdict} />
          {/* Cerrada: la referencia en una línea. Abierta: el texto completo va debajo. */}
          <span className="min-w-0 flex-1 truncate text-small text-body group-open:hidden">
            {referenceText(reference)}
          </span>
          <span className="hidden flex-1 group-open:block" />
          <span className="hidden text-small group-open:inline">
            <span className="text-accent-text underline">Página {reference.page}</span>
            {reference.formatFindings.length > 0
              ? ` · ${findingsLabel(reference.formatFindings.length)}`
              : null}
          </span>
          <ChevronDown
            aria-hidden="true"
            className="size-5 shrink-0 text-body transition-transform duration-(--cr-duration-fast) group-open:rotate-180"
          />
        </summary>

        <div className="flex flex-col gap-3 pt-3">
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

          {reference.formatFindings.length > 0 ? (
            <FormatFindings findings={reference.formatFindings} />
          ) : null}

          {reference.comparisons.length > 0 || reference.nli ? (
            <div className="flex flex-col gap-4 md:flex-row md:items-start">
              {reference.comparisons.length > 0 ? (
                <ComparisonBlocks rows={reference.comparisons} />
              ) : null}
              {reference.comparisons.length > 0 ? (
                <table className="hidden flex-1 border-collapse text-small text-ink md:table">
                  <caption className="sr-only">
                    Comparación con el registro de Crossref u OpenAlex
                  </caption>
                  <thead className="bg-canvas text-left">
                    <tr>
                      <th scope="col" className="px-3 py-1.5 font-semibold">
                        Campo
                      </th>
                      <th scope="col" className="px-3 py-1.5 font-semibold">
                        En tu referencia
                      </th>
                      <th scope="col" className="px-3 py-1.5 font-semibold">
                        En el registro
                      </th>
                      <th scope="col" className="px-3 py-1.5 font-semibold">
                        Estado
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Valores completos: un título largo baja de línea en vez de recortarse. */}
                    {reference.comparisons.map((row) => (
                      <tr key={row.label} className="align-top">
                        <td className="px-3 py-1.5 whitespace-nowrap">{row.label}</td>
                        <td className="px-3 py-1.5">{row.given}</td>
                        <td className="px-3 py-1.5">{row.official}</td>
                        <td className={`px-3 py-1.5 whitespace-nowrap ${matchClass(row.matches)}`}>
                          {matchLabel(row.matches)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
              {reference.nli ? <NliBox nli={reference.nli} /> : null}
            </div>
          ) : (
            <p className="text-small">{noMatchMessage(reference.verdict)}</p>
          )}
        </div>
      </details>
    </article>
  );
}
