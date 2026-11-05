/*
 * Datos de ejemplo de la maqueta 11. Se reemplazan por datos reales en HU-05
 * (progreso).
 */
import type { ProgressStep } from "./types";

export const SAMPLE_PROGRESS = {
  fileName: "Ensayo_metodologia.pdf",
  standard: "APA",
  verified: 12,
  total: 34,
  steps: [
    { title: "Subido", detail: "2,4 MB · 14 páginas", state: "done" },
    { title: "Texto extraído", detail: "Sección “Referencias” en la página 12", state: "done" },
    {
      title: "34 referencias detectadas",
      detail: "Campos separados con AnyStyle y formato revisado",
      state: "done",
    },
    {
      title: "Verificando con Crossref, OpenAlex y NLI",
      detail: "12 de 34 referencias",
      state: "current",
    },
    { title: "Informe listo", detail: "Pendiente", state: "pending" },
  ] satisfies ProgressStep[],
  latest: [
    { label: "[12] Pérez y López (2021)", verdict: "discrepancia" },
    { label: "[11] Rivas (2020)", verdict: "verificada" },
    { label: "[10] Moreira (2022)", verdict: "sin_respaldo" },
  ] as const,
};
