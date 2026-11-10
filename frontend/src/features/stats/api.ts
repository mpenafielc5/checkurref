import { apiGet } from "@/shared/lib/api-client";
import { toStatistics } from "./statistics-mapper";
import type { Statistics } from "./types";

const SESSION_ERROR = "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo.";
const LOAD_ERROR = "No se pudieron cargar las estadísticas. Intenta de nuevo en unos minutos.";

export type StatisticsOutcome =
  { kind: "ready"; statistics: Statistics } | { kind: "error"; message: string };

/** Las cifras del rol de la sesión: la API no permite pedir las de otra cuenta. */
export async function fetchStatistics(onSlow: () => void): Promise<StatisticsOutcome> {
  const response = await apiGet("/estadisticas", onSlow);
  if (response.kind === "failed") {
    return { kind: "error", message: response.reason === "session" ? SESSION_ERROR : LOAD_ERROR };
  }
  const statistics = response.status === 200 ? toStatistics(response.body) : null;
  return statistics ? { kind: "ready", statistics } : { kind: "error", message: LOAD_ERROR };
}
