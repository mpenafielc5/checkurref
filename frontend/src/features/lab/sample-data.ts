/*
 * Datos de ejemplo de las maquetas 17 y 18. Los valores son ilustrativos: los
 * reales salen del benchmark contra el estándar de oro (HU-12 y HU-13).
 */

export type EngineField = { label: string; value: string; missing?: boolean };

export type EngineResult = {
  engine: string;
  timeMs: number;
  fields: EngineField[];
};

export const SAMPLE_REFERENCE =
  "Pérez, M. y López, J. (2021). Redes neuronales en la educación superior. Revista Ciencia y Tecnología, 14(2), 45–60.";

export const SAMPLE_ENGINES: EngineResult[] = [
  {
    engine: "AnyStyle (CRF)",
    timeMs: 12,
    fields: [
      { label: "autor", value: "Pérez, M.; López, J." },
      { label: "año", value: "2021" },
      { label: "título", value: "Redes neuronales en la educación superior" },
      { label: "revista", value: "Revista Ciencia y Tecnología" },
    ],
  },
  {
    engine: "spaCy + reglas",
    timeMs: 48,
    fields: [
      { label: "autor", value: "Pérez, M.; López, J." },
      { label: "año", value: "2021" },
      { label: "título", value: "Redes neuronales (incompleto)", missing: true },
      { label: "revista", value: "No detectada", missing: true },
    ],
  },
];

export const SAMPLE_AGREEMENT = "2 de 4 campos";

export const SAMPLE_BENCHMARK = {
  goldSet: "150 referencias",
  goldDetail: "100 APA · 50 IEEE · última ejecución: 9 oct 2026",
  summary: [
    { value: "0,93", label: "F1 medio · AnyStyle" },
    { value: "0,75", label: "F1 medio · spaCy" },
    { value: "12 / 48 ms", label: "Tiempo medio por referencia" },
  ],
  rows: [
    { field: "Autores", anystyle: 0.94, spacy: 0.81 },
    { field: "Año", anystyle: 0.98, spacy: 0.95 },
    { field: "Título", anystyle: 0.89, spacy: 0.62 },
    { field: "Revista", anystyle: 0.86, spacy: 0.48 },
    { field: "DOI", anystyle: 0.97, spacy: 0.9 },
  ],
};
