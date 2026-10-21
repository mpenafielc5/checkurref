/*
 * Datos de ejemplo de las maquetas 10, 11 y 13. Se reemplazan por datos de
 * Supabase en HU-04 (subida), HU-05 (progreso) y HU-07 (historial).
 */
import type { ProgressStep, WorkVersion } from "./types";

export const SAMPLE_WORKS: WorkVersion[] = [
  {
    analysisId: "a7f3",
    fileName: "Avance_cap2.pdf",
    version: 3,
    date: "08/10/2026",
    references: 34,
    index: 82,
    status: "listo",
  },
  {
    analysisId: "e2b9",
    fileName: "Ensayo_metodologia.pdf",
    version: 1,
    date: "10/10/2026",
    references: 20,
    index: null,
    status: "en_proceso",
    verified: 12,
  },
  {
    analysisId: "a5c1",
    fileName: "Avance_cap2.pdf",
    version: 2,
    date: "01/10/2026",
    references: 33,
    index: 64,
    status: "listo",
  },
  {
    analysisId: "a2d8",
    fileName: "Avance_cap2.pdf",
    version: 1,
    date: "24/09/2026",
    references: 30,
    index: 51,
    status: "listo",
  },
];

export const SAMPLE_RECENT_WORKS = SAMPLE_WORKS.slice(0, 2);

export const SAMPLE_VERSION_COMPARISON = {
  title: "Avance_cap2 · v2 → v3",
  latestAnalysisId: "a7f3",
  indexBefore: 64,
  indexAfter: 82,
  resolved: "7 de 9",
  newFindings: "1",
};

export const SAMPLE_PROGRESS = {
  fileName: "Ensayo_metodologia.pdf",
  standard: "APA",
  verified: 12,
  total: 34,
  steps: [
    { title: "Subido", detail: "2,4 MB · 14 páginas", state: "done" },
    { title: "Texto extraído", detail: "Sección “Referencias” en la página 12", state: "done" },
    { title: "34 referencias detectadas", detail: "Campos separados con AnyStyle", state: "done" },
    { title: "Verificando con Crossref y NLI", detail: "12 de 34 referencias", state: "current" },
    { title: "Informe listo", detail: "Pendiente", state: "pending" },
  ] satisfies ProgressStep[],
  latest: [
    { label: "[12] Pérez y López (2021)", verdict: "discrepancia" },
    { label: "[11] Rivas (2020)", verdict: "verificada" },
    { label: "[10] Moreira (2022)", verdict: "sin_respaldo" },
  ] as const,
};

/** Ruta a la que lleva cada trabajo: informe si terminó, progreso si sigue. */
export function workHref(work: WorkVersion): string {
  return work.status === "listo"
    ? `/estudiante/trabajos/${work.analysisId}`
    : `/estudiante/trabajos/${work.analysisId}/progreso`;
}
