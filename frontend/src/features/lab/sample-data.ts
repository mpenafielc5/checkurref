/* Datos de ejemplo de la maqueta 17. Los valores son ilustrativos: los reales llegan en HU-13. */

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
