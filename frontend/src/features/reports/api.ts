import { apiGet } from "@/shared/lib/api-client";
import { isReportDto, toReport } from "./report-mapper";
import type { Report } from "./types";

export type ReportOutcome =
  | { kind: "ready"; report: Report }
  /** El análisis sigue en curso: el informe estará al terminar. */
  | { kind: "in_progress" }
  | { kind: "error"; message: string };

const NOT_FOUND = "No se encontró este informe. Vuelve a la lista de tus trabajos.";
const CONNECTION =
  "No se pudo conectar con el motor de análisis. Revisa tu conexión e intenta de nuevo.";
const SESSION = "No se pudo verificar tu sesión. Recarga la página e intenta de nuevo.";

/** Un texto del cuerpo JSON de la respuesta, si lo trae. */
function textIn(body: unknown, key: string): string | null {
  if (typeof body !== "object" || body === null) return null;
  const value: unknown = Reflect.get(body, key);
  return typeof value === "string" ? value : null;
}

/**
 * Informe completo de un análisis (HU-06). Si todavía no hay informe (409), se
 * consulta el estado para distinguir un análisis en curso de uno con error.
 */
export async function fetchReport(analysisId: string, onSlow: () => void): Promise<ReportOutcome> {
  const path = `/analisis/${encodeURIComponent(analysisId)}`;
  const response = await apiGet(`${path}/informe`, onSlow);
  if (response.kind === "failed") {
    return { kind: "error", message: response.reason === "session" ? SESSION : CONNECTION };
  }
  if (response.status === 200 && isReportDto(response.body)) {
    return { kind: "ready", report: toReport(response.body) };
  }
  if (response.status === 404 || response.status === 422) {
    return { kind: "error", message: NOT_FOUND };
  }
  if (response.status === 409) {
    const state = await apiGet(path);
    const body = state.kind === "response" && state.status === 200 ? state.body : null;
    if (textIn(body, "status") !== "error") return { kind: "in_progress" };
    return {
      kind: "error",
      message: textIn(body, "error_message") ?? textIn(response.body, "detail") ?? CONNECTION,
    };
  }
  return { kind: "error", message: textIn(response.body, "detail") ?? CONNECTION };
}
