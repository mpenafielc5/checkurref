/* Traduce la respuesta de /laboratorio/comparar (LabComparison del backend). */
import type { EngineId, EngineOutput, LabComparison } from "./types";

/** El orden de la tabla del backend: todos los motores muestran los campos igual. */
const FIELD_ORDER = [
  "autores",
  "anio",
  "titulo",
  "contenedor",
  "editorial",
  "volumen",
  "numero",
  "paginas",
  "doi",
];

type EngineOutputDto = {
  engine: EngineId;
  elapsed_ms: number;
  error: string | null;
  fields: Record<string, string | null> | null;
};

type LabComparisonDto = {
  engines: EngineOutputDto[];
  different_fields: string[];
  compared_fields: number;
  matching_fields: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isEngineOutputDto(value: unknown): value is EngineOutputDto {
  return (
    isRecord(value) &&
    (value.engine === "anystyle" || value.engine === "spacy") &&
    typeof value.elapsed_ms === "number" &&
    (value.fields === null || isRecord(value.fields))
  );
}

function isLabComparisonDto(body: unknown): body is LabComparisonDto {
  return (
    isRecord(body) &&
    Array.isArray(body.engines) &&
    body.engines.every(isEngineOutputDto) &&
    Array.isArray(body.different_fields) &&
    typeof body.compared_fields === "number" &&
    typeof body.matching_fields === "number"
  );
}

function toEngineOutput(dto: EngineOutputDto): EngineOutput {
  return {
    engine: dto.engine,
    elapsedMs: dto.elapsed_ms,
    error: dto.error ?? null,
    fields: dto.fields,
  };
}

/** La comparación; null si la respuesta no es la esperada. */
export function toLabComparison(body: unknown): LabComparison | null {
  if (!isLabComparisonDto(body)) return null;
  return {
    engines: body.engines.map(toEngineOutput),
    differentFields: body.different_fields,
    comparedFields: body.compared_fields,
    matchingFields: body.matching_fields,
  };
}

/** Campos que al menos un motor reconoció: los demás solo alargarían las tarjetas. */
export function comparedFieldsOf(comparison: LabComparison): string[] {
  return FIELD_ORDER.filter((field) =>
    comparison.engines.some((engine) => Boolean(engine.fields?.[field])),
  );
}
