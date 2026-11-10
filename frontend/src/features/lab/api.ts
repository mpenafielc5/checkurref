import { apiGet, apiPost } from "@/shared/lib/api-client";
import { detailOf } from "@/shared/lib/pdf-upload";
import { toBenchmarkOverview } from "./benchmark-mapper";
import { toLabComparison } from "./comparison-mapper";
import type { BenchmarkOverview, LabComparison } from "./types";

const SESSION_ERROR = "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo.";
const LOAD_ERROR = "No se pudo cargar el benchmark. Intenta de nuevo en unos minutos.";
const COMPARE_ERROR = "No se pudo comparar los motores. Intenta de nuevo en unos minutos.";
const RUN_ERROR = "No se pudo ejecutar el benchmark. Intenta de nuevo en unos minutos.";

export type BenchmarkOutcome =
  { kind: "ready"; overview: BenchmarkOverview } | { kind: "error"; message: string };

function outcomeOf(
  response: Awaited<ReturnType<typeof apiGet>>,
  fallback: string,
): BenchmarkOutcome {
  if (response.kind === "failed") {
    return { kind: "error", message: response.reason === "session" ? SESSION_ERROR : fallback };
  }
  const overview = response.status === 200 ? toBenchmarkOverview(response.body) : null;
  if (overview) return { kind: "ready", overview };
  // Una medición rechazada (409, por ejemplo sin AnyStyle) llega con su motivo.
  return { kind: "error", message: detailOf(response.body) ?? fallback };
}

export async function fetchBenchmark(onSlow: () => void): Promise<BenchmarkOutcome> {
  return outcomeOf(await apiGet("/laboratorio/benchmark", onSlow), LOAD_ERROR);
}

export async function runBenchmark(onSlow: () => void): Promise<BenchmarkOutcome> {
  return outcomeOf(await apiPost("/laboratorio/benchmark", {}, onSlow), RUN_ERROR);
}

export type ComparisonOutcome =
  { kind: "ready"; comparison: LabComparison } | { kind: "error"; message: string };

/** Salida de cada motor para una referencia (HU-13). */
export async function compareEngines(
  reference: string,
  onSlow: () => void,
): Promise<ComparisonOutcome> {
  const response = await apiPost("/laboratorio/comparar", { reference }, onSlow);
  if (response.kind === "failed") {
    return {
      kind: "error",
      message: response.reason === "session" ? SESSION_ERROR : COMPARE_ERROR,
    };
  }
  const comparison = response.status === 200 ? toLabComparison(response.body) : null;
  return comparison ? { kind: "ready", comparison } : { kind: "error", message: COMPARE_ERROR };
}
