/* Traduce la respuesta de /laboratorio/benchmark (BenchmarkOverview del backend). */
import type { BenchmarkOverview, BenchmarkRun, EngineId, EngineScores } from "./types";

type FieldScoreDto = { field: string; precision: number; recall: number; f1: number };

type EngineScoresDto = {
  engine: EngineId;
  version: string | null;
  samples: number;
  key_f1: number;
  fields: FieldScoreDto[];
};

type BenchmarkRunDto = {
  executed_at: string;
  engines: EngineScoresDto[];
  selected_engine: EngineId;
  tie: boolean;
  difference: number;
};

type BenchmarkOverviewDto = {
  gold_set: { total: number; real: number; apa: number; ieee: number };
  runs: BenchmarkRunDto[];
  engine_in_use: EngineId;
  key_fields: string[];
  tie_margin: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isEngineId(value: unknown): value is EngineId {
  return value === "anystyle" || value === "spacy";
}

function isFieldScoreDto(value: unknown): value is FieldScoreDto {
  return (
    isRecord(value) &&
    typeof value.field === "string" &&
    typeof value.precision === "number" &&
    typeof value.recall === "number" &&
    typeof value.f1 === "number"
  );
}

function isEngineScoresDto(value: unknown): value is EngineScoresDto {
  return (
    isRecord(value) &&
    isEngineId(value.engine) &&
    typeof value.key_f1 === "number" &&
    typeof value.samples === "number" &&
    Array.isArray(value.fields) &&
    value.fields.every(isFieldScoreDto)
  );
}

function isRunDto(value: unknown): value is BenchmarkRunDto {
  return (
    isRecord(value) &&
    typeof value.executed_at === "string" &&
    isEngineId(value.selected_engine) &&
    typeof value.tie === "boolean" &&
    typeof value.difference === "number" &&
    Array.isArray(value.engines) &&
    value.engines.every(isEngineScoresDto)
  );
}

function isOverviewDto(body: unknown): body is BenchmarkOverviewDto {
  return (
    isRecord(body) &&
    isRecord(body.gold_set) &&
    Array.isArray(body.runs) &&
    body.runs.every(isRunDto) &&
    isEngineId(body.engine_in_use) &&
    Array.isArray(body.key_fields) &&
    typeof body.tie_margin === "number"
  );
}

function toEngineScores(dto: EngineScoresDto): EngineScores {
  return {
    engine: dto.engine,
    version: dto.version ?? null,
    samples: dto.samples,
    keyF1: dto.key_f1,
    fields: dto.fields,
  };
}

function toRun(dto: BenchmarkRunDto): BenchmarkRun {
  return {
    executedAt: dto.executed_at,
    engines: dto.engines.map(toEngineScores),
    selectedEngine: dto.selected_engine,
    tie: dto.tie,
    difference: dto.difference,
  };
}

/** Lo que muestra el panel; null si la respuesta no es la esperada. */
export function toBenchmarkOverview(body: unknown): BenchmarkOverview | null {
  if (!isOverviewDto(body)) return null;
  return {
    goldSet: body.gold_set,
    runs: body.runs.map(toRun),
    engineInUse: body.engine_in_use,
    keyFields: body.key_fields,
    tieMargin: body.tie_margin,
  };
}
