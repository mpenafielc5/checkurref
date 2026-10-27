/*
 * Datos de ejemplo de las maquetas 14, 15 y 16. Se reemplazan por datos de
 * Supabase en HU-08 (lotes), HU-09 (tablero) y HU-10 (exportación).
 */
import type { BatchSummary, BatchUpload, BatchWork } from "./types";

export const SAMPLE_TEACHER_STATS = {
  activeBatches: "3",
  works: "64",
  verified: "73 %",
  alerts: "11",
};

export const SAMPLE_BATCHES: BatchSummary[] = [
  {
    id: "is-7a",
    name: "Ingeniería de Software 7A · Avance 2",
    works: 28,
    period: "2026-2S",
    status: { kind: "alerts", count: 9 },
  },
  {
    id: "met-5b",
    name: "Metodología 5B · Ensayo final",
    works: 20,
    period: "2026-2S",
    status: { kind: "analyzing", done: 14 },
  },
  {
    id: "tit-c2",
    name: "Titulación · Capítulo 2",
    works: 16,
    period: "2026-2S",
    status: { kind: "alerts", count: 2 },
  },
];

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

export const SAMPLE_NEW_BATCH_UPLOADS: BatchUpload[] = [
  { fileName: "Ensayo_Estudiante_A.pdf", sizeBytes: 1.8 * 1024 * 1024, state: { kind: "listo" } },
  {
    fileName: "Ensayo_Estudiante_B.pdf",
    sizeBytes: 2.3 * 1024 * 1024,
    state: { kind: "verificando", done: 8, total: 22 },
  },
  {
    fileName: "Ensayo_Estudiante_C.pdf",
    sizeBytes: 6.1 * 1024 * 1024,
    state: { kind: "error", reason: "PDF escaneado" },
  },
];
