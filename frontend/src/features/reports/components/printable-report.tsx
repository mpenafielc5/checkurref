"use client";

import { useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { formatDateTime, formatPercent } from "@/shared/lib/format";
import { INDEX_LEVELS, indexExplanation } from "@/shared/lib/truthfulness";
import { VERDICT_ORDER, VERDICTS } from "@/shared/lib/verdicts";
import { canCopyCorrected, printTitle, referenceText } from "../rules";
import type { ReferenceResult, Report } from "../types";

const UNVERIFIED = "Sin verificar";

/**
 * Fecha y hora de generación del informe impreso. Se actualiza justo antes de
 * imprimir (también con Ctrl + P), no solo al abrir la pantalla.
 */
function useGeneratedAt(): string {
  const [generatedAt, setGeneratedAt] = useState(() => new Date().toISOString());
  useEffect(() => {
    const update = () => flushSync(() => setGeneratedAt(new Date().toISOString()));
    window.addEventListener("beforeprint", update);
    return () => window.removeEventListener("beforeprint", update);
  }, []);
  return generatedAt;
}

/**
 * El navegador guarda el PDF con el título de la pestaña: mientras se imprime pasa
 * a "Informe CheckUrRef - <trabajo>" y luego vuelve al de siempre.
 */
function usePrintTitle(fileName: string): void {
  useEffect(() => {
    let previous = document.title;
    const set = () => {
      previous = document.title;
      document.title = printTitle(fileName);
    };
    const restore = () => {
      document.title = previous;
    };
    window.addEventListener("beforeprint", set);
    window.addEventListener("afterprint", restore);
    return () => {
      window.removeEventListener("beforeprint", set);
      window.removeEventListener("afterprint", restore);
    };
  }, [fileName]);
}

function Meta({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex gap-1.5">
      <dt className="font-semibold">{term}:</dt>
      <dd>{value}</dd>
    </div>
  );
}

function verdictName(reference: ReferenceResult): string {
  return reference.verdict ? VERDICTS[reference.verdict].label : UNVERIFIED;
}

function PrintedReference({ reference }: { reference: ReferenceResult }) {
  const differences = reference.comparisons.filter((row) => !row.matches);
  return (
    <li className="flex break-inside-avoid flex-col gap-1.5 border-t border-hairline pt-3 text-small">
      <p className="font-semibold">
        [{reference.order}] {verdictName(reference)}
        {reference.page !== null ? ` · Página ${reference.page}` : null}
      </p>
      <p className="wrap-anywhere">{referenceText(reference)}</p>
      {reference.notice ? <p>{reference.notice}</p> : null}
      {differences.length > 0 ? (
        <div className="flex flex-col gap-0.5">
          <p className="font-semibold">Diferencias con el registro</p>
          <ul className="flex flex-col gap-0.5">
            {differences.map((row) => (
              <li key={row.label} className="wrap-anywhere">
                {row.label}: «{row.given}» en la referencia; «{row.official}» en el registro.
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {reference.formatFindings.length > 0 ? (
        <div className="flex flex-col gap-0.5">
          <p className="font-semibold">Hallazgos de formato</p>
          <ul className="flex flex-col gap-0.5">
            {reference.formatFindings.map((finding) => (
              <li key={finding.message} className="wrap-anywhere">
                {finding.message} Dice «{finding.given}»; debería decir «{finding.expected}».
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {reference.corrected && canCopyCorrected(reference) ? (
        <div className="flex flex-col gap-0.5">
          <p className="font-semibold">Referencia corregida</p>
          <p className="wrap-anywhere">{reference.corrected.text}</p>
        </div>
      ) : null}
    </li>
  );
}

/**
 * Versión del informe para imprimir o guardar en PDF (HU-15). Solo aparece al
 * imprimir: trae todas las referencias, sin filtro ni páginas, y escribe el
 * nombre de cada veredicto para que se distinga sin color en blanco y negro.
 */
export function PrintableReport({ report }: { report: Report }) {
  const generatedAt = useGeneratedAt();
  usePrintTitle(report.fileName);
  const counted = VERDICT_ORDER.filter((verdict) => report.counts[verdict] > 0);

  return (
    <article className="hidden flex-col gap-5 text-ink print:flex">
      <header className="flex flex-col gap-2 border-b border-hairline pb-3">
        <p className="font-mono text-caption tracking-label uppercase">
          CheckUrRef · Informe de veracidad
        </p>
        <h2 className="text-title font-semibold tracking-normal wrap-anywhere">
          {report.fileName}
        </h2>
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-small">
          <Meta term="Norma" value={report.standard} />
          {report.finishedAt ? (
            <Meta term="Análisis" value={formatDateTime(report.finishedAt)} />
          ) : null}
          <Meta term="Generado" value={formatDateTime(generatedAt)} />
        </dl>
      </header>

      <section aria-label="Resumen" className="flex flex-col gap-2 text-small">
        <p>
          <span className="font-semibold">Índice de veracidad:</span>{" "}
          {report.index !== null
            ? `${formatPercent(report.index)}${
                report.indexLevel ? ` (${INDEX_LEVELS[report.indexLevel].label.toLowerCase()})` : ""
              }. ${indexExplanation(report.counts)}`
            : "sin referencias que contar"}
        </p>
        <ul className="flex flex-wrap gap-x-6 gap-y-1">
          {counted.map((verdict) => (
            <li key={verdict}>
              {VERDICTS[verdict].label}: {report.counts[verdict]}
            </li>
          ))}
          {report.queryErrors > 0 ? (
            <li>
              {UNVERIFIED}: {report.queryErrors}
            </li>
          ) : null}
        </ul>
        {report.standardNotice ? <p>{report.standardNotice}</p> : null}
      </section>

      <ol aria-label="Referencias" className="flex flex-col gap-3">
        {report.references.map((reference) => (
          <PrintedReference key={reference.order} reference={reference} />
        ))}
      </ol>
    </article>
  );
}
