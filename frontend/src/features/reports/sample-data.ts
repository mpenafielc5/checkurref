/*
 * Informe de ejemplo de la maqueta 12. Se reemplaza por el informe real de la
 * API en HU-06.
 */
import type { Report } from "./types";

export const SAMPLE_REPORT: Report = {
  analysisId: "a7f3",
  fileName: "Avance_cap2_v3.pdf",
  standard: "APA",
  index: 82,
  counts: {
    verificada: 24,
    discrepancia: 5,
    contradiccion: 1,
    sin_respaldo: 2,
    no_verificable: 2,
  },
  references: [
    {
      order: 7,
      verdict: "discrepancia",
      page: 12,
      formatFindings: 1,
      segments: [
        { text: "Pérez, M. y López, J.", field: "authors" },
        { text: " " },
        { text: "(2021)", field: "year" },
        { text: ". " },
        { text: "Redes neuronales en la educación superior", field: "title" },
        { text: ". " },
        { text: "Revista Ciencia y Tecnología", field: "container" },
        { text: ", 14(2), 45–60." },
      ],
      comparisons: [
        { label: "Año", given: "2021", official: "2019", matches: false },
        {
          label: "Título",
          given: "Redes neuronales…",
          official: "Redes neuronales…",
          matches: true,
        },
        { label: "Autores", given: "Pérez, López", official: "Pérez, López", matches: true },
      ],
      nli: { field: "título", entailment: 91, neutral: 7, contradiction: 2 },
    },
    {
      order: 11,
      verdict: "verificada",
      page: 13,
      formatFindings: 0,
      segments: [
        { text: "Rivas, A.", field: "authors" },
        { text: " " },
        { text: "(2020)", field: "year" },
        { text: ". " },
        { text: "Evaluación formativa en entornos virtuales", field: "title" },
        { text: ". " },
        { text: "Revista Educación Digital", field: "container" },
        { text: ", 8(1), 10–22." },
      ],
      comparisons: [
        { label: "Año", given: "2020", official: "2020", matches: true },
        {
          label: "Título",
          given: "Evaluación formativa…",
          official: "Evaluación formativa…",
          matches: true,
        },
        { label: "Autores", given: "Rivas", official: "Rivas", matches: true },
      ],
      nli: { field: "título", entailment: 96, neutral: 3, contradiction: 1 },
    },
    {
      order: 10,
      verdict: "sin_respaldo",
      page: 13,
      formatFindings: 0,
      segments: [
        { text: "Moreira, L.", field: "authors" },
        { text: " " },
        { text: "(2022)", field: "year" },
        { text: ". " },
        { text: "Inteligencia artificial y aprendizaje autónomo", field: "title" },
        { text: ". " },
        { text: "Revista Andina de Pedagogía", field: "container" },
        { text: ", 3(2), 77–90." },
      ],
      comparisons: [],
      nli: null,
    },
  ],
};
