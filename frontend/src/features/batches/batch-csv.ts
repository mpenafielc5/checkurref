/*
 * Archivo CSV de los resultados del lote (HU-10). Excel decide cómo abrirlo por
 * dos cosas: la marca UTF-8 hace que respete las tildes y la ñ (CA02), y el punto
 * y coma es el separador de listas de la configuración regional de Ecuador.
 */
import { fieldLabel } from "@/shared/lib/reference-fields";
import { VERDICT_ORDER, VERDICTS } from "@/shared/lib/verdicts";
import type { BatchExport, ExportWork } from "./types";
import { ANALYSIS_FAILED } from "./upload-progress";

const UTF8_MARK = "﻿";
const SEPARATOR = ";";
const LINE_END = "\r\n";
const HEADERS = ["Autores", "Archivo", "N.º", "Referencia", "Veredicto", "Campos con diferencias"];
const NO_VERDICT = "Sin veredicto: una fuente no respondió";
const UNKNOWN_COVER = "Portada no reconocida";
const FALLBACK_NAME = "lote";

/**
 * Autores y archivos llegan de PDF de terceros: una celda que empieza con estos
 * signos Excel la ejecutaría como fórmula. El apóstrofo la deja como texto.
 */
const FORMULA_START = /^[=+\-@\t\r]/;

function cell(value: string): string {
  const flat = value.replace(/\s+/g, " ").trim();
  const safe = FORMULA_START.test(flat) ? `'${flat}` : flat;
  return /[";]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
}

function verdictLabel(verdict: string | null): string {
  const known = VERDICT_ORDER.find((item) => item === verdict);
  if (known) return VERDICTS[known].label;
  return verdict ?? NO_VERDICT;
}

/** Un trabajo sin referencias que informar también aparece: no debe faltar sin explicación. */
function statusLabel(work: ExportWork): string {
  if (work.status === "error") return `Error: ${work.errorMessage ?? ANALYSIS_FAILED}`;
  if (work.status === "completado") return "Sin referencias";
  return "En análisis";
}

function rowsOf(work: ExportWork): string[][] {
  const authors = work.authors.length > 0 ? work.authors.join(", ") : UNKNOWN_COVER;
  if (work.references.length === 0) {
    return [[authors, work.fileName, "", "", statusLabel(work), ""]];
  }
  return work.references.map((reference) => [
    authors,
    work.fileName,
    String(reference.order),
    reference.text,
    verdictLabel(reference.verdict),
    reference.differentFields.map(fieldLabel).join(", "),
  ]);
}

/** Una fila por referencia del lote (HU-10 CA01). */
export function buildBatchCsv(batch: BatchExport): string {
  const rows = [HEADERS, ...batch.works.flatMap(rowsOf)];
  return UTF8_MARK + rows.map((row) => row.map(cell).join(SEPARATOR)).join(LINE_END) + LINE_END;
}

/** "Metodología 5B · Ensayo" pasa a resultados-metodologia-5b-ensayo.csv. */
export function batchCsvFileName(batchName: string): string {
  const slug = batchName
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `resultados-${slug || FALLBACK_NAME}.csv`;
}
