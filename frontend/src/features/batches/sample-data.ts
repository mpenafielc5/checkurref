/*
 * Datos de ejemplo de las maquetas 14 y 16. Se reemplazan por datos reales en
 * HU-09 (tablero) y HU-18 (estadísticas).
 */
import type { BatchWork } from "./types";

export const SAMPLE_TEACHER_STATS = {
  activeBatches: "3",
  works: "64",
  verified: "73 %",
  alerts: "11",
};

export const SAMPLE_BATCH_DETAIL = {
  id: "is-7a",
  name: "Ingeniería de Software 7A · Avance 2",
  stats: { works: "28", references: "1046", verified: "71 %", alerts: "9" },
  // Todos suben el archivo con el nombre de la tarea: por eso se muestran los autores.
  works: [
    {
      analysisId: "a7f3",
      fileName: "Avance 2.pdf",
      authors: ["Andrea Vera", "Carlos Mendoza"],
      references: 41,
      index: 58,
      alerts: 6,
      risk: "alto",
    },
    {
      analysisId: "b3k1",
      fileName: "avance2_final.pdf",
      authors: [],
      references: 29,
      index: 71,
      alerts: 3,
      risk: "medio",
    },
    {
      analysisId: "c8m2",
      fileName: "Avance 2.pdf",
      authors: ["Lucía Salas"],
      references: 35,
      index: 77,
      alerts: 2,
      risk: "medio",
    },
    {
      analysisId: "d1p5",
      fileName: "Avance_2_grupo3.pdf",
      authors: ["Diego Paredes", "Ana Quiroz", "Mateo Ñauta"],
      references: 22,
      index: 93,
      alerts: 0,
      risk: "bajo",
    },
    {
      analysisId: "e6r9",
      fileName: "Avance 2.pdf",
      authors: ["Valeria Cedeño"],
      references: 30,
      index: 95,
      alerts: 0,
      risk: "bajo",
    },
  ] satisfies BatchWork[],
};
